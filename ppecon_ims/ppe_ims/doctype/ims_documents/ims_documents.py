
# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class IMSDocuments(Document):
    pass


def notify_ims_document_assignees(doc, method):
    if not doc.assigned_to:
        return

    recipients = []
    for row in doc.assigned_to:
        if row.user:
            recipients.append(row.user)

    if not recipients:
        return

    send_ims_document_mail(doc, recipients)


def send_ims_document_mail(doc, recipients):
    document_link = frappe.utils.get_url_to_form("IMS Documents", doc.name)

    subject = f"IMS Document Assigned: {doc.document_name or doc.name}"

    # Current session user (jisne submit kiya) ka full name nikal rahe hain
    current_user = frappe.session.user
    created_by = frappe.db.get_value("User", current_user, "full_name") or current_user

    # Fields to show — sirf tab dikhega jab value ho
    fields_to_show = [
        ("Document Name", doc.document_name),
        ("Document Category", doc.document_category),
        ("Document Issue Date", doc.document_issue_date),
        ("Document Code", doc.document_code),
        ("Document Number", doc.document_number),
        ("Document Type", doc.document_type),
        ("Department", doc.department),
        ("Revision Number", doc.revision_number),
        # ("Description", doc.documents_description),
        ("Submitted By", created_by),
    ]

    rows_html = ""
    for label, value in fields_to_show:
        if value:  # sirf non-empty fields ka row banega
            rows_html += f"""
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0; width: 40%; vertical-align: top;">{label}</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{value}</td>
                </tr>
            """

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a3c6e; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">📄 IMS Document Assignment</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi,</p>
            <p style="font-size: 15px; color: #333;">
                You have been assigned to the following <b>IMS Document</b> by <b>{created_by}</b>. Please review the details below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Document
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