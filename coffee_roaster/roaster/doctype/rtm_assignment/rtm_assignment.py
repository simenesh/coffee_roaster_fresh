import frappe
from frappe.model.document import Document

def _pick_default_company():
    # 1) user default, 2) global default, 3) any leaf company
    ud = frappe.defaults.get_user_default("company")
    if ud and frappe.db.exists("Company", ud): return ud
    gd = frappe.defaults.get_global_default("company")
    if gd and frappe.db.exists("Company", gd): return gd
    return frappe.db.get_value("Company", {"is_group": 0}, "name")

class RTMAssignment(Document):
    def validate(self):
        # Keep your other validations here if you have them
        self._ensure_company()
        self._populate_customer_name()
        self._enforce_uniqueness()
        self._populate_contact_details()
        self._populate_address_details()
        self._normalize_weekly_fields()

    # --- helpers (safe no-ops unless the fields exist) ---

    def _ensure_company(self):
        meta = getattr(self, "meta", None)
        has_company = bool(meta and meta.get_field("company")) or hasattr(self, "company")
        if not has_company:
            return
        if getattr(self, "company", None):
            return
        chosen = _pick_default_company()
        if chosen:
            self.company = chosen
        else:
            frappe.throw("Please set Company or configure a Default Company (Setup → Global Defaults).",
                         title="Company Required")

    def _populate_customer_name(self):
        if not (hasattr(self, "customer") and hasattr(self, "customer_name")):
            return
        if self.customer and not self.customer_name:
            self.customer_name = frappe.db.get_value("Customer", self.customer, "customer_name") or self.customer

    def _enforce_uniqueness(self):
        if not (hasattr(self, "customer") and hasattr(self, "day")):
            return
        if not (self.customer and self.day):
            return
        exists = frappe.db.exists("RTM Assignment", {
            "name": ["!=", self.name or ""], "customer": self.customer,
            "day": self.day, "docstatus": ["<", 2]
        })
        if exists:
            frappe.throw(f"Another RTM Assignment already exists for {self.customer} on {self.day}.",
                         title="Duplicate Assignment")

    def _populate_contact_details(self):
        # Safe placeholder; extend as needed
        return

    def _populate_address_details(self):
        # Safe placeholder; extend as needed
        return

    def _normalize_weekly_fields(self):
        if not hasattr(self, "day"): return
        if self.day:
            d = str(self.day).strip().lower()
            days = {"monday","tuesday","wednesday","thursday","friday","saturday","sunday"}
            if d in days: self.day = d.capitalize()

