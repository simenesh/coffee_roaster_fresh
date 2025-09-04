import json
import frappe
from frappe.utils import get_datetime, format_datetime

def execute(filters=None):
    filters = filters or {}
    rb_name = filters.get("roast_batch") or filters.get("name") or filters.get("rb_name")
    if not rb_name:
        frappe.throw("Please pick a Roast Batch in the report filter.")

    # Columns
    columns = [
        {"label": "Round #", "fieldname": "round_no", "fieldtype": "Int", "width": 80},
        {"label": "Logs", "fieldname": "logs", "fieldtype": "Int", "width": 80},
        {"label": "Start", "fieldname": "start", "fieldtype": "Datetime", "width": 180},
        {"label": "End", "fieldname": "end", "fieldtype": "Datetime", "width": 180},
        {"label": "Duration (s)", "fieldname": "duration_s", "fieldtype": "Int", "width": 110}
    ]

    # Data via API (keeps logic in one place)
    data = []
    out = frappe.get_attr("coffee_roaster.coffee_roaster.api.get_round_machine_data")(rb_name)
    for rn, logs in sorted(out.items(), key=lambda x: x[0]):
        start = get_datetime(logs[0]["timestamp"]) if logs else None
        end   = get_datetime(logs[-1]["timestamp"]) if logs else None
        dur_s = int((end - start).total_seconds()) if (start and end) else 0
        data.append({
            "round_no": rn,
            "logs": len(logs),
            "start": format_datetime(start) if start else None,
            "end": format_datetime(end) if end else None,
            "duration_s": dur_s
        })
    return columns, data
