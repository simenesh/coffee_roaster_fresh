import frappe
import csv
from frappe.utils import get_files_path

# === 1. CHART OF ACCOUNTS EXPORT (COMPLETE AND UPDATED) ===

# Numeric Sage Account Type Mapping (for reference)
SAGE_ACCOUNT_TYPES = {
    "Cash": 0, "Accounts Receivable": 1, "Inventory": 2, "Other Current Assets": 3,
    "Fixed Assets": 4, "Accumulated Depreciation": 5, "Accounts Payable": 6,
    "Credit Card": 7, "Other Current Liabilities": 8, "Long Term Liabilities": 9,
    "Equity-does not close": 10, "Income": 11, "Cost of Sales": 12, "Expenses": 13
}


@frappe.whitelist()
def map_to_sage_type_numeric(name, root_type, is_group=False):
    """
    Corrected and improved function to map Frappe account types to Sage numeric types.
    Handles specific keywords for more accurate classification.
    """
    # Sanitize inputs to prevent errors with empty names or types
    name_lower = (name or '').lower()
    root_lower = (root_type or '').lower()

    if is_group:
        # Group accounts are not postable. Default to 'Expenses' as they are often filtered out by Sage.
        return 13

    # --- Classification based on ROOT TYPE first for accuracy ---

    if root_lower == 'expense':
        # Check for specific Cost of Sales keywords. Added 'cost of ' based on your data.
        if any(cogs in name_lower for cogs in ['cost of sales', 'cogs', 'cost of goods sold', 'cost of ']):
            return 12
        # All other accounts with a root_type of 'Expense' map to Sage's 'Expenses'.
        return 13

    if root_lower == 'asset':
        if 'receivable' in name_lower:
            return 1
        # Added 'grind' and 'intransit' from your data for better inventory matching
        if any(word in name_lower for word in ['inventory', 'stock', 'grind', 'intransit']):
            return 2
        if any(word in name_lower for word in ['fixed asset', 'machin', 'furnitur', 'property', 'building']):
            return 4
        if 'depreciation' in name_lower or 'accum' in name_lower:
            return 5
        # Added more specific bank names from your data
        if any(bank_term in name_lower for bank_term in ['bank', 'cash', 'checking', 'checke', 'tele birr', 'dashen', 'cbe', 'enat']):
            return 0
        # If it's an asset but doesn't fit the above, it's 'Other Current Assets'.
        return 3

    if root_lower == 'liability':
        if 'payable' in name_lower and 'tax' not in name_lower:
            return 6
        if 'credit card' in name_lower:
            return 7
        if 'long term' in name_lower:
            return 9
        # All other liabilities, including various taxes, go to 'Other Current Liabilities'.
        return 8

    if root_lower == 'equity':
        return 10

    if root_lower == 'income':
        return 11

    # Default to 'Expenses' if no other category fits. This is the safest fallback.
    return 13


@frappe.whitelist()
def export_chart_of_accounts_for_sage():
    """
    Exports the Chart of Accounts from ERPNext to a Sage 50 compatible CSV file.
    """
    accounts = frappe.get_all(
        "Account",
        fields=["account_number", "account_name", "root_type", "disabled", "is_group"],
        filters={"company": "Coffee Rosters"} # IMPORTANT: Add your company name here
    )

    fieldnames = [
        "Account ID", "Account Description", "Account Type", "Inactive",
        "Tax Code", "Next Check Number", "Current Balance", "1099 Settings"
    ]

    records = []
    for acc in accounts:
        # Call the helper function to get the Sage account type code
        acc_type_code = map_to_sage_type_numeric(acc.account_name, acc.root_type, acc.is_group)

        records.append({
            "Account ID": acc.account_number or acc.account_name, # Use name as fallback if number is missing
            "Account Description": acc.account_name or "",
            "Account Type": acc_type_code,
            "Inactive": "TRUE" if acc.disabled else "FALSE",
            "Tax Code": "",
            "Next Check Number": "",
            "Current Balance": "0.00", # Sage expects a value, 0.00 is safe
            "1099 Settings": ""
        })

    # Define the file path for the export
    file_path = get_files_path("chart_of_accounts_for_sage.csv")

    # Write the data to a tab-delimited file
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(records)

    # Return the public URL to download the file
    return "/files/chart_of_accounts_for_sage.csv"

