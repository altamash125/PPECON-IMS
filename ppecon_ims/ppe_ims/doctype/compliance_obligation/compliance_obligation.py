# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_months, getdate, nowdate
from frappe.model.document import Document


class ComplianceObligation(Document):
    pass


def notify_compliance_obligation_responsible_person(doc, method):
    if not doc.responsible_person:
        return

    recipients = [doc.responsible_person]

    send_compliance_obligation_mail(doc, recipients, is_update=False)


def notify_compliance_obligation_responsible_person_after_submit(doc, method):
    # 1. Agar responsible_person change hui hai to unhe bhi mail jaaye
    if doc.responsible_person and doc.has_value_changed("responsible_person"):
        send_compliance_obligation_mail(doc, [doc.responsible_person], is_update=False)

    # 2. Document ka koi bhi update ho to creator (owner) ko notify karo
    notify_document_creator_on_update(doc)


def notify_document_creator_on_update(doc):
    if not doc.owner:
        return

    recipients = [doc.owner]

    send_compliance_obligation_mail(doc, recipients, is_update=True)


def send_compliance_obligation_mail(doc, recipients, is_update=False):
    document_link = frappe.utils.get_url_to_form("Compliance Obligation", doc.name)

    if is_update:
        subject = f"Compliance Obligation Updated: {doc.name}"
        intro_text = f"The following <b>Compliance Obligation</b> (created by you) has been updated by <b>{frappe.db.get_value('User', frappe.session.user, 'full_name') or frappe.session.user}</b>. Please review the changes below."
    else:
        subject = f"Compliance Obligation Assigned: {doc.name}"
        intro_text = f"You have been assigned as the <b>Responsible Person</b> for the following Compliance Obligation. Please review the details below."

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
            <h2 style="color: #ffffff; margin: 0;">📋 Compliance Obligation {"Update" if is_update else "Assignment"}</h2>
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


def send_compliance_obligation_expiry_reminders():
    reminder_date = add_months(getdate(nowdate()), 1)

    obligations = frappe.get_all(
        "Compliance Obligation",
        filters={
            "expiration_date": reminder_date,
            "docstatus": 1
        },
        fields=["name"]
    )

    for row in obligations:
        doc = frappe.get_doc("Compliance Obligation", row.name)

        if not doc.responsible_person:
            continue

        send_compliance_obligation_expiry_mail(doc, [doc.responsible_person])


def send_compliance_obligation_expiry_mail(doc, recipients):
    document_link = frappe.utils.get_url_to_form("Compliance Obligation", doc.name)

    subject = f"Compliance Obligation Expiring Soon: {doc.name}"

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
        <div style="background-color: #b02a2a; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">⏰ Compliance Obligation Expiring Soon</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi,</p>
            <p style="font-size: 15px; color: #333;">
                The following <b>Compliance Obligation</b>, for which you are the Responsible Person, is set to <b>expire in one month</b>. Please take the necessary action before the expiration date.
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
            This is an automated reminder from your ERP system.
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        now=True
    )