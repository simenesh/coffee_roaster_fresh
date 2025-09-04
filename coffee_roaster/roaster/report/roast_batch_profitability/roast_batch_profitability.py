# --- Monthly export helpers (drop-in) ---------------------------------------
import os, io, zipfile
from datetime import date, timedelta
import frappe

def _month_bounds(year: int, month: int):
    start = date(year, month, 1)
    # next month:
    if month == 12:
        nxt = date(year+1, 1, 1)
    else:
        nxt = date(year, month+1, 1)
    end = nxt - timedelta(days=1)
    return start.isoformat(), end.isoformat()

@frappe.whitelist()
def export_month_for_sage(company: str = None, year: int = None, month: int = None, email_to: str = None):
    """Generate ALL Sage files for a specific month, zip them, and return /files/... zip path."""
    today = date.today()
    year  = year or today.year
    month = month or today.month

    start, end = _month_bounds(year, month)

    # Generate files (masters are full; journals & sales filtered)
    paths = []
    paths.append(export_chart_of_accounts_for_sage(company))
    paths.append(export_customers_for_sage())
    paths.append(export_suppliers_for_sage())
    paths.append(export_inventory_for_sage())
    paths.append(export_general_journal_for_sage(start, end))
    paths.append(export_sales_invoices_for_sage(start, end))

    # Collect absolute filesystem paths
    file_urls = [p for p in paths if p]
    base_dir = frappe.utils.get_files_path()
    abs_paths = []
    for u in file_urls:
        # u like '/files/GENERAL.TXT'
        fname = u.split("/files/")[-1]
        abs_paths.append(os.path.join(base_dir, fname))

    # Create a single zip in /files/
    zip_name = f"sage_export_{year}-{str(month).zfill(2)}.zip"
    zip_path = os.path.join(base_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in abs_paths:
            z.write(p, arcname=os.path.basename(p))

    # Create File doc so it’s visible in File Manager
    file_url = f"/files/{zip_name}"
    if not frappe.db.exists("File", {"file_url": file_url}):
        frappe.get_doc({
            "doctype": "File",
            "file_name": zip_name,
            "is_private": 0,
            "file_url": file_url
        }).insert(ignore_permissions=True)

    # Optional email to accounting
    if email_to:
        with open(zip_path, "rb") as f:
            content = f.read()
        frappe.sendmail(
            recipients=[x.strip() for x in email_to.split(",")],
            subject=f"Sage monthly export – {year}-{str(month).zfill(2)}",
            message=f"Attached is the Sage 50 import pack for {year}-{str(month).zfill(2)}.\n\nFiles:\n" + "\n".join(file_urls),
            attachments=[{"fname": zip_name, "fcontent": content}],
        )

    return file_url

@frappe.whitelist()
def export_previous_month_for_sage(company: str = None, email_to: str = None):
    """Convenience: export last calendar month and (optionally) email it."""
    today = date.today().replace(day=1) - timedelta(days=1)
    return export_month_for_sage(company, today.year, today.month, email_to)
