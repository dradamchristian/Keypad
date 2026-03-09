#!/usr/bin/env python3
"""Host-side preview for MacroPad macro layers + overrides.

Usage:
  python menu_simulator.py
  python menu_simulator.py --layer 02_reports.py
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
        "SPACE", "DELETE", "HOME", "END", "TWO", "THREE", "QUOTE", "APOSTROPHE"
    ], start=1):
        setattr(_Keycode, name, idx)

    keycode_mod.Keycode = _Keycode
    adafruit_hid.keycode = keycode_mod
    sys.modules["adafruit_hid"] = adafruit_hid
    sys.modules["adafruit_hid.keycode"] = keycode_mod



ROOT = Path(__file__).resolve().parent
MACROS_DIR = ROOT / "macros"
OVERRIDES_PATH = MACROS_DIR / "overrides.json"


def load_app(path: Path):
    _install_stubs()
    ns = {}
    src = path.read_text(encoding="utf-8")
    exec(compile(src, str(path), "exec"), ns)
    return ns.get("app", {"name": path.name, "macros": []})


def apply_overrides(filename: str, app: dict):
    data = {}
    if OVERRIDES_PATH.exists():
        data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
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


def preview(app: dict):
    print(f"\n== {app.get('name','Unnamed')} ==")
    for i in range(12):
        if i < len(app.get("macros", [])):
            color, label, seq = app["macros"][i]
            print(f"K{i+1:02d}  {label or '(empty)':8}  color={int(color):06X}  action={seq}")
        else:
            print(f"K{i+1:02d}  (unassigned)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", help="Macro layer filename, e.g. 02_reports.py")
    args = parser.parse_args()

    files = sorted(MACROS_DIR.glob("*.py"))
    if args.layer:
        files = [MACROS_DIR / args.layer]
    for path in files:
        if not path.exists():
            raise SystemExit(f"Missing layer: {path.name}")
        app = load_app(path)
        app = apply_overrides(path.name, app)
        preview(app)


if __name__ == "__main__":
    main()
