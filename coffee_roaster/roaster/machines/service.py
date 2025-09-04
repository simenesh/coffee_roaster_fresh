import frappe, io
from typing import Optional, Tuple
from .adapters import artisan, cropster, probat

ADAPTERS = [
    ("artisan", artisan),
    ("cropster", cropster),
    ("probat", probat),
]

def _detect_adapter(filename: str, head_text: str):
    for name, mod in ADAPTERS:
        try:
            if mod.detect(filename, head_text):
                return name, mod
        except Exception:
            continue
    return "artisan", artisan  # safe default

def _read_head(content: bytes, n=1024) -> str:
    return content[:n].decode("utf-8", errors="ignore")

def _sec_to_timestr(sec: Optional[int]) -> Optional[str]:
    if sec is None: return None
    m, s = divmod(int(sec), 60)
    return f"{m:02d}:{s:02d}"

def _first(events, *names) -> Optional[dict]:
    want = {n.lower() for n in names}
    for e in (events or []):
        t = (e.get("type") or "").lower()
        if any(w in t for w in want):
            return e
    return None

def _compute_phases(points, events) -> Tuple[list, dict]:
    """Return (phases, metrics) where phases = list of {phase,start_time,end_time,temperature_c,...}."""
    # Heuristics:
    t0 = 0
    fc_s = _first(events, "FCs", "first crack start", "first crack")
    fc_e = _first(events, "FCe", "first crack end")
    yel  = _first(events, "yellow", "dry end", "color change")
    drop = _first(events, "drop", "end", "eject")

    # Fallbacks if events missing
    last_t = max([p.get("t") or 0 for p in (points or [])] + [fc_s.get("t") if fc_s else 0, fc_e.get("t") if fc_e else 0])
    if not drop: drop = {"t": last_t}
    # naive yellow at ~4m if unavailable
    if not yel: yel = {"t": min(240, (fc_s.get("t") if fc_s else last_t//2 or 240))}

    phases = []
    def add(name, start, end):
        if start is None or end is None or end <= start: return
        phases.append({
            "phase": name,
            "start_time": _sec_to_timestr(start),
            "end_time": _sec_to_timestr(end),
            "temperature_c": None,
            "observations": None
        })

    add("Drying", t0, yel.get("t"))
    add("Maillard", yel.get("t"), (fc_s or {"t": drop.get("t")}).get("t"))
    if fc_s:
        add("First Crack", fc_s.get("t"), (fc_e or {"t": min(drop.get("t"), (fc_s.get("t") or 0) + 120)}).get("t"))
        add("Development", (fc_s.get("t")), drop.get("t"))

    metrics = {
        "first_crack_start": _sec_to_timestr(fc_s.get("t")) if fc_s else None,
        "first_crack_end": _sec_to_timestr(fc_e.get("t")) if fc_e else None,
        "development_time": _sec_to_timestr((drop.get("t") - fc_s.get("t")) if (fc_s and drop) else None),
        "roast_time": _sec_to_timestr(drop.get("t") if drop else last_t)
    }
    return phases, metrics

def import_curve_into_log(doctype: str, name: str, *, filename: Optional[str]=None, content: Optional[bytes]=None, file_url: Optional[str]=None, adapter: Optional[str]=None) -> dict:
    """Parse a machine file and write phases + metrics into Coffee Roasting Log."""
    if doctype != "Coffee Roasting Log":
        frappe.throw("Only Coffee Roasting Log is supported")
    doc = frappe.get_doc(doctype, name)

    if file_url and not content:
        from frappe.utils.file_manager import get_file
        _, content = get_file(file_url)

    if not content:
        frappe.throw("No content to import. Provide file_url or content.")

    head = _read_head(content)
    chosen = None
    if adapter:
        for nm, mod in ADAPTERS:
            if adapter == nm:
                chosen = (nm, mod); break
    if not chosen:
        chosen = _detect_adapter(filename or "", head)
    adapter_name, mod = chosen

    parsed = mod.parse(content, filename or "")
    points, events = parsed.get("points") or [], parsed.get("events") or []
    phases, metrics = _compute_phases(points, events)

    # write phases
    doc.roast_phases = []
    for p in phases:
        row = doc.append("roast_phases", {})
        row.phase = p["phase"]
        row.start_time = p["start_time"]
        row.end_time = p["end_time"]
        row.temperature_c = p["temperature_c"]
        row.observations = p["observations"]

    # write metrics if fields exist
    for f, v in {
        "first_crack_start": metrics.get("first_crack_start"),
        "first_crack_end": metrics.get("first_crack_end"),
        "development_time": metrics.get("development_time"),
        "roast_time": metrics.get("roast_time"),
    }.items():
        if v and frappe.db.has_column("Coffee Roasting Log", f):
            setattr(doc, f, v)

    doc.save()
    return {"adapter": adapter_name, "points": len(points), "events": len(events), "phases": len(phases)}
