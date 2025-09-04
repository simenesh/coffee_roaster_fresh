/* global frappe */
frappe.query_reports["Master Route Plan by Sub City"] = {
  filters: [
    {
      fieldname: "sub_city",
      label: __("Sub City"),
      fieldtype: "MultiSelectList",
      reqd: 0,
      get_data: function (txt) {
        const filters = txt ? [["sub_city","like", `%${txt}%`]] : undefined;
        return frappe.db.get_list("Route Plan Detail", {
          fields: ["distinct sub_city as value"],
          filters, limit: 50
        }).then(r => (r || []).map(x => x.value).filter(Boolean)
          .map(v => ({ value: v, description: v })));
      }
    },
    {
      fieldname: "weekday",
      label: __("Weekday"),
      fieldtype: "Select",
      options: "\nMonday\nTuesday\nWednesday\nThursday\nFriday\nSaturday\nSunday"
    },
    { fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
    { fieldname: "to_date",   label: __("To Date"),   fieldtype: "Date" }
  ]
};
