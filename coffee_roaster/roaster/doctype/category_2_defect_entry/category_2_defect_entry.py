import frappe
from frappe.model.document import Document

class Category2DefectEntry(Document):
    def validate(self):
        weights = {
            "Partial Black": 3,
            "Partial Sour": 3,
            "Parchment / Pergamino": 5,
            "Floater": 5,
            "Immature / Unripe": 5,
            "Withered": 5,
            "Shell": 5,
            "Broken / Chipped / Cut": 5,
            "Hull / Husk": 5,
            "Slight Insect Damage": 10,
        }

        self.full_defects = self.defect_count * weights.get(self.defect_type, 1)
