# Hollow Mac Trainer

A separate Python/Qt macOS window for the native Steam editions of **Hollow Knight
1.5.12620** and **Hollow Knight: Silksong 1.0.30000**. No Windows executable or Wine.

Choose **English** or **Русский** in the sidebar; the language is saved automatically.
Labels, status messages and supported bridge diagnostics switch immediately.

Open the application, select a game and choose **Launch with mods**. Load a save;
the switches become available when the bridge reports a gameplay scene. Use Command-Tab
to move between the game and trainer. The launcher opens the game in a window; fullscreen
can be selected in the game's settings. Ordinary Steam launches remain unmodified.

## Controls

Both games: invincibility, infinite health, infinite soul/silk, infinite jumps,
unlimited dashes (requires the ability), attack cooldown removal, noclip, weapon damage,
game speed, movement speed and adding Geo/rosaries. Silksong also supports infinite tool
use and adding shell shards. This is not a conversion of the Windows trainer and does
not claim all of its 17 functions (crafting bypass and resource pickup multipliers are
not implemented).

Closing the trainer expires its lease within four seconds. The bridge restores values
it changed in the running game. Reset also restores those values. **This does not undo
saved progress**: currencies, damage and PlayerData cheat flags may be serialized by the
game while enabled. Every launch creates a verified save backup. Prefer a separate save
for experimenting; never restore a backup over newer progress without keeping a copy.

The application stores runtime files, logs, preferences and dated backups under
`~/Library/Application Support/Hollow Mac Trainer`. The game `.app` bundles and their
assemblies are never modified. Quit the games and trainer before removing its runtime
folder. A normal Steam launch works without the trainer.

## Build

Requires macOS, Python 3.13, .NET 8 SDK and a legally installed supported Hollow Knight
copy for compile-only Unity references. No proprietary game binaries are committed or
bundled. Install `requirements.txt` in a virtual environment, then run:

```text
python tools/build.py --download --game /path/to/hollow_knight.app
python -m unittest discover -s tests -v
```

The output is `dist/Hollow Mac Trainer.app`. The local bundle is ad-hoc signed, not
Apple-notarized. Qt packaging needs ordinary host access to detect ARM capabilities;
build tools running in a restrictive sandbox may omit the Cocoa plugin.

`vendor-lock.json` pins upstream archives by SHA-256. The small C# bridge has no network
listener or code-evaluation interface: it accepts allowlisted operations through atomic
local JSON files, bound to a process session with a short expiry. Unity operations run
on the main thread. Commands, especially currency additions, are never retried silently.

## Upstream components

- [BepInEx 5.4.23.6](https://github.com/BepInEx/BepInEx/releases/tag/v5.4.23.6)
- [Hollow Knight Unity 6 DebugMod](https://github.com/wzxnb2333/New.HK.Debug/releases/tag/v1.4.10.5-r2)
- [Silksong DebugMod 1.2.1](https://github.com/hk-speedrunning/Silksong.DebugMod/releases/tag/v1.2.1)
- Silksong Modlist 0.3.1 and I18N 1.1.1, distributed by their upstream maintainers.

The original components retain their own licenses. Downloaded binaries and build
artifacts are excluded from Git. See `VERIFICATION.md` for tested behavior and limits.
