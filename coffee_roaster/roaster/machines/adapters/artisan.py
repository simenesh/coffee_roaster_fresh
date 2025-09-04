import csv, io, json

def detect(filename: str, head: str) -> bool:
    fn = (filename or "").lower()
    if fn.endswith(".alog") or fn.endswith(".json"):
        try:
            j = json.loads(head)
            return "artisan" in json.dumps(j).lower() or "roast" in j
        except Exception:
            return False
    # CSV: headers often include BT, ET, Event, Time
    return any(k in head.lower() for k in ["bt", "bean", "time","event","et"])

def parse(content: bytes, filename: str) -> dict:
    text = content.decode("utf-8", errors="ignore")
    # try JSON first
    try:
        data = json.loads(text)
        # flexible: data may be list of points or dict with 'points'
        points = data if isinstance(data, list) else data.get("points", [])
        rows = []
        events = []
        for p in points:
            t = p.get("time") or p.get("t") or p.get("sec")
            bt = p.get("BT") or p.get("bean") or p.get("bean_temp")
            et = p.get("ET") or p.get("env") or p.get("environment")
            ror = p.get("RoR") or p.get("ror")
            ev = p.get("event")
            rows.append({"t": _to_sec(t), "bt": _flt(bt), "et": _flt(et), "ror": _flt(ror)})
            if ev:
                events.append({"type": str(ev), "t": _to_sec(t), "temp": _flt(bt)})
        return {"points": rows, "events": events}
    except Exception:
        pass

    # CSV fallback
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    rows, events = [], []
    # normalize header keys
    for r in reader:
        t = _pick(r, ["time","sec","t","elapsed","time (s)","time(s)"])
        bt = _pick(r, ["bt","bean","bean temp","bean_temp","bean temperature"])
        et = _pick(r, ["et","env","environment","env temp","exhaust"])
        ror= _pick(r, ["ror","rate of rise","rate_of_rise"])
        ev = _pick(r, ["event","flag","mark"])
        ts = _to_sec(r.get(t))
        rows.append({"t": ts, "bt": _flt(r.get(bt)), "et": _flt(r.get(et)), "ror": _flt(r.get(ror))})
        if ev and r.get(ev):
            events.append({"type": r.get(ev), "t": ts, "temp": _flt(r.get(bt))})
    return {"points": rows, "events": events}

def _pick(row, names):
    keys = [k for k in (row.keys() if hasattr(row,"keys") else [])]
    for n in names:
        for k in keys:
            if k and k.strip().lower() == n.lower():
                return k
    return None

def _flt(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None

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