# === 2. JOURNAL ENTRIES (GL) EXPORT ===
@frappe.whitelist()
def export_journal_entries_for_sage():
    """
    Export Journal Entries in Sage 50 (Peachtree) compatible format (tab-delimited).
    This version is corrected to handle transaction grouping.
    """
    entry_line_counts = frappe.db.sql("""
        SELECT parent, count(*) as line_count
        FROM `tabJournal Entry Account`
        WHERE docstatus = 1
        GROUP BY parent
    """, as_dict=1)
    counts = {d.parent: d.line_count for d in entry_line_counts}

    data = frappe.db.sql("""
        SELECT
            je.name, je.posting_date,
            jea.reference_name, jea.account, jea.user_remark, (jea.debit - jea.credit) AS amount
        FROM `tabJournal Entry Account` AS jea
        JOIN `tabJournal Entry` AS je ON jea.parent = je.name
        WHERE je.docstatus = 1
        ORDER BY je.name, jea.idx
    """, as_dict=True)

    fieldnames = [
        "Date", "Reference", "Date Clear in Bank Rec", "Number of Distributions",
        "G/L Account", "Description", "Amount", "Job ID",
        "Used for Reimbursable Expenses", "Transaction Period", "Transaction Number",
        "Consolidated Transaction", "Recur Number", "Recur Frequency"
    ]
    
    sage_formatted_rows = []
    current_entry_id = None
    for row in data:
        is_first_line = row.name != current_entry_id
        
        sage_row = {field: "" for field in fieldnames}

        if is_first_line:
            sage_row["Date"] = row.posting_date
            sage_row["Reference"] = row.reference_name or row.name
            sage_row["Transaction Number"] = row.name
            sage_row["Number of Distributions"] = counts.get(row.name, 1)
            current_entry_id = row.name

        sage_row["G/L Account"] = row.account
        sage_row["Description"] = row.user_remark
        sage_row["Amount"] = row.amount

        sage_formatted_rows.append(sage_row)

    file_path = get_files_path("GENERAL.TXT")
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(sage_formatted_rows)
        
    return "/files/GENERAL.TXT"


# === 3. CUSTOMERS EXPORT ===
@frappe.whitelist()
def export_customers_for_sage():
    """
    Export Customers in Sage 50 (Peachtree) compatible format (tab-delimited).
    This version includes primary billing and shipping address details.
    """
    customers = frappe.get_all(
        "Customer",
        fields=["name", "customer_name", "disabled", "customer_group", "phone", "email_id", "tax_id"]
    )

    fieldnames = [
        "Customer ID", "Customer Name", "Prospect", "Inactive",
        "Bill to Contact First Name", "Bill to Contact Last Name",
        "Bill to Address-Line One", "Bill to Address-Line Two", "Bill to City", "Bill to State", "Bill to Zip", "Bill to Country",
        "Bill to Sales Tax ID", "Ship to Address 1-Line One", "Ship to Address 1-Line Two", "Ship to City 1", "Ship to State 1", "Ship to Zipcode 1", "Ship to Country 1", "Ship to Sales Tax ID 1",
        "Customer Type", "Telephone 1", "Telephone 2", "Fax Number", "Customer E-mail",
        "Sales Representative ID", "Account #", "G/L Sales Account", "Open Purchase Order Number", "Ship Via", "Resale Number",
        "Pricing Level", "Use Standard Terms", "C.O.D. Terms", "Prepaid Terms", "Terms Type", "Due Days", "Discount Days", "Discount Percent", "Credit Limit", "Credit Status", "Charge Finance Charges", "Due Month End Terms",
        "Cardholder's Name", "Credit Card Address Line 1", "Credit Card Address Line 2", "Credit Card City", "Credit Card State", "Credit Card Zip Code", "Credit Card Country", "Credit Card Number", "Credit Card Expiration Date",
        "Use Receipt Settings", "Customer Payment Method", "Customer Cash Account", "Second Contact", "Reference", "Mailing List?", "Multiple Sites?", "Customer Since Date", "Last Statement Date", "Customer Web Site", "ID Replacement"
    ]

    sage_formatted_rows = []
    for c in customers:
        sage_row = {field: "" for field in fieldnames}

        sage_row["Customer ID"] = c.name
        sage_row["Customer Name"] = c.customer_name
        sage_row["Inactive"] = "TRUE" if c.disabled else "FALSE"
        sage_row["Customer Type"] = c.customer_group
        sage_row["Telephone 1"] = c.phone
        sage_row["Customer E-mail"] = c.email_id
        sage_row["Bill to Sales Tax ID"] = c.tax_id

        billing_address = frappe.db.get_value("Address", {"link_doctype": "Customer", "link_name": c.name, "is_primary_billing": 1},
            ["address_line1", "address_line2", "city", "state", "pincode", "country"], as_dict=True)
        if billing_address:
            sage_row["Bill to Address-Line One"] = billing_address.address_line1
            sage_row["Bill to Address-Line Two"] = billing_address.address_line2
            sage_row["Bill to City"] = billing_address.city
            sage_row["Bill to State"] = billing_address.state
            sage_row["Bill to Zip"] = billing_address.pincode
            sage_row["Bill to Country"] = billing_address.country

        shipping_address = frappe.db.get_value("Address", {"link_doctype": "Customer", "link_name": c.name, "is_primary_shipping": 1},
            ["address_line1", "address_line2", "city", "state", "pincode", "country"], as_dict=True)
        if shipping_address:
            sage_row["Ship to Address 1-Line One"] = shipping_address.address_line1
            sage_row["Ship to Address 1-Line Two"] = shipping_address.address_line2
            sage_row["Ship to City 1"] = shipping_address.city
            sage_row["Ship to State 1"] = shipping_address.state
            sage_row["Ship to Zipcode 1"] = shipping_address.pincode
            sage_row["Ship to Country 1"] = shipping_address.country
            
        sage_formatted_rows.append(sage_row)

    file_path = get_files_path("CUSTOMER.TXT")
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(sage_formatted_rows)
        
    return "/files/CUSTOMER.TXT"


