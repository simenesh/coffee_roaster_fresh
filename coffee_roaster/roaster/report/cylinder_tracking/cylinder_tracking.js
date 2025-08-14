frappe.query_reports["Cylinder Tracking"] = {
  filters: [
    { fieldname: "roast_cylinder", label: __("Cylinder"), fieldtype: "Link", options: "Roast Cylinder", default: "" },
    { fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: "" },
    { fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: "" }
  ]
};
