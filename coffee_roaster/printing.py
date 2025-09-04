import frappe

def _get_company_field_safe(company_name: str, candidates: list[str]) -> str:
    """Try a list of possible fieldnames on Company, return first non-empty value.
       Never throws if a field/column is missing."""
    if not company_name:
        return ""
    # Use has_column to avoid 1054 errors
    for field in candidates:
        try:
            if frappe.db.has_column("Company", field):
                val = frappe.db.get_value("Company", company_name, field)
                if val:
                    return val
        except Exception:
            # Ignore any unexpected errors and try next candidate
            pass
    return ""

def get_company_tin(company_name: str) -> str:
    # Standard ERPNext field for TIN is tax_id
    return _get_company_field_safe(company_name, ["tax_id"])

def get_company_vat_reg(company_name: str) -> str:
    # Try common custom/legacy names. Keep your preferred one first if you later add it.
    return _get_company_field_safe(company_name, [
        "vat_registration_number", "vat_id", "vat_reg_no", "vat_no", "company_vat_number"
    ])

def get_company_phone(company_name: str) -> str:
    # Common field is phone_no; fall back to phone/phone_number if present
    return _get_company_field_safe(company_name, ["phone_no", "phone", "phone_number"])

def get_company_address_display(company_name: str) -> str:
    """Return the Address.address_display of Company.company_address, safely."""
    try:
        if not company_name:
            return ""
        if not frappe.db.has_column("Company", "company_address"):
            return ""
        addr_name = frappe.db.get_value("Company", company_name, "company_address")
        if not addr_name:
            return ""
        # address_display is standard on Address
        return frappe.db.get_value("Address", addr_name, "address_display") or ""
    except Exception:
        return ""

