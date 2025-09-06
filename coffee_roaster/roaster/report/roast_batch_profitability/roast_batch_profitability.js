// Place next to the .py as your report JS
frappe.query_reports["Roast Batch Profitability"] = {
  "filters": [
    {
      "fieldname": "roast_date_range",
      "label": "Roast Date",
      "fieldtype": "DateRange"
    },
    {
      "fieldname": "roast_batch",
      "label": "Roast Batch",
      "fieldtype": "Link",
      "options": "Roast Batch"
    },
    {
      "fieldname": "rb_docstatus",
      "label": "Roast Batch State",
      "fieldtype": "Select",
      "options": ["Both", "Draft", "Submitted"],
      "default": "Both"
    },
    {
      "fieldname": "only_submitted_batch_cost",
      "label": "Only batches with submitted Batch Cost",
      "fieldtype": "Check",
      "default": 0
    }
  ]
}
