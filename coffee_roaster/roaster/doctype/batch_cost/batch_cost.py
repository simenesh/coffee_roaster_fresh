import frappe
from frappe.model.document import Document
from frappe.utils import flt

class BatchCost(Document):

    def validate(self):
        # Always fetch output from Roast Batch
        self._pull_output_from_roast_batch()
        self._compute_child_amounts()
        self._sum_totals()

    def before_submit(self):
        # Final recompute before submit
        self._pull_output_from_roast_batch()
        self._compute_child_amounts()
        self._sum_totals()

    # ---------------- helpers ----------------
    def _pull_output_from_roast_batch(self):
        """Always fetch Roast Batch.output_qty into output_weight."""
        if not self.batch_no:
            return
        try:
            rb = frappe.get_doc("Roast Batch", self.batch_no)
        except frappe.DoesNotExistError:
            return

        # force overwrite every time
        self.output_weight = flt(rb.get("output_qty"))

    def _compute_child_amounts(self):
        def mul(a, b): return flt(a) * flt(b)

        for r in (self.raw_bean_costs or []):
            qty = r.get("qty_kg") if "qty_kg" in r.as_dict() else r.get("qty")
            if "amount" in r.as_dict():
                r.amount = mul(qty, r.get("rate"))

        for o in (self.overheads or []):
            if "amount" in o.as_dict():
                o.amount = mul(o.get("qty"), o.get("rate"))

        for p in (self.packaging_costs or []):
            if "amount" in p.as_dict():
                p.amount = mul(p.get("qty"), p.get("rate"))

    def _sum_totals(self):
        self.total_raw_beans_cost    = sum(flt(r.amount) for r in (self.raw_bean_costs or []))
        self.total_roasting_overhead = sum(flt(o.amount) for o in (self.overheads or []))
        self.total_packaging_cost    = sum(flt(p.amount) for p in (self.packaging_costs or []))
        self.total_batch_cost        = self.total_raw_beans_cost + self.total_roasting_overhead + self.total_packaging_cost
        self.cost_per_kg             = (self.total_batch_cost / flt(self.output_weight)) if flt(self.output_weight) else 0

