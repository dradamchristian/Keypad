# MacroPad configuration for CircuitPython 9.2.8
# Breathing LEDs per-layer + idle dim + OLED blanking + reporting helpers
# Screen wakes on key press, encoder press, or encoder rotation

import os, time, math, json, displayio, terminalio, usb_hid
from adafruit_display_text import label
from adafruit_macropad import MacroPad
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse

# --- Typing speed ---
TYPE_CHAR_DELAY       = 0.0015
TYPE_SPACE_DELAY      = 0.003
TYPE_NEWLINE_DELAY    = 0.015
TYPE_SENTENCE_DELAY   = 0.015
WORD_FLUSH_MAX_CHARS  = 60

# --- Breathing + idle dim ---
BREATH_SPEED          = 0.05
BREATH_MIN            = 0.30
BREATH_MAX            = 1.00
IDLE_TIMEOUT          = 600.0
IDLE_RAMP             = 2.0
IDLE_MIN              = 0.15

# --- Screen blanking ---
SCREEN_OFF_TIMEOUT    = 600.0  # set to 3.0 for quick testing

# --- Setup ---
macropad = MacroPad()
display = macropad.display
mouse = Mouse(usb_hid.devices)

# UK quote key alias (some builds expose QUOTE, others APOSTROPHE)
try:
    KC_QUOTE = Keycode.QUOTE
except AttributeError:
    KC_QUOTE = Keycode.APOSTROPHE

# --- OLED layout ---
group = displayio.Group()
title = label.Label(terminalio.FONT, text="Loading...", color=0xFFFFFF)
title.anchor_point = (0.0, 0.0)
title.anchored_position = (2, 0)
group.append(title)

key_labels = []
COLS, ROWS = 3, 4
cell_w, cell_h = 42, 16
for i in range(12):
    r, c = divmod(i, COLS)
    lbl = label.Label(terminalio.FONT, text="", color=0xFFFFFF)
    lbl.anchor_point = (0.0, 0.0)
    lbl.anchored_position = (2 + c*cell_w, 16 + r*cell_h)
    key_labels.append(lbl)
    group.append(lbl)

display.root_group = group

# --- Lighting state ---
base_color = 0x202020
phase = 0.0
flash_until = 0.0
flash_index = None
last_activity = time.monotonic()
screen_off = False
last_encoder = macropad.encoder  # track dial movement

OVERRIDES_PATH = "/macros/overrides.json"

# --- Helpers ---
def _mix(a, b, t): return a + (b - a) * t

def set_base_color(color):
    global base_color
    base_color = int(color) & 0xFFFFFF

def note_activity():
    """Reset idle timer and wake display if asleep."""
    global last_activity, screen_off, last_encoder
    last_activity = time.monotonic()
    last_encoder = macropad.encoder
    if screen_off:
        macropad.display.root_group = group
        macropad.display.auto_refresh = True
        screen_off = False

def update_breathing():
    global phase
    now = time.monotonic()
    phase = (phase + BREATH_SPEED) % (2 * math.pi)
    sin01 = 0.5 + 0.5 * math.sin(phase)
    breath = _mix(BREATH_MIN, BREATH_MAX, sin01)

    idle_for = now - last_activity
    if idle_for <= IDLE_TIMEOUT:
        idle_factor = 1.0
    else:
        t = min(1.0, (idle_for - IDLE_TIMEOUT) / max(0.001, IDLE_RAMP))
        idle_factor = _mix(1.0, IDLE_MIN, t)

    f = breath * idle_factor
    r = (base_color >> 16) & 0xFF
    g = (base_color >> 8) & 0xFF
    b = base_color & 0xFF

    sr, sg, sb = int(r * f) & 0xFF, int(g * f) & 0xFF, int(b * f) & 0xFF

    if flash_index is None or now > flash_until:
        for i in range(12):
            macropad.pixels[i] = (sr, sg, sb)
    macropad.pixels.show()

