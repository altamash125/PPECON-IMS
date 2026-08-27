# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DesignandDevelopment(Document):
    pass


def notify_design_development_lead(doc, method):
    if not doc.design_lead:
        return

    recipients = [doc.design_lead]

    send_design_development_mail(doc, recipients)


def send_design_development_mail(doc, recipients):
    document_link = frappe.utils.get_url_to_form("Design and Development", doc.name)

    subject = f"Design and Development Update: {doc.prospect_company or doc.name}"

    current_user = frappe.session.user
    updated_by = frappe.db.get_value("User", current_user, "full_name") or current_user

    lead_name = frappe.db.get_value("User", doc.design_lead, "full_name") or doc.design_lead

    fields_to_show = [
        ("Folder Number", doc.folder_number),
        ("Prospect Company", doc.prospect_company),
        ("Opportunity Date", doc.transaction_date),
        ("Design Lead", lead_name),
        ("Planning Date", doc.planning_date),
        ("Target Date", doc.target_date),
        ("Brief Description", doc.brief_description),
        ("Project Description", doc.project_description),
        ("Updated By", updated_by),
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
            <h2 style="color: #ffffff; margin: 0;">🛠️ Design and Development Update</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi {lead_name},</p>
            <p style="font-size: 15px; color: #333;">
                The following <b>Design and Development</b> record has been updated by <b>{updated_by}</b>. Please review the details below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Record
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