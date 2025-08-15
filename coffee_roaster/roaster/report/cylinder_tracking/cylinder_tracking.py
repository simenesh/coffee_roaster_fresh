import frappe

def execute(filters=None):
    f = frappe._dict(filters or {})
    # defaults so empty filters show ALL rows
    f.setdefault("roast_cylinder","")
    f.setdefault("from_date","")
    f.setdefault("to_date","")
    f.setdefault("roasting_machine","")
    f.setdefault("operator","")

    where, vals = ["1=1"], {}
    if f.roast_cylinder:
        where.append("COALESCE(rbr.roast_cylinder, rb.roast_cylinder) = %(roast_cylinder)s")
        vals["roast_cylinder"] = f.roast_cylinder
    if f.from_date:
        where.append("rb.roast_date >= %(from_date)s"); vals["from_date"] = f.from_date
    if f.to_date:
        where.append("rb.roast_date <= %(to_date)s");  vals["to_date"] = f.to_date
    if f.roasting_machine:
        where.append("rb.roasting_machine = %(roasting_machine)s"); vals["roasting_machine"] = f.roasting_machine
    if f.operator:
        where.append("rb.operator = %(operator)s"); vals["operator"] = f.operator

    sql = f"""
        SELECT
            COALESCE(rbr.roast_cylinder, rb.roast_cylinder) AS roast_cylinder,
            rb.roast_date,
            rb.name AS roast_batch,

            /* GREEN by group */
            SUM(CASE WHEN rbr.bean_group='G1' THEN COALESCE(rbr.input_qty,0)  ELSE 0 END) AS g1_green,
            SUM(CASE WHEN rbr.bean_group='G2' THEN COALESCE(rbr.input_qty,0)  ELSE 0 END) AS g2_green,
            SUM(CASE WHEN rbr.bean_group='G3' THEN COALESCE(rbr.input_qty,0)  ELSE 0 END) AS g3_green,

            /* ROASTED by group */
            SUM(CASE WHEN rbr.bean_group='G1' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS g1_roasted,
            SUM(CASE WHEN rbr.bean_group='G2' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS g2_roasted,
            SUM(CASE WHEN rbr.bean_group='G3' THEN COALESCE(rbr.output_qty,0) ELSE 0 END) AS g3_roasted,

            /* MOISTURE LOSS by group (green - roasted) */
            SUM(CASE WHEN rbr.bean_group='G1' THEN COALESCE(rbr.input_qty,0)-COALESCE(rbr.output_qty,0) ELSE 0 END) AS g1_moisture_loss,
            SUM(CASE WHEN rbr.bean_group='G2' THEN COALESCE(rbr.input_qty,0)-COALESCE(rbr.output_qty,0) ELSE 0 END) AS g2_moisture_loss,
            SUM(CASE WHEN rbr.bean_group='G3' THEN COALESCE(rbr.input_qty,0)-COALESCE(rbr.output_qty,0) ELSE 0 END) AS g3_moisture_loss,

            /* QUACKER LOSS by group */
            SUM(CASE WHEN rbr.bean_group='G1' THEN COALESCE(rbr.quacker,0) ELSE 0 END) AS g1_quacker_loss,
            SUM(CASE WHEN rbr.bean_group='G2' THEN COALESCE(rbr.quacker,0) ELSE 0 END) AS g2_quacker_loss,
            SUM(CASE WHEN rbr.bean_group='G3' THEN COALESCE(rbr.quacker,0) ELSE 0 END) AS g3_quacker_loss,

            /* NET COFFEE by group (roasted - quacker) */
            SUM(CASE WHEN rbr.bean_group='G1' THEN COALESCE(rbr.output_qty,0)-COALESCE(rbr.quacker,0) ELSE 0 END) AS g1_net_coffee,
            SUM(CASE WHEN rbr.bean_group='G2' THEN COALESCE(rbr.output_qty,0)-COALESCE(rbr.quacker,0) ELSE 0 END) AS g2_net_coffee,
            SUM(CASE WHEN rbr.bean_group='G3' THEN COALESCE(rbr.output_qty,0)-COALESCE(rbr.quacker,0) ELSE 0 END) AS g3_net_coffee,

            /* TOTALS */
            SUM(COALESCE(rbr.input_qty,0))                                        AS total_input,
            SUM(COALESCE(rbr.output_qty,0))                                       AS total_output,
            SUM(COALESCE(rbr.input_qty,0)-COALESCE(rbr.output_qty,0))             AS total_moisture_loss,
            SUM(COALESCE(rbr.quacker,0))                                          AS total_quacker_loss,
            SUM(COALESCE(rbr.output_qty,0)-COALESCE(rbr.quacker,0))               AS total_net_coffee

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

        {"label":"G1 Green","fieldname":"g1_green","fieldtype":"Float","width":90},
        {"label":"G2 Green","fieldname":"g2_green","fieldtype":"Float","width":90},
        {"label":"G3 Green","fieldname":"g3_green","fieldtype":"Float","width":90},

        {"label":"G1 Roasted","fieldname":"g1_roasted","fieldtype":"Float","width":100},
        {"label":"G2 Roasted","fieldname":"g2_roasted","fieldtype":"Float","width":100},
        {"label":"G3 Roasted","fieldname":"g3_roasted","fieldtype":"Float","width":100},

        {"label":"G1 Moisture Loss","fieldname":"g1_moisture_loss","fieldtype":"Float","width":120},
        {"label":"G2 Moisture Loss","fieldname":"g2_moisture_loss","fieldtype":"Float","width":120},
        {"label":"G3 Moisture Loss","fieldname":"g3_moisture_loss","fieldtype":"Float","width":120},

        {"label":"G1 Quacker Loss","fieldname":"g1_quacker_loss","fieldtype":"Float","width":120},
        {"label":"G2 Quacker Loss","fieldname":"g2_quacker_loss","fieldtype":"Float","width":120},
        {"label":"G3 Quacker Loss","fieldname":"g3_quacker_loss","fieldtype":"Float","width":120},

        {"label":"G1 Net Coffee","fieldname":"g1_net_coffee","fieldtype":"Float","width":110},
        {"label":"G2 Net Coffee","fieldname":"g2_net_coffee","fieldtype":"Float","width":110},
        {"label":"G3 Net Coffee","fieldname":"g3_net_coffee","fieldtype":"Float","width":110},

        {"label":"Total In (kg)","fieldname":"total_input","fieldtype":"Float","width":110},
        {"label":"Total Out (kg)","fieldname":"total_output","fieldtype":"Float","width":110},
        {"label":"Total Moisture Loss","fieldname":"total_moisture_loss","fieldtype":"Float","width":140},
        {"label":"Total Quacker","fieldname":"total_quacker_loss","fieldtype":"Float","width":120},
        {"label":"Total Net Coffee","fieldname":"total_net_coffee","fieldtype":"Float","width":130},
    ]
    return columns, data
