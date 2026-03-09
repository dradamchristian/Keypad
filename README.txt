This build uses clipboard snippets for all 'Canned' macros.
Files are in /snippets and are loaded via PowerShell Set-Clipboard.
Press the macro: it copies the snippet, then pastes (Ctrl+V).

On-device macro editor
- Open editor: hold encoder button + press key 12.
- Rotate encoder: change layer.
- Hold encoder + rotate: change key within layer.
- Key 9: cycle mode (label / macro / clear).
- Key 10: edit selected field.
- Key 11: done.

Macro token syntax for editable macros
- Plain text types directly.
- Single key: <ENTER>, <TAB>, <F5>
- Chord: <CONTROL+V>, <SHIFT+TAB>

Edits are stored in /macros/overrides.json so original macro files are unchanged.

Testing menu changes without device
- Run `python menu_simulator.py` on your computer to preview each layer and any overrides.
- Run `python menu_simulator.py --layer 02_reports.py` to preview one layer.
