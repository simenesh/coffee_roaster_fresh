import frappe
from frappe.model.document import Document

class GreenBeanAssessment(Document):
    def before_insert(self):
        if not self.sample_id:
            self.sample_id = frappe.model.naming.make_autoname("GBA-{YYMM}-.#####")