# === 4. SUPPLIERS EXPORT ===
@frappe.whitelist()
def export_suppliers_for_sage():
    suppliers = frappe.get_all(
        "Supplier",
        fields=[
            "name", "supplier_name", "supplier_type", "tax_id",
            "supplier_group", "country"
        ]
    )
    fieldnames = [
        "SupplierID", "SupplierName", "Type", "TaxID", "Group", "Country"
    ]
    file_path = get_files_path("erpnext_suppliers_for_sage.csv")
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for s in suppliers:
            writer.writerow({
                "SupplierID": s.name,
                "SupplierName": s.supplier_name,
                "Type": s.supplier_type or "",
                "TaxID": s.tax_id or "",
                "Group": s.supplier_group or "",
                "Country": s.country or ""
            })
    return "/files/erpnext_suppliers_for_sage.csv"


# === 5. SALES INVOICES EXPORT ===
@frappe.whitelist()
def export_sales_invoices_for_sage():
    """
    Export Sales Invoices in Sage 50 Sales Journal format (tab-delimited, no header).
    """
    invoice_item_counts = frappe.db.sql("""
        SELECT parent, count(*) as item_count
        FROM `tabSales Invoice Item`
        WHERE docstatus = 1
        GROUP BY parent
    """, as_dict=1)
    counts = {d.parent: d.item_count for d in invoice_item_counts}

    invoices_data = frappe.db.sql("""
        SELECT
            si.name, si.posting_date, si.due_date, si.po_no, si.debit_to, si.payment_terms, si.tax_id, si.remarks,
            si.customer, sii.item_code, sii.description, sii.qty, sii.rate, sii.amount, sii.income_account
        FROM `tabSales Invoice Item` AS sii
        JOIN `tabSales Invoice` AS si ON si.name = sii.parent
        WHERE si.docstatus = 1
        ORDER BY si.name, sii.idx
    """, as_dict=True)

    fieldnames = [
        "Customer ID", "Invoice/CM #", "Apply to Invoice Number", "Credit Memo", "Progress Billing Invoice", "Date",
        "Ship By", "Quote", "Quote #", "Quote Good Thru Date", "Drop Ship", "Ship to Name", "Ship to Address-Line One",
        "Ship to Address-Line Two", "Ship to City", "Ship to State", "Ship to Zipcode", "Ship to Country", "Customer PO",
        "Ship Via", "Ship Date", "Date Due", "Discount Amount", "Discount Date", "Displayed Terms", "Sales Representative ID",
        "Accounts Receivable Account", "Sales Tax ID", "Invoice Note", "Note Prints After Line Items", "Statement Note",
        "Stmt Note Prints Before Ref", "Internal Note", "Beginning Balance Transaction", "Number of Distributions",
        "Invoice/CM Distribution", "Apply to Invoice Distribution", "Apply To Sales Order", "Apply to Proposal", "Quantity",
        "SO/Proposal Number", "Item ID", "Serial Number", "SO/Proposal Distribution", "Description", "G/L Account",
        "Unit Price", "Tax Type", "UPC / SKU", "Weight", "Amount", "Job ID", "Sales Tax Agency ID", "Transaction Period",
        "Transaction Number", "Return Authorization", "Voided by Transaction", "Recur Number", "Recur Frequency"
    ]

    sage_formatted_rows = []
    current_invoice_id = None
    for row in invoices_data:
        is_first_line = row.name != current_invoice_id

        sage_row = {field: "" for field in fieldnames}

        if is_first_line:
            sage_row["Customer ID"] = row.customer
            sage_row["Invoice/CM #"] = row.name
            sage_row["Date"] = row.posting_date
            sage_row["Date Due"] = row.due_date
            sage_row["Customer PO"] = row.po_no
            sage_row["Displayed Terms"] = row.payment_terms
            sage_row["Accounts Receivable Account"] = row.debit_to
            sage_row["Sales Tax ID"] = row.tax_id
            sage_row["Invoice Note"] = row.remarks
            sage_row["Transaction Number"] = row.name
            sage_row["Credit Memo"] = "FALSE"
            sage_row["Number of Distributions"] = counts.get(row.name, 1)
            current_invoice_id = row.name

        sage_row["Quantity"] = row.qty
        sage_row["Item ID"] = row.item_code
        sage_row["Description"] = row.description
        sage_row["G/L Account"] = row.income_account
        sage_row["Unit Price"] = row.rate
        sage_row["Amount"] = row.amount

        sage_formatted_rows.append(sage_row)

    file_path = get_files_path("SALES.TXT")
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        for row in sage_formatted_rows:
            values = [str(row.get(field, "")) for field in fieldnames]
            f.write("\t".join(values) + "\n")

    return "/files/SALES.TXT"


