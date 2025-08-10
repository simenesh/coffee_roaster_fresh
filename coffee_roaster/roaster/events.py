# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.model.naming import make_autoname

@frappe.whitelist()
def create_roasting_stock_entry(doc, method):
    if frappe.db.exists("Stock Entry", {"custom_roast_batch": doc.name}):
        frappe.log_error("Duplicate Stock Entry creation attempt for Roast Batch", doc.name)
        return

    try:
        # 1. Get the active BOM for the finished item
        bom_name = frappe.db.get_value("BOM", {"item": doc.roasted_item, "is_active": 1})
        if not bom_name:
            frappe.throw(_("A valid, active Bill of Materials for Finished Item '{0}' is required.").format(doc.roasted_item))

        # 2. Manually create a unique name for the new batch
        new_batch_id = make_autoname(doc.name + '-.BATCH')

        # 3. Create and save the Batch document first
        batch = frappe.get_doc({
            "doctype": "Batch", "batch_id": new_batch_id, "item": doc.roasted_item,
            "reference_doctype": "Roast Batch", "reference_name": doc.name,
        }).insert(ignore_permissions=True)
        frappe.db.set_value("Roast Batch", doc.name, "batch_no", batch.name, update_modified=False)

        # 4. Create the new Stock Entry document
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Manufacture"
        se.purpose = "Manufacture"
        se.company = doc.company
        se.set("custom_roast_batch", doc.name)
        se.to_warehouse = doc.target_warehouse # For finished good

        # =====================================================================
        # MANUAL BOM ITEM FETCHING - THE FINAL FIX
        # =====================================================================
        # Step 5A: Add the FINISHED GOOD to the items table
        se.append("items", {
            "item_code": doc.roasted_item,
            "qty": doc.output_qty,
            "t_warehouse": doc.target_warehouse,
            "batch_no": new_batch_id,
            "is_finished_item": 1,
            "bom_no": bom_name # Link the BOM to the finished item
        })

        # Step 5B: Fetch the BOM document itself to get its materials
        bom = frappe.get_doc("BOM", bom_name)
        
        # Step 5C: Loop through the raw materials in the BOM and add them to the items table
        for material in bom.items:
            # Calculate the required quantity of this material for our production run
            # bom.quantity is the output qty of the BOM (e.g. 1), doc.output_qty is our actual run
            required_qty = (material.qty / bom.quantity) * doc.output_qty
            
            se.append("items", {
                "item_code": material.item_code,
                "qty": required_qty,
                "s_warehouse": doc.source_warehouse,
                "is_finished_item": 0,
            })
        # =====================================================================

        # 6. Finalize the inventory transaction
        se.insert(ignore_permissions=True)
        se.submit()
        frappe.msgprint(_("Manufacturing Stock Entry <a href='/app/stock-entry/{0}'>{0}</a> created.").format(se.name), indicator='green', alert=True)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Roast Batch Stock Entry Creation Failed")
        frappe.throw(_("Could not create the Manufacturing Stock Entry. Error: {0}").format(str(e)))