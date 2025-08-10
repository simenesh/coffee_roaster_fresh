"""Workspace config for Coffee Roaster"""
from frappe import _

def get_data():
    return {
        "label": _("Coffee Roaster"),
        "icon": "octicon octicon-beaker",
        "route": "coffee-roaster",
        "items": [
            # === Inventory Management ===
            {"type": "doctype", "name": "Item", "label": _("Products & Beans"), "description": _("Manage green & roasted coffee, packaging materials")},
            {"type": "doctype", "name": "Warehouse", "label": _("Warehouses"), "description": _("Locations for raw & finished goods")},
            {"type": "doctype", "name": "Stock Entry", "label": _("Stock Movements"), "description": _("Track inventory inflow and outflow")},

            # === Production & Roasting ===
            {"type": "doctype", "name": "Roast Batch", "label": _("Roast Batches"), "description": _("Schedule and log roast batches")},
            {"type": "doctype", "name": "Roast Log", "label": _("Roast Logs"), "description": _("Detailed roast profile entries")},
            {"type": "doctype", "name": "Roast Profile", "label": _("Roast Profiles"), "description": _("Manage standard roast curves")},

            # === Quality Control & Sensory ===
            {"type": "doctype", "name": "Green Bean Assessment", "label": _("Green Bean QC"), "description": _("Record defect levels in raw beans")},
            {"type": "doctype", "name": "Cupping Score Entry", "label": _("Cupping Scores"), "description": _("Log sensory evaluation results")},

            # === Sales & Orders ===
            {"type": "doctype", "name": "Sales Order", "label": _("Sales Orders"), "description": _("Manage customer orders")},
            {"type": "doctype", "name": "Sales Invoice", "label": _("Invoices"), "description": _("Billing and invoicing customers")},
            {"type": "doctype", "name": "Delivery Note", "label": _("Deliveries"), "description": _("Track shipments to customers")},

            # === Procurement & Suppliers ===
            {"type": "doctype", "name": "Purchase Order", "label": _("Purchase Orders"), "description": _("Manage raw bean and material purchases")},
            {"type": "doctype", "name": "Purchase Receipt", "label": _("Receipts"), "description": _("Record goods received from suppliers")},
            {"type": "doctype", "name": "Supplier", "label": _("Suppliers"), "description": _("Manage vendor contacts and terms")},

            # === Finance & Accounting ===
            {"type": "doctype", "name": "Journal Entry", "label": _("Journal Entries"), "description": _("Post accounting transactions")},
            {"type": "doctype", "name": "Cost Center", "label": _("Cost Centers"), "description": _("Track costs by department or batch")},

            # === CRM & Customers ===
            {"type": "doctype", "name": "Customer", "label": _("Customers"), "description": _("Manage B2B and B2C contacts")},
            {"type": "doctype", "name": "Lead", "label": _("Leads"), "description": _("Track potential customers and inquiries")},

            # === Dashboards & Quick Metrics ===
            {"type": "number_card", "label": _("Open Roast Batches"), "doctype": "Roast Batch", "fieldname": "name", "filters": {"workflow_state": "Open"}},
            {"type": "number_card", "label": _("Pending Sales Orders"), "doctype": "Sales Order", "fieldname": "name", "filters": {"status": "To Deliver and Bill"}},
            {"type": "number_card", "label": _("Low Stock Items"), "doctype": "Item", "fieldname": "name", "filters": {"qty_on_hand": ["<", 10]}},
            {"type": "chart", "label": _("Sales Trend (30d)"), "chart_type": "Line", "doctype": "Sales Invoice", "timespan": "Last 30 Days", "field": "grand_total", "values": ["grand_total"]},
            {"type": "chart", "label": _("Roast Duration Avg (30d)"), "chart_type": "Bar", "doctype": "Roast Log", "timespan": "Last 30 Days", "field": "duration", "values": ["duration"]}
        ]
    }

