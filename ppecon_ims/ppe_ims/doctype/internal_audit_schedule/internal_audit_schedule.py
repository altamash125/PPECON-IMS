# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InternalAuditSchedule(Document):
	pass



import frappe


def get_multiselect_user_emails(doc, fieldname):
    """Generic helper: fetch User emails from any Table MultiSelect field linked to User."""
    rows = doc.get(fieldname) or []
    if not rows:
        return []

    child_doctype = doc.meta.get_field(fieldname).options
    user_field = None
    for df in frappe.get_meta(child_doctype).fields:
        if df.fieldtype == "Link" and df.options == "User":
            user_field = df.fieldname
            break

    if not user_field:
        frappe.log_error(f"No User link field found in {child_doctype}", "Audit Schedule Notify")
        return []

    users = [row.get(user_field) for row in rows if row.get(user_field)]
    if not users:
        return []

    emails = frappe.get_all("User", filters={"name": ["in", users]}, pluck="email")
    return [e for e in emails if e]


def notify_on_update(doc, method):
    """Triggered on save — sends mail to Auditor(s) and/or Auditee(s) whenever either field changes."""
    if doc.has_value_changed("auditor"):
        recipients = get_multiselect_user_emails(doc, "auditor")
        if recipients:
            send_audit_notification_email(doc, recipients, role="Auditor")

    if doc.has_value_changed("auditee"):
        recipients = get_multiselect_user_emails(doc, "auditee")
        if recipients:
            send_audit_notification_email(doc, recipients, role="Auditee")


def send_audit_notification_email(doc, recipients, role):
    schedule_link = frappe.utils.get_url_to_form(doc.doctype, doc.name)

    auditors = ", ".join(get_multiselect_user_emails(doc, "auditor")) or "-"
    auditees = ", ".join(get_multiselect_user_emails(doc, "auditee")) or "-"

    role_color = "#1f4e79" if role == "Auditor" else "#8e44ad"

    subject = f"Internal Audit Notification: {doc.name} — You've Been Assigned as {role}"

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: {role_color}; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">📋 Internal Audit Schedule Notification</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">
                Dear Team,
            </p>
            <p style="font-size: 15px; color: #333;">
                You have been assigned as <b>{role}</b> for the following scheduled internal audit.
                Please review the details below and prepare accordingly.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0; width: 40%;">Audit Reference</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{doc.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0;">Audit Year</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{doc.get("audit_year") or "-"}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0;">Process</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{doc.get("processes") or "-"}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0;">Audit Date</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0; color: #c0392b; font-weight: bold;">{doc.get("date") or "-"}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0;">Auditor(s)</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{auditors}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background-color: #f8f9fa; font-weight: bold; border: 1px solid #e0e0e0;">Auditee(s)</td>
                    <td style="padding: 10px; border: 1px solid #e0e0e0;">{auditees}</td>
                </tr>
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{schedule_link}" style="background-color: {role_color}; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Audit Schedule
                </a>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #888;">
            This is an automated notification from your IMS (Integrated Management System).
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        now=True
    )