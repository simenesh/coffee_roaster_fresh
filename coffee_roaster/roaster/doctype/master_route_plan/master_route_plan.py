import frappe
from frappe.utils.jinja import render_template

# This autoname function is likely for a DocType and is separate from the report logic.
# It should remain as is if it's in the correct file (e.g., master_route_plan.py).
def autoname(doc, method=None):
    if not doc.route_order:
        doc.route_order = 0

# If this code is for a Script Report, it should be structured like this:
def execute(filters=None):
    # ⚠️ NOTE: You must define 'columns' and fetch your 'data' here first.
    # This part was missing from your code. I've added an example placeholder.
    columns = [
        {"label": "Sub City", "fieldname": "sub_city", "width": 170},
        {"label": "Route No", "fieldname": "route_no", "width": 50},
        {"label": "Day", "fieldname": "day", "width": 90},
        {"label": "Area", "fieldname": "area"},
        {"label": "RT", "fieldname": "rt", "width": 65},
        {"label": "WS", "fieldname": "ws", "width": 65},
        {"label": "MM", "fieldname": "mm", "width": 65},
        {"label": "SM", "fieldname": "sm", "width": 65},
        {"label": "Total", "fieldname": "total", "width": 70},
    ]

    # Fetch your data using frappe.db.sql or frappe.get_all, for example:
    data = [] # Replace with your actual database query

    # --- Excel-style print layout (HTML injected in "message") ---
    PRINT_TPL = """
    <style>
      .mrp-wrap { font-family: Arial, sans-serif; }
      .mrp-title { font-weight: 700; font-size: 20px; text-align:center; border-bottom:1px solid #000; padding:6px 0; }
      /* ... rest of your CSS ... */
    </style>

    <div class="mrp-wrap">
      <div class="mrp-title">MASTER ROUTE PLAN BY SUB CITY</div>
      <div class="mrp-subtitle">Distrributor - {{ distributor or "-" }}</div>
      <table class="mrp-table">
        </table>
    </div>
    """

    message_html = render_template(
        PRINT_TPL,
        {
            "distributor": filters.get("distributor"),
            "rows": data
        }
    )

    # This return is now correctly inside the 'execute' function
    return columns, data, message_html# Build the rows list from your data (rename keys if different)
# Expecting each row dict to have: sub_city, route_no, day, area, rt, ws, mm, sm
# If your report's `data` already matches, you can pass it directly.
def get_master_route_plan(columns, data, filters):
    message_html = render_template(
        PRINT_TPL,
        {
            "distributor": filters.get("distributor"),
            "rows": data  # your report rows
        }
    )
    # Return BOTH: normal columns/data (for on‑screen grid) + printable message
    return columns, data, message_html
