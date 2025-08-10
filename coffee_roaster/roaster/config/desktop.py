from frappe import _

def get_data():
    return [
        {
            "module_name": "Coffee Roaster",
            "color": "#874c22",
            "icon": "octicon octicon-flame",
            "type": "module",
            "label": _("Coffee Roaster"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Roast Profile",
                    "label": _("Roast Profiles")
                },
                {
                    "type": "doctype",
                    "name": "Roast Batch",
                    "label": _("Roast Batches")
                },
                {
                    "type": "doctype",
                    "name": "Roast Log",
                    "label": _("Roast Logs")
                },
                {
                    "type": "doctype",
                    "name": "Green Bean Assessment",
                    "label": _("Green Bean Assessments")
                },
                {
                    "type": "doctype",
                    "name": "Descriptive Assessment",
                    "label": _("Descriptive Assessments")
                },
                {
                    "type": "doctype",
                    "name": "Affective Assessment",
                    "label": _("Affective Assessments")
                },
                {
                    "type": "doctype",
                    "name": "Physical Assessment",
                    "label": _("Physical Assessments")
                },
                {
                    "type": "doctype",
                    "name": "Extrinsic Assessment",
                    "label": _("Extrinsic Assessments")
                }
            ]
        }
    ]