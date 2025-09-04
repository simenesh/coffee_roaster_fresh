# -*- coding: utf-8 -*-
import os, re, io, zipfile
from datetime import date, timedelta
import frappe
from frappe.utils import get_site_path

# ---------------- Top-level helpers (column 0) ----------------

def _yyyymm(y, m):
    return f"{int(y):04d}{int(m):02d}"

def _month_bounds(year, month):
    start = date(int(year), int(month), 1)
    nxt = date(start.year + (1 if start.month == 12 else 0),
               1 if start.month == 12 else start.month + 1, 1)
    return start, (nxt - timedelta(days=1))

def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", (s or "")).strip("_")

def _sanitize(v):
    if v is None:
        return ""
    return str(v).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()

def _tab_text(header, rows):
    lines = ["\t".join(header)]
    for r in rows:
        lines.append("\t".join(_sanitize(x) for x in r))
    return "\n".join(lines) + "\n"

def _tab_text_no_header(rows):
    # Peachtree/Sage 50 prefers CRLF and NO header for General Journal
    return "\r\n".join("\t".join(_sanitize(x) for x in r) for r in rows) + "\r\n"

def _fmt_us_date(d):
    """Return MM/DD/YYYY for date/datetime; fallback to str."""
    try:
        return d.strftime("%m/%d/%Y")
    except Exception:
        return str(d)

def _files_dir():
    return get_site_path("public", "files")

def _account_number_or_name(acc_name):
    if not acc_name:
        return ""
    num = frappe.db.get_value("Account", acc_name, "account_number")
    return num or acc_name

def _map_sage_account_type(acc_doc: dict) -> str:
    """
    Map ERPNext Account to Sage 'Type'.
    Only label 'Cash' for *Asset* accounts that are clearly bank/cash.
    Otherwise map by root_type.
    """
    rt = (acc_doc.get("root_type") or "").title()          # Asset/Liability/Equity/Income/Expense
    at = (acc_doc.get("account_type") or "").strip().lower()
    nm = (acc_doc.get("account_name") or acc_doc.get("name") or "").lower()

    if rt == "Asset" and at in {"bank", "cash"}:
        return "Cash"
    if rt == "Asset" and re.search(r"\b(cash|bank|checking)\b", nm):
        return "Cash"
    if rt in {"Asset","Liability","Equity","Income","Expense"}:
        return rt
    return "Asset"

def _first_address(party_doctype: str, party_name: str) -> dict:
    """Fetch latest Address; fallback to latest Contact for phone/email."""
    out = {"line1":"", "line2":"", "city":"", "state":"", "pincode":"", "country":"", "phone":"", "email":""}

    rows = frappe.db.sql("""
        SELECT a.address_line1, a.address_line2, a.city, a.state, a.pincode, a.country,
               a.phone AS phone, a.email_id AS email
        FROM `tabAddress` a
        JOIN `tabDynamic Link` dl ON dl.parent = a.name
        WHERE dl.link_doctype = %s AND dl.link_name = %s
        ORDER BY a.modified DESC
        LIMIT 1
    """, (party_doctype, party_name), as_dict=True)
    if rows:
        r = rows[0]
        out.update({
            "line1": r.address_line1 or "", "line2": r.address_line2 or "",
            "city": r.city or "", "state": r.state or "", "pincode": r.pincode or "",
            "country": r.country or "", "phone": r.phone or "", "email": r.email or "",
        })

    if not out["phone"] or not out["email"]:
        crows = frappe.db.sql("""
            SELECT c.mobile_no, c.phone, c.email_id
            FROM `tabContact` c
            JOIN `tabDynamic Link` dl ON dl.parent = c.name
            WHERE dl.link_doctype = %s AND dl.link_name = %s
            ORDER BY c.modified DESC
            LIMIT 1
        """, (party_doctype, party_name), as_dict=True)
        if crows:
            cr = crows[0]
            out["phone"] = out["phone"] or cr.get("mobile_no") or cr.get("phone") or ""
            out["email"] = out["email"] or cr.get("email_id") or ""

    return out

def _inventory_account(company):
    acc = frappe.db.get_value("Account",
        {"company": company, "account_name": ["like", "Stock In Hand%"], "is_group": 0},
        "name")
    if acc:
        return _account_number_or_name(acc)
    acc = frappe.db.get_value("Account",
        {"company": company, "root_type": "Asset", "is_group": 0},
        "name")
    return _account_number_or_name(acc) if acc else "Inventory"

