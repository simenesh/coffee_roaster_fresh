frappe.ui.form.on('Affective Cupping', {
  cup_scores_add: function(frm) {
    calculate_final_score(frm);
  },
  cup_scores_remove: function(frm) {
    calculate_final_score(frm);
  },
  cup_scores_score: function(frm, cdt, cdn) {
    calculate_final_score(frm);
  }
});

function calculate_final_score(frm) {
  let total = 0;
  let count = 0;

  (frm.doc.cup_scores || []).forEach(row => {
    if (row.score !== undefined && row.score !== null && !isNaN(row.score)) {
      total += row.score;
      count++;
    }
  });

  let avg = count > 0 ? (total / count) : 0;

  frm.set_value('final_score', avg);
  frm.refresh_field('final_score');
}

