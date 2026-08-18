# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

# apps/ppecon_ims/ppecon_ims/ppecon_ims/doctype/supplier_evaluation/supplier_evaluation.py
# Server-side calc — score tamper-proof rahega chahe client script bypass ho

import re
import frappe
from frappe.model.document import Document

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


def get_points(value):
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
        if missing and self.docstatus == 1:
            frappe.throw("All 8 criteria must be scored before submission.")

        total = sum(get_points(self.get(f)) for f in CRITERIA_FIELDS)
        self.total_score = total
        self.percentage = round(total / 40 * 100, 1)
        self.rating = get_rating(total) if not missing else ""




# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SupplierEvaluation(Document):
    pass


def notify_supplier_evaluation_evaluated_by(doc, method):
    if not doc.evaluated_by:
        return

    recipients = [doc.evaluated_by]

    send_supplier_evaluation_mail(doc, recipients, is_update=False)


def notify_supplier_evaluation_evaluated_by_after_submit(doc, method):
    # 1. Agar evaluated_by naya set/change hua hai to unhe mail
    if doc.evaluated_by and doc.has_value_changed("evaluated_by"):
        send_supplier_evaluation_mail(doc, [doc.evaluated_by], is_update=False)

    # 2. Document ka koi bhi update ho to creator (owner) ko notify karo
    notify_document_creator_on_update(doc)


def notify_document_creator_on_update(doc):
    if not doc.owner:
        return

    recipients = [doc.owner]

    send_supplier_evaluation_mail(doc, recipients, is_update=True)


def send_supplier_evaluation_mail(doc, recipients, is_update=False):
    document_link = frappe.utils.get_url_to_form("Supplier Evaluation", doc.name)

    current_user = frappe.session.user
    created_by = frappe.db.get_value("User", current_user, "full_name") or current_user

    if is_update:
        subject = f"Supplier Evaluation Updated: {doc.supplier_name or doc.name}"
        intro_text = f"The following <b>Supplier Evaluation</b> (created by you) has been updated by <b>{created_by}</b>. Please review the changes below."
    else:
        subject = f"Supplier Evaluation Assigned: {doc.supplier_name or doc.name}"
        intro_text = f"You have been assigned as the <b>Evaluator</b> for the following Supplier Evaluation by <b>{created_by}</b>. Please review the details below."

    fields_to_show = [
        ("Supplier Name", doc.supplier_name),
        ("Related PO No", doc.related_po_no),
        ("Project", doc.project),
        ("Date of Evaluation", doc.date_of_evaluation),
        ("Evaluated By", frappe.db.get_value("User", doc.evaluated_by, "full_name") or doc.evaluated_by),
        ("Updated By" if is_update else "Submitted By", created_by),
    ]

    rows_html = ""
    for label, value in fields_to_show:
        if value:
            rows_html += f"""
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0; width: 40%; vertical-align: top;">{label}</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{value}</td>
                </tr>
            """

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a3c6e; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">📝 Supplier Evaluation {"Update" if is_update else "Assignment"}</h2>
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
        now=True
    )