# roaster/report/cylinder_tracking/cylinder_tracking.py
import frappe

def execute(filters=None):
    f = frappe._dict(filters or {})

    where, vals = ["1=1"], {}
    if f.get("roast_cylinder"):
        where.append("(COALESCE(rbr.roast_cylinder, rb.roast_cylinder) = %(roast_cylinder)s)")
        vals["roast_cylinder"] = f.roast_cylinder
    if f.get("from_date"):
        where.append("rb.roast_date >= %(from_date)s"); vals["from_date"] = f.from_date
    if f.get("to_date"):
        where.append("rb.roast_date <= %(to_date)s"); vals["to_date"] = f.to_date

    sql = f"""
        SELECT
            COALESCE(rbr.roast_cylinder, rb.roast_cylinder) AS roast_cylinder,
            COALESCE(rb.customer, '')                        AS customer,
            rb.roast_date,
            rb.name AS roast_batch,

            SUM(CASE WHEN rbr.bean_group='G1' THEN COALESCE(rbr.input_qty,0)  ELSE 0 END) AS g1_green,
            SUM(CASE WHEN rbr.bean_group='G2' THEN COALESCE(rbr.input_qty,0)  ELSE 0 END) AS g2_green,
            SUM(CASE WHEN rbr.bean_group='G3' THEN COALESCE(rbr.input_qty,0)  ELSE 0 END) AS g3_green,

            SUM(CASE WHEN rbr.bean_group='G1' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS g1_roasted,
            SUM(CASE WHEN rbr.bean_group='G2' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS g2_roasted,
            SUM(CASE WHEN rbr.bean_group='G3' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS g3_roasted,

            SUM(COALESCE(rbr.input_qty,0))  AS total_input,
            SUM(COALESCE(rbr.output_qty,0)) AS total_output,
            SUM(COALESCE(rbr.input_qty,0) - COALESCE(rbr.output_qty,0)) AS total_loss
        FROM `tabRoast Batch` rb
        LEFT JOIN `tabRoast Batch Round` rbr ON rbr.parent = rb.name
        WHERE {" AND ".join(where)}
        GROUP BY COALESCE(rbr.roast_cylinder, rb.roast_cylinder), rb.customer, rb.roast_date, rb.name
        ORDER BY rb.roast_date DESC, rb.name DESC
    """
    data = frappe.db.sql(sql, vals, as_dict=True)

    columns = [
        {"label":"Cylinder","fieldname":"roast_cylinder","fieldtype":"Link","options":"Roast Cylinder","width":140},
        {"label":"Customer","fieldname":"customer","fieldtype":"Data","width":160},
        {"label":"Date","fieldname":"roast_date","fieldtype":"Date","width":105},
        {"label":"Roast Batch","fieldname":"roast_batch","fieldtype":"Link","options":"Roast Batch","width":160},

        {"label":"G1 (green)","fieldname":"g1_green","fieldtype":"Float","width":95},
        {"label":"G2 (green)","fieldname":"g2_green","fieldtype":"Float","width":95},
        {"label":"G3 (green)","fieldname":"g3_green","fieldtype":"Float","width":95},

        {"label":"G1 (roasted)","fieldname":"g1_roasted","fieldtype":"Float","width":110},
        {"label":"G2 (roasted)","fieldname":"g2_roasted","fieldtype":"Float","width":110},
        {"label":"G3 (roasted)","fieldname":"g3_roasted","fieldtype":"Float","width":110},

        {"label":"Total In (kg)","fieldname":"total_input","fieldtype":"Float","width":110},
        {"label":"Total Out (kg)","fieldname":"total_output","fieldtype":"Float","width":110},
        {"label":"Total Loss (kg)","fieldname":"total_loss","fieldtype":"Float","width":110}
    ]
    return columns, data
