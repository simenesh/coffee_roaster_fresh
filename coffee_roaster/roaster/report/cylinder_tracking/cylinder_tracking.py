# file: roaster/report/cylinder_tracking/cylinder_tracking.py
import frappe

def execute(filters=None):
    f = frappe._dict(filters or {})

    where, vals = ["1=1"], {}
    if f.roast_cylinder:
        where.append("(rbr.roast_cylinder = %(roast_cylinder)s OR rb.roast_cylinder = %(roast_cylinder)s)")
        vals["roast_cylinder"] = f.roast_cylinder
    if f.from_date:
        where.append("rb.roast_date >= %(from_date)s"); vals["from_date"] = f.from_date
    if f.to_date:
        where.append("rb.roast_date <= %(to_date)s"); vals["to_date"] = f.to_date
    if f.roasting_machine:
        where.append("rb.roasting_machine = %(roasting_machine)s"); vals["roasting_machine"] = f.roasting_machine
    if f.operator:
        where.append("rb.operator = %(operator)s"); vals["operator"] = f.operator

    sql = f"""
        SELECT
            COALESCE(rbr.roast_cylinder, rb.roast_cylinder) AS roast_cylinder,
            rb.roast_date,
            rb.name AS roast_batch,
            -- Green inputs per grade
            SUM(CASE WHEN rbr.grade='G1' THEN COALESCE(rbr.input_qty,0) ELSE 0 END) AS green_g1,
            SUM(CASE WHEN rbr.grade='G2' THEN COALESCE(rbr.input_qty,0) ELSE 0 END) AS green_g2,
            SUM(CASE WHEN rbr.grade='G3' THEN COALESCE(rbr.input_qty,0) ELSE 0 END) AS green_g3,
            -- Roasted outputs per grade
            SUM(CASE WHEN rbr.grade='G1' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS roast_g1,
            SUM(CASE WHEN rbr.grade='G2' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS roast_g2,
            SUM(CASE WHEN rbr.grade='G3' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS roast_g3,
            -- Totals
            SUM(COALESCE(rbr.input_qty,0))  AS total_input,
            SUM(COALESCE(rbr.output_qty,0)) AS total_output,
            SUM(COALESCE(rbr.input_qty,0) - COALESCE(rbr.output_qty,0)) AS total_loss
        FROM `tabRoast Batch` rb
        LEFT JOIN `tabRoast Batch Round` rbr ON rbr.parent = rb.name
        WHERE {" AND ".join(where)}
        GROUP BY COALESCE(rbr.roast_cylinder, rb.roast_cylinder), rb.roast_date, rb.name
        ORDER BY rb.roast_date DESC, rb.name DESC
    """

    data = frappe.db.sql(sql, vals, as_dict=True)

    columns = [
        {"label":"Cylinder","fieldname":"roast_cylinder","fieldtype":"Link","options":"Roast Cylinder","width":140},
        {"label":"Date","fieldname":"roast_date","fieldtype":"Date","width":105},
        {"label":"Roast Batch","fieldname":"roast_batch","fieldtype":"Link","options":"Roast Batch","width":160},

        {"label":"G1 (green)","fieldname":"green_g1","fieldtype":"Float","precision":2,"width":95},
        {"label":"G2 (green)","fieldname":"green_g2","fieldtype":"Float","precision":2,"width":95},
        {"label":"G3 (green)","fieldname":"green_g3","fieldtype":"Float","precision":2,"width":95},

        {"label":"G1 (roasted)","fieldname":"roast_g1","fieldtype":"Float","precision":2,"width":110},
        {"label":"G2 (roasted)","fieldname":"roast_g2","fieldtype":"Float","precision":2,"width":110},
        {"label":"G3 (roasted)","fieldname":"roast_g3","fieldtype":"Float","precision":2,"width":110},

        {"label":"Total In (kg)","fieldname":"total_input","fieldtype":"Float","precision":2,"width":110},
        {"label":"Total Out (kg)","fieldname":"total_output","fieldtype":"Float","precision":2,"width":110},
        {"label":"Total Loss (kg)","fieldname":"total_loss","fieldtype":"Float","precision":2,"width":110}
    ]
    return columns, data

