from __future__ import annotations
import re, datetime
from math import radians, sin, cos, asin, sqrt
import frappe

# Fixed outlet columns
BUCKETS = ["GOV","NGO","EMB","CORP","EDU","SMKT","EXPO","RETAIL","DIST","CAF","HOTEL","REST"]
WEEKDAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# ---------- helpers ----------
def _listify(v):
    if not v: return []
    if isinstance(v,(list,tuple,set)): return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v,str): return [p.strip() for p in re.split(r"[,\n]+", v) if p.strip()]
    return []

def _weekday_from_date(dstr: str | None) -> str:
    if not dstr: return "Monday"
    try: return datetime.date.fromisoformat(str(dstr)).strftime("%A")
    except Exception: return "Monday"

def _hav(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi  = radians(lat2 - lat1)
    dlmb  = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(p1)*cos(p2)*sin(dlmb/2)**2
    return 2*R*asin(sqrt(a))

def _nearest_neighbor(points):
    if not points:
        return []

    # start with the first point
    un = points[:]       # clone list
    route = [un[0]]      # first element is starting point
    un = un[1:]          # remove it from unvisited

    while un:
        last = route[-1]
        # find nearest neighbor by distance
        next_point = min(un, key=lambda p: (p['lat']-last['lat'])**2 + (p['lng']-last['lng'])**2)
        route.append(next_point)
        un.remove(next_point)

    return route

def _columns():
    cols = [
        {"label": "SubCity", "fieldname": "sub_city", "fieldtype": "Data", "width": 180},
        {"label": "Rout",    "fieldname": "rout",     "fieldtype": "Int",  "width": 50},
        {"label": "Day",     "fieldname": "day",      "fieldtype": "Data", "width": 90},
        {"label": "Area",    "fieldname": "area",     "fieldtype": "Data", "width": 600},
    ]
    cols += [{"label": b, "fieldname": b.lower(), "fieldtype": "Int", "width": 70} for b in BUCKETS]
    cols += [{"label": "Total", "fieldname": "total", "fieldtype": "Int", "width": 80}]
    return cols

# Strict, child-first mapper. Never guesses CORP unless text says CORP/CORPORATE.
def _bucket_from_text(v: str | None) -> str:
    if not v:
        return "RETAIL"
    key = str(v).strip().upper()

    # exact label wins
    if key in BUCKETS:
        return key

    # avoid false-corporate from generic words
    if key in {"COMPANY","INDIVIDUAL","OFFICE","HQ","HEAD OFFICE"}:
        return "RETAIL"

    # tolerant patterns (order matters)
    if "SUPERMARKET" in key or "HYPER" in key:                          return "SMKT"
    if "WHOLE" in key or "DISTRIB" in key or key == "WS":                return "DIST"
    if "CAFE" in key or "CAFÉ" in key or "COFFEE" in key:                return "CAF"
    if "RESTAURANT" in key:                                              return "REST"
    if "GOV" in key or "MINISTRY" in key or "MUNIC" in key:              return "GOV"
    if "NGO" in key or "FOUNDATION" in key or "CHARITY" in key:          return "NGO"
    if "EMBASSY" in key or "CONSUL" in key:                              return "EMB"
    if "SCHOOL" in key or "UNIVERSITY" in key or "COLLEGE" in key \
       or "ACADEMY" in key or "INSTITUTE" in key:                        return "EDU"
    if "HOTEL" in key or "RESORT" in key:                                return "HOTEL"
    if "CORPORATE" in key or "CORP" in key:                              return "CORP"
    if "SHOP" in key or "STORE" in key or "RETAIL" in key or "MART" in key \
       or "BOUTIQUE" in key or "MINIMARKET" in key or "MINI MARKET" in key:
        return "RETAIL"

    # default: never CORP by accident
    return "RETAIL"

# ---------- main ----------
def execute(filters=None):
    f = frappe._dict(filters or {})

    # Filters
    sub_cities = [s.strip().lower() for s in _listify(f.get("sub_city") or f.get("sub_cities"))]
    weekday_filter = (f.get("weekday") or "").strip() or None
    from_date = f.get("from_date")
    to_date   = f.get("to_date")

    # Build SELECT safely (only existing columns)
    d_has = lambda c: frappe.db.has_column("Route Plan Detail", c)
    c_has = lambda c: frappe.db.has_column("Customer", c)

    sel = [
        "p.name AS parent",
        "p.date AS parent_date",
        "d.customer", "d.customer_name",
    ]

    # sub_city (child first, else customer)
    if d_has("sub_city") and c_has("sub_city"):
        sel.append("COALESCE(NULLIF(d.sub_city,''), c.sub_city) AS sub_city")
    elif d_has("sub_city"):
        sel.append("d.sub_city AS sub_city")
    elif c_has("sub_city"):
        sel.append("c.sub_city AS sub_city")
    else:
        sel.append("NULL AS sub_city")

    # outlet_raw: child-first; then customer type/label
    src = []
    if d_has("bucket"):        src.append("NULLIF(d.bucket,'')")
    if d_has("outlet_type"):   src.append("NULLIF(d.outlet_type,'')")
    if d_has("channel"):       src.append("NULLIF(d.channel,'')")
    if d_has("rtm_channel"):   src.append("NULLIF(d.rtm_channel,'')")
    if c_has("outlet_type"):   src.append("NULLIF(c.outlet_type,'')")
    if c_has("outlet"):        src.append("NULLIF(c.outlet,'')")
    outlet_expr = "COALESCE(" + ", ".join(src) + ")" if src else "NULL"
    sel.append(f"{outlet_expr} AS outlet_raw")

    # coordinates: child → customer
    if d_has("latitude") and c_has("latitude"):
        sel.append("COALESCE(NULLIF(d.latitude,0), c.latitude) AS latitude")
    elif d_has("latitude"):
        sel.append("d.latitude AS latitude")
    elif c_has("latitude"):
        sel.append("c.latitude AS latitude")
    else:
        sel.append("NULL AS latitude")

    if d_has("longitude") and c_has("longitude"):
        sel.append("COALESCE(NULLIF(d.longitude,0), c.longitude) AS longitude")
    elif d_has("longitude"):
        sel.append("d.longitude AS longitude")
    elif c_has("longitude"):
        sel.append("c.longitude AS longitude")
    else:
        sel.append("NULL AS longitude")

    # order priority
    sel.append("d.order_priority" if d_has("order_priority") else "NULL AS order_priority")

    # area/notes text for the Area column
    if d_has("notes"):  sel.append("d.notes AS notes")
    elif d_has("area"): sel.append("d.area AS notes")
    else:               sel.append("NULL AS notes")

    select_sql = ", ".join(sel)

    # WHERE with inclusive date range
    where, params = ["COALESCE(p.docstatus,0) IN (0,1)"], {}
    if from_date:
        where.append("p.date >= %(from_date)s"); params["from_date"] = from_date
    if to_date:
        where.append("p.date <= %(to_date)s");   params["to_date"] = to_date
    where_sql = " AND ".join(where)

    rows = frappe.db.sql(
        f"""
        SELECT {select_sql}
        FROM `tabRoute Plan Detail` d
        JOIN `tabRoute Plan` p ON p.name = d.parent
        LEFT JOIN `tabCustomer` c ON c.name = d.customer
        WHERE {where_sql}
        ORDER BY p.date ASC, COALESCE(d.order_priority, 999999) ASC, d.customer_name ASC
        """,
        params, as_dict=True
    )

    # optional sub-city filter (case/space-insensitive)
    if sub_cities:
        rows = [r for r in rows if (r.get("sub_city") or "").strip().lower() in sub_cities]

    # Group → SubCity → Weekday (from parent date)
    by_sc = {}
    for r in rows:
        sc = (r.get("sub_city") or "").strip()
        wd = _weekday_from_date(r.get("parent_date"))
        if weekday_filter and wd != weekday_filter:
            continue
        by_sc.setdefault(sc, {}).setdefault(wd, []).append(r)

    columns, data = _columns(), []
    grand_totals = {b: 0 for b in BUCKETS}
    grand_total_all = 0

    for sc in sorted([k for k in by_sc.keys() if k], key=str.casefold):
        per_day = by_sc[sc]
        route_idx = 1

        for wd in WEEKDAYS:
            day_rows = per_day.get(wd, [])
            if not day_rows:
                continue

            # distance order using available coords (no start point needed)
            geo, no_geo = [], []
            for r in day_rows:
                try:
                    lat = float(r.get("latitude") or 0); lng = float(r.get("longitude") or 0)
                except Exception:
                    lat = lng = 0.0
                (geo if (lat and lng) else no_geo).append({**r, "lat": lat, "lng": lng})
            ordered = (_nearest_neighbor(geo) if geo else []) + no_geo

            # Area = notes/area only
            area_path = " - ".join([(r.get("notes") or "").strip() for r in ordered if (r.get("notes") or "").strip()])

            # bucket counts
            cnt = {b: 0 for b in BUCKETS}
            for r in ordered:
                cnt[_bucket_from_text(r.get("outlet_raw"))] += 1

            row_total = sum(cnt.values())
            for b in BUCKETS: grand_totals[b] += cnt[b]
            grand_total_all += row_total

            row = {"sub_city": sc if route_idx == 1 else "", "rout": route_idx,
                   "day": wd, "area": area_path, "total": row_total}
            for b in BUCKETS: row[b.lower()] = cnt[b]
            data.append(row)
            route_idx += 1

    # One final TOTAL only
    total_row = {"sub_city": "TOTAL", "rout": "", "day": "", "area": "", "total": grand_total_all}
    for b in BUCKETS: total_row[b.lower()] = grand_totals[b]
    if not data:
        return columns, [total_row], None, None
    data.append(total_row)
    return columns, data, None, None
