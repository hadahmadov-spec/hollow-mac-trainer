"""Package the original PNG into all standard macOS icon representations."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def build_icon():
    source = ROOT / "assets/app-icon.png"
    target = ROOT / "assets/app-icon.icns"
    with tempfile.TemporaryDirectory(prefix="hollow-icon-") as directory:
        iconset = Path(directory) / "app.iconset"
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                pixels = size * scale
                suffix = "@2x" if scale == 2 else ""
                destination = iconset / f"icon_{size}x{size}{suffix}.png"
                subprocess.run(["sips", "-z", str(pixels), str(pixels),
                                str(source), "--out", str(destination)],
                               check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["iconutil", "-c", "icns", str(iconset),
                        "-o", str(target)], check=True)
    return target


if __name__ == "__main__":
    print(build_icon())
