import frappe
from frappe.utils import flt
from frappe.utils.file_manager import get_file
from ...machines.service import import_curve_into_log

# TOP of file
from frappe.utils.file_manager import get_file

# ✅ use absolute import (avoid relative import resolution issues)
from coffee_roaster.roaster.machines.service import import_curve_into_log

@frappe.whitelist()
def import_roast_curve_from_attachment(name: str, adapter: str=None):
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Coffee Roasting Log", "attached_to_name": name},
        fields=["file_url"],
        order_by="creation desc",
        limit=1
    )
    if not files:
        frappe.throw("No attachment found on this Coffee Roasting Log.")
    return import_curve_into_log(
        "Coffee Roasting Log",
        name,
        file_url=files[0]["file_url"],
        adapter=adapter,
    )

@frappe.whitelist()
def import_roast_curve_from_attachment(name: str, adapter: str=None):
    files = frappe.get_all("File",
        filters={"attached_to_doctype": "Coffee Roasting Log", "attached_to_name": name},
        fields=["file_url"], order_by="creation desc", limit=1
    )
    if not files:
        frappe.throw("No attachment found on this Coffee Roasting Log.")
    return import_curve_into_log("Coffee Roasting Log", name, file_url=files[0]["file_url"], adapter=adapter)

def _pick(doc, doctype, *candidates):
    for f in candidates:
        if frappe.db.has_column(doctype, f):
            return doc.get(f)
    return None

@frappe.whitelist()
def pull_from_roast_batch(roast_batch: str) -> dict:
    if not roast_batch:
        frappe.throw("Roast Batch is required")
    dt = "Roast Batch"
    rb = frappe.get_doc(dt, roast_batch)
    result = {
        "roast_date":        _pick(rb, dt, "roast_date", "posting_date", "date"),
        "company":           _pick(rb, dt, "company"),
        "roasted_item":      _pick(rb, dt, "roasted_item", "item", "finished_item", "fg_item"),
        "roaster_used":      _pick(rb, dt, "roaster_used", "roasting_machine", "machine"),
        "roast_profile":     _pick(rb, dt, "roast_profile", "profile"),
        "green_origin":      _pick(rb, dt, "green_origin", "origin"),
        "green_grade":       _pick(rb, dt, "green_grade", "grade"),
        "batch_weight_kg":   flt(_pick(rb, dt, "input_weight", "green_weight", "batch_weight_kg", "total_input_qty", "input_qty")),
        "yield_kg":          flt(_pick(rb, dt, "output_weight", "yield_kg", "total_output_qty", "roasted_weight", "output_qty")),
        "charge_temp_c":     _pick(rb, dt, "charge_temp", "charge_temperature_c"),
        "final_temp_c":      _pick(rb, dt, "final_temp", "drop_temp", "drop_temperature_c"),
        "color_agtron":      _pick(rb, dt, "agtron", "color_agtron"),
        "quality_inspection":_pick(rb, dt, "quality_inspection"),
    }
    bw, y = flt(result.get("batch_weight_kg")), flt(result.get("yield_kg"))
    if bw > 0 and y >= 0:
        result["weight_loss_pct"] = (1 - (y / bw)) * 100.0
    phases = []
    meta = frappe.get_meta(dt)
    phase_child = None
    for f in meta.fields:
        if f.fieldtype == "Table" and (f.options or "").lower().find("phase") >= 0:
            phase_child = f.options
            break
    if phase_child and frappe.db.table_exists("tab" + phase_child):
        rows = frappe.get_all(
            phase_child,
            filters={"parenttype": dt, "parent": rb.name},
            fields=["phase", "start_time", "end_time", "temperature_c", "observations"]
        )
        for r in rows:
            phases.append({
                "phase": r.get("phase"),
                "start_time": r.get("start_time"),
                "end_time": r.get("end_time"),
                "temperature_c": r.get("temperature_c"),
                "observations": r.get("observations"),
            })
    return {"doc": result, "phases": phases}
