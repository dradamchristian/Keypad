# MacroPad configuration for CircuitPython 9.2.8
# Breathing LEDs per-layer + idle dim + OLED sleep/wake + reporting helpers

import os, time, math, displayio, terminalio
from adafruit_display_text import label
from adafruit_macropad import MacroPad
from adafruit_hid.keycode import Keycode

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
IDLE_TIMEOUT          = 240.0
IDLE_RAMP             = 2.0
IDLE_MIN              = 0.15

# --- Screen blanking ---
SCREEN_OFF_TIMEOUT    = 3.0

# --- Setup ---
macropad = MacroPad()
display = macropad.display

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

# --- Helpers ---
def _mix(a, b, t): return a + (b - a) * t

def set_base_color(color):
    global base_color
    base_color = int(color) & 0xFFFFFF

def note_activity():
    global last_activity, screen_off
    last_activity = time.monotonic()
    if screen_off:
        try:
            macropad.display.wake()
        except AttributeError:
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

# --- Text typing (UK £ fix) ---
PUNCT_FLUSH = set(' \n\t.,;:!?)]}')

def send_text_uk(text):
    i = 0
    word = []
    def flush_word():
        if word:
            macropad.keyboard_layout.write("".join(word))
            word.clear()
            time.sleep(TYPE_CHAR_DELAY)
    while i < len(text):
        ch = text[i]
        if ch == '£':
            flush_word()
            macropad.keyboard.press(Keycode.SHIFT, Keycode.THREE)
            macropad.keyboard.release_all()
            time.sleep(TYPE_CHAR_DELAY)
            i += 1; continue
        word.append(ch)
        time.sleep(TYPE_CHAR_DELAY)
        if len(word) >= WORD_FLUSH_MAX_CHARS:
            flush_word()
        if ch in PUNCT_FLUSH:
            flush_word()
            if ch == ' ':   time.sleep(TYPE_SPACE_DELAY)
            elif ch == '\n': time.sleep(TYPE_NEWLINE_DELAY)
            elif ch in '.!?': time.sleep(TYPE_SENTENCE_DELAY)
        i += 1
    flush_word()

def drain_key_events(dt=0.05):
    t0 = time.monotonic()
    while time.monotonic() - t0 < dt:
        if not macropad.keys.events.get():
            time.sleep(0.005)

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
        mlh1=pms2=msh2=msh6="Retained"; msi_line="No MSI."
    else:
        mlh1=choose_simple("MLH1",["Retained","Lost"])
        pms2=choose_simple("PMS2",["Retained","Lost"])
        msh2=choose_simple("MSH2",["Retained","Lost"])
        msh6=choose_simple("MSH6",["Retained","Lost"])
        msi_line="MSI present."
    lines=["BIOMARKER REPORT","",f"HER2: {her2_score} ({her2_interp})","",f"PD-L1 CPS {cps}%{tps_part}","",
           "MMR:",f"MLH1: {mlh1}",f"PMS2: {pms2}",f"MSH2: {msh2}",f"MSH6: {msh6}",msi_line,"","Reported by: Dr Adam Christian"]
    send_text_uk("\n".join(lines))

# --- Run sequence ---
def run_sequence(seq):
    for item in seq:
        if callable(item): item(); continue
        if isinstance(item,float): time.sleep(item)
        elif isinstance(item,tuple):
            chord=[]; 
            for k in item:
                if isinstance(k,str) and k.startswith("Keycode."): chord.append(getattr(Keycode,k.split(".",1)[1]))
                elif isinstance(k,int): chord.append(k)
            if chord: macropad.keyboard.send(*chord); time.sleep(0.05)
        elif isinstance(item,int): macropad.keyboard.send(item); time.sleep(0.05)
        elif isinstance(item,str):
            if item.startswith("Keycode."): macropad.keyboard.send(getattr(Keycode,item.split(".",1)[1])); time.sleep(0.05)
            else: send_text_uk(item)
        elif isinstance(item,dict) and "choose" in item:
            cfg=item["choose"]; choose_and_type(cfg.get("title","Choose"),cfg["template"],cfg["options"])
        elif isinstance(item,dict) and "choose_multi" in item:
            cfg=item["choose_multi"]; choose_multi(cfg.get("title","Choose"),cfg["template"],cfg["fields"])
        elif isinstance(item,dict) and "bio_wizard" in item: biomarker_wizard()

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
    app=ns.get("app",{"name":filename,"macros":[]})
    title.text=app.get("name",filename)
    for i in range(12):
        key_labels[i].text=app["macros"][i][1] if i<len(app["macros"]) else ""
    set_base_color(app["macros"][0][0] if app["macros"] else 0x202020)
    note_activity(); update_breathing()

load_layer(current_index)

# --- Main loop ---
while True:
    now=time.monotonic()
    ev=macropad.keys.events.get()
    if ev and ev.pressed and (not is_running) and now>=cooldown_until:
        i=ev.key_number
        if i<len(app["macros"]):
            is_running=True; _,_,seq=app["macros"][i]
            flash_key(i); note_activity()
            try: run_sequence(seq)
            finally:
                is_running=False; cooldown_until=time.monotonic()+0.30; note_activity()

    pos=macropad.encoder
    if pos!=last_pos and (not is_running):
        delta=pos-last_pos; last_pos=pos
        current_index=(current_index+delta)%len(macro_files)
        load_layer(current_index); note_activity()

    # --- Screen blanking with OLED sleep/wake ---
    idle_time=now-last_activity
    if idle_time>SCREEN_OFF_TIMEOUT and not screen_off:
        try:
            macropad.display.sleep()   # true OLED power down
        except AttributeError:
            macropad.display.auto_refresh=False
            macropad.display.root_group=displayio.Group()
        screen_off=True
    elif idle_time<=SCREEN_OFF_TIMEOUT and screen_off:
        try:
            macropad.display.wake()    # power back on
            macropad.display.root_group=group
        except AttributeError:
            macropad.display.root_group=group
            macropad.display.auto_refresh=True
        screen_off=False

    if flash_index is not None and now>flash_until: flash_index=None
    update_breathing(); time.sleep(0.02)
