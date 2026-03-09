from adafruit_hid.keycode import Keycode

app = {
    'name': 'M codes',
    'macros': [
	(0xFFA500, 'Itis', ['M40000', Keycode.TAB]),
	(0xFF0000, 'Normal', ['M-00100', Keycode.TAB]),
	(0xFF0000, 'Adenoca', ['M-81403', Keycode.TAB]),
	(0xFF0000, 'Polyp', ['M-76800', Keycode.TAB])
		]
}

