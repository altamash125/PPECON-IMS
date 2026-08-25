# =========================================================================
#  ppecon_ims/audit/checklist_template.py
#  Both "Internal Audit CheckList Master" and "Internal Audit Inspection"
#  share the same child doctype "Check List Point" — so we just find the
#  Table field pointing to it on each side and copy all fields across.
#
#  Confirmed child doctype fields: check_point (Link -> IMS Documents),
#  conformance, record, remarks
# =========================================================================
import frappe

CHILD_DOCTYPE = "Check List Point"


def find_table_field(doctype):
    """Find the fieldname of the Table field whose child is Check List Point."""
    meta = frappe.get_meta(doctype)
    for f in meta.fields:
        if f.fieldtype == "Table" and f.options == CHILD_DOCTYPE:
            return f.fieldname
    return None


@frappe.whitelist()
def get_checklist_templates(department=None):
    """List of templates for the picker — filtered by department if given."""
    filters = {}
    if department:
        filters["department"] = department

    return frappe.get_all(
        "Internal Audit CheckList Master",
        filters=filters,
        fields=["name", "check_list_name", "department"],
        order_by="modified desc",
    )


@frappe.whitelist()
def get_template_points(template):
    """Return full checklist point rows (check_point, conformance, record,
    remarks) from the master's child table."""
    if not template:
        return []

    table_field = find_table_field("Internal Audit CheckList Master")
    if not table_field:
        frappe.throw("Could not find the Check List Point table on Internal Audit CheckList Master.")

    doc = frappe.get_doc("Internal Audit CheckList Master", template)
    rows = doc.get(table_field) or []

    return [
        {
            "check_point": r.check_point,
            "conformance": r.conformance,
            "record": r.record,
            "remarks": r.remarks,
        }
        for r in rows if r.check_point
    ]