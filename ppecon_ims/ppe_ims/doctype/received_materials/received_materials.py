# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReceivedMaterial(Document):
    pass


def notify_received_material_responsible_persons(doc, method):
    if not doc.responsible_person:
        return

    recipients = []
    for row in doc.responsible_person:
        if row.user:
            recipients.append(row.user)

    if not recipients:
        return

    send_received_material_mail(doc, recipients)


def send_received_material_mail(doc, recipients):
    document_link = frappe.utils.get_url_to_form("Received Material", doc.name)

    subject = f"Received Material Assigned: {doc.name}"

    current_user = frappe.session.user
    created_by = frappe.db.get_value("User", current_user, "full_name") or current_user

    fields_to_show = [
        ("Project Name", doc.project_name),
        ("Material Category", doc.material_category),
        ("Received Material", doc.received_material),
        ("Technical Details", doc.technical_details),
        ("Management System Type", doc.management_system_type),
        ("Delivery Note", doc.delivery_note),
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
            <h2 style="color: #ffffff; margin: 0;">📦 Received Material Assignment</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi,</p>
            <p style="font-size: 15px; color: #333;">
                You have been assigned as a <b>Responsible Person</b> for the following Received Material record by <b>{created_by}</b>. Please review the details below.
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