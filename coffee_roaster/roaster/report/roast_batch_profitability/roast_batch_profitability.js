/* eslint-disable */

frappe.query_reports["Roast Batch Profitability"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            // Default only if not null
            default: frappe.defaults.get_user_default("Company") || undefined
        },
        {
            fieldname: "roast_date_range",
            label: __("Roast Date Range"),
            fieldtype: "DateRange",
            default: [
                frappe.datetime.get_today(),   // from-date
                frappe.datetime.get_today()    // to-date
            ]
        }
    ]
};
