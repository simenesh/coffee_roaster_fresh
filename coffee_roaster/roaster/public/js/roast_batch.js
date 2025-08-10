frappe.ui.form.on("Roast Batch", {
    onload(frm) {
        if (frm.doc.qty_to_roast && frm.doc.output_qty) {
            let loss = 100 * (frm.doc.qty_to_roast - frm.doc.output_qty) / frm.doc.qty_to_roast;
            frm.set_value("weight_loss_percentage", flt(loss, 2));
        }
    },

    refresh(frm) {
        //
    },

    setup(frm) {
        frm.set_query("green_bean_item", () => {
            return {
                filters: {
                    is_stock_item: 1
                }
            };
        });

        frm.set_query("roasted_item", () => {
            return {
                filters: {
                    is_stock_item: 1
                }
            };
        });
    },

    output_qty(frm) {
        if (frm.doc.qty_to_roast && frm.doc.output_qty) {
            let loss = 100 * (frm.doc.qty_to_roast - frm.doc.output_qty) / frm.doc.qty_to_roast;
            frm.set_value("weight_loss_percentage", flt(loss, 2));
        }
    }
});
