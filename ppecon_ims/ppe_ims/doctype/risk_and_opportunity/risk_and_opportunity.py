# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RiskAndOpportunity(Document):
    pass


def notify_risk_opportunity_assignees(doc, method):
    if not doc.assigned_to:
        return

    recipients = []
    for row in doc.assigned_to:
        if row.user:
            recipients.append(row.user)

    if not recipients:
        return

    send_risk_opportunity_mail(doc, recipients)


def send_risk_opportunity_mail(doc, recipients):
    document_link = frappe.utils.get_url_to_form("Risk And Opportunity", doc.name)

    subject = f"Risk & Opportunity Assigned: {doc.name}"

    current_user = frappe.session.user
    created_by = frappe.db.get_value("User", current_user, "full_name") or current_user

    fields_to_show = [
        ("Risk Category", doc.risk_category),
        ("Risk / Opportunity Type", doc.risk_opportunity_type),
        ("Risk Impact", doc.risk_impact),
        ("Risk Probability", doc.risk_probability),
        ("Management System Type", doc.management_system_type),
        ("Department", doc.deaprtment),
        ("Treatment Type", doc.treatement_type),
        ("Source / Activity", doc.riskopportunity_source_or_activity),
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
            <h2 style="color: #ffffff; margin: 0;">⚠️ Risk & Opportunity Assignment</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi,</p>
            <p style="font-size: 15px; color: #333;">
                You have been assigned to the following <b>Risk & Opportunity</b> record by <b>{created_by}</b>. Please review the details below.
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