from adafruit_hid.keycode import Keycode

import time, usb_hid
from adafruit_hid.mouse import Mouse
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS  # OK for plain text on UK KB

# ---- edit these if needed ----
X_OFFSET = 550   # best guess for 3840×2160 (175% scale) from your screenshot
Y_OFFSET = 175
TEXT_TO_TYPE = "ad086881"
CLICK_DELAY = 0.01
# ------------------------------

_mouse = Mouse(usb_hid.devices)
_kbd = Keyboard(usb_hid.devices)
_layout = KeyboardLayoutUS(_kbd)

def _park_top_left():
    # Force cursor to (0,0) so offsets are reliable across DPI/scaling
    for _ in range(8):
        _mouse.move(x=-5000, y=-5000)
        time.sleep(0.01)

def _rep_pathologist_action():
    _park_top_left()
    _mouse.move(x=X_OFFSET, y=Y_OFFSET)
    time.sleep(0.001)
    _mouse.click(Mouse.LEFT_BUTTON)
    time.sleep(CLICK_DELAY)
    _layout.write(TEXT_TO_TYPE)
    _kbd.send(Keycode.TAB) 

app = {
    'name': 'Trak',
    'macros': [
        # First macro
        (0xFF0000, 'Deauth', [
            (Keycode.ALT, Keycode.D),
            0.3,
            (Keycode.ALT, Keycode.O)
        ]),

        # Second macro
        (0xcc6600, 'Auth', [
            (Keycode.ALT, Keycode.T),
            0.5,
            (Keycode.ALT, Keycode.L),
        ]),

        # Third macro
        (0xcc6600, 'TLogin', [
            'ad086881',
            Keycode.TAB,
            'Squidge123£',
            Keycode.TAB,
            Keycode.ENTER
        ]),

        (0x33cc, 'Email', ['adam.christian@wales.nhs.uk']),
        (0x33cc, 'Nadex', ['ad086881', Keycode.TAB]),
        (0x33cc, 'Sign', ['Dr Adam Christian']),
        (0x33cc, 'Login', ['ad086881', Keycode.TAB, 'Squidge123£', Keycode.ENTER]),

        # Rep Pathologist macro (wrapped in a list so it's valid for Hotkeys)
        (0x008000, "RepPath", [
            lambda: _rep_pathologist_action()
        ]),
    ]
}
