# =========================================================================
#  ppecon_ims/it_assets/employee_custody.py
#  Live IT asset custody list for an Employee, read straight from
#  IT Inventory — no duplication, no sync.
# =========================================================================
import frappe


def _has(doctype, field):
    try:
        return frappe.get_meta(doctype).has_field(field)
    except Exception:
        return False


@frappe.whitelist()
def get_custody_details(employee):
    """All IT Inventory assets currently assigned to this employee."""
    if not employee or not frappe.db.exists("DocType", "IT Inventory"):
        return []

    wanted = [
        "asset_name", "model_no", "sn", "manufacturerbrand", "asset_type",
        "purchase_date", "hddssd", "ram", "os", "processor", "specification",
        "assigned_to", "assigned_date", "request_reference", "name1", "status",
    ]
    fields = ["name"] + [f for f in wanted if _has("IT Inventory", f)]

    try:
        rows = frappe.get_all(
            "IT Inventory",
            filters={"assigned_to": employee, "docstatus": ("<", 2)},
            fields=fields,
            order_by="assigned_date desc, modified desc",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IT custody fetch")
        return []

    return rows


@frappe.whitelist()
def get_custody_summary(employee):
    rows = get_custody_details(employee)
    types = {}
    for r in rows:
        t = r.get("asset_type") or "Other"
        types[t] = types.get(t, 0) + 1
    return {"total": len(rows), "by_type": types, "rows": rows}