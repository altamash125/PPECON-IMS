# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

# apps/ppecon_ims/ppecon_ims/ppecon_ims/doctype/supplier_evaluation/supplier_evaluation.py
# Server-side calc — score tamper-proof rahega chahe client script bypass ho

import re

import frappe
from frappe.model.document import Document
from frappe.utils import escape_html, formatdate, today

CRITERIA_FIELDS = [
    "quality_of_product",
    "timelines_of_deliveries",
    "communication_and_responsiveness",
    "problem_resolution",
    "consistency_and_reliability",
    "adhere_to_contract_terms",
    "professionalism",
    "overall_satisfaction",
]

MAX_POINTS_PER_CRITERIA = 5
MAX_SCORE = len(CRITERIA_FIELDS) * MAX_POINTS_PER_CRITERIA  # 40


def get_points(value):
    """'Good (4 pts)' jaisi value se points nikalta hai."""
    if not value:
        return 0
    m = re.search(r"\((\d)\s*pts?\)", value, re.I)
    return int(m.group(1)) if m else 0


def get_rating(total):
    if total >= 36:
        return "Excellent"
    if total >= 26:
        return "Satisfactory"
    if total >= 21:
        return "Average"
    return "Poor"


class SupplierEvaluation(Document):
    def validate(self):
        missing = [f for f in CRITERIA_FIELDS if not self.get(f)]

        # Ratings sirf assigned evaluator ke liye mandatory hain
        # (jo assign kar raha hai, uske liye nahi) aur final submit pe sabke liye.
        if missing and (self.is_assigned_evaluator() or self.docstatus == 1):
            labels = ", ".join(frappe.bold(self.meta.get_label(f)) for f in missing)
            frappe.throw(
                f"Evaluator Should be All {len(CRITERIA_FIELDS)} criteria fulfilled. "
                f"Missing: {labels}",
                title="Ratings Required",
            )

        total = sum(get_points(self.get(f)) for f in CRITERIA_FIELDS)
        self.total_score = total
        self.percentage = round(total / MAX_SCORE * 100, 1)
        self.rating = get_rating(total) if not missing else ""

    def before_submit(self):
        # Final submit pe submission date auto set
        self.submission_date = today()

    def is_assigned_evaluator(self):
        """True jab current user wahi hai jise evaluator assign kiya gaya hai,
        aur document pehle se save ho chuka hai (naya document nahi)."""
        return bool(
            not self.is_new()
            and self.assigned_user
            and frappe.session.user == self.assigned_user
        )


# ---------------------------------------------------------------------------
# Notifications (hooks.py ke doc_events se call hote hain)
# ---------------------------------------------------------------------------

def notify_supplier_evaluation_evaluated_by(doc, method=None):
    """Evaluator naya assign ya change hone par hi mail (on_update har save pe chalta hai)."""
    if not doc.assigned_user:
        return

    # Naye doc pe has_value_changed True aata hai, isliye creation bhi cover hai
    if not doc.has_value_changed("assigned_user"):
        return

    send_supplier_evaluation_mail(doc, [doc.assigned_user], is_update=False)


def notify_supplier_evaluation_evaluated_by_after_submit(doc, method=None):
    # 1. assigned_user naya set/change hua ho to unhe mail
    if doc.assigned_user and doc.has_value_changed("assigned_user"):
        send_supplier_evaluation_mail(doc, [doc.assigned_user], is_update=False)

    # 2. Document update hone par creator (owner) ko notify karo
    notify_document_creator_on_update(doc)


def notify_document_creator_on_update(doc):
    if not doc.owner:
        return

    # Khud ke kiye hue update ka mail khud ko bhejne ki zaroorat nahi
    if doc.owner == frappe.session.user:
        return

    send_supplier_evaluation_mail(doc, [doc.owner], is_update=True)


def get_full_name(user):
    if not user:
        return ""
    return frappe.db.get_value("User", user, "full_name") or user


def send_supplier_evaluation_mail(doc, recipients, is_update=False):
    document_link = frappe.utils.get_url_to_form("Supplier Evaluation", doc.name)

    current_user = frappe.session.user
    current_user_name = escape_html(get_full_name(current_user))
    supplier_label = escape_html(doc.supplier_name or doc.name)

    if is_update:
        subject = f"Supplier Evaluation Updated: {doc.supplier_name or doc.name}"
        heading = "Supplier Evaluation Update"
        intro_text = (
            "The following <b>Supplier Evaluation</b> (created by you) has been "
            f"updated by <b>{current_user_name}</b>. Please review the changes below."
        )
        actor_label = "Updated By"
    else:
        subject = f"Supplier Evaluation Assigned: {doc.supplier_name or doc.name}"
        heading = "Supplier Evaluation Assignment"
        intro_text = (
            "You have been assigned as the <b>Evaluator</b> for the following "
            f"Supplier Evaluation by <b>{current_user_name}</b>. "
            "Please review the details below and complete all the ratings."
        )
        actor_label = "Submitted By"

    fields_to_show = [
        ("Supplier Name", supplier_label),
        ("Related PO No", escape_html(doc.related_po_no or "")),
        ("Project", escape_html(doc.project or "")),
        (
            "Date of Evaluation",
            formatdate(doc.date_of_evaluation) if doc.date_of_evaluation else "",
        ),
        ("Evaluated By", escape_html(get_full_name(doc.assigned_user))),
        (actor_label, current_user_name),
    ]

    rows_html = "".join(
        f"""
        <tr>
            <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0; width: 40%; vertical-align: top;">{label}</td>
            <td style="padding: 10px; border: 1px solid #e0e0e0;">{value}</td>
        </tr>
        """
        for label, value in fields_to_show
        if value
    )

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a3c6e; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">📝 {heading}</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi,</p>
            <p style="font-size: 15px; color: #333;">
                {intro_text}
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Supplier Evaluation
                </a>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #888;">
            This is an automated notification from your ERP system.
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        reference_doctype="Supplier Evaluation",
        reference_name=doc.name,
        now=True,
    )