def _item_defaults(item_code, company):
    d = frappe.db.sql("""
        SELECT income_account, expense_account, default_warehouse
        FROM `tabItem Default`
        WHERE parent = %s AND company = %s
        ORDER BY modified DESC
        LIMIT 1
    """, (item_code, company), as_dict=True)
    return d[0] if d else {}

def _item_price(item_code):
    r = frappe.get_all("Item Price",
        filters={"item_code": item_code, "price_list": "Standard Selling"},
        fields=["price_list_rate"], order_by="modified desc", limit=1)
    if r: return float(r[0].price_list_rate or 0)
    r = frappe.get_all("Item Price",
        filters={"item_code": item_code, "selling": 1},
        fields=["price_list_rate"], order_by="modified desc", limit=1)
    return float(r[0].price_list_rate or 0) if r else 0.0

def _default_income_account_for_item(item_code: str, company: str) -> str:
    r = frappe.db.sql("""
        SELECT income_account
        FROM `tabItem Default`
        WHERE parent = %s AND company = %s
        ORDER BY modified DESC
        LIMIT 1
    """, (item_code, company), as_dict=True)
    if r and r[0].get("income_account"):
        return _account_number_or_name(r[0]["income_account"])
    ig = frappe.db.get_value("Item", item_code, "item_group")
    if ig:
        acc = frappe.db.get_value("Item Group", ig, "default_income_account")
        if acc:
            return _account_number_or_name(acc)
    acc = frappe.db.get_value("Company", company, "default_income_account")
    return _account_number_or_name(acc) if acc else ""

# ---------------- Main exports ----------------

