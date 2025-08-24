frappe.query_reports["Roast Batch Profitability"] = {
    filters: [
        {
            fieldname: "roast_batch",
            label: __("Roast Batch"),
            fieldtype: "Link",
            options: "Roast Batch"
        },
        {
            fieldname: "roast_date_range",
            label: __("Roast Date Range"),
            fieldtype: "DateRange"
        }
    ]
};

