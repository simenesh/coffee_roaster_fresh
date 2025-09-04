import frappe

def execute(filters=None):
    f = frappe._dict(filters or {})

    columns = [
        {"label": "Batch",        "fieldname": "batch",        "fieldtype": "Link",    "options": "Roast Batch", "width": 160},
        {"label": "Item Code",    "fieldname": "item_code",    "fieldtype": "Link",    "options": "Item",        "width": 160},
        {"label": "Date",         "fieldname": "date",         "fieldtype": "Date",                               "width": 110},
        {"label": "Qty Sold (Kg)","fieldname": "sold_qty",     "fieldtype": "Float",                              "width": 110},
        {"label": "Sales/Kg",     "fieldname": "sales_per_kg", "fieldtype": "Currency",                           "width": 110},
        {"label": "Cost/Kg",      "fieldname": "cost_per_kg",  "fieldtype": "Currency",                           "width": 110},
        {"label": "Margin/Kg",    "fieldname": "margin",       "fieldtype": "Currency",                           "width": 110},
        {"label": "Margin %",     "fieldname": "margin_pct",   "fieldtype": "Percent",                            "width": 90},
        {"label": "Company",      "fieldname": "company",      "fieldtype": "Link",    "options": "Company",      "width": 140},
    ]

    where = ["si.docstatus = 1", "sii.batch_no IS NOT NULL", "sii.batch_no != ''"]
    vals = {}

    if f.get("from_date"):
        where.append("COALESCE(rb.roast_date, si.posting_date) >= %(from_date)s")
        vals["from_date"] = f.from_date
    if f.get("to_date"):
        where.append("COALESCE(rb.roast_date, si.posting_date) <= %(to_date)s")
        vals["to_date"] = f.to_date
    if f.get("company"):
        where.append("si.company = %(company)s")
        vals["company"] = f.company
    if f.get("item_code"):
        where.append("sii.item_code = %(item_code)s")
        vals["item_code"] = f.item_code
    if f.get("batch"):
        where.append("sii.batch_no = %(batch)s")
        vals["batch"] = f.batch

    where_sql = " AND ".join(where)

    # Anchor on Sales Invoice + Items, LEFT JOIN to Roast Batch and Batch Cost so missing
    # batch records or costs do not hide sales rows.
    data = frappe.db.sql(f"""
        SELECT
            sii.batch_no                                  AS batch,
            sii.item_code                                 AS item_code,
            COALESCE(rb.roast_date, si.posting_date)      AS date,
            SUM(sii.qty)                                  AS sold_qty,
            AVG(sii.base_rate)                            AS sales_per_kg,
            COALESCE(bc.cost_per_kg, 0)                   AS cost_per_kg,
            AVG(sii.base_rate) - COALESCE(bc.cost_per_kg, 0) AS margin,
            CASE
                WHEN COALESCE(bc.cost_per_kg, 0) > 0
                    THEN ROUND(((AVG(sii.base_rate) - COALESCE(bc.cost_per_kg, 0))
                               / COALESCE(bc.cost_per_kg, 0)) * 100, 2)
                ELSE 0
            END                                           AS margin_pct,
            si.company                                    AS company
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii
              ON sii.parent = si.name
        LEFT JOIN `tabRoast Batch` rb
              ON rb.name = sii.batch_no
        LEFT JOIN `tabBatch Cost` bc
              ON bc.batch_no = sii.batch_no
        WHERE {where_sql}
        GROUP BY
            sii.batch_no, sii.item_code, si.company,
            COALESCE(rb.roast_date, si.posting_date),
            COALESCE(bc.cost_per_kg, 0)
        HAVING SUM(sii.qty) <> 0
        ORDER BY COALESCE(rb.roast_date, si.posting_date) DESC
    """, vals, as_dict=True)

    return columns, data

