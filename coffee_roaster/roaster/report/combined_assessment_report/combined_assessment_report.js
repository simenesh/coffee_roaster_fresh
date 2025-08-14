frappe.query_reports["Combined Assessment"] = {
  filters: [
    {
      fieldname: "roast_batch",
      label: __("Roast Batch"),
      fieldtype: "Link",
      options: "Roast Batch",
      reqd: 0
    }
  ]
};
