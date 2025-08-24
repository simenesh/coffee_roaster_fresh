# -*- coding: utf-8 -*-
import frappe
from frappe.utils import getdate, flt

# =======================
# Public API for Frappe
# =======================
def execute(filters=None):
    """
    Script Report entrypoint.
    Returns: (columns, data, message, chart, report_summary)
    """
    filters = filters or {}
    from_date, to_date = _parse_date_range(filters.get("roast_date_range"))

    columns = _get_columns()
    rows = _build_rows(from_date, to_date, filters.get("roast_batch"))

    summary = _build_summary(rows)
    return columns, rows, None, None, summary


# =======================
# Columns
# =======================
def _get_columns():
    return [
        {"label": "Roast Batch", "fieldname": "roast_batch", "fieldtype": "Link", "options": "Roast Batch", "width": 180},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 140},
        {"label": "Roast Date", "fieldname": "roast_date", "fieldtype": "Date", "width": 110},

        {"label": "Input Qty (kg)", "fieldname": "input_qty", "fieldtype": "Float", "width": 120},
        {"label": "Output Qty (kg)", "fieldname": "output_qty", "fieldtype": "Float", "width": 120},
        {"label": "Yield (%)", "fieldname": "yield_pct", "fieldtype": "Percent", "width": 100},

        {"label": "Unit Cost (ETB/kg)", "fieldname": "unit_cost", "fieldtype": "Currency", "options": "ETB", "width": 130},
        {"label": "Total Cost (ETB)", "fieldname": "total_cost", "fieldtype": "Currency", "options": "ETB", "width": 130},

        {"label": "Selling Rate (ETB/kg)", "fieldname": "selling_rate", "fieldtype": "Currency", "options": "ETB", "width": 150},
        {"label": "Revenue (ETB)", "fieldname": "revenue", "fieldtype": "Currency", "options": "ETB", "width": 130},

        {"label": "Profit (ETB)", "fieldname": "profit", "fieldtype": "Currency", "options": "ETB", "width": 130},
        {"label": "Profit Margin (%)", "fieldname": "profit_margin", "fieldtype": "Percent", "width": 140},
    ]


# =======================
# Data
# =======================
def _build_rows(from_date, to_date, roast_batch):
    conds = ["rb.docstatus = 1"]
    params = {}

    if from_date and to_date:
        conds.append("rb.roast_date BETWEEN %(fd)s AND %(td)s")
        params.update({"fd": from_date, "td": to_date})
    elif from_date:
        conds.append("rb.roast_date >= %(fd)s")
        params.update({"fd": from_date})
    elif to_date:
        conds.append("rb.roast_date <= %(td)s")
        params.update({"td": to_date})

    if roast_batch:
        conds.append("rb.name = %(roast_batch)s")
        params["roast_batch"] = roast_batch

    where_sql = " AND ".join(conds)

    roast_batches = frappe.db.sql(
        f"""
        SELECT
            rb.name AS roast_batch,
            rb.company AS company,
            rb.roast_date AS roast_date,
            COALESCE(rb.input_qty, 0) AS input_qty,
            COALESCE(rb.output_qty, 0) AS output_qty
        FROM `tabRoast Batch` rb
        WHERE {where_sql}
        ORDER BY rb.roast_date DESC, rb.name DESC
        """,
        params,
        as_dict=True,
    ) or []

    rows = []
    for rb in roast_batches:
        rb_name = rb["roast_batch"]

        bc_name = _find_batch_cost_name_for_roast(rb_name)

        total_cost, unit_cost = _compute_costs_safely(
            bc_name=bc_name,
            roast_batch=rb_name,
            output_qty=flt(rb["output_qty"]),
        )

        selling_rate = _detect_selling_rate(rb_name)

        revenue = selling_rate * flt(rb["output_qty"])
        profit = revenue - total_cost
        yield_pct = (flt(rb["output_qty"]) / flt(rb["input_qty"]) * 100.0) if rb["input_qty"] else None
        profit_margin = (profit / revenue * 100.0) if revenue else None

        rows.append({
            "roast_batch": rb_name,
            "company": rb["company"],
            "roast_date": rb["roast_date"],
            "input_qty": flt(rb["input_qty"]),
            "output_qty": flt(rb["output_qty"]),
            "yield_pct": yield_pct,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "selling_rate": selling_rate,
            "revenue": revenue,
            "profit": profit,
            "profit_margin": profit_margin,
        })

    return rows


# =======================
# Helpers
# =======================
def _find_batch_cost_name_for_roast(roast_batch_name: str):
    """
    Find submitted Batch Cost linked to a Roast Batch, regardless of link field name.
    Guarded with proper table-exists check using table name ('tabBatch Cost').
    """
    # Correct: table_exists expects TABLE name, e.g. 'tabBatch Cost'
    if not frappe.db.table_exists("tabBatch Cost"):
        return None

    candidates = [
        "roast_batch", "batch", "batch_no", "roast_batch_no",
        "roast", "roast_ref", "roast_reference",
        "reference_batch", "reference",
    ]

    # Try direct match per column (only if the column exists)
    for field in candidates:
        if frappe.db.has_column("tabBatch Cost", field):
            name = frappe.db.get_value(
                "Batch Cost",
                {field: roast_batch_name, "docstatus": 1},
                "name",
                order_by="modified desc",
            )
            if name:
                return name

    # Fallback: OR across any existing candidate columns
    existing_cols = [f for f in candidates if frappe.db.has_column("tabBatch Cost", f)]
    if existing_cols:
        or_predicates = " OR ".join([f"{frappe.db.escape_column(c)}=%(rb)s" for c in existing_cols])
        res = frappe.db.sql(
            f"""
            SELECT name
            FROM `tabBatch Cost`
            WHERE docstatus=1 AND ({or_predicates})
            ORDER BY modified DESC
            LIMIT 1
            """,
            {"rb": roast_batch_name},
        )
        if res:
            return res[0][0]

    return None


