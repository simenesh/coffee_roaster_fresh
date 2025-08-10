# apps/coffee_roaster/coffee_roaster/roaster/doctype/batch_cost/batch_cost.py
import frappe
from frappe.model.document import Document

class BatchCost(Document):
    def validate(self):
        # sum up child table amounts
        self.total_raw_beans_cost       = sum([r.amount for r in self.raw_bean_costs])
        self.total_roasting_overhead    = sum([o.amount for o in self.overheads])
        self.total_packaging_cost       = sum([p.amount for p in self.packaging_costs])

        # total batch cost & cost per kg
        self.total_batch_cost = (self.total_raw_beans_cost
                                + self.total_roasting_overhead
                                + self.total_packaging_cost)
        if self.output_weight:
            self.cost_per_kg = self.total_batch_cost / self.output_weight
        else:
            self.cost_per_kg = 0

    def on_submit(self):
        # call your existing GL entry helper
        from coffee_roaster.roaster.doctype.batch_cost.post import post_batch_cost_gl_entry
        post_batch_cost_gl_entry(self, None)

