# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "coffee_roaster"
app_title = "Coffee Roaster"
app_publisher = "Sime"
app_description = " ERP for coffee roasting workflows" # THIS LINE IS CRITICAL
app_email = "your.email@example.com"
app_license = "mit"
# ... other details ...

doc_events = {
    "Roast Batch": {
        # The ONLY event needed for the inventory transaction
         "on_submit": "coffee_roaster.roaster.events.create_roasting_stock_entry" 
    },
     "Sales Invoice": {
        "validate": "coffee_roaster.finance_integration.apply_vat_on_invoice"
    }
}

doctype_js = {
    # We only need JS for the Roast Batch form itself
     "Roast Batch": "roaster/js/roast_batch.js"
    }


# You should export your new Workflow and Custom Fields via fixtures

# REMOVE the override_doctype_class. It's not needed and adds complexity.
# REMOVE all other doc_events related to custom stock doctypes.

#Data to be exported with the app
# Data to be exported with the app
fixtures = [
    {"doctype": "Custom Field", "filters": [["module", "=", "Roaster"]]},
    {"doctype": "Property Setter", "filters": [["module", "=", "Roaster"]]},
    {"doctype": "Client Script", "filters": [["module", "=", "Roaster"]]},
    {"doctype": "Server Script", "filters": [["module", "=", "Roaster"]]},
    {"doctype": "Workspace", "filters": [["module", "=", "Roaster"]]},
    {"doctype": "Custom DocPerm", "filters": [["parent", "in", [
        "Roast Batch",
        "Batch Cost",
        "Raw Bean Cost Item",
        "Overhead Item",
        "Packaging Cost Item",
        "Roasting Overhead Template",
        "Roasting Overhead Template Item",
        "Roasting Overhead Item",
        "Loyalty Profile",
        "Customer Interaction",
        "RTM Assignment",
        "Roaster Settings",
        "Roasting Machine",
        "Roast Machine Telemetry",
        "Green Bean",
        "Physical Assessment",
        "Descriptive Assessment",
        "Extrinsic Assessment",
        "Affective Assessment",
        "Combined Assessment",
    ]]]},
    {"doctype": "Workflow", "filters": [["module", "=", "Roaster"]]},
]
