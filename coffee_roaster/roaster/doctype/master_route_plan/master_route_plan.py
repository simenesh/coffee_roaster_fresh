import frappe

def autoname(doc, method=None):
    if not doc.route_order:
        doc.route_order = 0
