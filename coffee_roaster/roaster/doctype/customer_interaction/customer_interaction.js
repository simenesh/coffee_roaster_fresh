frappe.ui.form.on('Customer Interaction', {
    onload: function(frm) {
        if (frm.is_new()) {
            frm.set_value('interaction_date', frappe.datetime.get_today());
        }
    }
});

