import frappe

def execute(filters=None):
    filters = filters or {}

    # Columns definition
    columns = [
        {"label": "Cylinder", "fieldname": "roast_cylinder", "fieldtype": "Link", "options": "Roast Cylinder", "width": 140},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Data", "width": 160},
        {"label": "Date", "fieldname": "roast_date", "fieldtype": "Date", "width": 105},
        {"label": "G1 (green)", "fieldname": "green_g1", "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": "G2 (green)", "fieldname": "green_g2", "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": "G3 (green)", "fieldname": "green_g3", "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": "Sum (green)", "fieldname": "green_sum", "fieldtype": "Float", "precision": 2, "width": 95},
        {"label": "G1 (roasted)", "fieldname": "roast_g1", "fieldtype": "Float", "precision": 2, "width": 95},
        {"label": "G2 (roasted)", "fieldname": "roast_g2", "fieldtype": "Float", "precision": 2, "width": 95},
        {"label": "G3 (roasted)", "fieldname": "roast_g3", "fieldtype": "Float", "precision": 2, "width": 95},
        {"label": "Sum (roasted)", "fieldname": "roast_sum", "fieldtype": "Float", "precision": 2, "width": 105},
        {"label": "G1 (loss)", "fieldname": "loss_g1", "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": "G2 (loss)", "fieldname": "loss_g2", "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": "G3 (loss)", "fieldname": "loss_g3", "fieldtype": "Float", "precision": 2, "width": 90},
        {"label": "Sum (loss)", "fieldname": "loss_sum", "fieldtype": "Float", "precision": 2, "width": 95},
        {"label": "Quacker (kg)", "fieldname": "quacker", "fieldtype": "Float", "precision": 2, "width": 85},
        {"label": "Net Coffee (kg)", "fieldname": "net_coffee", "fieldtype": "Float", "precision": 2, "width": 110},
        {"label": "Batch ID", "fieldname": "batch_id", "fieldtype": "Link", "options": "Roast Batch", "width": 130},
        {"label": "Machine", "fieldname": "roasting_machine", "fieldtype": "Link", "options": "Roasting Machine", "width": 150},
        {"label": "Operator", "fieldname": "operator", "fieldtype": "Link", "options": "User", "width": 130}
    ]

    conditions = []
    values = {}

    # Force Cylinder filter only if you want it mandatory
    if filters.get("roast_cylinder"):
        conditions.append("rb.roast_cylinder = %(roast_cylinder)s")
        values["roast_cylinder"] = filters["roast_cylinder"]

    # Optional filters
    if filters.get("from_date"):
        conditions.append("rb.roast_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("rb.roast_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("roasting_machine"):
        conditions.append("rb.roasting_machine = %(roasting_machine)s")
        values["roasting_machine"] = filters["roasting_machine"]

    if filters.get("operator"):
        conditions.append("rb.operator = %(operator)s")
        values["operator"] = filters["operator"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT
            rb.roast_cylinder,
            COALESCE(rb.customer, '') AS customer,
            rb.roast_date,
            ROUND(SUM(CASE WHEN rbr.group_code='G1' THEN COALESCE(rbr.input_qty,0) ELSE 0 END), 2) AS green_g1,
            ROUND(SUM(CASE WHEN rbr.group_code='G2' THEN COALESCE(rbr.input_qty,0) ELSE 0 END), 2) AS green_g2,
            ROUND(SUM(CASE WHEN rbr.group_code='G3' THEN COALESCE(rbr.input_qty,0) ELSE 0 END), 2) AS green_g3,
            ROUND(SUM(COALESCE(rbr.input_qty,0)), 2) AS green_sum,
            ROUND(SUM(CASE WHEN rbr.group_code='G1' THEN COALESCE(rbr.output_qty,0) ELSE 0 END), 2) AS roast_g1,
            ROUND(SUM(CASE WHEN rbr.group_code='G2' THEN COALESCE(rbr.output_qty,0) ELSE 0 END), 2) AS roast_g2,
            ROUND(SUM(CASE WHEN rbr.group_code='G3' THEN COALESCE(rbr.output_qty,0) ELSE 0 END), 2) AS roast_g3,
            ROUND(SUM(COALESCE(rbr.output_qty,0)), 2) AS roast_sum,
            ROUND(SUM(CASE WHEN rbr.group_code='G1' THEN (COALESCE(rbr.input_qty,0)-COALESCE(rbr.output_qty,0)) ELSE 0 END), 2) AS loss_g1,
            ROUND(SUM(CASE WHEN rbr.group_code='G2' THEN (COALESCE(rbr.input_qty,0)-COALESCE(rbr.output_qty,0)) ELSE 0 END), 2) AS loss_g2,
            ROUND(SUM(CASE WHEN rbr.group_code='G3' THEN (COALESCE(rbr.input_qty,0)-COALESCE(rbr.output_qty,0)) ELSE 0 END), 2) AS loss_g3,
            ROUND(SUM(COALESCE(rbr.input_qty,0)-COALESCE(rbr.output_qty,0)), 2) AS loss_sum,
            ROUND(SUM(COALESCE(rbr.quacker,0)), 2) AS quacker,
            ROUND(SUM(COALESCE(rbr.output_qty,0)-COALESCE(rbr.quacker,0)), 2) AS net_coffee,
            rb.name AS batch_id,
            rb.roasting_machine,
            rb.operator
        FROM `tabRoast Batch` rb
        LEFT JOIN `tabRoast Batch Round` rbr ON rbr.parent = rb.name
        WHERE {where_clause}
        GROUP BY rb.name, rb.roast_cylinder, rb.customer, rb.roast_date
        ORDER BY rb.roast_date, rb.name
    """

    data = frappe.db.sql(sql, values, as_dict=True)
    return columns, data
