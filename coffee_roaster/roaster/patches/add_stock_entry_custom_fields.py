import frappe

def execute():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field

    create_custom_field("Stock Entry", {
        "fieldname": "roast_batch_no",
        "label": "Roast Batch No",
        "fieldtype": "Link",
        "options": "Roast Batch",
        "insert_after": "batch_no"
    })
    create_custom_field("Stock Entry", {
        "fieldname": "machine_id",
        "label": "Machine ID",
        "fieldtype": "Data",
        "insert_after": "roast_batch_no"
    })
