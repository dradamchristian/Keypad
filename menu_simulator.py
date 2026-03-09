#!/usr/bin/env python3
"""PC-side macro menu/editor for MacroPad layers.

Features:
- List all layers and current key assignments.
- Edit label/text+keystroke tokens for any key in any layer.
- Advanced mode for action sequences (chooser/mouse/click/sleep/key chords).
- Save edits to macros/overrides.json (device reads this at runtime).
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parent
MACROS_DIR = ROOT / "macros"
OVERRIDES_PATH = MACROS_DIR / "overrides.json"


def _install_stubs():
    if "adafruit_hid.keycode" in sys.modules:
        return
    adafruit_hid = types.ModuleType("adafruit_hid")
    keycode_mod = types.ModuleType("adafruit_hid.keycode")

    class _Keycode:
        pass

    for idx, name in enumerate([
        "ALT", "D", "O", "T", "L", "TAB", "ENTER", "CONTROL", "SHIFT", "GUI", "R",
        "SPACE", "DELETE", "HOME", "END", "TWO", "THREE", "QUOTE", "APOSTROPHE",
        "A", "B", "C", "V", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"
    ], start=1):
        setattr(_Keycode, name, idx)

    keycode_mod.Keycode = _Keycode
    adafruit_hid.keycode = keycode_mod
    sys.modules["adafruit_hid"] = adafruit_hid
    sys.modules["adafruit_hid.keycode"] = keycode_mod


def load_app(path: Path):
    _install_stubs()
    ns = {}
    src = path.read_text(encoding="utf-8")
    exec(compile(src, str(path), "exec"), ns)
    return ns.get("app", {"name": path.name, "macros": []})


def sequence_to_tokens(seq):
    out = []
    for item in seq:
        if isinstance(item, str):
            if item.startswith("Keycode."):
                out.append(f"<{item.split('.',1)[1]}>")
            else:
                out.append(item)
        elif isinstance(item, int):
            out.append(f"<KEY_{item}>")
        elif isinstance(item, tuple):
            names = []
            for k in item:
                if isinstance(k, str) and k.startswith("Keycode."):
                    names.append(k.split(".", 1)[1])
                elif isinstance(k, int):
                    names.append(f"KEY_{k}")
            if names:
                out.append(f"<{'+'.join(names)}>")
    return "".join(out)


def sequence_to_jsonable(seq):
    out = []
    for item in seq:
        if isinstance(item, str):
            if item.startswith("Keycode."):
                out.append({"key": item.split(".", 1)[1]})
            else:
                out.append(item)
        elif isinstance(item, int):
            out.append({"key": f"KEY_{item}"})
        elif isinstance(item, float):
            out.append({"sleep": item})
        elif isinstance(item, tuple):
            keys = []
            for k in item:
                if isinstance(k, str) and k.startswith("Keycode."):
                    keys.append(k.split(".", 1)[1])
                elif isinstance(k, int):
                    keys.append(f"KEY_{k}")
            out.append({"key_chord": keys})
        elif isinstance(item, dict):
            out.append(item)
        elif callable(item):
            out.append({"note": "callable (cannot serialize)"})
    return out


def read_overrides():
    if not OVERRIDES_PATH.exists():
        return {}
    return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))


def write_overrides(data):
    OVERRIDES_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def apply_overrides(filename: str, app: dict, data: dict):
    layer = data.get(filename, {})
    macros = list(app.get("macros", []))
    for idx_txt, payload in layer.items():
        try:
            idx = int(idx_txt)
        except ValueError:
            continue
        while len(macros) <= idx:
            macros.append((0x202020, "", []))

        if isinstance(payload.get("sequence"), list):
            seq = payload.get("sequence", [])
        else:
            seq = [payload.get("tokens", "")]

        macros[idx] = (
            int(payload.get("color", 0x202020)),
            str(payload.get("label", ""))[:8],
            seq,
        )
    out = dict(app)
    out["macros"] = macros
    return out


def show_layer(path: Path, data: dict):
    app = apply_overrides(path.name, load_app(path), data)
    print(f"\n== {path.name} :: {app.get('name','Unnamed')} ==")
    for i in range(12):
        if i < len(app.get("macros", [])):
            color, label, seq = app["macros"][i]
            token_view = seq[0] if seq and isinstance(seq[0], str) else sequence_to_tokens(seq)
            extra = ""
            if any(isinstance(x, dict) for x in seq):
                extra = "  [advanced]"
            print(f"K{i+1:02d}  {label or '(empty)':8}  color={int(color):06X}  {token_view}{extra}")
        else:
            print(f"K{i+1:02d}  (unassigned)")


def interactive_edit(files: list[Path]):
    data = read_overrides()
    while True:
        print("\nLayers:")
        for idx, p in enumerate(files, start=1):
            print(f"  {idx}. {p.name}")
        sel = input("Select layer number (or q): ").strip().lower()
        if sel == "q":
            break
        if not sel.isdigit() or not (1 <= int(sel) <= len(files)):
            print("Invalid layer.")
            continue
        path = files[int(sel) - 1]
        app = load_app(path)
        merged = apply_overrides(path.name, app, data)
        show_layer(path, data)

        k = input("Key to edit (1-12), or b: ").strip().lower()
        if k == "b":
            continue
        if not k.isdigit() or not (1 <= int(k) <= 12):
            print("Invalid key.")
            continue
        key_idx = int(k) - 1
        current = data.get(path.name, {}).get(str(key_idx), {})
        base = merged.get("macros", [])
        base_label = base[key_idx][1] if key_idx < len(base) else ""
        base_color = int(base[key_idx][0]) if key_idx < len(base) else 0x202020
        base_tokens = sequence_to_tokens(base[key_idx][2]) if key_idx < len(base) else ""
        base_sequence = sequence_to_jsonable(base[key_idx][2]) if key_idx < len(base) else []

        print("Press Enter to keep current value.")
        new_label = input(f"Label [{current.get('label', base_label)}]: ").strip()
        mode = input("Edit mode: (t)okens or (a)dvanced JSON [t]: ").strip().lower() or "t"
        clear = input("Clear override for this key? (y/N): ").strip().lower() == "y"

        layer = data.get(path.name, {})
        if clear:
            layer.pop(str(key_idx), None)
        else:
            entry = {
                "label": (new_label if new_label else current.get("label", base_label))[:8],
                "color": int(current.get("color", base_color)),
            }
            if mode == "a":
                current_seq = current.get("sequence", base_sequence)
                print("Current sequence JSON:")
                print(json.dumps(current_seq, indent=2))
                print("Paste new sequence JSON (single line). Leave blank to keep current.")
                raw = input("sequence JSON: ").strip()
                if raw:
                    try:
                        parsed = json.loads(raw)
                        if not isinstance(parsed, list):
                            raise ValueError("Sequence must be a JSON list")
                        entry["sequence"] = parsed
                    except Exception as exc:
                        print(f"Invalid JSON ({exc}), keeping current sequence")
                        entry["sequence"] = current.get("sequence", base_sequence)
                else:
                    entry["sequence"] = current.get("sequence", base_sequence)
            else:
                new_tokens = input(f"Macro tokens [{current.get('tokens', base_tokens)}]: ").strip()
                entry["tokens"] = new_tokens if new_tokens else current.get("tokens", base_tokens)
            layer[str(key_idx)] = entry
        data[path.name] = layer
        write_overrides(data)
        print(f"Saved {OVERRIDES_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", help="Show one layer, e.g. 02_reports.py")
    parser.add_argument("--edit", action="store_true", help="Open interactive editor")
    args = parser.parse_args()

    files = sorted(MACROS_DIR.glob("*.py"))
    if args.layer:
        files = [MACROS_DIR / args.layer]
    for p in files:
        if not p.exists():
            raise SystemExit(f"Missing layer: {p.name}")

    if args.edit:
        interactive_edit(files)
    else:
        data = read_overrides()
        for p in files:
            show_layer(p, data)


if __name__ == "__main__":
    main()
