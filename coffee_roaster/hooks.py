# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "coffee_roaster"
app_title = "Coffee Roaster"
app_publisher = "Sime"
app_description = " ERP for coffee roasting workflows" # THIS LINE IS CRITICAL
app_email = "your.email@example.com"
app_license = "mit"
# ... other details ...

scheduler_events = {
    "cron": {
        "0 2 1 * *": [  # 02:00 on day 1 of every month
            "coffee_roaster.peachtree_export.export_previous_month_for_sage"
        ]
    }
}

doc_events = {
    "Roast Batch": {
        # The ONLY event needed for the inventory transaction
         "on_submit": "coffee_roaster.roaster.events.create_roasting_stock_entry" 
    },
     "Sales Invoice": {
        "validate": "coffee_roaster.finance_integration.apply_vat_on_invoice"
    },
      "Physical Assessment": {
        "on_submit": "coffee_roaster.roaster.doctype.physical_assessment.physical_assessment.PhysicalAssessment.on_submit"
    },
      "Batch Cost": {
        "on_submit": "coffee_roaster.finance_integration.post_batch_cost_gl_entry"
    },
     "Coffee Roasting Log": {
    "on_update_after_submit": "coffee_roaster.roaster.doctype.coffee_roasting_log.coffee_roasting_log_api.sync_phases_to_roast_batch"
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
    {"doctype": "Custom Field", "filters": {"module": "Roaster"}},
    {"doctype": "Property Setter", "filters": {"module": "Roaster"}},
    {"doctype": "Client Script", "filters": {"module": "Roaster"}},
    {"doctype": "Server Script", "filters": {"module": "Roaster"}},
    {"doctype": "Workspace", "filters": {"module": "Roaster"}},
     {"doctype": "Custom Field", "filters": [["dt","in",["Sales Invoice"]],["fieldname","in",["net_total_excl_vat"]]]},
  {"doctype": "Property Setter", "filters": [["doc_type","in",["Sales Invoice"]]]},
    {"doctype": "Custom DocPerm", "filters": {
        "parent": ["in", [
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
        ]]
    }},
    
    
    {"doctype": "Workflow State", "filters": [["workflow_state_name", "in", [
        "Open", "Qualified", "Converted", "Lost"
    ]]]},
    {"doctype": "Print Format", "filters": [["name", "in", [
"RTM Assignment — Detail"
]]]},

    {"doctype": "Workflow", "filters": {
        "name": ["in", [
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
        ]]
    }},

    {"doctype": "Server Script", "filters": {
        "reference_doctype": ["in", ["Green Bean Assessment", "Roast Batch"]]
    }},
     {"doctype": "Report", "filters": {"module": "Roaster"}},

    # 🚀 Explicitly include Combined Assessment Report
    {"doctype": "Report", "filters": {"name": "Combined Assessment Report"}},
]
jenv = {
    "methods": [
        "get_company_tin:coffee_roaster.printing.get_company_tin",
        "get_company_vat_reg:coffee_roaster.printing.get_company_vat_reg",
        "get_company_phone:coffee_roaster.printing.get_company_phone",
        "get_company_address_display:coffee_roaster.printing.get_company_address_display",
    ]
}
