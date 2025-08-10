import frappe

def execute(filters=None):
    filter_clause = ""
    filter_vals = {}

    # Apply roast_batch filter INSIDE the Descriptive Assessment subquery
    if filters and filters.get("roast_batch"):
        filter_clause = "AND roast_batch = %(roast_batch)s"
        filter_vals["roast_batch"] = filters["roast_batch"]

    query = f"""
        SELECT
            da.roast_batch,
            da.sample_no,
            da.roast_date,
            da.roast_time,
            da.roast_level,

            ea.assessor_name,
            ea.assessment_date,
            ea.purpose,
            ea.country,
            ea.region,
            ea.farm_or_coop_name,
            ea.producer_name,
            ea.species,
            ea.variety,
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

            pa.moisture,
            pa.total_full_defects,
            pa.max_screen_size,
            pa.grade AS physical_grade,

            aa.total_score AS affective_total_score,
            aa.grade AS affective_grade,

            pa.blue_green,
            pa.bluish_green,
            pa.green,
            pa.greenish,
            pa.yellow_green,
            pa.pale_yellow,
            pa.yellowish,
            pa.brownish

        FROM
            (SELECT * FROM `tabDescriptive Assessment` WHERE docstatus < 2 {filter_clause} GROUP BY roast_batch) da
        LEFT JOIN
            (SELECT * FROM `tabExtrinsic Assessment` WHERE docstatus < 2 GROUP BY roast_batch) ea ON da.roast_batch = ea.roast_batch
        LEFT JOIN
            (SELECT * FROM `tabPhysical Assessment` WHERE docstatus < 2 GROUP BY roast_batch) pa ON da.roast_batch = pa.roast_batch
        LEFT JOIN
            (SELECT * FROM `tabAffective Assessment` WHERE docstatus < 2 GROUP BY roast_batch) aa ON da.roast_batch = aa.roast_batch
        ORDER BY da.roast_batch DESC
        LIMIT 100
    """

    data = frappe.db.sql(query, filter_vals, as_dict=True)

    # --- Only show checked color fields ---
    color_fields = [
        ("blue_green", "Blue-Green"),
        ("bluish_green", "Bluish-Green"),
        ("green", "Green"),
        ("greenish", "Greenish"),
        ("yellow_green", "Yellow-Green"),
        ("pale_yellow", "Pale Yellow"),
        ("yellowish", "Yellowish"),
        ("brownish", "Brownish"),
    ]
    for row in data:
        checked = [label for field, label in color_fields if row.get(field)]
        row["color_assessment"] = ", ".join(checked)
        # Remove the individual color fields so only 'color_assessment' is in report
        for field, _ in color_fields:
            row.pop(field, None)

    columns = [
        {"label": "Roast Batch", "fieldname": "roast_batch", "fieldtype": "Data"},
        {"label": "Sample No.", "fieldname": "sample_no", "fieldtype": "Data"},
        {"label": "Roast Date", "fieldname": "roast_date", "fieldtype": "Date"},
        {"label": "Roast Time", "fieldname": "roast_time", "fieldtype": "Time"},
        {"label": "Roast Level", "fieldname": "roast_level", "fieldtype": "Data"},

        # Extrinsic
        {"label": "Assessor Name", "fieldname": "assessor_name", "fieldtype": "Data"},
        {"label": "Assessment Date", "fieldname": "assessment_date", "fieldtype": "Date"},
        {"label": "Purpose", "fieldname": "purpose", "fieldtype": "Data"},
        {"label": "Country", "fieldname": "country", "fieldtype": "Data"},
        {"label": "Region", "fieldname": "region", "fieldtype": "Data"},
        {"label": "Farm/Coop Name", "fieldname": "farm_or_coop_name", "fieldtype": "Data"},
        {"label": "Producer Name", "fieldname": "producer_name", "fieldtype": "Data"},
        {"label": "Species", "fieldname": "species", "fieldtype": "Data"},
        {"label": "Variety", "fieldname": "variety", "fieldtype": "Data"},
        {"label": "Harvest Date/Year", "fieldname": "harvest_date_year", "fieldtype": "Data"},
        {"label": "Other Farming Attribute", "fieldname": "other_farming_attribute", "fieldtype": "Data"},
        {"label": "Farming Notes", "fieldname": "farming_notes", "fieldtype": "Data"},
        {"label": "Processor Name", "fieldname": "processor_name", "fieldtype": "Data"},
        {"label": "Process Type", "fieldname": "process_type", "fieldtype": "Data"},
        {"label": "Processing Notes", "fieldname": "processing_notes", "fieldtype": "Data"},
        {"label": "Trading Size Grade", "fieldname": "trading_size_grade", "fieldtype": "Data"},
        {"label": "Trading ICO Number", "fieldname": "trading_ico_number", "fieldtype": "Data"},
        {"label": "Trading Other Grade", "fieldname": "trading_other_grade", "fieldtype": "Data"},
        {"label": "Trading Other Attribute", "fieldname": "trading_other_attribute", "fieldtype": "Data"},
        {"label": "Trading Notes", "fieldname": "trading_notes", "fieldtype": "Data"},
        {"label": "Certifications", "fieldname": "certifications", "fieldtype": "Data"},
        {"label": "Certification Notes", "fieldname": "certification_notes", "fieldtype": "Data"},
        {"label": "General Notes", "fieldname": "general_notes", "fieldtype": "Data"},

        # Physical Assessment - Color (as one column)
        {"label": "Color Assessment", "fieldname": "color_assessment", "fieldtype": "Data"},

        # Physical Assessment - Moisture & Summary
        {"label": "Moisture (%)", "fieldname": "moisture", "fieldtype": "Float"},
        {"label": "Total Full Defects", "fieldname": "total_full_defects", "fieldtype": "Int"},
        {"label": "Max Screen Size", "fieldname": "max_screen_size", "fieldtype": "Int"},
        {"label": "Physical Grade", "fieldname": "physical_grade", "fieldtype": "Int"},

        # Affective
        {"label": "Affective Total Score", "fieldname": "affective_total_score", "fieldtype": "Int"},
        {"label": "Affective Grade", "fieldname": "affective_grade", "fieldtype": "Int"}
    ]
  
    # Clean up numeric fields so no None or NaN is present
    numeric_fields = [
        "moisture", "total_full_defects", "max_screen_size",
        "physical_grade", "affective_total_score", "affective_grade"
    ]
    for row in data:
        for field in numeric_fields:
            val = row.get(field)
            if val is None or val == "" or (isinstance(val, float) and str(val).lower() == 'nan'):
                row[field] = 0

    return columns, data

  
