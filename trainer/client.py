"""File IPC, game discovery and launch. Never edits game assemblies or save data."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

GAMES = {
    "knight": {"title": "Hollow Knight", "appid": "367520", "folder": "Hollow Knight", "app": "hollow_knight.app", "version": "1.5.12620", "save": "unity.Team Cherry.Hollow Knight"},
    "silksong": {"title": "Silksong", "appid": "1030300", "folder": "Hollow Knight Silksong", "app": "Hollow Knight Silksong.app", "version": "1.0.30000", "save": "unity.Team-Cherry.Silksong"},
}
SUPPORT = Path.home() / "Library/Application Support/Hollow Mac Trainer"
ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "vendor"


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_status(folder: Path, now: float | None = None) -> dict | None:
    now = time.time() if now is None else now
    try:
        path = folder / "status.json"
        if path.stat().st_size > 16384:
            return None
        data = json.loads(path.read_text())
        age = now - data["timestamp"]
        if data.get("protocol") != 1 or not isinstance(data.get("session"), str) or not (-2 <= age < 3):
            return None
        if data.get("game") not in GAMES:
            return None
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


class Client:
    def __init__(self, game: str, support: Path = SUPPORT):
        self.game = game
        self.folder = support / "runtime" / game
        self.pending: tuple[str, str, float] | None = None
        self.error = ""
        self.session = None

    def poll(self) -> dict | None:
        state = read_status(self.folder)
        if not state or state["game"] != self.game:
            if self.pending:
                self.error = "Связь прервалась. Результат последнего действия неизвестен."
            self.pending = None
            return None
        if self.session and state["session"] != self.session:
            self.pending = None
            self.error = "Игра перезапущена; настройки не переносились."
        self.session = state["session"]
        atomic_json(self.folder / "lease.json", {"session": self.session, "timestamp": time.time()})
        if self.pending:
            request_id, session, start = self.pending
            if state.get("lastCommand") == request_id and state["session"] == session:
                self.pending = None
                self.error = state.get("error", "")
            elif time.time() - start > 6:
                self.pending = None
                self.error = "Нет подтверждения. Проверьте игру перед повторным действием."
        return state

    def send(self, operation: str, value: float = 0) -> None:
        if self.pending:
            raise RuntimeError("Дождитесь подтверждения предыдущего действия.")
        state = read_status(self.folder)
        if not state or state["game"] != self.game:
            raise RuntimeError("Запустите игру с модом.")
        if operation != "reset" and not state.get("ready"):
            raise RuntimeError("Загрузите сохранение и дождитесь управления героем.")
        identifier = uuid.uuid4().hex
        timestamp = time.time()
        atomic_json(self.folder / "lease.json", {"session": state["session"], "timestamp": timestamp})
        atomic_json(self.folder / "request.json", {"id": identifier, "session": state["session"], "created": timestamp, "operation": operation, "value": value})
        self.pending = identifier, state["session"], timestamp
        self.error = ""

    def close(self) -> None:
        # The bridge expires ownership within four seconds and restores temporary values.
        (self.folder / "lease.json").unlink(missing_ok=True)


def find_game(game: str, library: str = "") -> Path | None:
    roots = [Path(library)] if library else []
    roots += [Path("/Volumes/MyData/SteamLibrary"), Path.home() / "Library/Application Support/Steam"]
    folders = Path.home() / "Library/Application Support/Steam/steamapps/libraryfolders.vdf"
    if folders.exists():
        roots += [Path(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', folders.read_text())]
    for root in roots:
        candidate = root / "steamapps/common" / GAMES[game]["folder"] / GAMES[game]["app"]
        if candidate.is_dir():
            return candidate
    return None


def backup_saves(game: str, support: Path = SUPPORT) -> Path | None:
    source = Path.home() / "Library/Application Support" / GAMES[game]["save"]
    if not source.exists():
        return None
    destination = support / "backups" / game / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
    destination.mkdir(parents=True, mode=0o700)
    hashes = {}
    # Save files only, not potentially unbounded mod savestates or logs.
    folders = [source] + [p for p in source.iterdir() if p.is_dir() and p.name.isdigit() and not p.is_symlink()]
    for path in (p for folder in folders for p in folder.iterdir()):
        if not path.is_symlink() and path.is_file() and (".dat" in path.name or path.name == "steam_autocloud.vdf"):
            relative = path.relative_to(source)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copy2(path, target)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise RuntimeError("Не удалось проверить резервную копию сохранения.")
            hashes[str(relative)] = digest
    atomic_json(destination / "hashes.json", hashes)
    return destination


def prepare_runtime(game: str, support: Path = SUPPORT, assets: Path = ASSETS) -> Path:
    destination = support / "runtime" / game
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Only managed package files are copied; existing game files are untouched.
    for source in (assets / "loader").rglob("*"):
        if source.is_file():
            target = destination / source.relative_to(assets / "loader")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    plugins = destination / "BepInEx/plugins"
    shutil.copytree(assets / game, plugins, dirs_exist_ok=True)
    bridge = plugins / "HollowTrainerBridge"
    bridge.mkdir(exist_ok=True)
    shutil.copy2(assets / "HollowTrainerBridge.dll", bridge / "HollowTrainerBridge.dll")
    return destination


def launch(game: str, library: str = "") -> subprocess.Popen:
    import plistlib
    app = find_game(game, library)
    if not app:
        raise RuntimeError("Игра не найдена. Укажите папку SteamLibrary.")
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    actual = info.get("CFBundleShortVersionString", "")
    if actual != GAMES[game]["version"]:
        raise RuntimeError(f"Установлена версия {actual}; проверена {GAMES[game]['version']}. Нужна проверка совместимости.")
    executable = app / "Contents/MacOS" / info["CFBundleExecutable"]
    processes = subprocess.run(["/bin/ps", "-axo", "command="], capture_output=True, text=True, check=True).stdout
    if str(executable) in processes:
        raise RuntimeError("Игра уже запущена. Закройте её перед запуском с модом.")
    backup_saves(game)
    runtime = prepare_runtime(game)
    subprocess.run(["/usr/bin/open", "-g", "-a", "Steam"], check=True)
    environment = os.environ.copy()
    environment.update(SteamAppId=GAMES[game]["appid"], SteamGameId=GAMES[game]["appid"], HOLLOW_TRAINER_IPC=str(runtime))
    log = (runtime / "launch.log").open("w")
    try:
        return subprocess.Popen(["/bin/sh", str(runtime / "run_bepinex.sh"), str(app), "-screen-fullscreen", "0", "-screen-width", "1280", "-screen-height", "800", "-logFile", str(runtime / "unity.log")],
                                cwd=runtime, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        log.close()
