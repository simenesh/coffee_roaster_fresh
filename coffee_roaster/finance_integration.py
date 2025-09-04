import frappe
from frappe.utils import flt, nowdate

def _has_col(table: str, col: str) -> bool:
    try:
        return frappe.db.has_column(table, col)
    except Exception:
        try:
            cols = [c.get("name") for c in (frappe.db.get_table_columns(table) or [])]
            return col in cols
        except Exception:
            return False
def post_batch_cost_gl_entry(doc, method=None):
    if getattr(doc, "docstatus", 0) != 1:
        return

    has_against = _has_col("Journal Entry Account", "against_voucher") and _has_col("Journal Entry Account", "against_voucher_type")

    if has_against:
        if frappe.db.exists("Journal Entry Account", {"against_voucher_type": "Batch Cost", "against_voucher": doc.name}):
            return
    else:
        if frappe.get_all("Journal Entry", filters={"docstatus":1, "user_remark":["like", f"%{doc.name}%"]}, limit=1):
            return

    raw_total       = sum(flt(r.amount) for r in (getattr(doc, "raw_bean_costs", []) or []))
    overhead_total  = sum(flt(o.amount) for o in (getattr(doc, "overheads", []) or []))
    packaging_total = sum(flt(p.amount) for p in (getattr(doc, "packaging_costs", []) or []))
    total_cost      = raw_total + overhead_total + packaging_total

    for f in ("raw_bean_expense_account", "overhead_expense_account", "packaging_expense_account", "inventory_account"):
        if not getattr(doc, f, None):
            raise frappe.ValidationError(f"Missing required account field on Batch Cost: {f}")

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = nowdate()
    je.user_remark  = f"Batch Cost for {doc.name}"

    def add_line(account, debit=0.0, credit=0.0):
        d, c = flt(debit), flt(credit)
        if not d and not c:
            return
        row = {"account": account, "debit": d, "credit": c}
        if has_against:
            row.update({"against_voucher_type": "Batch Cost", "against_voucher": doc.name})
        je.append("accounts", row)

    add_line(doc.raw_bean_expense_account,  debit=raw_total)
    add_line(doc.overhead_expense_account,  debit=overhead_total)
    add_line(doc.packaging_expense_account, debit=packaging_total)
    add_line(doc.inventory_account,         credit=total_cost)

    # final guard
    je.accounts = [a for a in je.accounts if a.debit or a.credit]
    tot_dr = sum(flt(a.debit) for a in je.accounts)
    tot_cr = sum(flt(a.credit) for a in je.accounts)
    if not je.accounts or not tot_dr or not tot_cr:
        return
    if round(tot_dr,2) != round(tot_cr,2):
        raise frappe.ValidationError(f"Journal Entry not balanced: Dr {tot_dr} vs Cr {tot_cr}")

    je.insert(ignore_permissions=True)
    je.submit()

