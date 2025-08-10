function calculate_all_totals(frm) {
    let total1 = 0;
    if (frm.doc.cat1_defects) {
        frm.doc.cat1_defects.forEach(d => {
            total1 += d.defect_count || 0;
        });
    }
    frm.set_value("total_cat1_defects", total1);

    let total2 = 0;
    if (frm.doc.cat2_defects) {
        frm.doc.cat2_defects.forEach(d => {
            total2 += d.defect_count || 0;
        });
    }
    frm.set_value("total_cat2_defects", total2);

    let total = total1 + total2;
    frm.set_value("total_defects", total);

    // ✅ Logic to set Passed checkbox:
    if (total1 <= 23 && total2 <= 51) {
        frm.set_value("passed_qc", 1); // checked
    } else {
        frm.set_value("passed_qc", 0); // unchecked
    }
}
// Trigger when the Green Bean Assessment form is loaded/refreshed
frappe.ui.form.on("Green Bean Assessment", {
    refresh(frm) {
        calculate_all_totals(frm);
    }
});

// Trigger when Category 1 Defects table is updated
frappe.ui.form.on("Category 1 Defect Entry", {
    defect_count(frm) {
        calculate_all_totals(frm);
    },
    cat1_defects_add(frm) {
        calculate_all_totals(frm);
    },
    cat1_defects_remove(frm) {
        calculate_all_totals(frm);
    }
});

// Trigger when Category 2 Defects table is updated
frappe.ui.form.on("Category 2 Defect Entry", {
    defect_count(frm) {
        calculate_all_totals(frm);
    },
    cat2_defects_add(frm) {
        calculate_all_totals(frm);
    },
    cat2_defects_remove(frm) {
        calculate_all_totals(frm);
    }
});
