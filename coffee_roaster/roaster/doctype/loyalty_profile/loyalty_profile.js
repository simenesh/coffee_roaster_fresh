frappe.ui.form.on('Loyalty Profile', {
  onload: function(frm) {
    // Auto-set today's date on new records
    if (frm.is_new()) {
      frm.set_value('enrolled_date', frappe.datetime.get_today());
    }
  },

  points: function(frm) {
    // Automatically update tier based on points
    const points = frm.doc.points || 0;

    let tier = "Bronze";
    if (points >= 1000) {
      tier = "Platinum";
    } else if (points >= 500) {
      tier = "Gold";
    } else if (points >= 250) {
      tier = "Silver";
    }

    frm.set_value('tier', tier);
  },

  status: function(frm) {
    // Clear points if profile is terminated
    if (frm.doc.status === "Terminated") {
      frm.set_value('points', 0);
      frappe.msgprint(__('Points reset because status is Terminated'));
    }
  }
});
