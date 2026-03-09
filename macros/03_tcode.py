from adafruit_hid.keycode import Keycode

app = {
    'name': 'T codes',
    'macros': [
        (0x00FF00, 'Colon', ['T59300,']),
        (0xFF0000, 'Duo', ['T58200,']),
        (0xFF0000, 'Stomach', ['T57000,']),
        (0xFF0000, 'Oes', ['T56000,']),
 	(0xFF0000, 'App', ['T59200,']),
	(0xFF0000, 'Glb', ['T63000,']),
    ]
}
