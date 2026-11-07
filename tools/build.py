"""Reproduce the local macOS bundle; proprietary game assemblies are compile-only."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from build_icon import build_icon

ROOT = Path(__file__).resolve().parents[1]


def vendor():
    base = ROOT / "vendor"
    base.mkdir(exist_ok=True)
    for key, spec in json.loads((ROOT / "vendor-lock.json").read_text()).items():
        with urllib.request.urlopen(spec["url"], timeout=90) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != spec["sha256"]:
            raise RuntimeError(f"Checksum mismatch: {key}")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                name = Path(member.filename)
                if name.is_absolute() or ".." in name.parts:
                    raise RuntimeError("Unsafe archive path")
                if member.is_dir():
                    continue
                if key == "knight":
                    if name.name != "DebugMod.dll": continue
                    target = base / "knight/DebugMod" / name.name
                elif key == "i18n":
                    if member.filename != "lib/netstandard2.1/Silksong.I18N.dll": continue
                    target = base / "silksong/I18N/Silksong.I18N.dll"
                else:
                    target = base / key / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dotnet", default="dotnet")
    parser.add_argument("--game", type=Path, required=True, help="Path to hollow_knight.app")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.download: vendor()
    managed = args.game / "Contents/Resources/Data/Managed"
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    subprocess.run([args.dotnet, "build", "bridge/TrainerBridge.csproj", "-c", "Release",
                    f"-p:ManagedDir={managed}", f"-p:LoaderDir={ROOT / 'vendor/loader/BepInEx/core'}"], cwd=ROOT, env=env, check=True)
    shutil.copy2(ROOT / "bridge/bin/Release/netstandard2.1/HollowTrainerBridge.dll", ROOT / "vendor/HollowTrainerBridge.dll")
    icon = build_icon()
    subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "--windowed",
                    "--name", "Hollow Mac Trainer", "--osx-bundle-identifier", "local.hollowtrainer.app",
                    "--icon", str(icon),
                    "--add-data", "vendor:vendor", "main.py"], cwd=ROOT, check=True)


if __name__ == "__main__": main()
