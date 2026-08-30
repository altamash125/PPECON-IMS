import frappe

TABLE_FIELD = "hse_checklist_item"


@frappe.whitelist()
def get_template_points(template):
    """Return checklist item rows + image from HSE Checklist Master."""
    if not template:
        return {}

    doc = frappe.get_doc("HSE Checklist Master", template)
    rows = doc.get(TABLE_FIELD) or []

    return {
        "points": [
            {
                "description": r.description,
                "status": r.status,
                "remark": r.remark,
            }
            for r in rows
        ],
        "image": doc.get("image")
    }





def attach_image_to_doc(doc, method=None):
    """Ensure the image field's file also shows in the Attachments sidebar."""
    if not doc.get("image"):
        return

    exists = frappe.db.exists(
        "File",
        {
            "file_url": doc.image,
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
        }
    )
    if exists:
        return

    source_file = frappe.db.get_value(
        "File", {"file_url": doc.image}, ["is_private"], as_dict=True
    )

    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_url": doc.image,
        "attached_to_doctype": doc.doctype,
        "attached_to_name": doc.name,
        "attached_to_field": "image",
        "is_private": source_file.is_private if source_file else 0,
    })
    file_doc.save(ignore_permissions=True)
