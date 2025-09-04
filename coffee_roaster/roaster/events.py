import re
import frappe
from frappe.utils import now_datetime, flt

def on_machine_event(rb_name: str, round_no: int, state: str, ts: str):
    """Map machine events to Roast Batch timestamps without schema changes.
    state: 'start' or 'finish' (others ignored)
    """
    if not (rb_name and state and ts):
        return
    try:
        rb = frappe.get_doc("Roast Batch", rb_name)
    except frappe.DoesNotExistError:
        return

    changed = False
    n = len(rb.get("rounds") or [])

    if state == "start":
        if not rb.charge_start:
            rb.charge_start = get_datetime(ts)
            changed = True

    elif state == "finish":
        # set Development End when the final round finishes
        if n and round_no == n and not rb.development_end:
            rb.development_end = get_datetime(ts)
            changed = True

    if changed:
        rb.save(ignore_permissions=True)
        frappe.db.commit()

def _snake(s: str) -> str:
    return re.sub(r"\W+", "_", s).strip("_").lower()

def _rank(name: str) -> int:
    s = (name or "").lower()
    score = 0
    if "fg" in s: score += 5
    if "finished" in s: score += 5
    if "output" in s: score += 4
    if "roast" in s: score += 2
    if "item" in s: score += 2
    if "qty" in s or "weight" in s: score += 1
    return score

def _first_present(doc, candidates):
    for f in candidates:
        if hasattr(doc, f):
            v = doc.get(f)
            if v or isinstance(v, (int, float)):
                return f, v
    return None, None

def _get_single_value(dt, fields):
    for f in fields:
        try:
            val = frappe.db.get_single_value(dt, f)
            if val:
                return val
        except Exception:
            pass
    return None

def _resolve_fg_from_meta(rb):
    meta = frappe.get_meta(rb.doctype)

    # 1) Item on parent (Link to Item)
    item_links = []
    for df in meta.fields:
        if df.fieldtype == "Link" and df.options == "Item":
            val = rb.get(df.fieldname)
            if val:
                item_links.append((df.fieldname, val, _rank(df.fieldname)))
    item_links.sort(key=lambda x: x[2], reverse=True)
    fg_item_code = item_links and item_links[0][1]
    fg_item_field = item_links and item_links[0][0]

    # 2) Qty/UOM on parent
    numeric_types = {"Float", "Int", "Currency"}
    qty_fields, uom_fields = [], []
    for df in meta.fields:
        if df.fieldtype in numeric_types:
            val = rb.get(df.fieldname)
            if val not in (None, ""):
                qty_fields.append((df.fieldname, flt(val), _rank(df.fieldname)))
        if df.fieldtype in {"Data", "Select", "Link"} and df.fieldname.lower().endswith("uom"):
            val = rb.get(df.fieldname)
            if val:
                uom_fields.append((df.fieldname, val, _rank(df.fieldname)))

    qty_fields.sort(key=lambda x: x[2], reverse=True)
    uom_fields.sort(key=lambda x: x[2], reverse=True)
    fg_qty = qty_fields and qty_fields[0][1]
    fg_uom = uom_fields and uom_fields[0][1]

    if fg_item_code and fg_qty not in (None, ""):
        return fg_item_code, flt(fg_qty), fg_uom, f"parent:{fg_item_field}"

    # 3) Child tables (outputs/finished/roasted)
    table_candidates = []
    for df in meta.fields:
        if df.fieldtype == "Table" and rb.get(df.fieldname):
            table_candidates.append((df.fieldname, df.options, _rank(df.fieldname)))
    table_candidates.sort(key=lambda x: x[2], reverse=True)

    for tbl_field, child_dt, _ in table_candidates:
        rows = rb.get(tbl_field) or []
        if not rows:
            continue
        child_meta = frappe.get_meta(child_dt)

        item_fields = []
        for cdf in child_meta.fields:
            if (cdf.fieldtype == "Link" and cdf.options == "Item") or cdf.fieldname == "item_code":
                item_fields.append(cdf.fieldname)

        qty_candidates = []
        for cdf in child_meta.fields:
            if cdf.fieldtype in numeric_types and any(k in cdf.fieldname.lower() for k in ["qty","weight","output"]):
                qty_candidates.append(cdf.fieldname)

        for row in rows:
            item_code = None
            for fn in sorted(item_fields, key=_rank, reverse=True):
                v = row.get(fn)
                if v:
                    item_code = v
                    break
            if not item_code:
                continue

            qty_val = None
            for fn in sorted(qty_candidates, key=_rank, reverse=True):
                v = row.get(fn)
                if v not in (None, ""):
                    qty_val = flt(v)
                    break
            if qty_val is None:
                continue

            uom_val = row.get("uom") or row.get("stock_uom")
            return item_code, qty_val, uom_val, f"child:{tbl_field}"

    return None, None, None, None

