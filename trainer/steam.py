"""Steam-owned game launch. Never restore saves or rewrite Steam configuration."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import time

from trainer.client import GAMES, SUPPORT, atomic_json, backup_saves, find_game, prepare_runtime


def app_details(game: str, library: str = "") -> tuple[Path, Path, str]:
    app = find_game(game, library)
    if app is None:
        raise RuntimeError("Игра не найдена. Укажите папку SteamLibrary.")
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    executable = app / "Contents/MacOS" / info["CFBundleExecutable"]
    return app, executable, info.get("CFBundleShortVersionString", "?")


def game_processes() -> dict[str, list[int]]:
    """Read executable names, not command arguments containing another app's path."""
    result = {game: [] for game in GAMES}
    lines = subprocess.run(["/bin/ps", "-axo", "pid=,comm="], check=True,
                           capture_output=True, text=True).stdout.splitlines()
    for line in lines:
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        for game, info in GAMES.items():
            if f"/{info['app']}/Contents/MacOS/" in parts[1]:
                result[game].append(int(parts[0]))
    return result


def launch_options(game: str) -> str:
    """A stable installed bundle acts as the Steam wrapper; no generated shell code."""
    if game not in GAMES:
        raise ValueError("Unknown game")
    if getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        command = [sys.executable, str(Path(__file__).resolve().parents[1] / "main.py")]
    # Steam's macOS launch-options syntax uses double quoted absolute paths.
    if any(any(c in part for c in '\n\r"`$') for part in command):
        raise RuntimeError("Путь тренера содержит неподдерживаемые символы.")
    return " ".join(f'"{part}"' for part in command) + f" --steam-launch {game} %command%"


def launch_via_steam(game: str, library: str = "") -> None:
    app_details(game, library)
    if game_processes()[game]:
        raise RuntimeError("Игра уже открыта. Тренер подключится автоматически, если модуль загружен.")
    subprocess.run(["/usr/bin/open", f"steam://rungameid/{GAMES[game]['appid']}"], check=True)


def _steam_app(game: str, command: list[str]) -> tuple[Path, list[str]]:
    if not command:
        raise RuntimeError("Steam не передал команду игры. Проверьте параметр %command%.")
    target = Path(command[0]).resolve()
    app = target if target.suffix == ".app" else next(
        (parent for parent in target.parents if parent.suffix == ".app"), None)
    if app is None or app.name != GAMES[game]["app"]:
        raise RuntimeError("Steam передал другую игру. Проверьте параметры запуска.")
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    executable = (app / "Contents/MacOS" / info["CFBundleExecutable"]).resolve()
    if target not in (app, executable) or not executable.is_file():
        raise RuntimeError("Не найден исполняемый файл игры Steam.")
    for key in ("SteamAppId", "SteamGameId"):
        if os.environ.get(key) not in (None, "", GAMES[game]["appid"]):
            raise RuntimeError("Идентификатор игры Steam не совпадает.")
    return app, command[1:]


def run_steam_game(game: str, command: list[str]) -> int:
    """Stay alive until the game exits so Steam owns playtime and cloud sync."""
    if game not in GAMES:
        raise ValueError("Unknown game")
    runtime = SUPPORT / "runtime" / game
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    result_path = runtime / "steam-launch.json"
    # Separate from app.lock: the GUI can open/close independently of the game.
    with (runtime / "steam-launch.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 1
        try:
            app, arguments = _steam_app(game, command)
            if game_processes()[game]:
                raise RuntimeError("Игра уже открыта. Второй экземпляр не запускается.")
            atomic_json(result_path, {"timestamp": time.time(), "phase": "preparing", "error": ""})
            backup = backup_saves(game)
            runtime = prepare_runtime(game)
            # An old request must never become a command in the next game session.
            for name in ("request.json", "lease.json", "status.json"):
                (runtime / name).unlink(missing_ok=True)
            environment = os.environ.copy()
            environment["HOLLOW_TRAINER_IPC"] = str(runtime)
            # PyInstaller's private Qt/Python library paths must not leak into Unity.
            for key in ("DYLD_LIBRARY_PATH", "LD_LIBRARY_PATH"):
                original = environment.pop(key + "_ORIG", None)
                environment.pop(key, None)
                if original:
                    environment[key] = original
            with (runtime / "launch.log").open("w") as log:
                process = subprocess.Popen(
                    ["/bin/sh", str(runtime / "run_bepinex.sh"), str(app), *arguments,
                     "-logFile", str(runtime / "unity.log")],
                    cwd=app.parent, env=environment, stdout=log, stderr=subprocess.STDOUT)
                atomic_json(result_path, {"timestamp": time.time(), "phase": "running",
                                          "pid": process.pid, "app": str(app),
                                          "backup": str(backup) if backup else None, "error": ""})
                code = process.wait()
            atomic_json(result_path, {"timestamp": time.time(), "phase": "exited", "exitCode": code,
                                      "error": "" if code == 0 else "Игра завершилась с ошибкой. Откройте журнал игры."})
            return code
        except Exception as error:
            atomic_json(result_path, {"timestamp": time.time(), "phase": "failed", "error": str(error)})
            return 1


def recent_launch(game: str) -> dict:
    try:
        data = json.loads((SUPPORT / "runtime" / game / "steam-launch.json").read_text())
        return data if 0 <= time.time() - data["timestamp"] < 180 else {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}
