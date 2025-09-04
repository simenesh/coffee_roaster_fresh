# Route Plan Summary — safe starter that never crashes and returns basic rows
import frappe

def execute(filters=None):
    f = frappe._dict(filters or {})

    columns = [
        {"label": "Route No",    "fieldname": "route_no",    "fieldtype": "Int",     "width": 90},
        {"label": "Day",         "fieldname": "day",         "fieldtype": "Data",    "width": 90},
        {"label": "Customer",    "fieldname": "customer",    "fieldtype": "Link",    "options": "Customer", "width": 200},
        {"label": "Sub-City",    "fieldname": "sub_city",    "fieldtype": "Data",    "width": 140},
        {"label": "Outlet Type", "fieldname": "outlet_type", "fieldtype": "Data",    "width": 120}
    ]

    # You can adapt the source table/fields to your actual Master Route Plan schema.
    # This defensive SQL will work even if some columns are NULL or missing on older rows.
    data = frappe.db.sql("""
        SELECT
            COALESCE(mrp.route_no, 0)             AS route_no,
            COALESCE(mrp.day, '')                 AS day,
            COALESCE(mrp.customer, '')            AS customer,
            COALESCE(cus.sub_city, '')            AS sub_city,
            COALESCE(cus.outlet_type, '')         AS outlet_type
        FROM `tabMaster Route Plan` mrp
        LEFT JOIN `tabCustomer` cus ON cus.name = mrp.customer
        ORDER BY
            FIELD(mrp.day,'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'),
            mrp.route_no
    """, as_dict=True)

    return columns, data

