import frappe
from frappe import _

def validate_item(doc, method):
    """Validate that a default warehouse is set for stock items."""
    if not hasattr(doc, 'maintain_stock'):
        return

    if doc.maintain_stock and not doc.default_warehouse:
        frappe.throw(_("Default Warehouse is required for stock item: {0}").format(doc.item_code))

def validate_warehouse(doc, method):
    """Ensure warehouse has a company set."""
    if not doc.company:
        frappe.throw(_("Company is required"))

def check_warehouse_empty(doc, method):
    """Prevent deletion if warehouse contains stock."""
    stock_balance = frappe.db.get_value(
        "Stock Ledger Entry",
        filters={"warehouse": doc.name},
        fieldname="SUM(actual_qty)"
    )

    if stock_balance and stock_balance > 0:
        frappe.throw(
            _("Cannot delete {0}: {1} units still in stock").format(doc.name, stock_balance),
            title=_("Warehouse Not Empty")
        )

def validate_phase_times(doc, method):
    """Ensure end time is after start time."""
    if doc.end_time <= doc.start_time:
        frappe.throw(_("End Time must be after Start Time"))

def calculate_weight_loss(doc, method):
    """Calculate roast weight loss."""
    if not doc.input_weight or not doc.output_weight:
        doc.weight_loss = 0
        doc.weight_loss_percentage = 0
        return

    if doc.output_weight > doc.input_weight:
        frappe.throw(_("Output weight cannot be greater than input weight."))

    doc.weight_loss = doc.input_weight - doc.output_weight
    doc.weight_loss_percentage = (
        (doc.weight_loss / doc.input_weight) * 100
        if doc.input_weight else 0
    )

def create_stock_entry_from_roasted(roasted_name):
    """Create a Material Receipt Stock Entry from Roasted Coffee record."""
    roasted = frappe.get_doc("Roasted Coffee", roasted_name)

    if not roasted.item:
        frappe.throw(_("Roasted Coffee must have an Item Code."))
    if not roasted.warehouse:
        frappe.throw(_("Roasted Coffee must have a Warehouse."))
    if not roasted.quantity:
        frappe.throw(_("Roasted Coffee must have a Quantity."))

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Receipt"
    stock_entry.purpose = "Material Receipt"
    stock_entry.to_warehouse = roasted.warehouse

    stock_entry.append("items", {
        "item_code": roasted.item,
        "qty": roasted.quantity,
        "uom": "Gram",  # change to "Kg" if that's your UOM
        "conversion_factor": 1,
        "t_warehouse": roasted.warehouse
    })

    stock_entry.insert()
    stock_entry.submit()

    roasted.db_set("status", "In Stock")

    frappe.msgprint(
        _("Stock Entry {0} created for Roasted Coffee {1}")
        .format(stock_entry.name, roasted.name)
    )

import frappe, math, datetime

def _dist(a, b):
    # Fast Euclidean (good enough intra-city). For longer routes, switch to haversine.
    return math.hypot((a[0]-b[0]), (a[1]-b[1]))

def _nearest_neighbor(points, start=None):
    """
    points: list[dict] with keys lat, lng, and any payload fields
    start:  (lat, lng) tuple or None
    returns list[dict] in visiting order
    """
    if not points:
        return []
    unvisited = points[:]
    route = []
    if start is not None:
        cur = min(unvisited, key=lambda p: _dist(start, (p["lat"], p["lng"])))
    else:
        cur = unvisited[0]
    route.append(cur); unvisited.remove(cur)
    while unvisited:
        nxt = min(unvisited, key=lambda p: _dist((cur["lat"], cur["lng"]), (p["lat"], p["lng"])))
        route.append(nxt); unvisited.remove(nxt); cur = nxt
    return route

def _weekday_name(iso_date_str):
    # Returns 'Monday', 'Tuesday', ...
    d = datetime.date.fromisoformat(iso_date_str)
    return d.strftime("%A")

