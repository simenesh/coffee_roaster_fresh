import frappe
from frappe.model.document import Document

class GreenBeanAssessment(Document):
    def on_submit(self):
        if not self.batch_no or not self.item_code:
            frappe.throw("Batch No and Item Code are required.")

        src_wh = "QC Pending - CR"
        if self.qc_result == "Pass":
            target_wh = "Green Beans - CR"
        else:
            target_wh = "Rejected Beans - CR"

        qty = self.total_qty or 0
        if qty <= 0:
            frappe.throw("Total Qty must be greater than zero for QC transfer.")

        # Create Material Transfer
        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Transfer",
            "items": [{
                "item_code": self.item_code,
                "qty": qty,
                "s_warehouse": src_wh,
                "t_warehouse": target_wh,
                "batch_no": self.batch_no,
                "uom": "Kg"
            }]
        })
        se.insert(ignore_permissions=True)
        se.submit()
        frappe.msgprint(f"Batch {self.batch_no} moved to {target_wh}"
