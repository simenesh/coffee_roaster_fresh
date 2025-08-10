frappe.ui.form.on("Route Plan", {
  customer: function(frm) {
    if (frm.doc.customer) {
      frappe.db.get_doc("Customer", frm.doc.customer).then(doc => {
        frm.set_value("address", doc.address || "");
        frm.set_value("sub_city", doc.sub_city || "");
      });
    }
  }
});