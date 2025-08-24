# apps/coffee_roaster/coffee_roaster/finance_integration.py
import frappe
from frappe.utils import flt, nowdate

def _has_col(table: str, col: str) -> bool:
    try:
        return frappe.db.has_column(table, col)
    except Exception:
        # very old versions: fallback to raw describe
        cols = [c.get("name") for c in (frappe.db.get_table_columns(table) or [])]
        return col in cols

def post_batch_cost_gl_entry(doc, method=None):
    # only for submitted Batch Cost
    if getattr(doc, "docstatus", 0) != 1:
        return

    # detect schema support
    has_against = _has_col("Journal Entry Account", "against_voucher") and _has_col("Journal Entry Account", "against_voucher_type")

    # de-dupe guard
    if has_against:
        already = frappe.db.exists(
            "Journal Entry Account",
            {"against_voucher_type": "Batch Cost", "against_voucher": doc.name}
        )
        if already:
            return
    else:
        # fallback: look for a JE we created earlier via remark
        already = frappe.get_all(
            "Journal Entry",
            filters={"docstatus": 1, "user_remark": ["like", f"%{doc.name}%"]},
            limit=1,
            pluck="name",
        )
        if already:
            return

    # totals
    raw_total       = sum(flt(r.amount) for r in (getattr(doc, "raw_bean_costs", []) or []))
    overhead_total  = sum(flt(r.amount) for r in (getattr(doc, "overheads", []) or []))
    packaging_total = sum(flt(r.amount) for r in (getattr(doc, "packaging_costs", []) or []))
    total_cost      = raw_total + overhead_total + packaging_total

    # sanity: need accounts
    for f in ("raw_bean_expense_account", "overhead_expense_account", "packaging_expense_account", "inventory_account"):
        if not getattr(doc, f, None):
            raise frappe.ValidationError(f"Missing required account field on Batch Cost: {f}")

    # build JE
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = nowdate()
    je.user_remark  = f"Batch Cost for {doc.name}"

    def add_line(account, debit=0.0, credit=0.0):
        row = {"account": account, "debit": flt(debit), "credit": flt(credit)}
        if has_against:
            row.update({"against_voucher_type": "Batch Cost", "against_voucher": doc.name})
        je.append("accounts", row)

    # debits
    add_line(doc.raw_bean_expense_account, debit=raw_total)
    add_line(doc.overhead_expense_account,  debit=overhead_total)
    add_line(doc.packaging_expense_account, debit=packaging_total)
    # credit
    add_line(doc.inventory_account, credit=total_cost)

    je.insert(ignore_permissions=True)
    je.submit()