@frappe.whitelist()
def export_sage_monthly_pack(company, year, month, email_to=None):
    """Create one ZIP under /files with COA/Customers/Suppliers/Items/Sales/GeneralJournal for YYYY-MM."""
    year, month = int(year), int(month)
    yyyymm = _yyyymm(year, month)
    dfrom, dto = _month_bounds(year, month)

    # 1) COA
    accounts = frappe.get_all("Account",
        filters={"company": company, "is_group": 0},
        fields=["name","account_name","account_number","root_type","account_type","disabled"],
        order_by="IFNULL(account_number, name), name")
    coa_rows = []
    for a in accounts:
        acc_id = (a["account_number"] or a["name"]).strip()
        desc   = (a["account_name"] or a["name"]).strip()
        typ    = _map_sage_account_type(a)
        inactive = "Y" if int(a.get("disabled") or 0) else "N"
        coa_rows.append([acc_id, desc, typ, inactive])

    # 2) Customers
    customers = frappe.get_all("Customer",
        filters={}, fields=["name","customer_name","tax_id","default_currency","disabled"])
    cust_rows = []
    for c in customers:
        addr = _first_address("Customer", c["name"])
        cust_rows.append([
            c["name"], c.get("customer_name") or c["name"],
            addr["line1"], addr["line2"], addr["city"], addr["state"], addr["pincode"], addr["country"],
            addr["phone"], addr["email"],
            c.get("tax_id") or "", c.get("default_currency") or "ETB",
        ])

    # 3) Suppliers
    suppliers = frappe.get_all("Supplier",
        filters={}, fields=["name","supplier_name","tax_id","default_currency","disabled"])
    supp_rows = []
    for s in suppliers:
        addr = _first_address("Supplier", s["name"])
        supp_rows.append([
            s["name"], s.get("supplier_name") or s["name"],
            addr["line1"], addr["line2"], addr["city"], addr["state"], addr["pincode"], addr["country"],
            addr["phone"], addr["email"],
            s.get("tax_id") or "", s.get("default_currency") or "ETB",
        ])

    # 4) Items
    inv_acc_default = _inventory_account(company)
    items = frappe.get_all("Item",
        filters={"disabled": 0}, fields=["name","item_name","is_stock_item","stock_uom"])
    item_rows = []
    for it in items:
        d = _item_defaults(it["name"], company)
        sales_acc = _account_number_or_name(d.get("income_account")) if d.get("income_account") else ""
        cogs_acc  = _account_number_or_name(d.get("expense_account")) if d.get("expense_account") else ""
        inv_acc   = inv_acc_default
        price     = _item_price(it["name"])
        cost      = 0.0
        item_rows.append([
            it["name"], it.get("item_name") or it["name"], it.get("stock_uom") or "",
            "Y" if int(it.get("is_stock_item") or 0) else "N",
            sales_acc, cogs_acc, inv_acc, f"{price:.2f}", f"{cost:.2f}",
        ])

    # 5) Sales
    si = frappe.db.sql("""
        SELECT si.name AS inv, si.posting_date, si.customer,
               sii.item_code, sii.qty, sii.rate, sii.amount, sii.income_account
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.company = %s AND si.docstatus = 1
          AND si.posting_date BETWEEN %s AND %s
        ORDER BY si.posting_date, si.name, sii.idx
    """, (company, str(dfrom), str(dto)), as_dict=True)
    sales_rows = []
    for r in si:
        sales_acc = (_account_number_or_name(r["income_account"])
                     if r.get("income_account") else _default_income_account_for_item(r["item_code"], company))
        sales_rows.append([
            r["customer"], r["inv"], _fmt_us_date(r["posting_date"]),
            r["item_code"], f"{float(r.get('qty') or 0):.4f}", f"{float(r.get('rate') or 0):.4f}",
            f"{float(r.get('amount') or 0):.2f}", sales_acc
        ])

    # 6) General Journal (Peachtree-friendly: US dates, NO header)
    acc_map = {}
    for a in frappe.get_all("Account", filters={"company": company}, fields=["name","account_number"]):
        acc_map[a["name"]] = a.get("account_number") or a["name"]
    gj = frappe.db.sql("""
        SELECT posting_date, voucher_no, account, remarks, debit, credit
        FROM `tabGL Entry`
        WHERE company = %s AND is_cancelled = 0
          AND posting_date BETWEEN %s AND %s
        ORDER BY posting_date, voucher_no, name
    """, (company, str(dfrom), str(dto)), as_dict=True)
    gj_rows = []
    for g in gj:
        acc_id = acc_map.get(g["account"], g["account"])
        gj_rows.append([
            _fmt_us_date(g["posting_date"]),
            g["voucher_no"],
            acc_id,
            g.get("remarks") or "",
            f"{float(g.get('debit') or 0):.2f}",
            f"{float(g.get('credit') or 0):.2f}",
        ])

    # ---- Write ZIP in one context ----
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"COA_{yyyymm}.txt",
                   _tab_text(["Account ID","Description","Type","Inactive"], coa_rows))
        z.writestr(f"Customers_{yyyymm}.txt",
                   _tab_text(["Customer ID","Customer Name","Address1","Address2","City","State","Zip","Country","Phone","Email","Tax ID","Currency"], cust_rows))
        z.writestr(f"Suppliers_{yyyymm}.txt",
                   _tab_text(["Supplier ID","Supplier Name","Address1","Address2","City","State","Zip","Country","Phone","Email","Tax ID","Currency"], supp_rows))
        z.writestr(f"Items_{yyyymm}.txt",
                   _tab_text(["Item ID","Description","UOM","Is Stock Item","Sales GL","COGS GL","Inventory GL","Price","Cost"], item_rows))
        z.writestr(f"Sales_{yyyymm}.txt",
                   _tab_text(["Customer ID","Invoice No","Date","Item ID","Qty","Unit Price","Line Total","Sales GL"], sales_rows))
        # General Journal WITHOUT header and with CRLF:
        z.writestr(f"GeneralJournal_{yyyymm}.txt", _tab_text_no_header(gj_rows))

    # ---- Save ZIP + optional email ----
    os.makedirs(_files_dir(), exist_ok=True)
    zip_name = f"SAGE_{_slug(company)}_{yyyymm}.zip"
    with open(os.path.join(_files_dir(), zip_name), "wb") as f:
        f.write(mem.getvalue())

    if email_to:
        try:
            frappe.sendmail(
                recipients=[email_to],
                subject=f"Sage Monthly Export - {company} {yyyymm}",
                message=f"Attached is the Sage monthly export for {company} ({yyyymm}).",
                attachments=[{"fname": zip_name, "fcontent": mem.getvalue()}],
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Sage Monthly Pack Email Failed")

    return f"/files/{zip_name}"

@frappe.whitelist()
def export_sage_previous_month_pack(company, email_to=None):
    today = date.today()
    last_prev = date(today.year, today.month, 1) - timedelta(days=1)
    return export_sage_monthly_pack(company=company, year=last_prev.year, month=last_prev.month, email_to=email_to)

# ---- Back-compat aliases for older scripts ----
@frappe.whitelist()
def export_previous_month_for_sage(company, email_to=None):
    return export_sage_previous_month_pack(company=company, email_to=email_to)

@frappe.whitelist()
def export_month_for_sage(company, year=None, month=None, email_to=None):
    if not year or not month:
        today = date.today()
        last_prev = date(today.year, today.month, 1) - timedelta(days=1)
        year, month = last_prev.year, last_prev.month
    return export_sage_monthly_pack(company=company, year=int(year), month=int(month), email_to=email_to)

