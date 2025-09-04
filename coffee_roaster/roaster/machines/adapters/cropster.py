import csv, io, json

def detect(filename: str, head: str) -> bool:
    blob = (filename or "") + " " + (head or "")
    s = blob.lower()
    return "cropster" in s or any(k in s for k in ["bean temp","rate of rise","first crack","yellow"])

def parse(content: bytes, filename: str) -> dict:
    text = content.decode("utf-8", errors="ignore")
    # JSON?
    try:
        data = json.loads(text)
        pts = data.get("curve") or data.get("points") or []
        evs = data.get("events") or []
        rows = [{"t": _to_sec(p.get("t") or p.get("time")),
                 "bt": _flt(p.get("bt") or p.get("bean_temp")),
                 "et": _flt(p.get("et") or p.get("env_temp")),
                 "ror": _flt(p.get("ror"))} for p in pts]
        events = [{"type": (e.get("type") or e.get("name")),
                   "t": _to_sec(e.get("t") or e.get("time")),
                   "temp": _flt(e.get("temp") or e.get("bt"))} for e in evs]
        return {"points": rows, "events": events}
    except Exception:
        pass

    # CSV
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    rows, events = [], []
    for r in reader:
        t = _to_sec(_pick(r, ["time","sec","elapsed"]))
        bt = _flt(_pickv(r, ["bean temp","bt","bean_temp"]))
        et = _flt(_pickv(r, ["env temp","et","environment"]))
        ror= _flt(_pickv(r, ["rate of rise","ror"]))
        rows.append({"t": t, "bt": bt, "et": et, "ror": ror})
        # Cropster exports often have separate event sheets; if present in same CSV, map generically
        ev = _pickv(r, ["event","event name"])
        if ev:
            events.append({"type": ev, "t": t, "temp": bt})
    return {"points": rows, "events": events}

def _pickv(r, cands):
    for c in cands:
        for k, v in r.items():
            if k and k.lower() == c:
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
