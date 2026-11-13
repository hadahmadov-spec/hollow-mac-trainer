<p align="center">
  <img src="assets/app-icon.png" width="128" height="128" alt="Hollow Mac Trainer: the Knight and Hornet masks">
</p>

<h1 align="center">Hollow Mac Trainer</h1>

<p align="center"><strong>A macOS trainer for Hollow Knight &amp; Silksong</strong></p>
<p align="center">Standalone app · Native Steam games · English / Русский · No Wine</p>

Control cheats from a separate Mac app: infinite health, soul or silk, extra jumps,
game speed and more. Launch your installed game through Steam; the trainer connects
automatically when its bridge loads. The Steam wrapper backs up saves before launch.

**Tested versions:** Hollow Knight **1.5.12620** and Hollow Knight: Silksong
**1.0.30000** (native macOS Steam editions). An unofficial fan project.

## Getting started

Choose **English** or **Русский** in the sidebar; the language is saved automatically.
Labels, status messages and supported bridge diagnostics switch immediately.

Keep the trainer in a stable location, such as `~/Applications`. For each game, select
**Set up Steam**, copy the command, open the game's **Properties → General → Launch
Options** in Steam and paste it. Preserve existing game arguments after `%command%`;
do not combine this with a second launcher wrapper. The setup screen does not edit
Steam's live configuration files.

After this one-time setup, use Steam's normal **Play** button or **Open through Steam**
in the trainer. You can open the trainer before or after the game. Load a save to
enable the switches; use Command-Tab to move between the game and trainer. Window
size and fullscreen settings are left to the game. Steam owns the launch and game
lifetime, including its usual Cloud synchronization.

An already running game without the bridge needs one restart after setup; this is
not live injection into an unmodified process. Remove the launch option to disable
integration. If the trainer is moved or removed, update or remove that option first.
The displayed version comes from the installed game (or the connected bridge).
Other versions are not rejected solely by version number, but compatibility beyond
the tested versions above is unverified. A missing bridge is shown separately from
a game that is not running; launch failures are recorded in `steam-launch.json`.

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

Backups include the game's own restore-point files. The trainer never restores a
backup automatically or copies saved progress back into the game's save directory.

The application stores runtime files, logs, preferences and dated backups under
`~/Library/Application Support/Hollow Mac Trainer`. The game `.app` bundles and their
assemblies are never modified. Quit the games and trainer before removing its runtime
folder. Remove the Steam launch option before removing the trainer or its runtime.

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
