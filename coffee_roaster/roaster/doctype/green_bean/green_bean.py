import frappe
from frappe.model.document import Document

class GreenBean(Document):
    def on_submit(self):
        if not self.item:
            # Build a unique item code
            item_code = f"{self.origin}-{self.grade}-{self.received_date}"
            item_code = item_code.replace(" ", "-").upper()

            # Check if it already exists (prevent duplicates)
            if frappe.db.exists("Item", item_code):
                item_doc = frappe.get_doc("Item", item_code)
            else:
                # Create new item
                item_doc = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": f"{self.origin} {self.grade}",
                    "item_group": "Green Beans",
                    "is_stock_item": 1,
                    "stock_uom": "Kg",
                    "description": f"Green beans from {self.origin}, Grade {self.grade}, Lot {self.lot_number or 'N/A'}",
                    "is_purchase_item": 1,
                    "is_production_item": 1,
                    "is_sales_item": 0,
                }).insert(ignore_permissions=True)

            # Link it back to this Green Bean
            self.db_set("item", item_doc.name)
            frappe.msgprint(f"✅ Linked Item <b>{item_doc.name}</b> has been created.")