def flash_key(i, duration=0.12):
    global flash_index, flash_until
    flash_index = i
    flash_until = time.monotonic() + duration
    macropad.pixels[i] = (255, 255, 255)
    macropad.pixels.show()

# --- Text typing (UK layout fixes for £ @ ") ---
PUNCT_FLUSH = set(' \n\t.,;:!?)]}')

def send_text_uk(text, char_delay=None):
    """Types text using UK-friendly mappings for £, @, and ".
       char_delay overrides TYPE_CHAR_DELAY when provided."""
    delay = TYPE_CHAR_DELAY if char_delay is None else char_delay
    i = 0
    word = []
    def flush_word():
        if word:
            macropad.keyboard_layout.write("".join(word))
            word.clear()
            time.sleep(delay)

    while i < len(text):
        ch = text[i]

        # UK: £ = Shift+3
        if ch == '£':
            flush_word()
            macropad.keyboard.press(Keycode.SHIFT, Keycode.THREE)
            macropad.keyboard.release_all()
            time.sleep(delay)
            i += 1
            continue

        # UK: @ = Shift + ' (quote key)
        if ch == '@':
            flush_word()
            macropad.keyboard.press(Keycode.SHIFT, KC_QUOTE)
            macropad.keyboard.release_all()
            time.sleep(delay)
            i += 1
            continue

        # UK: " = Shift + 2
        if ch == '"':
            flush_word()
            macropad.keyboard.press(Keycode.SHIFT, Keycode.TWO)
            macropad.keyboard.release_all()
            time.sleep(delay)
            i += 1
            continue

        word.append(ch)
        time.sleep(delay)
        if len(word) >= WORD_FLUSH_MAX_CHARS:
            flush_word()
        if ch in PUNCT_FLUSH:
            flush_word()
            if ch == ' ':
                time.sleep(TYPE_SPACE_DELAY)
            elif ch == '\n':
                time.sleep(TYPE_NEWLINE_DELAY)
            elif ch in '.!?':
                time.sleep(TYPE_SENTENCE_DELAY)
        i += 1
    flush_word()


def _key_name_to_code(name):
    return getattr(Keycode, name, None)


def _code_to_key_name(code):
    for attr in dir(Keycode):
        if attr.isupper() and getattr(Keycode, attr) == code:
            return attr
    return None


def sequence_to_tokens(seq):
    tokens = []
    for item in seq:
        if isinstance(item, str):
            if item.startswith("Keycode."):
                tokens.append("<{}>".format(item.split(".", 1)[1]))
            else:
                tokens.append(item)
        elif isinstance(item, int):
            name = _code_to_key_name(item)
            if name:
                tokens.append("<{}>".format(name))
        elif isinstance(item, tuple):
            names = []
            for k in item:
                if isinstance(k, str) and k.startswith("Keycode."):
                    names.append(k.split(".", 1)[1])
                elif isinstance(k, int):
                    nk = _code_to_key_name(k)
                    if nk:
                        names.append(nk)
            if names:
                tokens.append("<{}>".format("+".join(names)))
    return "".join(tokens)


def tokens_to_sequence(text):
    seq = []
    buf = []
    i = 0
    while i < len(text):
        if text[i] == "<":
            j = text.find(">", i + 1)
            if j == -1:
                buf.append(text[i])
                i += 1
                continue
            if buf:
                seq.append("".join(buf))
                buf = []
            token = text[i + 1:j].strip().upper()
            parts = [p for p in token.split("+") if p]
            if len(parts) == 1:
                code = _key_name_to_code(parts[0])
                if code is not None:
                    seq.append(code)
                else:
                    seq.append("<{}>".format(token))
            else:
                chord = []
                for p in parts:
                    code = _key_name_to_code(p)
                    if code is None:
                        chord = []
                        break
                    chord.append(code)
                if chord:
                    seq.append(tuple(chord))
                else:
                    seq.append("<{}>".format(token))
            i = j + 1
        else:
            buf.append(text[i])
            i += 1
    if buf:
        seq.append("".join(buf))
    return seq


