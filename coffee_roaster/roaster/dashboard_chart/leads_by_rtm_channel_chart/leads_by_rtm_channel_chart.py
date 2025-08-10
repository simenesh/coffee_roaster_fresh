import frappe
from frappe import _

def execute(filters=None):
    data = frappe.get_all(
        "Lead",
        fields=["preferred_rtm_channel", "count(name) as total"],
        filters={"docstatus": ["<", 2]},
        group_by="preferred_rtm_channel",
        order_by="total desc"
    )

    labels = [d["preferred_rtm_channel"] or "Not Set" for d in data]
    values = [d["total"] for d in data]

    return {
        "labels": labels,
        "datasets": [{"name": _("Leads"), "values": values}]
    }

