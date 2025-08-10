import frappe
from frappe.utils import nowdate

# You do not need to import StockEntry class directly

def create_stock_entry(doc, method):
    """
    Auto-create and submit a Stock Entry when a Roast Batch is submitted.
    """
    se = frappe.new_doc("Stock Entry")
    se.purpose = "Material Receipt"
    se.company = doc.company
    se.posting_date = doc.roast_date or nowdate()
    se.to_warehouse = doc.target_warehouse

    se.append("items", {
        "item_code": doc.product_item_code,
        "qty": doc.quantity,
        "uom": doc.uom,
        "batch_no": doc.name
    })

    try:
        se.insert()
        se.submit()
    except Exception:
        frappe.log_error(
            message=frappe.get_traceback(),
            title=f"create_stock_entry failed for {doc.name}"
        )
