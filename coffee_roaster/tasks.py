# apps/coffee_roaster/coffee_roaster/tasks.py

import frappe

def import_machine_logs():
    # e.g., read a file or call your machine’s API
    logs = read_csv("/path/to/machine.csv")
    for row in logs:
        frappe.get_doc({
            "doctype": "Roast Log",
            "batch": row["batch_id"],
            "temperature": row["temp"],
            "timestamp": row["time"],
            
        }).insert(ignore_permissions=True)

