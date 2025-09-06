# -*- coding: utf-8 -*-
# Coffee Roaster → Roast Batch Profitability
# - Shows Draft/Submitted Roast Batches (configurable)
# - Optionally restricts to batches that HAVE a submitted Batch Cost
# - Fixes the 6 financial fields using Batch Cost (with robust fallbacks)
#
# Fields used:
#   Roast Batch: qty_to_roast/input_qty, output_qty/output_weight, selling_rate* (optional), roasted_item (Link Item)
#   Batch Cost : total_batch_cost, cost_per_kg, selling_rate, revenue, profit, profit_margin
#
import frappe
from frappe.utils import getdate

# ---------------- Public API ----------------
def execute(filters=None):
    filters = filters or {}

    # Range & selectors
    fd, td = _safe_date_range(filters.get("roast_date_range"))
    roast_batch = filters.get("roast_batch")

    # NEW filters (both optional)
    rb_docstatus = (filters.get("rb_docstatus") or "Both").strip()  # "Draft" | "Submitted" | "Both"
    only_submitted_bc = 1 if str(filters.get("only_submitted_batch_cost")).lower() in ("1", "true", "yes", "on") else 0

    columns = _get_columns()
    rows = _build_rows(fd, td, roast_batch, rb_docstatus, only_submitted_bc)
    summary = _build_summary(rows)
    return columns, rows, None, None, summary


# ---------------- Columns ----------------
def _get_columns():
    return [
        {"label": "Roast Batch", "fieldname": "roast_batch", "fieldtype": "Link", "options": "Roast Batch", "width": 180},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
        {"label": "Roast Date", "fieldname": "roast_date", "fieldtype": "Date", "width": 110},

        {"label": "Input Qty (kg)", "fieldname": "input_qty", "fieldtype": "Float", "width": 120},
        {"label": "Output Qty (kg)", "fieldname": "output_qty", "fieldtype": "Float", "width": 120},
        {"label": "Yield (%)", "fieldname": "yield_pct", "fieldtype": "Percent", "width": 100},

        # Fixed financials (computed from Batch Cost with fallbacks)
        {"label": "Unit Cost (ETB/kg)", "fieldname": "unit_cost", "fieldtype": "Currency", "options": "ETB", "width": 130},
        {"label": "Total Cost (ETB)", "fieldname": "total_cost", "fieldtype": "Currency", "options": "ETB", "width": 130},
        {"label": "Selling Rate (ETB/kg)", "fieldname": "selling_rate", "fieldtype": "Currency", "options": "ETB", "width": 150},
        {"label": "Revenue (ETB)", "fieldname": "revenue", "fieldtype": "Currency", "options": "ETB", "width": 130},
        {"label": "Profit (ETB)", "fieldname": "profit", "fieldtype": "Currency", "options": "ETB", "width": 130},
        {"label": "Profit Margin (%)", "fieldname": "profit_margin", "fieldtype": "Percent", "width": 140},
    ]


# ---------------- Data ----------------
def _build_rows(fd, td, roast_batch, rb_docstatus="Both", only_submitted_bc=0):
    # Roast Batch docstatus condition
    if rb_docstatus == "Draft":
        rb_doc_cond = "rb.docstatus = 0"
    elif rb_docstatus == "Submitted":
        rb_doc_cond = "rb.docstatus = 1"
    else:
        rb_doc_cond = "rb.docstatus IN (0,1)"

    conds, params = [rb_doc_cond], {}
    if fd and td:
        conds.append("rb.roast_date BETWEEN %(fd)s AND %(td)s"); params.update({"fd": fd, "td": td})
    elif fd:
        conds.append("rb.roast_date >= %(fd)s"); params["fd"] = fd
    elif td:
        conds.append("rb.roast_date <= %(td)s"); params["td"] = td
    if roast_batch:
        conds.append("rb.name = %(rb)s"); params["rb"] = roast_batch

    # Optionally require a submitted Batch Cost
    if only_submitted_bc:
        conds.append("""
            EXISTS (
                SELECT 1
                FROM `tabBatch Cost` bc
                WHERE bc.batch_no = rb.name
                  AND bc.docstatus = 1
            )
        """)

    where_sql = " AND ".join(conds) if conds else "1=1"

    base = frappe.db.sql(
        f"""
        SELECT rb.name AS roast_batch, rb.company, rb.roast_date
        FROM `tabRoast Batch` rb
        WHERE {where_sql}
        ORDER BY rb.roast_date DESC, rb.name DESC
        """,
        params,
        as_dict=True,
    ) or []

    rows = []
    for rb in base:
        rb_name = rb["roast_batch"]

        # Quantities from RB (support common alternates)
        input_qty  = _pick_rb(rb_name, ["qty_to_roast","input_qty","input_weight"], 0.0)
        output_qty = _pick_rb(rb_name, ["output_qty","output_weight","finished_weight"], 0.0)
        yield_pct  = (float(output_qty) / float(input_qty) * 100.0) if input_qty else None

        # Prefer submitted Batch Cost; else latest any-status for graceful backfill
        bc = (frappe.db.get_value(
            "Batch Cost", {"batch_no": rb_name, "docstatus": 1},
            ["total_batch_cost","cost_per_kg","selling_rate","revenue","profit","profit_margin"],
            as_dict=True
        ) or frappe.db.get_value(
            "Batch Cost", {"batch_no": rb_name},
            ["total_batch_cost","cost_per_kg","selling_rate","revenue","profit","profit_margin"],
            as_dict=True
        ) or {})

        total_cost   = float(bc.get("total_batch_cost") or 0)
        unit_cost    = float(bc.get("cost_per_kg") or (total_cost / float(output_qty) if output_qty else 0))

        # Selling rate: BC → RB field → Item Price for roasted_item
        selling_rate = float(bc.get("selling_rate") or _selling_rate_from_rb_or_item(rb_name))

        # Revenue/Profit/Margin: BC values if present; else compute
        revenue = float(bc.get("revenue") or (selling_rate * float(output_qty)))
        profit  = float(bc.get("profit")  or (revenue - total_cost))
        margin  = float(bc.get("profit_margin") or ((profit / revenue * 100.0) if revenue else 0))

        rows.append({
            "roast_batch": rb_name,
            "company": rb["company"],
            "roast_date": rb["roast_date"],
            "input_qty": input_qty,
            "output_qty": output_qty,
            "yield_pct": yield_pct,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "selling_rate": selling_rate,
            "revenue": revenue,
            "profit": profit,
            "profit_margin": margin,
        })

    return rows


