import frappe
from frappe.model.document import Document
from frappe.utils import flt

QC_PENDING_WH = "QC Pending - CR"
PASSED_WH     = "Green Beans - CR"
REJECTED_WH   = "Rejected Beans - CR"

class GreenBeanAssessment(Document):

    def validate(self):
        # required fields
        for f in ("item_code", "batch_no", "qc_result"):
            if not self.get(f):
                frappe.throw(f"Missing required field: {f}")

        if flt(self.total_qty) <= 0:
            frappe.throw("Total Qty (Kg) must be greater than zero.")

        # batch must belong to the same item
        batch_item = frappe.db.get_value("Batch", {"name": self.batch_no}, "item")
        if batch_item and batch_item != self.item_code:
            frappe.throw(f"Batch {self.batch_no} belongs to {batch_item}, not {self.item_code}.")

        # ensure qty exists in QC Pending
        bal = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty), 0)
            FROM `tabStock Ledger Entry`
            WHERE item_code=%s AND batch_no=%s AND warehouse=%s
        """, (self.item_code, self.batch_no, QC_PENDING_WH))[0][0]

        if flt(bal) < flt(self.total_qty):
            frappe.throw(
                f"Insufficient qty in {QC_PENDING_WH}. Available {bal}, required {self.total_qty} Kg."
            )

    def on_submit(self):
        # decide target warehouse by qc_result
        target_wh = PASSED_WH if self.qc_result == "Pass" else REJECTED_WH

        # create Material Transfer to move stock out of QC Pending
        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Transfer",
            "items": [{
                "item_code": self.item_code,
                "qty": flt(self.total_qty),
                "uom": "Kg",
                "s_warehouse": QC_PENDING_WH,
                "t_warehouse": target_wh,
                "batch_no": self.batch_no
            }]
        })
        se.insert(ignore_permissions=True)
        se.submit()

        frappe.msgprint(f"Batch {self.batch_no} moved to {target_wh}.")

