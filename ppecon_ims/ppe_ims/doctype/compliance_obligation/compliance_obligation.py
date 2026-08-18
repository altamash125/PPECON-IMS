# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ComplianceObligation(Document):
    pass


def notify_compliance_obligation_responsible_person(doc, method):
    if not doc.responsible_person:
        return

    recipients = [doc.responsible_person]

    send_compliance_obligation_mail(doc, recipients)


def notify_compliance_obligation_responsible_person_after_submit(doc, method):
    if not doc.responsible_person:
        return

    # Sirf tab bhejo jab responsible_person naya set/change hua ho (already-submitted doc mein baad mein assign hone pe)
    if not doc.has_value_changed("responsible_person"):
        return

    recipients = [doc.responsible_person]

    send_compliance_obligation_mail(doc, recipients)


def send_compliance_obligation_mail(doc, recipients):
    document_link = frappe.utils.get_url_to_form("Compliance Obligation", doc.name)

    subject = f"Compliance Obligation Assigned: {doc.name}"

    current_user = frappe.session.user
    created_by = frappe.db.get_value("User", current_user, "full_name") or current_user

    fields_to_show = [
        ("Compliance Obligation Type", doc.compliance_obligation_type),
        ("Source Type", doc.complianceobligation_source_type),
        ("Frequency", doc.frequency),
        ("Document Name", doc.compliance_obligation_document_name),
        ("Compliance Obligation", doc.compliance_obligation),
        ("Applicable Section / Rule", doc.applicable_section_rule),
        ("Date Renewed", doc.date_renewed),
        ("Expiration Date", doc.expiration_date),
        ("Responsible Person", frappe.db.get_value("User", doc.responsible_person, "full_name") or doc.responsible_person),
        ("Submitted By", created_by),
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
            <h2 style="color: #ffffff; margin: 0;">📋 Compliance Obligation Assignment</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi,</p>
            <p style="font-size: 15px; color: #333;">
                You have been assigned as the <b>Responsible Person</b> for the following Compliance Obligation by <b>{created_by}</b>. Please review the details below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Compliance Obligation
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