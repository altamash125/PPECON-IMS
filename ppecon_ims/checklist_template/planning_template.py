# =========================================================================
#  Planning Operations — same pattern as Internal Audit Checklist
# =========================================================================
import frappe


PLANNING_CHILD_DOCTYPE = "Planning Operation Checklist  Item" 

@frappe.whitelist()
def get_planning_templates():
    """List of templates for the picker."""
    return frappe.get_all(
        "Planning Operation Checklist",
        fields=["name", "checklist_name"],
        order_by="modified desc",
    )


@frappe.whitelist()
def get_planning_template_points(template):
    """Return the criteria list from the master's child table."""
    if not template:
        return []

    table_field = find_table_field_generic("Planning Operation Checklist", PLANNING_CHILD_DOCTYPE)
    if not table_field:
        frappe.throw("Could not find the checklist table on Planning Operation Checklist.")

    doc = frappe.get_doc("Planning Operation Checklist", template)
    rows = doc.get(table_field) or []

    return [r.criteria for r in rows if r.criteria]


def find_table_field_generic(doctype, child_doctype):
    meta = frappe.get_meta(doctype)
    for f in meta.fields:
        if f.fieldtype == "Table" and f.options == child_doctype:
            return f.fieldname
    return None


