# Verification — 2026-11-07

Target: Apple Silicon Mac; native Steam Hollow Knight 1.5.12620 and Silksong 1.0.30000.

- 13 Python tests pass: session binding, malformed/stale status, duplicate suppression,
  acknowledgement/restart/disconnection, menu gating, lease revocation, library discovery,
  and backup of saves inside numeric Steam account folders.
- C# bridge builds with zero warnings/errors. Both upstream mods and bridge load natively.
- Runtime command suites passed: 22 acknowledged commands in Hollow Knight (new slot 4),
  25 in Silksong (new slot 2). Both checked toggle enable/disable, damage 5 → 15 → 5,
  movement 2× → original, game speed 1.5× → 1×, currency +7, explicit reset and lease expiry.
  Silksong additionally checked tools and shell shards +3. Currency updates are asynchronous.
- Independent review found HK reset could unpause the game via upstream component disposal.
  Disposal is now deferred. Explicit reset and lease expiry while paused were tested:
  paused remained true and Unity timeScale remained zero.
- Native Qt bundle inspected for game selection, connection/disabled controls, scrolling,
  labels and Russian text. Final package includes Cocoa platform plugin and is ad-hoc signed.
- HK original slot-1 files match the pre-test backup. Silksong slot-1 files were not loaded;
  their timestamps predate this session. Silksong backup discovery was corrected to include
  numeric account folders and a verified backup was then created.

## Limits

These are runtime smoke tests on early-game disposable slots, not a complete playthrough.
Late-game abilities, every enemy/scene transition, and interactions with other installed mods
have not been exhaustively tested. Dash still requires the unlocked ability. Tests verify
upstream cheat flags and live player values; they do not claim every combat combination.
The app refuses untested game versions. Cheats may be saved by the game; reset restores
current runtime settings, not older progress. Backups must not overwrite newer saves blindly.

Local test evidence is kept outside Git in /private/tmp/*-runtime-results.json and
/private/tmp/knight-pause-*.json. No game binaries or save files are published.
