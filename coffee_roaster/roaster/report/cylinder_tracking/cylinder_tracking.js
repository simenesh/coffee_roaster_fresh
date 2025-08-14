frappe.query_reports["Cylinder Tracking"] = {
  filters: [
    { fieldname: "roast_cylinder", label: __("Cylinder"), fieldtype: "Link", options: "Roast Cylinder", default: "" },
    { fieldname: "from_date", label: __("From Date"), fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1), reqd: 1 },
    { fieldname: "to_date", label: __("To Date"), fieldtype: "Date",
      default: frappe.datetime.get_today(), reqd: 1 },
    { fieldname: "roasting_machine", label: __("Machine"), fieldtype: "Link", options: "Roasting Machine", default: "" },
    { fieldname: "operator", label: __("Operator"), fieldtype: "Link", options: "User", default: "" },
  ],
  onload(report) {
    ["roast_cylinder","roasting_machine","operator"].forEach(k => {
      const v = report.get_filter_value(k);
      if (v === undefined || v === null) report.set_filter_value(k, "");
    });
    if (!report.get_filter_value("from_date")) {
      report.set_filter_value("from_date", frappe.datetime.add_months(frappe.datetime.get_today(), -1));
    }
    if (!report.get_filter_value("to_date")) {
      report.set_filter_value("to_date", frappe.datetime.get_today());
    }
  },
};
frappe.query_reports["Cylinder Tracking"].onload = function(report) {
  // Ensure that the filters are set to default values if not already set
  ["roast_cylinder", "roasting_machine", "operator"].forEach(k => {
    const v = report.get_filter_value(k);
    if (v === undefined || v === null) report.set_filter_value(k, "");
  });
  
  if (!report.get_filter_value("from_date")) {
    report.set_filter_value("from_date", frappe.datetime.add_months(frappe.datetime.get_today(), -1));
  }
  
  if (!report.get_filter_value("to_date")) {
    report.set_filter_value("to_date", frappe.datetime.get_today());
  }
};
frappe.query_reports["Cylinder Tracking"].filters = frappe.query_reports["Cylinder Tracking"].filters || [];
frappe.query_reports["Cylinder Tracking"].filters.push(
  { fieldname: "include_inactive", label: __("Include Inactive Cylinders"),
    fieldtype: "Check", default: 0, description: __("Include cylinders that are inactive in the report") }
);
// List fields whose values are objects (likely the culprit)
Object.entries(cur_frm.doc)
  .filter(([k, v]) => v && typeof v === "object" && !Array.isArray(v))
  .map(([k, v]) => ({
    fieldname: k,
    fieldtype: cur_frm.fields_dict[k]?.df?.fieldtype,
    sample: JSON.stringify(v).slice(0, 200) + "..."
  }));
