# Desktop interface

Operate mode. A 190 px game selector stays beside a single scrollable control surface.
The header names the game and supported version, then connection status and launch.
Switches show acknowledged game state; pending actions disable controls. Errors stay
visible near connection status. A reset button remains outside the scroll region.

Palette: canvas #181b20, sidebar #111419, text #edf0f4, secondary #adb6c2,
accent #f39a39, focus #f7bf82, borders #3b424e, success #b9d6bf, error #ffbe9c.
Native system font for a familiar macOS utility; 29 px game name, 14 px controls,
12 px secondary copy. Spacing: 28 px main inset, 10 px row insets, 18 px section lead.

QCheckBox-based switches retain keyboard focus and accessible names. Numerical settings
have explicit Apply buttons; currency uses Add. The minimum window is 820×660 and
default 920×760. No decorative animation or illustrative game art. State feedback is
immediate; acknowledged values are read back from the running game.
