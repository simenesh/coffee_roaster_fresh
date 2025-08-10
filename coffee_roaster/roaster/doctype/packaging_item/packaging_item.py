import frappe
from frappe.model.document import Document

class PackagingItem(Document):
    def autoname(self):
        if not self.item_code:
            self.item_code = self.item_name.lower().replace(" ", "-")

    def validate(self):
        # auto-fill capacity_kg for containers
        if self.is_container and not self.capacity_kg:
            if self.pack_size_g and self.units_per_container:
                self.capacity_kg = (self.pack_size_g * self.units_per_container) / 1000