# === 6. INVENTORY ITEMS EXPORT ===
def get_stock_balance(item_code):
    """Get stock balance for an item from Bin table."""
    result = frappe.db.get_value("Bin", {"item_code": item_code}, "actual_qty")
    return result or 0

@frappe.whitelist()
def export_inventory_for_sage():
    """
    Export Inventory Items in Sage 50 (Peachtree) compatible format (tab-delimited).
    """
    items = frappe.get_all(
        "Item",
        fields=["name", "item_name", "item_group", "disabled", "is_stock_item", "standard_selling_rate", "standard_rate", "description"]
    )

    fieldnames = [
        "Item ID", "Item Description", "Inactive", "Item Class", "Subject to Commission",
        "Description for Sales", "Description for Purchases",
        "Price Level 1", "Price Level 2", "Price Level 3", "Price Level 4", "Price Level 5",
        "Price Level 6", "Price Level 7", "Price Level 8", "Price Level 9", "Price Level 10",
        "G/L Sales Account", "G/L Inventory Account", "G/L Cost of Sales Account",
        "Item Tax Type", "Number of Stocking Units", "Unit of Measure", "Weight", "UPC/SKU",
        "Location", "Stocking Unit of Measure", "Last Unit Cost", "Item Type", "Quantity on Hand", "Cost Method",
        "Reorder Quantity", "Minimum Stock Level", "Buyer ID", "Preferred Supplier ID", "Substitute Item ID"
    ]

    sage_formatted_rows = []
    for item in items:
        sage_row = {field: "" for field in fieldnames}

        sage_row["Item ID"] = item.name
        sage_row["Item Description"] = item.item_name
        sage_row["Inactive"] = "TRUE" if item.disabled else "FALSE"
        sage_row["Description for Sales"] = item.description
        sage_row["Item Type"] = item.item_group
        
        if item.is_stock_item:
            sage_row["Item Class"] = "Stock Item"
        else:
            sage_row["Item Class"] = "Service"

        sage_row["Price Level 1"] = item.standard_selling_rate
        sage_row["Last Unit Cost"] = item.standard_rate
        sage_row["Cost Method"] = "FIFO"

        item_defaults = frappe.db.get_value("Item Default", {"parent": item.name}, ["income_account", "expense_account", "buying_cost_center"], as_dict=True)
        if item_defaults:
            sage_row["G/L Sales Account"] = item_defaults.income_account
            sage_row["G/L Cost of Sales Account"] = item_defaults.expense_account
            sage_row["G/L Inventory Account"] = item_defaults.buying_cost_center

        if item.is_stock_item:
            qty_on_hand = get_stock_balance(item.name)
            sage_row["Quantity on Hand"] = qty_on_hand if qty_on_hand is not None else 0

        sage_formatted_rows.append(sage_row)

    file_path = get_files_path("INVENTRY.TXT")
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(sage_formatted_rows)
        
    return "/files/INVENTRY.TXT"