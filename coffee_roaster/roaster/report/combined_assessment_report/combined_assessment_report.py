# Combined Assessment Report — Script Report
# Matches your current SELECT columns and makes filters work.
import frappe

def execute(filters=None):
    f = frappe._dict(filters or {})
    # defaults so empty filters show ALL rows
    f.setdefault("roast_batch", "")
    f.setdefault("from_date", "")
    f.setdefault("to_date", "")

    vals = {}
    where_da = ["da1.docstatus < 2"]
    if f.roast_batch:
        where_da.append("da1.roast_batch = %(roast_batch)s")
        vals["roast_batch"] = f.roast_batch
    if f.from_date:
        where_da.append("da1.roast_date >= %(from_date)s")
        vals["from_date"] = f.from_date
    if f.to_date:
        where_da.append("da1.roast_date <= %(to_date)s")
        vals["to_date"] = f.to_date

    # Use "latest per roast_batch" for each assessment (stable vs GROUP BY *)
    da_sub = f"""
        SELECT da1.*
        FROM `tabDescriptive Assessment` da1
        JOIN (
            SELECT roast_batch, MAX(modified) AS m
            FROM `tabDescriptive Assessment`
            WHERE docstatus < 2
            GROUP BY roast_batch
        ) x ON x.roast_batch = da1.roast_batch AND x.m = da1.modified
        WHERE {" AND ".join(where_da)}
    """
    ea_sub = """
        SELECT ea1.*
        FROM `tabExtrinsic Assessment` ea1
        JOIN (
            SELECT roast_batch, MAX(modified) AS m
            FROM `tabExtrinsic Assessment`
            WHERE docstatus < 2
            GROUP BY roast_batch
        ) x ON x.roast_batch = ea1.roast_batch AND x.m = ea1.modified
    """
    pa_sub = """
        SELECT pa1.*
        FROM `tabPhysical Assessment` pa1
        JOIN (
            SELECT roast_batch, MAX(modified) AS m
            FROM `tabPhysical Assessment`
            WHERE docstatus < 2
            GROUP BY roast_batch
        ) x ON x.roast_batch = pa1.roast_batch AND x.m = pa1.modified
    """
    aa_sub = """
        SELECT aa1.*
        FROM `tabAffective Assessment` aa1
        JOIN (
            SELECT roast_batch, MAX(modified) AS m
            FROM `tabAffective Assessment`
            WHERE docstatus < 2
            GROUP BY roast_batch
        ) x ON x.roast_batch = aa1.roast_batch AND x.m = aa1.modified
    """

    sql = f"""
        SELECT
            da.roast_batch,
            da.sample_no,
            da.roast_date,
            da.roast_time,
            da.roast_level,

            -- Extrinsic Assessment fields
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

            -- Physical Assessment (COLOR FIELDS)
            pa.blue_green,
            pa.bluish_green,
            pa.green,
            pa.greenish,
            pa.yellow_green,
            pa.pale_yellow,
            pa.yellowish,
            pa.brownish,

            -- Physical Assessment (MOISTURE & SUMMARY)
            pa.moisture,
            pa.total_full_defects,
            pa.max_screen_size,
            pa.grade AS physical_grade,

            -- Affective Assessment
            aa.total_score AS affective_total_score,
            aa.grade       AS affective_grade

        FROM ({da_sub}) da
        LEFT JOIN ({ea_sub}) ea ON ea.roast_batch = da.roast_batch
        LEFT JOIN ({pa_sub}) pa ON pa.roast_batch = da.roast_batch
        LEFT JOIN ({aa_sub}) aa ON aa.roast_batch = da.roast_batch
        ORDER BY da.roast_batch DESC
        LIMIT 100
    """
    data = frappe.db.sql(sql, vals, as_dict=True)

    columns = [
        {"label":"Roast Batch","fieldname":"roast_batch","fieldtype":"Link","options":"Roast Batch","width":160},
        {"label":"Sample No","fieldname":"sample_no","fieldtype":"Data","width":110},
        {"label":"Roast Date","fieldname":"roast_date","fieldtype":"Date","width":105},
        {"label":"Roast Time","fieldname":"roast_time","fieldtype":"Time","width":95},
        {"label":"Roast Level","fieldname":"roast_level","fieldtype":"Data","width":100},

        {"label":"Assessor Name","fieldname":"assessor_name","fieldtype":"Data","width":140},
        {"label":"Assessment Date","fieldname":"assessment_date","fieldtype":"Date","width":110},
        {"label":"Purpose","fieldname":"purpose","fieldtype":"Data","width":120},
        {"label":"Country","fieldname":"country","fieldtype":"Data","width":100},
        {"label":"Region","fieldname":"region","fieldtype":"Data","width":110},
        {"label":"Farm/Coop","fieldname":"farm_or_coop_name","fieldtype":"Data","width":140},
        {"label":"Producer Name","fieldname":"producer_name","fieldtype":"Data","width":140},
        {"label":"Species","fieldname":"species","fieldtype":"Data","width":90},
        {"label":"Variety","fieldname":"variety","fieldtype":"Data","width":120},
        {"label":"Harvest Date/Year","fieldname":"harvest_date_year","fieldtype":"Data","width":140},
        {"label":"Other Farming Attribute","fieldname":"other_farming_attribute","fieldtype":"Data","width":160},
        {"label":"Farming Notes","fieldname":"farming_notes","fieldtype":"Data","width":180},
        {"label":"Processor Name","fieldname":"processor_name","fieldtype":"Data","width":140},
        {"label":"Process Type","fieldname":"process_type","fieldtype":"Data","width":120},
        {"label":"Processing Notes","fieldname":"processing_notes","fieldtype":"Data","width":180},
        {"label":"Trading Size Grade","fieldname":"trading_size_grade","fieldtype":"Data","width":130},
        {"label":"Trading ICO Number","fieldname":"trading_ico_number","fieldtype":"Data","width":130},
        {"label":"Trading Other Grade","fieldname":"trading_other_grade","fieldtype":"Data","width":140},
        {"label":"Trading Other Attribute","fieldname":"trading_other_attribute","fieldtype":"Data","width":170},
        {"label":"Trading Notes","fieldname":"trading_notes","fieldtype":"Data","width":160},
        {"label":"Certifications","fieldname":"certifications","fieldtype":"Data","width":130},
        {"label":"Certification Notes","fieldname":"certification_notes","fieldtype":"Data","width":160},
        {"label":"General Notes","fieldname":"general_notes","fieldtype":"Data","width":180},

        {"label":"Blue-Green","fieldname":"blue_green","fieldtype":"Check","width":95},
        {"label":"Bluish-Green","fieldname":"bluish_green","fieldtype":"Check","width":110},
        {"label":"Green","fieldname":"green","fieldtype":"Check","width":80},
        {"label":"Greenish","fieldname":"greenish","fieldtype":"Check","width":90},
        {"label":"Yellow-Green","fieldname":"yellow_green","fieldtype":"Check","width":110},
        {"label":"Pale Yellow","fieldname":"pale_yellow","fieldtype":"Check","width":100},
        {"label":"Yellowish","fieldname":"yellowish","fieldtype":"Check","width":90},
        {"label":"Brownish","fieldname":"brownish","fieldtype":"Check","width":90},

        {"label":"Moisture (%)","fieldname":"moisture","fieldtype":"Float","width":110},
        {"label":"Total Full Defects","fieldname":"total_full_defects","fieldtype":"Int","width":130},
        {"label":"Max Screen Size","fieldname":"max_screen_size","fieldtype":"Int","width":120},
        {"label":"Physical Grade","fieldname":"physical_grade","fieldtype":"Int","width":110},

        {"label":"Affective Total Score","fieldname":"affective_total_score","fieldtype":"Int","width":140},
        {"label":"Affective Grade","fieldname":"affective_grade","fieldtype":"Int","width":120},
    ]
    return columns, data
