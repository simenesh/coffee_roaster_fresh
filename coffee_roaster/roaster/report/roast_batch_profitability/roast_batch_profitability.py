# roast_batch_profitability.py

import frappe
from frappe.utils import getdate

def execute(filters=None):
    filters = filters or {}
    fd, td = _safe_date_range(filters.get("roast_date_range"))
    columns = _get_columns()
    rows = _build_rows(fd, td, filters.get("roast_batch"))
    summary = _build_summary(rows)
    return columns, rows, None, None, summary

def _get_columns():
    return [
        {"label": "Roast Batch", "fieldname": "roast_batch", "fieldtype": "Link", "options": "Roast Batch"},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company"},
        {"label": "Roast Date", "fieldname": "roast_date", "fieldtype": "Date"},
        {"label": "Input Qty (kg)", "fieldname": "input_qty", "fieldtype": "Float"},
        {"label": "Output Qty (kg)", "fieldname": "output_qty", "fieldtype": "Float"},
        {"label": "Yield (%)", "fieldname": "yield_pct", "fieldtype": "Percent"},
        # --- fixed 6 fields ---
        {"label": "Unit Cost (ETB/kg)", "fieldname": "unit_cost", "fieldtype": "Currency", "options": "ETB"},
        {"label": "Total Cost (ETB)", "fieldname": "total_cost", "fieldtype": "Currency", "options": "ETB"},
        {"label": "Selling Rate (ETB/kg)", "fieldname": "selling_rate", "fieldtype": "Currency", "options": "ETB"},
        {"label": "Revenue (ETB)", "fieldname": "revenue", "fieldtype": "Currency", "options": "ETB"},
        {"label": "Profit (ETB)", "fieldname": "profit", "fieldtype": "Currency", "options": "ETB"},
        {"label": "Profit Margin (%)", "fieldname": "profit_margin", "fieldtype": "Percent"},
    ]

def _build_rows(fd, td, roast_batch):
    conds = ["rb.docstatus in (0,1)"]   # Draft + Submitted
    params = {}
    if fd and td:
        conds.append("rb.roast_date between %(fd)s and %(td)s"); params.update({"fd": fd, "td": td})
    if roast_batch:
        conds.append("rb.name = %(rb)s"); params["rb"] = roast_batch
    where_sql = " and ".join(conds)

    rbs = frappe.db.sql(f"""
        select rb.name as roast_batch, rb.company, rb.roast_date
        from `tabRoast Batch` rb
        where {where_sql}
        order by rb.roast_date desc, rb.name desc
    """, params, as_dict=True)

    rows = []
    for rb in rbs:
        rb_name = rb["roast_batch"]
        input_qty  = _pick(rb_name, ["qty_to_roast","input_qty"], 0.0)
        output_qty = _pick(rb_name, ["output_qty","output_weight"], 0.0)
        yield_pct  = (float(output_qty)/float(input_qty)*100.0) if input_qty else None

        # --- financials ---
        bc = frappe.db.get_value("Batch Cost", {"batch_no": rb_name, "docstatus": 1},
            ["total_batch_cost","cost_per_kg","selling_rate","revenue","profit","profit_margin"],
            as_dict=True) or {}

        total_cost  = float(bc.get("total_batch_cost") or 0)
        unit_cost   = float(bc.get("cost_per_kg") or (total_cost/output_qty if output_qty else 0))
        selling_rate= float(bc.get("selling_rate") or _selling_rate_from_rb_or_item(rb_name))
        revenue     = float(bc.get("revenue") or selling_rate*output_qty)
        profit      = float(bc.get("profit") or (revenue-total_cost))
        margin      = float(bc.get("profit_margin") or ((profit/revenue*100) if revenue else 0))

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

def _pick(rb_name, fields, default=None):
    for f in fields:
        if frappe.db.has_column("Roast Batch", f):
            v = frappe.db.get_value("Roast Batch", rb_name, f)
            if v not in (None,""):
                return v
    return default

def _selling_rate_from_rb_or_item(rb_name):
    for f in ["selling_rate","selling_price","price_per_kg","rate"]:
        if frappe.db.has_column("Roast Batch", f):
            v = frappe.db.get_value("Roast Batch", rb_name, f)
            if v: return float(v)
    item = frappe.db.get_value("Roast Batch", rb_name, "roasted_item")
    if item:
        rate = frappe.db.get_value("Item Price", {"item_code": item, "selling": 1}, "price_list_rate")
        return float(rate or 0)
    return 0.0

def _safe_date_range(val):
    if not val: return None, None
    if isinstance(val, (list,tuple)) and len(val)==2: return getdate(val[0]), getdate(val[1])
    return None, None

def _build_summary(rows):
    total_output = sum(float(r["output_qty"]) for r in rows)
    total_cost   = sum(float(r["total_cost"]) for r in rows)
    total_rev    = sum(float(r["revenue"]) for r in rows)
    total_profit = sum(float(r["profit"]) for r in rows)
    avg_unit     = (total_cost/total_output) if total_output else 0
    margin       = (total_profit/total_rev*100) if total_rev else 0
    return [
        {"label": "Total Output (kg)", "value": total_output, "indicator": "blue"},
        {"label": "Total Cost (ETB)", "value": total_cost, "indicator": "orange"},
        {"label": "Total Revenue (ETB)", "value": total_rev, "indicator": "green"},
        {"label": "Total Profit (ETB)", "value": total_profit, "indicator": "green" if total_profit>=0 else "red"},
        {"label": "Avg Unit Cost (ETB/kg)", "value": avg_unit, "indicator": "orange"},
        {"label": "Profit Margin (%)", "value": margin, "indicator": "green" if margin>=0 else "red"},
    ]
