import frappe
from frappe.utils import formatdate

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/ppe-policy"
        raise frappe.Redirect
    context.no_cache = 1
    return context


@frappe.whitelist(allow_guest=False)
def get_page_data():
    """
    Flat list of categories (from Policy Category master), each with its
    active Company Policy documents. Order follows sort_order as entered
    in the doctype — no grouping.
    """
    categories = frappe.get_all(
        "Policy Category",
        fields=["name", "category_name", "icon", "color",
                "badge_label", "description", "sort_order"],
        order_by="sort_order asc, category_name asc",
    )

    policies = frappe.get_all(
        "Company Policy",
        filters={"is_active": 1},
        fields=["name", "category", "title", "version", "effective_date",
                "description", "policy_file"],
        order_by="title asc",
    )

    by_category = {}
    for p in policies:
        by_category.setdefault(p.category, []).append({
            "name": p.name,
            "title": p.title,
            "version": p.version,
            "effective_date": formatdate(p.effective_date) if p.effective_date else None,
            "description": p.description,
            "file_url": p.policy_file,
        })

    result = []
    for c in categories:
        result.append({
            "name": c.name,
            "category_name": c.category_name,
            "icon": c.icon or "📄",
            "color": c.color or "#1f6fd0",
            "badge_label": c.badge_label,
            "description": c.description,
            "documents": by_category.get(c.category_name, []),
        })

    return {
        "categories": result,
        "total_categories": len(categories),
        "total_documents": len(policies),
    }