def _compute_costs_safely(bc_name, roast_batch, output_qty):
    """
    Get total/unit cost from Batch Cost with variable schema or compute from children.
    Fully guarded so we never touch a non-existent table/column.
    """
    total_cost = 0.0
    unit_cost = None

    # A) Try fields on Batch Cost (only if table exists)
    if bc_name and frappe.db.table_exists("tabBatch Cost"):
        for f in ["total_cost", "total_batch_cost", "grand_total", "total_expense", "total"]:
            if frappe.db.has_column("tabBatch Cost", f):
                total_cost = flt(frappe.db.get_value("Batch Cost", bc_name, f) or 0)
                break
        for f in ["unit_cost", "cost_per_kg", "rate_per_kg", "unit_rate"]:
            if frappe.db.has_column("tabBatch Cost", f):
                unit_cost = flt(frappe.db.get_value("Batch Cost", bc_name, f) or 0)
                break

    # B) If still zero/missing, compute by summing children
    if bc_name and frappe.db.table_exists("tabBatch Cost") and not total_cost:
        total_cost += _sum_child_costs(bc_name, "Raw Bean Cost Item")
        total_cost += _sum_child_costs(bc_name, "Overhead Item")
        total_cost += _sum_child_costs(bc_name, "Packaging Cost Item")

    # C) Unit cost fallback
    if unit_cost is None:
        unit_cost = (total_cost / output_qty) if output_qty else 0.0

    return flt(total_cost), flt(unit_cost)


def _sum_child_costs(parent_name, child_table):
    """
    Sum cost from a child table using 'amount' if present, else qty*rate'.
    Correct table_exists call with 'tab' prefix.
    """
    if not parent_name:
        return 0.0

    table_name = "tab" + child_table
    if not frappe.db.table_exists(table_name):
        return 0.0

    # Fast path: sum amount/total if a column exists
    for amount_col in ["amount", "total", "total_amount"]:
        if frappe.db.has_column(table_name, amount_col):
            res = frappe.db.sql(
                f"""
                SELECT SUM({frappe.db.escape_column(amount_col)}) AS s
                FROM `{table_name}`
                WHERE parent=%s AND parenttype='Batch Cost'
                """,
                (parent_name,),
            )
            return flt(res[0][0]) if res and res[0][0] is not None else 0.0

    # Fallback: qty * rate
    qty_col = _first_existing_column(table_name, ["qty", "quantity"])
    rate_col = _first_existing_column(table_name, ["rate", "price"])
    if not qty_col or not rate_col:
        return 0.0

    rows = frappe.get_all(
        child_table,
        fields=["name"],
        filters={"parent": parent_name, "parenttype": "Batch Cost"},
        limit=0,
    )
    total = 0.0
    for r in rows:
        qty = flt(frappe.db.get_value(child_table, r["name"], qty_col) or 0)
        rate = flt(frappe.db.get_value(child_table, r["name"], rate_col) or 0)
        total += qty * rate
    return total


def _first_existing_column(table_name, candidates):
    for c in candidates:
        if frappe.db.has_column(table_name, c):
            return c
    return None


def _detect_selling_rate(roast_batch_name):
    """Return selling rate from any plausible field on Roast Batch."""
    table_name = "tabRoast Batch"
    for field in ["selling_rate", "selling_price", "rate", "price"]:
        if frappe.db.has_column(table_name, field):
            val = frappe.db.get_value("Roast Batch", roast_batch_name, field)
            return flt(val or 0)
    return 0.0


def _parse_date_range(val):
    if not val:
        return None, None
    try:
        if isinstance(val, (list, tuple)) and len(val) == 2:
            return (getdate(val[0]) if val[0] else None,
                    getdate(val[1]) if val[1] else None)
        if isinstance(val, dict):
            return (getdate(val.get("from_date")) if val.get("from_date") else None,
                    getdate(val.get("to_date")) if val.get("to_date") else None)
        if isinstance(val, str) and "to" in val:
            a, b = [p.strip() for p in val.split("to", 1)]
            return (getdate(a) if a else None, getdate(b) if b else None)
        if isinstance(val, str):
            d = getdate(val)
            return d, d
    except Exception:
        return None, None
    return None, None


def _build_summary(rows):
    total_output = sum(flt(r.get("output_qty")) for r in rows)
    total_cost = sum(flt(r.get("total_cost")) for r in rows)
    total_revenue = sum(flt(r.get("revenue")) for r in rows)
    total_profit = sum(flt(r.get("profit")) for r in rows)
    weighted_unit_cost = (total_cost / total_output) if total_output else 0.0
    overall_margin = (total_profit / total_revenue * 100.0) if total_revenue else 0.0

    return [
        {"label": "Total Output (kg)", "value": total_output, "indicator": "blue"},
        {"label": "Total Cost (ETB)", "value": total_cost, "indicator": "orange"},
        {"label": "Total Revenue (ETB)", "value": total_revenue, "indicator": "green"},
        {"label": "Total Profit (ETB)", "value": total_profit, "indicator": "green" if total_profit >= 0 else "red"},
        {"label": "Avg Unit Cost (ETB/kg)", "value": weighted_unit_cost, "indicator": "orange"},
        {"label": "Profit Margin (%)", "value": overall_margin, "indicator": "green" if overall_margin >= 0 else "red"},
    ]