# ---------------- Helpers ----------------
def _pick_rb(rb_name, fields, default=None):
    """Return first non-empty RB field value among a list of candidates."""
    for f in fields:
        if frappe.db.has_column("Roast Batch", f):
            v = frappe.db.get_value("Roast Batch", rb_name, f)
            if v not in (None, ""):
                return v
    return default


def _selling_rate_from_rb_or_item(rb_name: str) -> float:
    # 1) direct selling fields on RB (if you have them)
    for f in ["selling_rate", "selling_price", "price_per_kg", "rate", "price"]:
        if frappe.db.has_column("Roast Batch", f):
            v = frappe.db.get_value("Roast Batch", rb_name, f)
            if v:
                return float(v)

    # 2) use roasted_item (finished good) for Item Price fallback
    item = None
    for f in ["roasted_item", "item_code", "product"]:
        if frappe.db.has_column("Roast Batch", f):
            item = frappe.db.get_value("Roast Batch", rb_name, f)
            if item:
                break

    # 3) Item Price (selling) — optional price list awareness
    if item and frappe.db.table_exists("tabItem Price"):
        where = {"item_code": item, "selling": 1}
        for pf in ["selling_price_list", "price_list"]:
            if frappe.db.has_column("Roast Batch", pf):
                pl = frappe.db.get_value("Roast Batch", rb_name, pf)
                if pl:
                    where["price_list"] = pl
                    break
        rate = frappe.db.get_value("Item Price", where, "price_list_rate")
        return float(rate or 0)

    return 0.0


def _safe_date_range(val):
    if not val:
        return None, None
    try:
        if isinstance(val, (list, tuple)) and len(val) == 2:
            return (getdate(val[0]) if val[0] else None, getdate(val[1]) if val[1] else None)
        if isinstance(val, dict):
            return (getdate(val.get("from_date")) if val.get("from_date") else None,
                    getdate(val.get("to_date")) if val.get("to_date") else None)
    except Exception:
        return None, None
    return None, None


# ---------------- Summary ----------------
def _build_summary(rows):
    total_output = sum(float(r["output_qty"]) for r in rows)
    total_cost   = sum(float(r["total_cost"]) for r in rows)
    total_rev    = sum(float(r["revenue"]) for r in rows)
    total_profit = sum(float(r["profit"]) for r in rows)

    weighted_unit = (total_cost / total_output) if total_output else 0.0
    margin        = (total_profit / total_rev * 100.0) if total_rev else 0.0

    return [
        {"label": "Total Output (kg)",       "value": total_output,  "indicator": "blue"},
        {"label": "Total Cost (ETB)",        "value": total_cost,    "indicator": "orange"},
        {"label": "Total Revenue (ETB)",     "value": total_rev,     "indicator": "green"},
        {"label": "Total Profit (ETB)",      "value": total_profit,  "indicator": "green" if total_profit >= 0 else "red"},
        {"label": "Avg Unit Cost (ETB/kg)",  "value": weighted_unit, "indicator": "orange"},
        {"label": "Profit Margin (%)",       "value": margin,        "indicator": "green" if margin >= 0 else "red"},
    ]
