frappe.ui.form.on('RTM Assignment', {
  customer: function(frm) {
    if (!frm.doc.customer) return;

    frappe.db.get_value('Customer', frm.doc.customer, 'customer_type', (r) => {
      if (!r) return;

      const type = r.customer_type;

      // Map customer type to RTM channel
      let rtm = "";
      if (type === "Individual") {
        rtm = "E-commerce";
      } else if (type === "Company") {
        rtm = "Distribution";
      }

      if (rtm && !frm.doc.rtm_channel) {
        frm.set_value('rtm_channel', rtm);
      }
    });
  }
});
