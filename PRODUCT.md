# Hollow Mac Trainer

Personal, local desktop trainer for the native macOS Steam editions of Hollow Knight
1.5.12620 and Silksong 1.0.30000. The user requested a separate window with switches,
similar to the supplied FLiNG trainer screenshot, and explicitly rejected downgrading.

Python owns the macOS application, launch and backup logic. A small C# Unity bridge is
explicitly permitted by the owner. It drives existing DebugMod implementations through
an allowlisted local file protocol. No network service or game memory attachment.

The primary task is selecting a game, launching with mods, and changing cheats while
playing. Disconnected and main-menu states must be honest and disable unavailable
actions. Currency operations require explicit clicks and are never retried automatically.
Save backups precede every launch; existing save slots are not used for automated testing.

The screenshot fixes the visual direction: dark, compact utility with amber emphasis,
clear labels, toggle switches and numeric controls. UI copy is Russian. No marketing page,
imagery requirement, onboarding survey, or alternative concept selection is needed.
