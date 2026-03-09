This build uses clipboard snippets for all 'Canned' macros.
Files are in /snippets and are loaded via PowerShell Set-Clipboard.
Press the macro: it copies the snippet, then pastes (Ctrl+V).

PC macro menu/editor (recommended workflow)
- Run `python menu_simulator.py --edit` on your PC.
- Pick a layer (rotary submenu equivalent), then pick a key (1-12).
- Edit:
  - label (what appears on the device)
  - macro tokens (typed text + keystrokes)
- Save. Changes go to `macros/overrides.json`.

Token syntax for macro editor
- Plain text types directly.
- Single key: `<ENTER>`, `<TAB>`, `<F5>`
- Chord: `<CONTROL+V>`, `<SHIFT+TAB>`

Device behavior
- Existing macro `.py` files remain unchanged.
- On boot, device loads base layer files and applies `macros/overrides.json` on top.

Testing menu changes without loading to device each time
- Preview all layers: `python menu_simulator.py`
- Preview one layer: `python menu_simulator.py --layer 02_reports.py`
- Edit from PC menu: `python menu_simulator.py --edit`