@frappe.whitelist()
def create_roasting_stock_entry(docname=None, *args, **kwargs):
    if not docname:
        frappe.throw("Please provide a Roast Batch document name")

    rb = frappe.get_doc("Roast Batch", docname)

    # Company
    company = rb.get("company") or _get_single_value("Global Defaults", ["default_company"])
    if not company:
        frappe.throw("Company not found on Roast Batch or Global Defaults")

    # Resolve FG (item/qty/uom)
    fg_item_code, fg_qty, fg_uom, source_hint = _resolve_fg_from_meta(rb)
    if not fg_item_code:
        meta = frappe.get_meta(rb.doctype)
        link_vals = []
        for df in meta.fields:
            if df.fieldtype == "Link" and df.options == "Item":
                val = rb.get(df.fieldname)
                if val:
                    link_vals.append(f"{df.fieldname}={val}")
        raise frappe.ValidationError(
            "Could not auto-detect Finished Good item on Roast Batch.\n"
            "Tip: add a Link-to-Item field (e.g., fg_item/finished_item/output_item) "
            "or an outputs child table with item+qty.\n"
            f"Detected Item links on parent: {', '.join(link_vals) if link_vals else 'none'}"
        )
    if fg_qty is None:
        raise frappe.ValidationError("Could not auto-detect Finished Good qty on Roast Batch.")

    # FG target warehouse (doc → Roaster Settings → Item Default → Stock Settings)
    fg_wh_candidates = ["fg_warehouse", "finished_goods_warehouse", "output_warehouse", "target_warehouse", "t_warehouse"]
    _, fg_wh = _first_present(rb, fg_wh_candidates)
    if not fg_wh:
        fg_wh = _get_single_value("Roaster Settings", ["finished_goods_warehouse", "fg_warehouse", "output_warehouse"])
    if not fg_wh:
        try:
            fg_wh = frappe.db.get_value("Item Default", {"parent": fg_item_code, "company": company}, "default_warehouse")
        except Exception:
            pass
    if not fg_wh:
        fg_wh = _get_single_value("Stock Settings", ["default_warehouse"])
    if not fg_wh:
        frappe.throw("Finished Goods warehouse not found. Set it on Roast Batch or in Roaster/Stock Settings.")

    # Gather Raw Materials
    rm_tables = ["roasting_materials", "raw_materials", "materials", "green_inputs", "ingredients", "rm_items", "items"]
    rm_lines = []
    for tbl in rm_tables:
        lines = rb.get(tbl)
        if isinstance(lines, (list, tuple)) and lines:
            for row in lines:
                item = row.get("item_code") or row.get("rm_item") or row.get("item")
                qty  = row.get("qty") or row.get("rm_qty") or row.get("quantity")
                uom  = row.get("uom") or row.get("stock_uom")
                swh  = row.get("s_warehouse") or row.get("source_warehouse") or row.get("warehouse")
                if item and qty:
                    rm_lines.append({
                        "item_code": item,
                        "qty": flt(qty),
                        "uom": uom,
                        "s_warehouse": swh,
                    })
            if rm_lines:
                break

    se_type = "Manufacture" if rm_lines else "Material Receipt"

    # Build Stock Entry
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = se_type
    se.company = company

    # RM items
    for rm in rm_lines:
        it = se.append("items", {})
        rm_item_code = rm["item_code"]
        it.item_code = rm_item_code
        it.qty = rm["qty"]
        it.uom = rm.get("uom") or frappe.db.get_value("Item", rm_item_code, "stock_uom")
        it.conversion_factor = 1

        if rm.get("s_warehouse"):
            it.s_warehouse = rm["s_warehouse"]
        else:
            swh = frappe.db.get_value(
                "Item Default", {"parent": rm_item_code, "company": company}, "default_warehouse"
            ) or _get_single_value("Stock Settings", ["default_warehouse"])
            if not swh:
                frappe.throw(f"Source warehouse not found for RM {rm_item_code}.")
            it.s_warehouse = swh

        if frappe.db.get_value("Item", rm_item_code, "has_batch_no"):
            try:
                from erpnext.stock.doctype.batch.batch import get_batch_no
                bn = get_batch_no(item_code=rm_item_code, warehouse=it.s_warehouse)
                if not bn:
                    frappe.throw(f"No available batch for {rm_item_code} in {it.s_warehouse}")
                it.batch_no = bn
            except Exception:
                pass


    # FG item
    it_fg = se.append("items", {})
    it_fg.item_code = fg_item_code
    it_fg.qty = flt(fg_qty)
    it_fg.uom = fg_uom or frappe.db.get_value("Item", fg_item_code, "stock_uom")
    it_fg.conversion_factor = 1
    it_fg.t_warehouse = fg_wh

    # Batch for FG if needed (v15 uses batch_id)
    if frappe.db.get_value("Item", fg_item_code, "has_batch_no"):
        series = frappe.db.get_value("Item", fg_item_code, "batch_number_series")
        if series:
            from frappe.model.naming import make_autoname
            batch_id = make_autoname(series)
        else:
            batch_id = f"{fg_item_code}-BATCH-{now_datetime().strftime('%Y%m%d%H%M%S')}"
        batch = frappe.get_doc({"doctype": "Batch", "item": fg_item_code, "batch_id": batch_id})
        batch.insert(ignore_permissions=True)
        it_fg.batch_no = batch.name  # batch.name == batch_id

    se.insert(ignore_permissions=True)
    se.submit()

    frappe.msgprint(f"{se.stock_entry_type} Stock Entry {se.name} created (FG via {source_hint or 'auto-detect'}).")
    return se.name