@frappe.whitelist()
@frappe.whitelist()
def build_route_from_rtm(sub_cities=None, date=None, marketer=None):
    # convert JSON from client to Python where needed
    sub_cities = sub_cities or []
    # ... your logic here ...
    # return a dict with a 'stops' list of rows
    return {
        "stops": [
            # {"seq": 1, "rtm_assignment": "...", "customer": "...", ...}
        ]
    }
    
    # ---- normalize inputs ----
    if isinstance(sub_cities, str):
        sub_cities = [s.strip() for s in sub_cities.split(",") if s.strip()]
    weekday = _weekday_name(date) if date else None
    start = None
    try:
        if depot_lat is not None and depot_lng is not None:
            start = (float(depot_lat), float(depot_lng))
    except Exception:
        start = None

    # ---- base query ----
    filters = {"active": 1}
    if sub_cities:
        filters["sub_city"] = ["in", sub_cities]
    if marketer:
        filters["marketer"] = marketer

    rows = frappe.get_all(
        "RTM Assignment",
        filters=filters,
        fields=[
            "name as rtm_name",
            "customer","customer_name","sub_city",
            "latitude","longitude",
            "rtm_channel","outlet_type",
            "marketer","visit_frequency","visit_day","priority"
        ],
        order_by="sub_city asc, priority asc, customer_name asc"
    )

    # ---- post-filter by weekday ----
    if weekday:
        keep = []
        for r in rows:
            vf = (r.get("visit_frequency") or "").strip()
            vd = r.get("visit_day")
            if vf == "Daily":
                keep.append(r)
            elif vf == "Weekly" and vd == weekday:
                keep.append(r)
        rows = keep

    # ---- sanitize coords, group all points (we’ll solve in one pass) ----
    points = []
    for r in rows:
        try:
            lat = float(r["latitude"] or 0); lng = float(r["longitude"] or 0)
        except Exception:
            lat = 0; lng = 0
        if not lat or not lng:
            # skip missing geo; you can choose to include and place at end
            continue
        r["lat"], r["lng"] = lat, lng
        points.append(r)

    if not points:
        return {"weekday": weekday, "stops": []}

    # ---- order all by nearest-neighbor (optionally starting at depot) ----
    ordered = _nearest_neighbor(points, start=start)

    # ---- emit Route Plan rows (seq + fields your child table expects) ----
    out = []
    seq = 1
    for p in ordered:
        out.append({
            "seq": seq,
            "rtm_assignment": p["rtm_name"],
            "customer": p["customer"],
            "customer_name": p["customer_name"],
            "sub_city": p["sub_city"],
            "latitude": p["lat"],
            "longitude": p["lng"],
            "rtm_channel": p.get("rtm_channel"),
            "outlet_type": p.get("outlet_type"),
            "marketer": p.get("marketer"),
            "priority": p.get("priority"),
        })
        seq += 1

    return {"weekday": weekday, "stops": out}

# API helpers for Coffee Roaster
import re
import json
import frappe
from frappe.utils import get_datetime

@frappe.whitelist()
def get_round_machine_data(rb_name: str) -> dict:
    """Return {round_no: [logs]} for the given Roast Batch.
    Strategy A: group Coffee Roasting Log rows whose log_name ends with -R##.
    Strategy B: if no tagging, partition charge_start..development_end into N equal windows.
    Assumes an existing DocType "Coffee Roasting Log" with fields:
      - roast_batch (Link), log_name (Data), timestamp (Datetime), data_json (Long Text / JSON)
    """
    if not rb_name:
        frappe.throw("rb_name is required")

    rb = frappe.get_doc("Roast Batch", rb_name)
    rounds = rb.get("rounds") or []
    n = len(rounds)
    out = {i + 1: [] for i in range(n)}
    if n == 0:
        return out

    logs = frappe.get_all(
        "Coffee Roasting Log",
        fields=["name", "log_name", "timestamp", "data_json"],
        filters={"roast_batch": rb_name},
        order_by="timestamp asc"
    )

    # Try Strategy A: suffix -R## in log_name
    got_any = False
    for l in logs:
        ln = (l.get("log_name") or "").strip()
        m = re.search(r"-R(\d{1,2})$", ln)
        if m:
            rn = int(m.group(1))
            if 1 <= rn <= n:
                out[rn].append(l)
                got_any = True
    if got_any:
        return out

    # Strategy B: equal time windows from charge_start..development_end (or charge_end)
    start = rb.get("charge_start") or rb.get("roast_date")
    end   = rb.get("development_end") or rb.get("charge_end") or rb.get("roast_date")
    if not (start and end):
        return out

    start_ts = get_datetime(start)
    end_ts = get_datetime(end)
    total = (end_ts - start_ts).total_seconds()
    if total <= 0:
        return out

    def bucket(ts):
        rel = (get_datetime(ts) - start_ts).total_seconds() / total
        idx = max(0, min(n - 1, int(rel * n)))
        return idx + 1

    for l in logs:
        rn = bucket(l["timestamp"])
        out[rn].append(l)

    return out
