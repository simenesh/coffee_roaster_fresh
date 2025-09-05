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
# hooks.py

fixtures = [
    # Custom fields you added to these doctypes
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "in", ["Sales Invoice", "Sales Invoice Item", "Customer", "Route Plan"]]
        ],
    },

    # Property Setters (reqd/hidden/read-only/labels/order/etc.) for those doctypes
    {
        "doctype": "Property Setter",
        "filters": [
            ["doc_type", "in", ["Sales Invoice", "Sales Invoice Item", "Customer", "Route Plan"]]
        ],
    },

    # Client Scripts you created (form logic)
    {
        "doctype": "Client Script",
        "filters": [
            ["dt", "in", ["Sales Invoice", "Customer", "Route Plan"]]
        ],
    },

    # Server Scripts (if any) tied to these doctypes
    {
        "doctype": "Server Script",
        "filters": [
            ["reference_doctype", "in", ["Sales Invoice", "Customer", "Route Plan"]]
        ],
    },

    # Print Formats you rely on (e.g., custom SI print)
    {
        "doctype": "Print Format",
        "filters": [
            ["doc_type", "in", ["Sales Invoice", "Customer"]]
        ],
    },

    # Custom Reports you mentioned (names must match exactly)
    {
        "doctype": "Report",
        "filters": [
            ["name", "in", ["Master Route Plan by Sub City", "SAG Export"]]
        ],
    },

    # Optional: Workspaces if you customized them
    # {"doctype": "Workspace"},
]

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
    {
        "doctype": "Report",
        "filters": [
            ["name", "in", ["Roast Batch Profitability", "SKU Profit"]]
        ]
    },
    {
        "doctype": "Server Script",
        "filters": [
            ["name", "in", ["Apply VAT on Sales Invoice", "Post Batch Cost GL Entry"]]
        ]
    },
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "in", ["Sales Invoice", "Batch Cost", "Roast Batch"]]
        ]
    },
    
     {"dt": "Custom Field", "filters": [["dt", "in", ["Route Plan Detail", "Customer"]]]},
  {"dt": "Property Setter"},
  {"dt": "Custom DocPerm", "filters": {"parent": ["in", ["Route Plan", "Route Plan Detail"]]}},
    {"doctype": "Role", "filters": {"name": ["in", ["Roaster User", "Roaster Manager"]]}},
    {"doctype": "Role Profile", "filters": {"name": "Roaster Default"}},
    {"doctype": "Module Def", "filters": {"name": "Roaster"}},
    {"doctype": "Module Def", "filters": {"name": "RTM"}},
    {"doctype": "Report", "filters": {"name": ["in", [
        "SKU Profitability",
        "Roast Batch Costing",
        "Raw Bean Cost",
        "Packaging Cost",
        "Roasting Overhead Cost",
        "Roasting Overhead Template Cost",
        "Monthly Green Bean Purchases",
        "Monthly Roasted Coffee Sales",
        "Customer Interaction Report",
        "Loyalty Points Summary",
        "Loyalty Points Expiry",
        "Route Plan",
        "Master Route Plan by Sub City"
    ]]}},
    {"doctype": "Print Format", "filters": [["name", "in", [
        "Roast Batch",
        "Green Bean",
        "Sales Invoice",
        "Delivery Note"
    ]]]},
    {"doctype": "Workflow Action", "filters": [["name", "in", [
        "Open to Qualified",
        "Qualified to Converted",
        "Qualified to Lost"
    ]]]},
    {"doctype": "Workflow", "filters": [["name", "in", [
        "Lead Workflow"
    ]]]},
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
