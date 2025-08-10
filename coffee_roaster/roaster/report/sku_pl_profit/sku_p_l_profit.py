# SKU P&L Profit Report
# ---------------------
# Compares cost and sales of each batch to compute profit per SKU.

import frappe
from frappe.utils import flt

def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = [
        {"label": "Batch",        "fieldname": "batch",       "fieldtype": "Link",    "options": "Roast Batch", "width": 150},
        {"label": "Item Code",    "fieldname": "item_code",   "fieldtype": "Link",    "options": "Item",        "width": 140},
        {"label": "Posting Date", "fieldname": "date",        "fieldtype": "Date",                             "width": 100},
        {"label": "Qty Sold (Kg)","fieldname": "sold_qty",    "fieldtype": "Float",                            "width": 100},
        {"label": "Sales/Kg",     "fieldname": "sales_per_kg","fieldtype": "Currency",                         "width": 110},
        {"label": "Cost/Kg",      "fieldname": "cost_per_kg", "fieldtype": "Currency",                         "width": 110},
        {"label": "Margin/Kg",    "fieldname": "margin",      "fieldtype": "Currency",                         "width": 110},
        {"label": "Margin %",     "fieldname": "margin_pct",  "fieldtype": "Percent",                          "width": 90},
        {"label": "Company",      "fieldname": "company",     "fieldtype": "Link",     "options": "Company",   "width": 100},
    ]

    data = frappe.db.sql("""
        SELECT
            rb.name                           AS batch,
            sii.item_code                     AS item_code,
            rb.posting_date                   AS date,
            SUM(sii.qty)                      AS sold_qty,
            AVG(sii.base_rate)                AS sales_per_kg,
            bc.cost_per_kg                    AS cost_per_kg,
            AVG(sii.base_rate) - bc.cost_per_kg             AS margin,
            ROUND(((AVG(sii.base_rate) - bc.cost_per_kg) / bc.cost_per_kg) * 100, 2) AS margin_pct,
            sii.company                       AS company
        FROM `tabBatch Cost` bc
        JOIN `tabRoast Batch`        rb  ON bc.batch_no = rb.name
        JOIN `tabSales Invoice Item` sii ON sii.batch_no = rb.name
        WHERE sii.docstatus = 1
        GROUP BY rb.name, sii.item_code, sii.company
        ORDER BY rb.posting_date DESC
    """, as_dict=True)

    return columns, data
