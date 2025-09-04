# apps/coffee_roaster/coffee_roaster/roaster/doctype/waste_defective_item/waste_defective_item.py
import frappe
from frappe.model.document import Document

class WasteDefectiveItem(Document):
    pass

def on_doctype_update():
    # keep empty; prevents import errors when Frappe calls this
    pass
