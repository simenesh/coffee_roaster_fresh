import frappe
from frappe.model.document import Document
from frappe.utils import flt, today

class BatchCost(Document):

    # -------- lifecycle --------
    def validate(self):
        self._pull_output_from_roast_batch()
        self._compute_child_amounts()
        self._sum_totals_and_sales()

    def before_submit(self):
        self._pull_output_from_roast_batch()
        self._compute_child_amounts()
        self._sum_totals_and_sales()

        # Basic gates to avoid bad submissions
        if not flt(self.output_weight):
            frappe.throw("Cannot submit: Output Weight is zero.")
        if flt(self.total_batch_cost) < 0:
            frappe.throw("Cannot submit: Total Batch Cost is negative.")
        if not self.inventory_account:
            frappe.throw("Inventory Account is required.")
        for f, lbl in [
            ("raw_bean_expense_account", "Raw Bean Expense Account"),
            ("overhead_expense_account", "Overhead Expense Account"),
            ("packaging_expense_account", "Packaging Expense Account"),
        ]:
            if not getattr(self, f, None):
                frappe.throw(f"{lbl} is required.")

    def on_submit(self):
        # keep "Status" select consistent
        if "status" in self.as_dict():
            self.db_set("status", "Submitted", update_modified=False)
        self._post_journal_entry()

    def on_cancel(self):
        if "status" in self.as_dict():
            self.db_set("status", "Draft", update_modified=False)

    # -------- helpers --------
    def _pull_output_from_roast_batch(self):
        """Fetch Roast Batch.output_qty into output_weight (always overwrite)."""
        if not self.batch_no:
            return
        try:
            rb = frappe.get_doc("Roast Batch", self.batch_no)
        except frappe.DoesNotExistError:
            return
        self.output_weight = flt(rb.get("output_qty"))
        # If you don't store company on Batch Cost, copy it from Roast Batch
        if not self.get("company") and rb.get("company"):
            self.company = rb.get("company")

    def _compute_child_amounts(self):
        """Ensure each child has amount = qty * rate if 'amount' exists."""
        def mul(a, b): return flt(a) * flt(b)

        for r in (self.raw_bean_costs or []):
            d = r.as_dict()
            qty = d.get("qty_kg", d.get("qty"))
            if "amount" in d:
                r.amount = mul(qty, d.get("rate"))

        for o in (self.overheads or []):
            d = o.as_dict()
            if "amount" in d:
                o.amount = mul(d.get("qty"), d.get("rate"))

        for p in (self.packaging_costs or []):
            d = p.as_dict()
            if "amount" in d:
                p.amount = mul(d.get("qty"), d.get("rate"))

    def _sum_totals_and_sales(self):
        """Compute totals, unit cost, and sales KPIs on the doc."""
        self.total_raw_beans_cost    = sum(flt(r.amount) for r in (self.raw_bean_costs or []))
        self.total_roasting_overhead = sum(flt(o.amount) for o in (self.overheads or []))
        self.total_packaging_cost    = sum(flt(p.amount) for p in (self.packaging_costs or []))
        self.total_batch_cost        = self.total_raw_beans_cost + self.total_roasting_overhead + self.total_packaging_cost

        out = flt(self.output_weight)
        self.cost_per_kg = (self.total_batch_cost / out) if out else 0

        # Sales KPIs (selling_rate is user-entered currency per kg)
        sr = flt(self.get("selling_rate"))
        self.revenue       = (sr * out) if (sr and out) else 0
        self.profit        = self.revenue - flt(self.total_batch_cost)
        self.profit_margin = (self.profit / self.revenue * 100.0) if self.revenue else 0

    # ---------- accounting ----------
    def _post_journal_entry(self):
        """
        Create a Journal Entry:
          Dr Inventory Account = total_nonzero_costs
          Cr Raw Bean Expense  = total_raw_beans_cost (if > 0)
          Cr Overhead Expense  = total_roasting_overhead (if > 0)
          Cr Packaging Expense = total_packaging_cost (if > 0)

        Skips any zero-amount rows to avoid "Both Debit and Credit values cannot be zero".
        """
        total_raw   = flt(self.total_raw_beans_cost)
        total_ovh   = flt(self.total_roasting_overhead)
        total_pack  = flt(self.total_packaging_cost)

        lines = []
        # Credits (only if > 0)
        if total_raw > 0:
            lines.append({"account": self.raw_bean_expense_account, "credit_in_account_currency": total_raw})
        if total_ovh > 0:
            lines.append({"account": self.overhead_expense_account, "credit_in_account_currency": total_ovh})
        if total_pack > 0:
            lines.append({"account": self.packaging_expense_account, "credit_in_account_currency": total_pack})

        total_credit = sum(flt(l.get("credit") or l.get("credit_in_account_currency") or 0) for l in lines)

        # If there's nothing to credit, don't create a JE
        if total_credit <= 0:
            return

        # Single debit line to Inventory for the whole total
        lines.append({"account": self.inventory_account, "debit_in_account_currency": total_credit})

        # Determine company: from doc or Roast Batch
        company = self.get("company")
        if not company and self.batch_no:
            company = frappe.db.get_value("Roast Batch", self.batch_no, "company")

        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        if company:
            je.company = company
        je.posting_date = today()
        je.user_remark = f"Batch Cost capitalization for {self.batch_no}"

        for l in lines:
            je.append("accounts", l)

        je.flags.ignore_permissions = True  # optional: if submitters lack JE perms
        je.save()
        je.submit()

        # Optionally store a link to the JE
        if "journal_entry" in self.as_dict():
            self.db_set("journal_entry", je.name, update_modified=False)
        frappe.msgprint(f"Created Journal Entry {je.name}")