import frappe
from frappe.model.document import Document
from erpnext.stock.utils import get_stock_balance

TOL = 0.001  # kg tolerance for sum checks


class RoastBatch(Document):

    # ====== VALIDATION / DERIVED FIELDS ======
    def validate(self):
        # base validations (keep your rules)
        if self.qty_to_roast and float(self.qty_to_roast) <= 0:
            frappe.throw("Input weight must be > 0 kg.")
        if self.output_qty and float(self.output_qty) <= 0:
            frappe.throw("Output weight must be > 0 kg.")
        if self.qc_score and not 50 <= int(self.qc_score) <= 100:
            frappe.throw("QC score must be between 50 and 100.")

        # rounds math → derive per-row loss/net and parent totals
        self.compute_round_derived_fields()
        self.compute_totals_from_rounds()
        self.validate_rounds_consistency()

        # weight loss % (prefer totals if rounds exist)
        in_qty, out_qty = self._effective_in_out()
        if in_qty and out_qty is not None:
            self.weight_loss_percentage = ((in_qty - out_qty) / in_qty) * 100.0

    def compute_round_derived_fields(self):
        """loss_qty = input - output, net_qty = output - quacker (per row)."""
        for r in (self.rounds or []):
            r.loss_qty = max(0.0, float(r.input_qty or 0) - float(r.output_qty or 0))
            r.net_qty  = max(0.0, float(r.output_qty or 0) - float(r.quacker or 0))

    def compute_totals_from_rounds(self):
        """Aggregate child rows into parent totals. Keeps legacy fields in sync."""
        tin = tout = tloss = tquack = 0.0
        for r in (self.rounds or []):
            tin   += float(r.input_qty or 0)
            tout  += float(r.output_qty or 0)
            tloss += float(r.loss_qty  or 0)
            tquack+= float(r.quacker   or 0)

        # store totals if you added these fields on the parent (recommended)
        self.total_input_qty  = round(tin, 3)
        self.total_output_qty = round(tout, 3)
        self.total_loss_qty   = round(tloss, 3)
        self.total_quacker    = round(tquack, 3)
        self.rounds_count     = len(self.rounds or [])

        # keep legacy parent fields in sync for reports that still read them
        if self.rounds:
            self.output_qty = self.total_output_qty

    def validate_rounds_consistency(self):
        """If rounds exist and parent qty_to_roast is set, sums must match."""
        if self.rounds and self.qty_to_roast:
            if abs(float(self.qty_to_roast) - float(self.total_input_qty or 0)) > TOL:
                frappe.throw(
                    f"Sum of round inputs ({self.total_input_qty} kg) "
                    f"does not match Batch Input Weight ({self.qty_to_roast} kg). "
                    "Adjust the rounds or the batch input."
                )

    def _effective_in_out(self):
        """Return (in_qty, out_qty) preferring rounds’ totals when available."""
        if self.rounds:
            return float(self.total_input_qty or 0), float(self.total_output_qty or 0)
        return float(self.qty_to_roast or 0), (None if self.output_qty is None else float(self.output_qty))

    # ====== STOCK FLOW ======
    @frappe.whitelist()
    def start_roast(self):
        if getattr(self, "stock_entry_created", 0):
            frappe.msgprint("Stock Entry already created.")
            return

        # make sure derived fields/totals are up to date
        self.compute_round_derived_fields()
        self.compute_totals_from_rounds()
        self.validate_rounds_consistency()

        in_qty, out_qty = self._effective_in_out()
        if not in_qty or in_qty <= 0:
            frappe.throw("Input quantity must be > 0 kg.")
        if out_qty is None or out_qty <= 0:
            frappe.throw("Output quantity must be > 0 kg.")

        # Check stock availability (green beans)
        available_qty = get_stock_balance(self.green_bean_item, self.source_warehouse)
        if available_qty < in_qty:
            frappe.throw(
                f"Not enough {self.green_bean_item} in {self.source_warehouse}. "
                f"Available: {available_qty} kg; Needed: {in_qty} kg."
            )

        # Create/ensure Batch for roasted item
        batch = frappe.get_doc({
            "doctype": "Batch",
            "item": self.roasted_item,
            "manufacturing_date": self.roast_date
        }).insert(ignore_permissions=True)
        self.batch_no = batch.name

        # Manufacture Stock Entry (consume green, produce roasted)
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Manufacture"
        se.posting_date = self.roast_date

        se.append("items", {
            "item_code": self.green_bean_item,
            "qty": in_qty,
            "s_warehouse": self.source_warehouse,
            "is_finished_item": 0
        })

        se.append("items", {
            "item_code": self.roasted_item,
            "qty": out_qty,
            "t_warehouse": self.target_warehouse,
            "batch_no": self.batch_no,
            "is_finished_item": 1
        })

        se.insert(ignore_permissions=True)
        se.submit()

        self.stock_entry_created = 1
        self.save(ignore_permissions=True)

        frappe.msgprint(f"Manufacture Stock Entry {se.name} created.")
        return se.name
