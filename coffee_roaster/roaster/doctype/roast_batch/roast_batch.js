frappe.ui.form.on("Roast Batch", {
  refresh(frm) {
    if (!frm.is_new()) return;
    // show Generate Rounds button (also exists as field button)
    frm.add_custom_button(__("Generate Rounds"), () => generate_rounds(frm), __("Rounds"));
  },
  generate_rounds(frm) { generate_rounds(frm); },
});

function generate_rounds(frm) {
  const total = flt(frm.doc.qty_to_roast) || 0;
  const cap   = flt(frm.doc.cylinder_capacity_kg) || 0;
  if (!total || !cap) {
    frappe.msgprint(__("Please set <b>Input Weight (kg)</b> and ensure <b>Cylinder Capacity (kg)</b> is available.")); 
    return;
  }

  const rounds = Math.ceil(total / cap);
  frm.clear_table("rounds");

  let remaining = total;
  for (let i = 1; i <= rounds; i++) {
    const row = frm.add_child("rounds", {
      round_no: i,
      input_qty: remaining >= cap ? cap : remaining
    });
    remaining = Math.max(0, remaining - cap);
  }
  frm.refresh_field("rounds");
  recompute_totals(frm);
}

frappe.ui.form.on("Roast Batch Round", {
  input_qty(frm, cdt, cdn) { per_row_compute(frm, cdt, cdn); },
  output_qty(frm, cdt, cdn) { per_row_compute(frm, cdt, cdn); },
  quacker(frm, cdt, cdn)    { per_row_compute(frm, cdt, cdn); },
  rounds_add(frm)           { recompute_totals(frm); },
  rounds_remove(frm)        { recompute_totals(frm); }
});

function per_row_compute(frm, cdt, cdn) {
  const row = frappe.get_doc(cdt, cdn);
  const input  = flt(row.input_qty)  || 0;
  const output = flt(row.output_qty) || 0;
  const quack  = flt(row.quacker)    || 0;

  row.loss_qty = Math.max(0, input - output);
  row.net_qty  = Math.max(0, output - quack);

  frm.refresh_field("rounds");
  recompute_totals(frm);
}

function recompute_totals(frm) {
  const r = frm.doc.rounds || [];
  let tin = 0, tout = 0, tloss = 0, tquack = 0;

  r.forEach(x => {
    tin   += flt(x.input_qty)  || 0;
    tout  += flt(x.output_qty) || 0;
    tloss += flt(x.loss_qty)   || 0;
    tquack+= flt(x.quacker)    || 0;
  });

  frm.set_value("total_input_qty",  tin);
  frm.set_value("total_output_qty", tout);
  frm.set_value("total_loss_qty",   tloss);
  frm.set_value("total_quacker",    tquack);
  frm.set_value("rounds_count",     r.length);

  // keep parent summary in sync for legacy reports/workflows
  frm.set_value("output_qty", tout);
  const input_total = tin || flt(frm.doc.qty_to_roast) || 0;
  frm.set_value("weight_loss_percentage",
    input_total ? ((input_total - tout) / input_total) * 100.0 : 0
  );
}
