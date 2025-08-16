frappe.query_reports["Combined Assessment Report"] = {
  filters: [
    { fieldname: "roast_batch", label: __("Roast Batch"), fieldtype: "Link", options: "Roast Batch", default: "" },
    { fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: "" },
    { fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: "" }
  ]
};
