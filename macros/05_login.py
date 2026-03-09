from adafruit_hid.keycode import Keycode

app = {
    'name': 'Login',
    'macros': [
        (0x33cc, 'Email', ['adam.christian@wales.nhs.uk']),
        (0x33cc, 'Nadex', ['ad086881', Keycode.TAB]),
        (0x33cc, 'Sign', ['Dr Adam Christian']),
        (0x33cc, 'Login', ['ad086881', Keycode.TAB, 'Squidge123£', Keycode.ENTER]),
    ]
}