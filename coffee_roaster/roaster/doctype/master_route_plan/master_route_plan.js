frappe.ui.form.on("Master Route Plan", {
    customer: function(frm) {
        if (frm.doc.customer) {
            frappe.db.get_doc("Customer", frm.doc.customer).then(customer => {
                frm.set_value("sub_city", customer.sub_city || "");
                frm.set_value("address", customer.address_line1 || customer.primary_address || "");
            });
        }
    }
});
frappe.ui.form.on("Master Route Plan", {
  route_no(frm) {
    const map = {
      1: "Monday", 2: "Tuesday", 3: "Wednesday",
      4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"
    };
    if (frm.doc.route_no && !frm.doc.day) {
      frm.set_value("day", map[frm.doc.route_no] || "");
    }
  }
});

