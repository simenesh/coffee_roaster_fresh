import frappe
from frappe import _
from frappe.utils import flt

def make_roasted_stock_entry(doc, method):
    if doc.workflow_state != "Completed":      # called on on_update
        return

    if frappe.db.exists("Stock Entry", {"roast_batch": doc.name, "purpose": "Manufacture"}):
        return  # already done

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Manufacture"
    se.purpose = "Manufacture"
    se.set_posting_time = 1
    se.posting_date = doc.packaging_date
    se.posting_time = "00:00:00"
    se.roast_batch = doc.name

    # Finished goods (target)
    se.append("items", {
        "item_code": "ROASTED-COFFEE",  # create Item once, maintain_stock=1
        "qty": flt(doc.packaged_weight),
        "uom": "kg",
        "t_warehouse": "Finished Goods - COFFEE"
    })

    se.insert(ignore_permissions=True)
    se.submit()
    frappe.msgprint(_("Stock Entry {0} created").format(se.name))