def sequence_to_jsonable(seq):
    out = []
    for item in seq:
        if isinstance(item, tuple):
            keys = []
            for k in item:
                name = _code_to_key_name(k) if isinstance(k, int) else None
                keys.append(name if name else str(k))
            out.append({"key_chord": keys})
        elif isinstance(item, int):
            name = _code_to_key_name(item)
            out.append({"key": name if name else item})
        elif isinstance(item, str):
            if item.startswith("Keycode."):
                out.append({"key": item.split(".", 1)[1]})
            else:
                out.append(item)
        elif isinstance(item, float):
            out.append({"sleep": item})
        elif isinstance(item, dict):
            out.append(item)
    return out


def jsonable_to_sequence(items):
    seq = []
    for item in items:
        if isinstance(item, str):
            seq.append(item)
        elif isinstance(item, (int, float)):
            seq.append(float(item))
        elif isinstance(item, dict):
            if "sleep" in item:
                seq.append(float(item.get("sleep", 0.0)))
            elif "key" in item:
                key = str(item.get("key", "")).upper()
                code = _key_name_to_code(key)
                if code is not None:
                    seq.append(code)
            elif "key_chord" in item and isinstance(item["key_chord"], list):
                chord = []
                for key in item["key_chord"]:
                    code = _key_name_to_code(str(key).upper())
                    if code is None:
                        chord = []
                        break
                    chord.append(code)
                if chord:
                    seq.append(tuple(chord))
            elif any(k in item for k in ("choose", "choose_multi", "bio_wizard", "extra_work_email", "mouse_move", "mouse_click")):
                seq.append(item)
    return seq

def drain_key_events(dt=0.05):
    t0 = time.monotonic()
    while time.monotonic() - t0 < dt:
        if not macropad.keys.events.get():
            time.sleep(0.005)


