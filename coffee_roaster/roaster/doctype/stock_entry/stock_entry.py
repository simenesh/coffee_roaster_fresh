import frappe

def update_roast_batch_batch_no(doc, method):
    """
    On submit of a Manufacture Stock Entry linked to a Roast Batch,
    copy the produced batch_no back into that Roast Batch record.
    """
    if doc.purpose == "Manufacture" and doc.get("roast_batch"):
        for row in doc.items:
            # detect the finished‐goods row
            if row.batch_no and row.t_warehouse:
                frappe.db.set_value(
                    "Roast Batch",
                    doc.roast_batch,
                    "batch_no",
                    row.batch_no
                )
                break
