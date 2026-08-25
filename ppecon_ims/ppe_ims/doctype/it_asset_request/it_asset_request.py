
import frappe
from frappe.model.document import Document


class ITAssetRequest(Document):
    pass




# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt


IT_TEAM_EMAIL = "it@ppecon.com"


class ITAssetRequest(Document):
    pass


def notify_on_workflow_change(doc, method):
    if not doc.has_value_changed("workflow_state"):
        return

    if doc.workflow_state == "Pending Manager Approval":
        notify_manager(doc)
    elif doc.workflow_state == "Pending IT Approval":
        notify_it_team(doc)
    elif doc.workflow_state == "Approved":
        notify_employee(doc)


def notify_manager(doc):
    document_link = frappe.utils.get_url_to_form("IT Asset Request", doc.name)

    manager_email = doc.manager_approval

    if not manager_email:
        return

    subject = f"IT Asset Request Pending Your Approval: {doc.name}"

    fields_to_show = [
        ("Employee", doc.employee),
        ("Employee Name", doc.employee_name),
        ("Department", doc.department),
        ("Job Title", doc.job_title),
        ("Request Date", doc.request_date),
        ("Priority", doc.priority),
        ("Description", doc.description),
    ]

    rows_html = build_rows_html(fields_to_show)

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a3c6e; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">📋 IT Asset Request — Approval Needed</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi,</p>
            <p style="font-size: 15px; color: #333;">
                The following <b>IT Asset Request</b> has been submitted and is awaiting your <b>Manager Approval</b>. Please review the details below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Request
                </a>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #888;">
            This is an automated notification from your ERP system.
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=[manager_email],
        subject=subject,
        message=message,
        now=True
    )


def notify_it_team(doc):
    document_link = frappe.utils.get_url_to_form("IT Asset Request", doc.name)

    subject = f"IT Asset Request Pending Approval: {doc.name}"

    fields_to_show = [
        ("Employee", doc.employee),
        ("Employee Name", doc.employee_name),
        ("Department", doc.department),
        ("Job Title", doc.job_title),
        ("Request Date", doc.request_date),
        ("Priority", doc.priority),
        ("Description", doc.description),
    ]

    rows_html = build_rows_html(fields_to_show)

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a3c6e; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">🖥️ IT Asset Request — Approval Needed</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi Team,</p>
            <p style="font-size: 15px; color: #333;">
                The following <b>IT Asset Request</b> has been approved by the Manager and is now awaiting <b>IT approval</b>. Please review the details below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Request
                </a>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #888;">
            This is an automated notification from your ERP system.
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=[IT_TEAM_EMAIL],
        subject=subject,
        message=message,
        now=True
    )


def notify_employee(doc):
    document_link = frappe.utils.get_url_to_form("IT Asset Request", doc.name)

    employee_email = doc.email_id

    if not employee_email:
        return

    subject = f"Your IT Asset Request Has Been Approved: {doc.name}"

    fields_to_show = [
        ("Employee", doc.employee),
        ("Employee Name", doc.employee_name),
        ("Department", doc.department),
        ("Job Title", doc.job_title),
        ("Request Date", doc.request_date),
        ("Priority", doc.priority),
        ("Description", doc.description),
    ]

    rows_html = build_rows_html(fields_to_show)

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a6e3c; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">✅ IT Asset Request Approved</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi {doc.employee_name or ''},</p>
            <p style="font-size: 15px; color: #333;">
                Your <b>IT Asset Request</b> has been approved. Please find the details below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Request
                </a>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #888;">
            This is an automated notification from your ERP system.
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=[employee_email],
        subject=subject,
        message=message,
        now=True
    )


def build_rows_html(fields_to_show):
    rows_html = ""
    for label, value in fields_to_show:
        if value:
            rows_html += f"""
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0; width: 40%; vertical-align: top;">{label}</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{value}</td>
                </tr>
            """
    return rows_html