This build uses clipboard snippets for all 'Canned' macros.
Files are in /snippets and are loaded via PowerShell Set-Clipboard.
Press the macro: it copies the snippet, then pastes (Ctrl+V).

PC macro menu/editor (recommended workflow)
- Run `python menu_simulator.py --edit` on your PC.
- Pick a layer (rotary submenu equivalent), then pick a key (1-12).
- Edit:
  - label (what appears on the device)
  - quick token mode (typed text + keystrokes)
  - advanced JSON mode (for chooser options, biomarker wizard, extra-work email flow, sleep delays, mouse movement/click)
- Save. Changes go to `macros/overrides.json`.

Token syntax for quick macro editor
- Plain text types directly.
- Single key: `<ENTER>`, `<TAB>`, `<F5>`
- Chord: `<CONTROL+V>`, `<SHIFT+TAB>`

Advanced sequence JSON format (editor advanced mode)
- Plain text: `"some text"`
- Single key: `{ "key": "ENTER" }`
- Chord: `{ "key_chord": ["CONTROL", "V"] }`
- Delay: `{ "sleep": 0.25 }`
- Mouse move: `{ "mouse_move": { "x": 120, "y": -40, "wheel": 0 } }`
- Mouse click: `{ "mouse_click": "left" }` (`left`, `right`, `middle`)
- Keep existing report flows:
  - `{ "choose": { ... } }`
  - `{ "choose_multi": { ... } }`
  - `{ "bio_wizard": true }`
  - `{ "extra_work_email": true }`

Device behavior
- Existing macro `.py` files remain unchanged.
- On boot, device loads base layer files and applies `macros/overrides.json` on top.
- Overrides now support either:
  - `tokens` (simple text/key tokens), or
  - `sequence` (advanced JSON action list).

Testing menu changes without loading to device each time
- Preview all layers: `python menu_simulator.py`
- Preview one layer: `python menu_simulator.py --layer 02_reports.py`
- Edit from PC menu: `python menu_simulator.py --edit`


Locked-down NHS PCs: does this require anything installed on the PC?
- If you need a full interactive menu editor on the PC, then yes: some host software (Python app, exe, or listener) must exist on that PC.
- If policy forbids installs/running custom apps, then a PC-side editor is not feasible.

What works with zero PC install
- Device-only operation via standard USB HID keystrokes/mouse actions from preloaded macros.
- Optional constrained on-device edit mode (CircuitPython UI on the MacroPad screen) that edits `/macros/overrides.json` directly.
- Plug-and-play usage is still possible, but editing UX is limited by keypad + encoder input.

Shipping guidance for locked-down environments
1. Ship with all required report shortcuts preconfigured.
2. Include only small, safe on-device edits (label tweaks, choose from preset snippets/actions).
3. Keep advanced macro authoring as an offline admin workflow on a non-locked machine before deployment.

Build a standalone Windows app (no Python install)
1. On your Windows PC, install PyInstaller once: `pip install pyinstaller`
2. Build exe from repo root:
   - `pyinstaller --onefile --name keypad-editor menu_simulator.py`
3. The executable will be in `dist/keypad-editor.exe`.
4. Keep `macros/` next to the exe so `overrides.json` is saved to your keypad repo.
