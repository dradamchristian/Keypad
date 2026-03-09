This build uses clipboard snippets for all 'Canned' macros.
Files are in /snippets and are loaded via PowerShell Set-Clipboard.
Press the macro: it copies the snippet, then pastes (Ctrl+V).

## What runs where
- **On device (MacroPad):** `code.py` + `macros/*.py` run normally.
- **On PC:** `menu_simulator.py` (or a packaged `.exe`) edits macro overrides.
- Device reads `macros/overrides.json` at boot and applies those edits on top of base layer files.

## How to run the programme on the device
1. Copy this repo content to the MacroPad CIRCUITPY drive (including `code.py`, `lib/`, and `macros/`).
2. Safely eject the drive.
3. Replug/reset the MacroPad.
4. It auto-runs `code.py` (no extra launch step needed).

## PC editor workflow (no re-flash each change)
- Preview all layers:
  - `python menu_simulator.py`
- Edit interactively:
  - `python menu_simulator.py --edit`
- Edit a connected MacroPad drive directly (example `E:`):
  - `python menu_simulator.py --edit --macros-dir E:\macros --overrides-path E:\macros\overrides.json`

## Standalone use on lab PCs (no Python installed)
Build once on a machine that has Python, then distribute the `.exe`:
1. Build exe:
   - `powershell -ExecutionPolicy Bypass -File tools\build_menu_editor_exe.ps1`
2. Copy `dist\KeypadMenuEditor.exe` to lab PCs.
3. Run it directly (or via `tools\run_menu_editor.bat`).
4. Point it at the device drive when needed:
   - `KeypadMenuEditor.exe --edit --macros-dir E:\macros --overrides-path E:\macros\overrides.json`

## Token syntax for macro editor
- Plain text types directly.
- Single key: `<ENTER>`, `<TAB>`, `<F5>`
- Chord: `<CONTROL+V>`, `<SHIFT+TAB>`

## Notes
- Base macro files stay unchanged.
- Custom edits are stored in `overrides.json`.
