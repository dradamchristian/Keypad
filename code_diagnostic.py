# Diagnostic loader (CP 9.2.8): sets display.root_group instead of show()
import os, time
from adafruit_macropad import MacroPad
from adafruit_display_text import label
import terminalio, displayio

m = MacroPad()
d = m.display
g = displayio.Group()
t = label.Label(terminalio.FONT, text="Checking...", color=0xFFFFFF)
t.anchored_position = (2,0); g.append(t)
d.root_group = g  # <- updated API

def show(msg):
    t.text = msg[:20]
    print(msg)

mf = [f for f in os.listdir("/macros") if f.endswith(".py")]
mf.sort()
for fname in mf:
    p = "/macros/" + fname
    try:
        show("Compiling " + fname)
        src = open(p, "r").read()
        code = compile(src, p, "exec")
        ns = {}; exec(code, ns)
        show("OK: " + ns.get("app", {}).get("name", fname))
        time.sleep(0.2)
    except Exception as e:
        show("ERROR in " + fname)
        raise

show("Done. Restore code.py")
while True:
    time.sleep(0.1)
