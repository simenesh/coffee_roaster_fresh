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
