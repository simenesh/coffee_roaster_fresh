/* eslint-disable */
// Doctype JS: Roast Batch
// - Add rounds (balanced split, respects cylinder capacity if set)
// - Live totals for input/output/loss/quacker and loss%
// - Load per-round machine stats (notes) via whitelisted API

frappe.ui.form.on('Roast Batch', {
  refresh(frm) {
    // Add "Add Round" -> ask how many, then distribute
    if (!frm._rb_round_btn) {
      frm._rb_round_btn = frm.add_custom_button(__('Add Round'), () => ask_and_distribute(frm));
    }
    // Add "Load Machine Data" -> summarize points per round into notes
    if (!frm._rb_load_btn) {
      frm._rb_load_btn = frm.add_custom_button(__('Load Machine Data'), () => load_machine_data(frm), 'Utilities');
    }
    recompute_parent_totals(frm);
  },

  qty_to_roast: recompute_parent_totals,
  rounds: recompute_parent_totals
});

frappe.ui.form.on('Roast Batch Round', {
  input_qty: (frm, cdt, cdn) => { line_recalc(frm, cdt, cdn); },
  output_qty: (frm, cdt, cdn) => { line_recalc(frm, cdt, cdn); },
  quacker: (frm, cdt, cdn) => { line_recalc(frm, cdt, cdn); }
});

function ask_and_distribute(frm) {
  const current = (frm.doc.rounds || []).length || 5;
  frappe.prompt(
    [{ fieldname: 'n', label: 'How many rounds?', fieldtype: 'Int', reqd: 1, default: current }],
    ({ n }) => distribute_rounds(frm, cint(n)),
    __('Distribute Rounds')
  );
}

function distribute_rounds(frm, n) {
  const qty = flt(frm.doc.qty_to_roast || 0);
  if (!qty || n <= 0) {
    frappe.msgprint(__('Set a valid "Input Weight (kg)" and number of rounds.'));
    return;
  }
  const cap = flt(frm.doc.cylinder_capacity_kg || 0);
  frm.clear_table('rounds');

  // Equal base split (3dp). Distribute remainder (grams) smoothly.
  const base = Math.floor((qty / n) * 1000) / 1000;
  let remainder_g = Math.round((qty - base * n) * 1000);

  for (let i = 1; i <= n; i++) {
    const d = frm.add_child('rounds');
    d.round_no = i;

    let in_kg = base;
    if (remainder_g > 0) {
      const add_g = Math.min(200, remainder_g); // add up to 0.2kg
      in_kg += add_g / 1000.0;
      remainder_g -= add_g;
    }
    if (cap && in_kg > cap) in_kg = cap;

    d.input_qty = in_kg;
    d.loss_qty = 0.0; // computed at save/display time
  }
  frm.doc.rounds_count = n;
  recompute_parent_totals(frm);
  frm.refresh_fields(['rounds', 'rounds_count', 'total_input_qty', 'total_output_qty', 'total_loss_qty', 'total_quacker', 'weight_loss_percentage']);
}

function line_recalc(frm, cdt, cdn) {
  const d = frappe.get_doc(cdt, cdn);
  const input = flt(d.input_qty || 0);
  const output = flt(d.output_qty || 0);
  d.loss_qty = input && output ? (input - output) : 0;
  frm.refresh_field('rounds');
  recompute_parent_totals(frm);
}

function recompute_parent_totals(frm) {
  let tin = 0, tout = 0, tloss = 0, tquack = 0;
  (frm.doc.rounds || []).forEach(r => {
    const input = flt(r.input_qty || 0);
    const output = flt(r.output_qty || 0);
    r.loss_qty = input && output ? (input - output) : flt(r.loss_qty || 0);
    tin += input; tout += output; tloss += (r.loss_qty || 0);
    tquack += flt(r.quacker || 0);
  });
  frm.doc.total_input_qty = tin;
  frm.doc.total_output_qty = tout;
  frm.doc.total_loss_qty = tloss;
  frm.doc.total_quacker = tquack;
  frm.doc.weight_loss_percentage = tin ? ((tin - tout) / tin) * 100.0 : 0.0;
  frm.refresh_fields(['total_input_qty','total_output_qty','total_loss_qty','total_quacker','weight_loss_percentage']);
}

async function load_machine_data(frm) {
  try {
    if (!frm.doc.name) {
      frappe.msgprint(__('Please save the Roast Batch first.'));
      return;
    }
    const { message } = await frappe.call({
      method: 'coffee_roaster.coffee_roaster.api.get_round_machine_data',
      args: { rb_name: frm.doc.name }
    });
    // message: { 1: [logs], 2: [logs], ... }
    const rounds = frm.doc.rounds || [];
    rounds.forEach(r => {
      const arr = message && message[r.round_no] ? message[r.round_no] : [];
      if (!arr || !arr.length) return;
      const firstTs = arr[0].timestamp;
      const lastTs  = arr[arr.length - 1].timestamp;
      const dur = (dayjs(lastTs).diff(dayjs(firstTs), 'second')) || 0;
      r.notes = `Logs: ${arr.length}, start: ${firstTs || '-'}, end: ${lastTs || '-'}, duration: ${dur}s`;
    });
    frm.refresh_field('rounds');
    frappe.show_alert({ message: __('Machine data summarized into Notes'), indicator: 'green' });
  } catch (e) {
    console.error(e);
    frappe.msgprint(__('Failed to load machine data. See console for details.'));
  }
}
