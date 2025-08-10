def create_batch_cost_journal_entry(batch_cost_doc):
    """Create Journal Entry to log all batch costs into GL."""
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = nowdate()
    je.company = batch_cost_doc.company
    je.user_remark = f"Auto-generated for Batch Cost {batch_cost_doc.name}"
    # Removed: je.reference_type and je.reference_name

    total_credit = 0

    # 🔸 Debit cost accounts
    for cost_table in ["raw_bean_costs", "packaging_costs", "overheads"]:
        for row in batch_cost_doc.get(cost_table):
            if not row.expense_account:
                frappe.throw(f"Missing expense account in {cost_table}: {row.description or ''}")
            je.append("accounts", {
                "account": row.expense_account,
                "debit_in_account_currency": flt(row.amount),
                "credit_in_account_currency": 0,
                "user_remark": row.description or cost_table.replace("_", " ").title()
            })
            total_credit += flt(row.amount)

    # 🔸 Credit COGS (Cost of Goods Sold)
    cogs_account = frappe.db.get_single_value("Roaster Settings", "cogs_account")
    if not cogs_account:
        frappe.throw("Please set 'COGS Account' in Roaster Settings.")

    je.append("accounts", {
        "account": cogs_account,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": total_credit,
        "user_remark": f"Batch cost offset for {batch_cost_doc.name}"
    })

    je.insert()
    je.submit()

    frappe.msgprint(f"✅ Journal Entry {je.name} created for Batch Cost {batch_cost_doc.name}")
