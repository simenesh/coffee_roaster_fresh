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
    # Generic core customizations
    "Property Setter",
    "Client Script",
    "Server Script",
    "Report",

    # All custom fields
    {"dt": "Custom Field"},

    # Custom permissions and notifications
    {"dt": "Custom DocPerm"},

    # Reports and dashboard charts
    {"dt": "Report", "filters": [["name", "in", [
        "Combined Assessment Report",
        "Cylinder Tracking",
        "Lead Interest Level",
        "Leads by RTM Channel",
        "Loyalty Profile Summary"
    ]]]},
    {"doctype": "Server Script", "filters": [["reference_doctype", "=", "Roast Batch"]]},
    {"dt": "Dashboard Chart"},

    # Workflows
    {"dt": "Workflow", "filters": [["name", "in", [
        "Roast Batch Workflow",
        "Roasting Overhead Template Workflow",
        "Roasting Overhead Template Item Workflow",
        "Roasting Overhead Item Workflow",
        "Raw Bean Cost Item Workflow",
        "Batch Cost Workflow",
        "Packaging Cost Item Workflow",
        "Lead Workflow",
        "Customer Interaction Workflow",
        "Loyalty Profile Workflow"
    ]]]}
]
