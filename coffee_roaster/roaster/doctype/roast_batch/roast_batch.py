import frappe
from frappe.model.document import Document
from erpnext.stock.utils import get_stock_balance

class RoastBatch(Document):

    def validate(self):
        if self.qty_to_roast <= 0:
            frappe.throw("Input weight must be > 0 kg.")
        if self.output_qty and self.output_qty <= 0:
            frappe.throw("Output weight must be > 0 kg.")
        if self.qc_score and not 50 <= self.qc_score <= 100:
            frappe.throw("QC score must be between 50 and 100.")

        if self.qty_to_roast and self.output_qty:
            self.weight_loss_percentage = (
                (self.qty_to_roast - self.output_qty) / self.qty_to_roast * 100
            )

    @frappe.whitelist()
    def start_roast(self):
        if self.stock_entry_created:
            frappe.msgprint("Stock Entry already created.")
            return

        # Check stock availability
        available_qty = get_stock_balance(self.green_bean_item, self.source_warehouse)
        if available_qty < self.qty_to_roast:
            frappe.throw(
                f"Not enough {self.green_bean_item} in {self.source_warehouse}. "
                f"Available: {available_qty} kg; Needed: {self.qty_to_roast} kg."
            )

        # Create Batch
        batch = frappe.get_doc({
            "doctype": "Batch",
            "item": self.roasted_item,
            "manufacturing_date": self.roast_date
        }).insert(ignore_permissions=True)
        self.batch_no = batch.name

        # Create Stock Entry
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Manufacture"
        stock_entry.posting_date = self.roast_date

        stock_entry.append("items", {
            "item_code": self.green_bean_item,
            "qty": self.qty_to_roast,
            "s_warehouse": self.source_warehouse,
            "is_finished_item": 0
        })

        stock_entry.append("items", {
            "item_code": self.roasted_item,
            "qty": self.output_qty,
            "t_warehouse": self.target_warehouse,
            "batch_no": self.batch_no,
            "is_finished_item": 1
        })

        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()

        self.stock_entry_created = 1
        self.save()

        frappe.msgprint(f"Manufacture Stock Entry {stock_entry.name} created.")
        return stock_entry.name

