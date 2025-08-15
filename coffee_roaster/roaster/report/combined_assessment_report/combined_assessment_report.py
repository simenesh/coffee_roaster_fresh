import frappe

def execute(filters=None):
    f = frappe._dict(filters or {})
    # Defaults so the report runs with NO filters (show all)
    for k in ("roast_batch", "from_date", "to_date" ):
        f.setdefault(k, "")

    vals = {}
    where_rb = ["rb.docstatus < 2"]  # in case we join Roast Batch later for machine/operator/date
    where_da = ["da.docstatus < 2"]
    where_ea = ["ea.docstatus < 2"]
    where_pa = ["pa.docstatus < 2"]
    where_aa = ["aa.docstatus < 2"]

    if f.roast_batch:
        vals["roast_batch"] = f.roast_batch
        where_da.append("da.roast_batch = %(roast_batch)s")
        where_ea.append("ea.roast_batch = %(roast_batch)s")
        where_pa.append("pa.roast_batch = %(roast_batch)s")
        where_aa.append("aa.roast_batch = %(roast_batch)s")

    # If you want date/machine/operator slicing, join Roast Batch metadata too
    if f.from_date:
        vals["from_date"] = f.from_date
        where_da.append("da.roast_date >= %(from_date)s")
    if f.to_date:
        vals["to_date"] = f.to_date
        where_da.append("da.roast_date <= %(to_date)s")
    # NOTE: roasting_machine/operator live on Roast Batch, not the assessments.
    # To support those, we’ll join Roast Batch after building the CTEs.

    # CTEs: pick the latest row per roast_batch from each assessment DocType
    da_sub = f"""
        SELECT da.*
        FROM `tabDescriptive Assessment` da
        JOIN (
            SELECT roast_batch, MAX(modified) AS m
            FROM `tabDescriptive Assessment`
            WHERE docstatus < 2
            GROUP BY roast_batch
        ) x ON x.roast_batch = da.roast_batch AND x.m = da.modified
        WHERE {' AND '.join(where_da)}
    """
    ea_sub = f"""
        SELECT ea.*
        FROM `tabExtrinsic Assessment` ea
        JOIN (
            SELECT roast_batch, MAX(modified) AS m
            FROM `tabExtrinsic Assessment`
            WHERE docstatus < 2
            GROUP BY roast_batch
        ) x ON x.roast_batch = ea.roast_batch AND x.m = ea.modified
        WHERE {' AND '.join(where_ea)}
    """
    pa_sub = f"""
        SELECT pa.*
        FROM `tabPhysical Assessment` pa
        JOIN (
            SELECT roast_batch, MAX(modified) AS m
            FROM `tabPhysical Assessment`
            WHERE docstatus < 2
            GROUP BY roast_batch
        ) x ON x.roast_batch = pa.roast_batch AND x.m = pa.modified
        WHERE {' AND '.join(where_pa)}
    """
    aa_sub = f"""
        SELECT aa.*
        FROM `tabAffective Assessment` aa
        JOIN (
            SELECT roast_batch, MAX(modified) AS m
            FROM `tabAffective Assessment`
            WHERE docstatus < 2
            GROUP BY roast_batch
        ) x ON x.roast_batch = aa.roast_batch AND x.m = aa.modified
        WHERE {' AND '.join(where_aa)}
    """

    # Optional Roast Batch join (for machine/operator filtering)
    rb_join = ""
    rb_where = ""
    if f.roasting_machine or f.operator:
        rb_join = "LEFT JOIN `tabRoast Batch` rb ON rb.name = da.roast_batch"
        if f.roasting_machine:
            vals["roasting_machine"] = f.roasting_machine
            where_rb.append("rb.roasting_machine = %(roasting_machine)s")
        if f.operator:
            vals["operator"] = f.operator
            where_rb.append("rb.operator = %(operator)s")
        rb_where = "WHERE " + " AND ".join(where_rb)

    sql = f"""
        WITH
            da AS ({da_sub}),
            ea AS ({ea_sub}),
            pa AS ({pa_sub}),
            aa AS ({aa_sub})
        SELECT
            da.roast_batch,
            da.sample_no,                     -- Descriptive Assessment
            da.roast_date,
            da.roast_time,
            da.roast_level,

            ea.assessor_name,
            ea.assessment_date,
            ea.purpose,
            ea.country, ea.region,
            ea.farm_or_coop_name,
            ea.producer_name,
            ea.species, ea.variety,
            ea.harvest_date_year,
            ea.other_farming_attribute,
            ea.farming_notes,
            ea.processor_name,
            ea.process_type,
            ea.processing_notes,
            ea.trading_size_grade,
            ea.trading_ico_number,
            ea.trading_other_grade,
            ea.trading_other_attribute,
            ea.trading_notes,
            ea.certifications,
            ea.certification_notes,
            ea.general_notes,

            -- Physical (selected)
            pa.moisture,
            pa.total_full_defects,
            pa.max_screen_size,
            pa.grade AS physical_grade,
            pa.blue_green, pa.bluish_green, pa.green, pa.greenish,
            pa.yellow_green, pa.pale_yellow, pa.yellowish, pa.brownish,

            -- Affective (totals)
            aa.total_score AS affective_total_score,
            aa.grade       AS affective_grade

        FROM da
        LEFT JOIN ea ON ea.roast_batch = da.roast_batch
        LEFT JOIN pa ON pa.roast_batch = da.roast_batch
        LEFT JOIN aa ON aa.roast_batch = da.roast_batch
        {rb_join}
        {rb_where}
        ORDER BY da.roast_date DESC, da.roast_batch DESC
    """

    data = frappe.db.sql(sql, vals, as_dict=True)

    # Fold PA color flags into a single string column
    color_fields = [
        ("blue_green",   "Blue-Green"),
        ("bluish_green", "Bluish-Green"),
        ("green",        "Green"),
        ("greenish",     "Greenish"),
        ("yellow_green", "Yellow-Green"),
        ("pale_yellow",  "Pale Yellow"),
        ("yellowish",    "Yellowish"),
        ("brownish",     "Brownish"),
    ]
    for row in data:
        labels = [label for field, label in color_fields if row.get(field)]
        row["color_assessment"] = ", ".join(labels) if labels else ""
        for field, _ in color_fields:
            row.pop(field, None)

    # Normalize some Nones
    for row in data:
        for fld in ("moisture", "total_full_defects", "max_screen_size", "physical_grade",
                    "affective_total_score", "affective_grade"):
            if row.get(fld) in (None, ""):
                row[fld] = 0

    columns = [
        {"label":"Roast Batch","fieldname":"roast_batch","fieldtype":"Link","options":"Roast Batch","width":160},
        {"label":"Sample No.","fieldname":"sample_no","fieldtype":"Data","width":110},
        {"label":"Roast Date","fieldname":"roast_date","fieldtype":"Date","width":105},
        {"label":"Roast Time","fieldname":"roast_time","fieldtype":"Time","width":95},
        {"label":"Roast Level","fieldname":"roast_level","fieldtype":"Data","width":90},

        {"label":"Assessor","fieldname":"assessor_name","fieldtype":"Data","width":140},
        {"label":"Assessment Date","fieldname":"assessment_date","fieldtype":"Date","width":110},
        {"label":"Purpose","fieldname":"purpose","fieldtype":"Data","width":120},
        {"label":"Country","fieldname":"country","fieldtype":"Data","width":100},
        {"label":"Region","fieldname":"region","fieldtype":"Data","width":110},
        {"label":"Farm/Co-op","fieldname":"farm_or_coop_name","fieldtype":"Data","width":140},
        {"label":"Producer","fieldname":"producer_name","fieldtype":"Data","width":140},
        {"label":"Species","fieldname":"species","fieldtype":"Data","width":90},
        {"label":"Variety","fieldname":"variety","fieldtype":"Data","width":120},
        {"label":"Harvest (Date/Year)","fieldname":"harvest_date_year","fieldtype":"Data","width":140},
        {"label":"Other Farming Attribute","fieldname":"other_farming_attribute","fieldtype":"Data","width":160},
        {"label":"Farming Notes","fieldname":"farming_notes","fieldtype":"Data","width":180},
        {"label":"Processor","fieldname":"processor_name","fieldtype":"Data","width":140},
        {"label":"Process Type","fieldname":"process_type","fieldtype":"Data","width":110},
        {"label":"Processing Notes","fieldname":"processing_notes","fieldtype":"Data","width":180},
        {"label":"Size Grade","fieldname":"trading_size_grade","fieldtype":"Data","width":100},
        {"label":"ICO Number","fieldname":"trading_ico_number","fieldtype":"Data","width":110},
        {"label":"Other Grade","fieldname":"trading_other_grade","fieldtype":"Data","width":110},
        {"label":"Other Trading Attribute","fieldname":"trading_other_attribute","fieldtype":"Data","width":160},
        {"label":"Trading Notes","fieldname":"trading_notes","fieldtype":"Data","width":160},
        {"label":"Certifications","fieldname":"certifications","fieldtype":"Data","width":140},
        {"label":"Certification Notes","fieldname":"certification_notes","fieldtype":"Data","width":160},
        {"label":"General Notes","fieldname":"general_notes","fieldtype":"Data","width":180},

        {"label":"Color Assessment","fieldname":"color_assessment","fieldtype":"Data","width":150},
        {"label":"Moisture (%)","fieldname":"moisture","fieldtype":"Float","width":110},
        {"label":"Total Full Defects","fieldname":"total_full_defects","fieldtype":"Int","width":130},
        {"label":"Max Screen Size","fieldname":"max_screen_size","fieldtype":"Int","width":120},
        {"label":"Physical Grade","fieldname":"physical_grade","fieldtype":"Int","width":110},

        {"label":"Affective Total Score","fieldname":"affective_total_score","fieldtype":"Int","width":140},
        {"label":"Affective Grade","fieldname":"affective_grade","fieldtype":"Int","width":120},
    ]
    return columns, data
