from frappe.model.document import Document

class CustomerInteraction(Document):
    def before_insert(self):
        # optional: log or sync interaction with a custom lead process
        pass

