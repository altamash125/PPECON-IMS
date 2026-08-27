# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_url_to_form

from ppecon_ims.it_assets.employee_custody import get_custody_details


IT_TEAM_EMAIL = "it@ppecon.com"


class ITAssetClearance(Document):
    def validate(self):
        self.compute_status()

    def compute_status(self):
        if not self.items:
            self.status = "Pending"
            return
        all_returned = all(row.returned for row in self.items)
        self.status = "Cleared" if all_returned else "Pending"

    def on_submit(self):
        if self.status != "Cleared":
            frappe.throw("All assets must be marked 'Returned' before submitting clearance.")

        released = 0
        for row in self.items:
            if row.returned and row.it_inventory:
                try:
                    frappe.db.set_value("IT Inventory", row.it_inventory, {
                        "assigned_to": None,
                        "assigned_date": None,
                        "status": "In Stock",
                        "name1": None,
                    })
                    released += 1
                except Exception:
                    frappe.log_error(frappe.get_traceback(),
                                     f"IT Asset Clearance release: {row.it_inventory}")

        self.db_set("cleared_by", frappe.session.user)
        self.db_set("cleared_on", now_datetime())
        frappe.msgprint(f"{released} asset(s) released from custody and marked In Stock.")

    def on_cancel(self):
        # Re-assign the assets back if the clearance is cancelled
        for row in self.items:
            if row.returned and row.it_inventory:
                try:
                    employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
                    frappe.db.set_value("IT Inventory", row.it_inventory, {
                        "assigned_to": self.employee,
                        "status": "Assigned",
                        "name1": employee_name,
                    })
                except Exception:
                    frappe.log_error(frappe.get_traceback(),
                                     f"IT Asset Clearance re-assign: {row.it_inventory}")


@frappe.whitelist()
def fetch_assigned_assets(employee):
    """Pull the employee's current custody list to populate the child table."""
    rows = get_custody_details(employee)
    return [
        {
            "it_inventory": r.get("name"),
            "asset_name": r.get("asset_name") or r.get("name1"),
            "asset_type": r.get("asset_type"),
            "sn": r.get("sn"),
            "returned": 0,
            "condition": "",
        }
        for r in rows
    ]


# ============================================================
#  Notifications
# ============================================================

def notify_on_update(doc, method):
    # 1. Asset-level "Returned" tick — sends to returned_to first, then IT
    try:
        notify_on_asset_return(doc, method)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IT Asset Clearance: asset return notify failed")

    # 2. Workflow state transitions
    if doc.has_value_changed("workflow_state"):
        try:
            if doc.workflow_state == "Pending IT Clearance":
                notify_it_team_hr_cleared(doc)
            elif doc.workflow_state == "Cleared":
                notify_employee_acknowledgment(doc)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IT Asset Clearance: workflow notify failed")


def notify_on_asset_return(doc, method):
    before_doc = doc.get_doc_before_save()

    before_returned_map = {}
    if before_doc:
        for row in before_doc.items:
            before_returned_map[row.name] = row.returned

    for row in doc.items:
        was_returned = before_returned_map.get(row.name, 0)

        if row.returned and not was_returned:
            # Pehle returned_to (generally HR) ko mail
            if row.returned_to:
                send_asset_return_mail(doc, row, recipients=[row.returned_to])

            # Uske baad IT team ko mail
            send_asset_return_mail(doc, row, recipients=[IT_TEAM_EMAIL])


def send_asset_return_mail(doc, row, recipients):
    document_link = get_url_to_form("IT Asset Clearance", doc.name)

    subject = f"IT Asset Returned: {row.asset_name or row.it_inventory}"

    fields_to_show = [
        ("Employee", doc.employee_name or doc.employee),
        ("Department", doc.department),
        ("IT Inventory", row.it_inventory),
        ("Asset Name", row.asset_name),
        ("Type", row.asset_type),
        ("Serial No.", row.sn),
        ("Condition", row.condition),
        ("Returned To", row.name1 or frappe.db.get_value("User", row.returned_to, "full_name") or row.returned_to),
        ("Remarks", row.remarks),
    ]

    rows_html = build_rows_html(fields_to_show)

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a6e3c; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">📦 IT Asset Returned</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi,</p>
            <p style="font-size: 15px; color: #333;">
                The following IT asset has been marked as <b>Returned</b>. Please review the details below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View IT Asset Clearance
                </a>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #888;">
            This is an automated notification from your ERP system.
        </div>
    </div>
    """

    frappe.sendmail(recipients=recipients, subject=subject, message=message, now=True)


def notify_it_team_hr_cleared(doc):
    document_link = get_url_to_form("IT Asset Clearance", doc.name)

    subject = f"IT Asset Clearance — HR Approved: {doc.name}"

    fields_to_show = [
        ("Employee", doc.employee_name or doc.employee),
        ("Department", doc.department),
        ("Last Working Date", doc.last_working_day),
        ("Status", "Approved by HR — Pending IT Clearance"),
    ]

    rows_html = build_rows_html(fields_to_show)

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a3c6e; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">✅ Clearance Approved by HR</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Dear IT Team,</p>
            <p style="font-size: 15px; color: #333;">
                HR has approved this employee's <b>IT Asset Clearance</b>. It is now awaiting <b>IT Supervisor</b> approval. Please review the details below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Clearance
                </a>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #888;">
            This is an automated notification from your ERP system.
        </div>
    </div>
    """

    frappe.sendmail(recipients=[IT_TEAM_EMAIL], subject=subject, message=message, now=True)


def notify_employee_acknowledgment(doc):
    document_link = get_url_to_form("IT Asset Clearance", doc.name)

    employee_email = doc.get("email_id") or frappe.db.get_value("Employee", doc.employee, "user_id")
    if not employee_email:
        return

    subject = f"IT Asset Clearance Completed: {doc.name}"

    fields_to_show = [
        ("Employee", doc.employee_name or doc.employee),
        ("Department", doc.department),
        ("Last Working Date", doc.last_working_day),
        ("Status", "Fully Cleared"),
    ]

    rows_html = build_rows_html(fields_to_show)

    message = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #1a6e3c; padding: 20px; text-align: center;">
            <h2 style="color: #ffffff; margin: 0;">🎉 IT Asset Clearance Completed</h2>
        </div>
        <div style="padding: 25px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333;">Hi {doc.employee_name or ''},</p>
            <p style="font-size: 15px; color: #333;">
                Your <b>IT Asset Clearance</b> has been fully processed and approved by both HR and IT. Please find the summary below.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                {rows_html}
            </table>
            <div style="text-align: center; margin-top: 25px;">
                <a href="{document_link}" style="background-color: #2c7be5; color: #ffffff; padding: 10px 25px; text-decoration: none; border-radius: 5px; font-size: 14px;">
                    View Clearance
                </a>
            </div>
        </div>
        <div style="background-color: #f8f9fa; padding: 12px; text-align: center; font-size: 12px; color: #888;">
            This is an automated notification from your ERP system.
        </div>
    </div>
    """

    frappe.sendmail(recipients=[employee_email], subject=subject, message=message, now=True)


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

