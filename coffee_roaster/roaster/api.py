import frappe
from frappe import _

def validate_item(doc, method):
    """Validate that a default warehouse is set for stock items."""
    if not hasattr(doc, 'maintain_stock'):
        return

    if doc.maintain_stock and not doc.default_warehouse:
        frappe.throw(_("Default Warehouse is required for stock item: {0}").format(doc.item_code))

def validate_warehouse(doc, method):
    """Ensure warehouse has a company set."""
    if not doc.company:
        frappe.throw(_("Company is required"))

def check_warehouse_empty(doc, method):
    """Prevent deletion if warehouse contains stock."""
    stock_balance = frappe.db.get_value(
        "Stock Ledger Entry",
        filters={"warehouse": doc.name},
        fieldname="SUM(actual_qty)"
    )

    if stock_balance and stock_balance > 0:
        frappe.throw(
            _("Cannot delete {0}: {1} units still in stock").format(doc.name, stock_balance),
            title=_("Warehouse Not Empty")
        )

def validate_phase_times(doc, method):
    """Ensure end time is after start time."""
    if doc.end_time <= doc.start_time:
        frappe.throw(_("End Time must be after Start Time"))

def calculate_weight_loss(doc, method):
    """Calculate roast weight loss."""
    if not doc.input_weight or not doc.output_weight:
        doc.weight_loss = 0
        doc.weight_loss_percentage = 0
        return

    if doc.output_weight > doc.input_weight:
        frappe.throw(_("Output weight cannot be greater than input weight."))

    doc.weight_loss = doc.input_weight - doc.output_weight
    doc.weight_loss_percentage = (
        (doc.weight_loss / doc.input_weight) * 100
        if doc.input_weight else 0
    )

def create_stock_entry_from_roasted(roasted_name):
    """Create a Material Receipt Stock Entry from Roasted Coffee record."""
    roasted = frappe.get_doc("Roasted Coffee", roasted_name)

    if not roasted.item:
        frappe.throw(_("Roasted Coffee must have an Item Code."))
    if not roasted.warehouse:
        frappe.throw(_("Roasted Coffee must have a Warehouse."))
    if not roasted.quantity:
        frappe.throw(_("Roasted Coffee must have a Quantity."))

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Receipt"
    stock_entry.purpose = "Material Receipt"
    stock_entry.to_warehouse = roasted.warehouse

    stock_entry.append("items", {
        "item_code": roasted.item,
        "qty": roasted.quantity,
        "uom": "Gram",  # change to "Kg" if that's your UOM
        "conversion_factor": 1,
        "t_warehouse": roasted.warehouse
    })

    stock_entry.insert()
    stock_entry.submit()

    roasted.db_set("status", "In Stock")

    frappe.msgprint(
        _("Stock Entry {0} created for Roasted Coffee {1}")
        .format(stock_entry.name, roasted.name)
    )

