import csv, io

def detect(filename: str, head: str) -> bool:
    return "probat" in (filename or "").lower() or "probat" in (head or "").lower()

def parse(content: bytes, filename: str) -> dict:
    text = content.decode("utf-8", errors="ignore")
    f = io.StringIO(text)
    reader = csv.DictReader(f, delimiter=";")  # Probat Pilot often uses ';'
    rows, events = [], []
    for r in reader:
        t  = _to_sec(_pickv(r, ["Time","time"]))
        bt = _flt(_pickv(r, ["BeanTemp","Bean Temperature","BT"]))
        et = _flt(_pickv(r, ["ExhaustTemp","Environmental","ET"]))
        ror= _flt(_pickv(r, ["RoR","RateOfRise"]))
        ev = _pickv(r, ["Event","Marker"])
        rows.append({"t": t, "bt": bt, "et": et, "ror": ror})
        if ev:
            events.append({"type": ev, "t": t, "temp": bt})
    return {"points": rows, "events": events}

def _pickv(r, names):
    for n in names:
        for k, v in r.items():
            if k and k.strip().lower() == n.lower():
                return v
    return None

def _flt(x):
    try: return float(str(x).strip())
    except Exception: return None

def _to_sec(v):
    if v is None: return None
    s = str(v).strip()
    if ":" in s:
        mm, ss = s.split(":")[-2:]
        return int(float(mm))*60 + int(float(ss))
    try:
        return int(float(s))
    except Exception:
        return None