def read_overrides():
    try:
        with open(OVERRIDES_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def write_overrides(data):
    with open(OVERRIDES_PATH, "w") as f:
        json.dump(data, f)


def apply_layer_override(filename, base_app):
    data = read_overrides()
    layer = data.get(filename, {})
    macros = list(base_app.get("macros", []))
    max_index = len(macros)
    for idx_txt in layer.keys():
        try:
            idx = int(idx_txt)
            if idx + 1 > max_index:
                max_index = idx + 1
        except ValueError:
            pass
    while len(macros) < max_index:
        macros.append((0x202020, "", []))
    for idx_txt, payload in layer.items():
        try:
            idx = int(idx_txt)
        except ValueError:
            continue
        if idx < 0 or idx >= 12:
            continue
        label_text = payload.get("label", "")
        color = int(payload.get("color", 0x202020)) & 0xFFFFFF
        if isinstance(payload.get("sequence"), list):
            seq = jsonable_to_sequence(payload.get("sequence", []))
        else:
            seq = tokens_to_sequence(payload.get("tokens", ""))
        macros[idx] = (color, label_text[:8], seq)
    out = dict(base_app)
    out["macros"] = macros
    return out



# PC-side editor writes /macros/overrides.json; device only loads overrides.


# --- Modal helpers ---
is_running = False
last_pos = macropad.encoder

def choose_simple(title_text, options):
    global is_running, last_pos
    was_running = is_running; is_running = True
    base = macropad.encoder; last_pos = base
    old_title = title.text
    def render(idx):
        for j in range(12): key_labels[j].text = ""
        title.text = title_text
        key_labels[0].text = f"> {options[idx]}"
        key_labels[3].text = "Press to confirm"
        key_labels[9].text = "Rotate to change"
    idx = 0; render(idx); note_activity()
    try:
        pressed = False
        while True:
            pos = macropad.encoder
            if pos != base:
                delta = pos - base; base = pos
                idx = (idx + delta) % len(options)
                render(idx); note_activity()
            if macropad.encoder_switch: pressed = True
            elif pressed: break
            update_breathing(); time.sleep(0.02)
        drain_key_events(0.08)
    finally:
        load_layer(current_index); title.text = old_title
        last_pos = macropad.encoder; is_running = was_running
        note_activity()
    return options[idx]

def input_number(title_text, min_val=0, max_val=100, step=1):
    global is_running, last_pos
    was_running = is_running; is_running = True
    base = macropad.encoder; last_pos = base
    value = min_val; old_title = title.text
    def render():
        for j in range(12): key_labels[j].text = ""
        title.text = f"{title_text}: {value}"
        key_labels[3].text = "Press to confirm"
        key_labels[9].text = "Rotate to change"
    render(); note_activity()
    try:
        pressed = False
        while True:
            pos = macropad.encoder
            if pos != base:
                delta = pos - base; base = pos
                value = max(min_val, min(max_val, value + delta * step))
                render(); note_activity()
            if macropad.encoder_switch: pressed = True
            elif pressed: break
            update_breathing(); time.sleep(0.02)
        drain_key_events(0.08)
    finally:
        load_layer(current_index); title.text = old_title
        last_pos = macropad.encoder; is_running = was_running
        note_activity()
    return int(value)

def choose_and_type(title_text, template, options):
    global is_running, last_pos
    was_running = is_running; is_running = True
    base = macropad.encoder; last_pos = base
    old_title = title.text
    def render(idx):
        for j in range(12): key_labels[j].text = ""
        key_labels[0].text = f"> {options[idx]}"
        key_labels[3].text = "Press knob to confirm"
        key_labels[6].text = "Rotate to change"
        title.text = title_text
    idx = 0; render(idx); note_activity()
    try:
        pressed = False
        while True:
            pos = macropad.encoder
            if pos != base:
                delta = pos - base; base = pos
                idx = (idx + delta) % len(options)
                render(idx); note_activity()
            if macropad.encoder_switch: pressed = True
            elif pressed: break
            update_breathing(); time.sleep(0.02)
    finally:
        load_layer(current_index); title.text = old_title
        last_pos = macropad.encoder; is_running = was_running
        note_activity(); drain_key_events(0.08)

    # Flexible template substitution
    try:
        text = template.format(option=options[idx])
    except (KeyError, IndexError):
        try:
            text = template.format(grade=options[idx])
        except (KeyError, IndexError):
            text = (template + " " + options[idx]) if template else options[idx]

    send_text_uk(text)

def choose_multi(title_text, template, fields):
    global is_running, last_pos
    was_running = is_running; is_running = True
    base = macropad.encoder; last_pos = base
    old_title = title.text; idx = 0; fi = 0
    choices = {}; total = len(fields)
    def render():
        for j in range(12): key_labels[j].text = ""
        f = fields[fi]
        title.text = f"{title_text} [{fi+1}/{total}]"
        key_labels[0].text = f"{f['label']}:"
        key_labels[3].text = f"> {f['options'][idx]}"
        key_labels[9].text = "Rotate: change • Press: confirm"
    render(); note_activity()
    try:
        pressed = False
        while True:
            pos = macropad.encoder
            if pos != base:
                delta = pos - base; base = pos
                options = fields[fi]['options']
                idx = (idx + delta) % len(options)
                render(); note_activity()
            if macropad.encoder_switch: pressed = True
            elif pressed:
                choices[fields[fi]['name']] = fields[fi]['options'][idx]
                fi += 1
                if fi >= total: break
                idx = 0; render(); note_activity(); pressed = False
            update_breathing(); time.sleep(0.02)
        drain_key_events(0.08)
    finally:
        load_layer(current_index); title.text = old_title
        last_pos = macropad.encoder; is_running = was_running
        note_activity()
    send_text_uk(template.format(**choices))

def biomarker_wizard():
    her2_score = choose_simple("HER2 score", ["0","1+","2+","3+"])
    her2_interp = "Positive" if her2_score=="3+" else "Equivocal - FISH to follow" if her2_score=="2+" else "Negative"
    cps = input_number("PD-L1 (22C3) CPS", 0, 100, 1)
    tps_part = ""
    if choose_simple("Record TPS?", ["No","Yes"])=="Yes":
        tps = input_number("TPS %",0,100,1); tps_part=f"; TPS {tps}%"
    if choose_simple("All MMR retained?", ["Yes","No"])=="Yes":
        mlh1=pms2=msh2=msh6="Retained"; msi_line="There is no evidence of microsatellite instability."
    else:
        mlh1=choose_simple("MLH1",["Retained","Lost"])
        pms2=choose_simple("PMS2",["Retained","Lost"])
        msh2=choose_simple("MSH2",["Retained","Lost"])
        msh6=choose_simple("MSH6",["Retained","Lost"])
        msi_line="MSI present."
    lines=["BIOMARKER REPORT","",f"HER2: {her2_score} ({her2_interp})","",f"PD-L1 22c3 CPS {cps},{tps_part}","",
           "MMR:",f"MLH1: {mlh1}",f"PMS2: {pms2}",f"MSH2: {msh2}",f"MSH6: {msh6}",msi_line,"","Reported by: Dr Adam Christian"]
    send_text_uk("\n".join(lines))

# ===== Extra Work Email (Camera inbox) =====
EMAIL_RECIPIENT = "histopathology.Camera@wales.nhs.uk"
EMAIL_SUBJECT   = "Extra Work Request"

# OS + launch method
EMAIL_OS_MODE   = "windows"            # "windows" or "mac"
EMAIL_LAUNCH    = "ui"                 # "ui" | "mailto" | "outlook_cli"
CLEAR_BODY_BEFORE_TYPING = True        # True = erase signature/body, False = type above signature

EXTRA_REQ_CHOICES = [
    "Level 4-6",
    "Level 2-3",
    "DS",
    "Liver specials (no H&Es)",
]

def _url_encode_mail(s: str) -> str:
    out=[]
    for ch in s:
        o=ord(ch)
        if (48<=o<=57) or (65<=o<=90) or (97<=o<=122) or ch in "-_.~":
            out.append(ch)
        elif ch==" ": out.append("%20")
        elif ch=="\n": out.append("%0D%0A")
        else: out.append("%%%02X"%o)
    return "".join(out)

def _type_runbox_string(s: str, delay=0.0009):
    # Use the UK-safe typer, faster for short strings
    send_text_uk(s, char_delay=delay)

def _enter(n=1):
    for _ in range(n):
        macropad.keyboard.press(Keycode.ENTER)
        macropad.keyboard.release_all()
        time.sleep(0.03)

def _compose_via_ui(request_text: str):
    # Body block
    body = (
        "Specimen Number: "
        "\n\n"
        f"Request: {request_text}"
        "\n\n"
        "Thank you,\n"
        "Adam"
    )

    # 1) Bring Outlook to front via Start → type → Enter
    macropad.keyboard.press(Keycode.GUI); macropad.keyboard.release_all()
    time.sleep(0.18)
    send_text_uk("Outlook", char_delay=0.0009)
    macropad.keyboard.send(Keycode.ENTER)
    time.sleep(0.9)  # bump to 1.1s if needed

    # 2) New message, then fill To → Subject → Body
    macropad.keyboard.send(Keycode.CONTROL, Keycode.N)
    time.sleep(0.35)
    send_text_uk(EMAIL_RECIPIENT)                 # To:
    macropad.keyboard.send(Keycode.TAB); time.sleep(0.05)
    send_text_uk(EMAIL_SUBJECT)                   # Subject
    macropad.keyboard.send(Keycode.TAB); time.sleep(0.05)

    # 3) Ensure we're in BODY and clear (or move top to keep signature)
    if CLEAR_BODY_BEFORE_TYPING:
        macropad.keyboard.send(Keycode.CONTROL, Keycode.A); time.sleep(0.06)
        macropad.keyboard.send(Keycode.DELETE); time.sleep(0.06)
    else:
        macropad.keyboard.send(Keycode.CONTROL, Keycode.HOME); time.sleep(0.06)

    # 4) Type the block, then park caret after "Specimen Number: "
    drain_key_events(0.08)
    send_text_uk(body)
    macropad.keyboard.send(Keycode.CONTROL, Keycode.HOME); time.sleep(0.05)
    macropad.keyboard.send(Keycode.END); time.sleep(0.05)  # ready to scan

# Clear the body before typing (keep True if Outlook adds a signature)
CLEAR_BODY_BEFORE_TYPING = True

# Give Outlook a moment to inject signature *before* we clear (tune if needed)
SIGNATURE_SETTLE_DELAY = 0.90  # try 1.1 on a slower PC

def _launch_camera_email(request_text: str):
    """Open a new message via mailto (subject only), then reliably clear and type the body,
       finally park the caret after 'Specimen Number: ' ready for barcode scan."""
    body = (
        "Specimen Number: "
        "\n\n"
        f"Request: {request_text}"
        "\n\n"
        "Thank you,\n"
        "Adam"
    )
    subj = _url_encode_mail(EMAIL_SUBJECT)
    uri  = f"mailto:{EMAIL_RECIPIENT}?subject={subj}"

    if EMAIL_OS_MODE == "windows":
        # Win+R → mailto (short) → Enter
        macropad.keyboard.press(Keycode.GUI); macropad.keyboard.press(Keycode.R)
        macropad.keyboard.release_all()
        time.sleep(0.18)
        _type_runbox_string(uri, delay=0.0009)
        macropad.keyboard.send(Keycode.ENTER)
    else:
        # macOS Spotlight path
        macropad.keyboard.press(Keycode.GUI); macropad.keyboard.press(Keycode.SPACE)
        macropad.keyboard.release_all()
        time.sleep(0.25)
        _type_runbox_string(uri, delay=0.0009)
        macropad.keyboard.send(Keycode.ENTER)

    # Let the compose window appear and any auto-signature settle
    time.sleep(SIGNATURE_SETTLE_DELAY)

    # Jump focus: To → Subject → Body
    macropad.keyboard.send(Keycode.TAB); time.sleep(0.05)
    macropad.keyboard.send(Keycode.TAB); time.sleep(0.05)

    if CLEAR_BODY_BEFORE_TYPING:
        # Double-clear to beat signatures that appear a bit late
        for _ in range(2):
            macropad.keyboard.send(Keycode.CONTROL, Keycode.A); time.sleep(0.06)
            macropad.keyboard.send(Keycode.DELETE); time.sleep(0.08)

    else:
        # Keep signature but type above it
        macropad.keyboard.send(Keycode.CONTROL, Keycode.HOME); time.sleep(0.06)

    # Type your block
    drain_key_events(0.08)
    send_text_uk(body)

    # Park caret after "Specimen Number: "
    macropad.keyboard.send(Keycode.CONTROL, Keycode.HOME); time.sleep(0.05)  # start of body
    macropad.keyboard.send(Keycode.END); time.sleep(0.05)                    # end of first line

def extra_work_email_flow():
    """Mini flow: pick request -> open Outlook draft ready for barcode scan."""
    choice = choose_simple("Extra Work Request", EXTRA_REQ_CHOICES)  # uses your modal UI
    note_activity()
    _launch_camera_email(choice)

# --- Run sequence ---
def run_sequence(seq):
    for item in seq:
        if callable(item): item(); continue
        if isinstance(item,float): time.sleep(item)
        elif isinstance(item,tuple):
            chord=[]
            for k in item:
                if isinstance(k,str) and k.startswith("Keycode."):
                    chord.append(getattr(Keycode,k.split(".",1)[1]))
                elif isinstance(k,int):
                    chord.append(k)
            if chord:
                macropad.keyboard.send(*chord); time.sleep(0.05)
        elif isinstance(item,int):
            macropad.keyboard.send(item); time.sleep(0.05)
        elif isinstance(item,str):
            if item.startswith("Keycode."):
                macropad.keyboard.send(getattr(Keycode,item.split(".",1)[1]))
                time.sleep(0.05)
            else:
                send_text_uk(item)
        elif isinstance(item,dict) and "choose" in item:
            cfg=item["choose"]; choose_and_type(cfg.get("title","Choose"),cfg["template"],cfg["options"])
        elif isinstance(item,dict) and "choose_multi" in item:
            cfg=item["choose_multi"]; choose_multi(cfg.get("title","Choose"),cfg["template"],cfg["fields"])
        elif isinstance(item,dict) and "bio_wizard" in item:
            biomarker_wizard()
        elif isinstance(item,dict) and "extra_work_email" in item:
            extra_work_email_flow()
        elif isinstance(item,dict) and "mouse_move" in item:
            cfg = item.get("mouse_move", {})
            mouse.move(x=int(cfg.get("x", 0)), y=int(cfg.get("y", 0)), wheel=int(cfg.get("wheel", 0)))
            time.sleep(0.02)
        elif isinstance(item,dict) and "mouse_click" in item:
            btn = str(item.get("mouse_click", "left")).lower()
            button = Mouse.LEFT_BUTTON if btn == "left" else (Mouse.RIGHT_BUTTON if btn == "right" else Mouse.MIDDLE_BUTTON)
            mouse.click(button)
            time.sleep(0.02)

# --- Macros ---
macros_folder = "/macros"
macro_files = [f for f in os.listdir(macros_folder) if f.endswith(".py")]
macro_files.sort()
current_index=0; last_pos=macropad.encoder; is_running=False; cooldown_until=0.0

def load_layer(idx):
    global app, base_color
    filename=macro_files[idx]
    with open(macros_folder+"/"+filename,"r") as f: code=f.read()
    ns={}; exec(code,ns)
    base_app=ns.get("app",{"name":filename,"macros":[]})
    app=apply_layer_override(filename, base_app)
    title.text=app.get("name",filename)
    for i in range(12):
        key_labels[i].text=app["macros"][i][1] if i<len(app["macros"]) else ""
    set_base_color(app["macros"][0][0] if app["macros"] else 0x202020)
    note_activity(); update_breathing()

load_layer(current_index)

# --- Main loop ---
while True:
    now=time.monotonic()

    # Handle macro key presses
    ev=macropad.keys.events.get()
    if ev and ev.pressed and (not is_running) and now>=cooldown_until:
        i=ev.key_number
        if i<len(app["macros"]):
            is_running=True; _,_,seq=app["macros"][i]
            flash_key(i); note_activity()
            try:
                run_sequence(seq)
            finally:
                is_running=False; cooldown_until=time.monotonic()+0.30; note_activity()

    # Encoder rotation changes layer
    pos=macropad.encoder
    if pos!=last_pos and (not is_running):
        delta=pos-last_pos; last_pos=pos
        current_index=(current_index+delta)%len(macro_files)
        load_layer(current_index); note_activity()

    # --- Screen blanking (with encoder wake) ---
    idle_time = now - last_activity

    # Wake on key, encoder rotation, or encoder press
    if ev and ev.pressed:
        note_activity()
    if macropad.encoder != last_encoder:
        note_activity()
    last_encoder = macropad.encoder
    if macropad.encoder_switch:
        note_activity()

    if idle_time > SCREEN_OFF_TIMEOUT and not screen_off:
        # Blank OLED by replacing with a black fill
        blank_group = displayio.Group()
        bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
        bg_palette = displayio.Palette(1)
        bg_palette[0] = 0x000000
        bg_tile = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)
        blank_group.append(bg_tile)
        macropad.display.root_group = blank_group
        macropad.display.auto_refresh = True
        screen_off = True

    elif idle_time <= SCREEN_OFF_TIMEOUT and screen_off:
        # Restore normal group
        macropad.display.root_group = group
        macropad.display.auto_refresh = True
        screen_off = False

    if flash_index is not None and now>flash_until:
        flash_index=None
    update_breathing(); time.sleep(0.02)
