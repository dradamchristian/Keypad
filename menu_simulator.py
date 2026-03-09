#!/usr/bin/env python3
"""PC-side macro menu/editor for MacroPad layers.

Can run directly with Python or as a packaged standalone .exe.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import types


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


def read_overrides(overrides_path: Path):
    if not overrides_path.exists():
        return {}
    return json.loads(overrides_path.read_text(encoding="utf-8"))


def write_overrides(data, overrides_path: Path):
    overrides_path.parent.mkdir(parents=True, exist_ok=True)
    overrides_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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
        macros[idx] = (
            int(payload.get("color", 0x202020)),
            str(payload.get("label", ""))[:8],
            [payload.get("tokens", "")],
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
            print(f"K{i+1:02d}  {label or '(empty)':8}  color={int(color):06X}  {token_view}")
        else:
            print(f"K{i+1:02d}  (unassigned)")


def interactive_edit(files: list[Path], overrides_path: Path):
    data = read_overrides(overrides_path)
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

        print("Press Enter to keep current value.")
        new_label = input(f"Label [{current.get('label', base_label)}]: ").strip()
        new_tokens = input(f"Macro tokens [{current.get('tokens', base_tokens)}]: ").strip()
        clear = input("Clear override for this key? (y/N): ").strip().lower() == "y"

        layer = data.get(path.name, {})
        if clear:
            layer.pop(str(key_idx), None)
        else:
            layer[str(key_idx)] = {
                "label": (new_label if new_label else current.get("label", base_label))[:8],
                "tokens": new_tokens if new_tokens else current.get("tokens", base_tokens),
                "color": int(current.get("color", base_color)),
            }
        data[path.name] = layer
        write_overrides(data, overrides_path)
        print(f"Saved {overrides_path}")


def main():
    repo_root = Path(__file__).resolve().parent
    default_macros_dir = repo_root / "macros"
    default_overrides = default_macros_dir / "overrides.json"

    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", help="Show one layer, e.g. 02_reports.py")
    parser.add_argument("--edit", action="store_true", help="Open interactive editor")
    parser.add_argument("--macros-dir", type=Path, default=default_macros_dir,
                        help="Directory containing layer .py files (default: ./macros)")
    parser.add_argument("--overrides-path", type=Path, default=default_overrides,
                        help="Path to overrides.json to read/write")
    args = parser.parse_args()

    macros_dir = args.macros_dir
    overrides_path = args.overrides_path

    files = sorted(macros_dir.glob("*.py"))
    if args.layer:
        files = [macros_dir / args.layer]
    for p in files:
        if not p.exists():
            raise SystemExit(f"Missing layer: {p.name}")

    if args.edit:
        interactive_edit(files, overrides_path)
    else:
        data = read_overrides(overrides_path)
        for p in files:
            show_layer(p, data)


if __name__ == "__main__":
    main()
