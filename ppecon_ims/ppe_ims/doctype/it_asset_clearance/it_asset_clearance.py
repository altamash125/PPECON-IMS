# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ITAssetClearance(Document):
	pass




# =========================================================================
#  apps/ppecon_ims/ppecon_ims/ppe_ims/doctype/it_asset_clearance/it_asset_clearance.py
# =========================================================================
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from ppecon_ims.it_assets.employee_custody import get_custody_details


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
                    })
                    released += 1
                except Exception:
                    frappe.log_error(frappe.get_traceback(),
                                     f"IT Asset Clearance release: {row.it_inventory}")

        self.db_set("cleared_by", frappe.session.user)
        self.db_set("cleared_on", now_datetime())
        frappe.msgprint(f"{released} asset(s) released from custody.")

    def on_cancel(self):
        # re-assign the assets back if the clearance is cancelled
        for row in self.items:
            if row.returned and row.it_inventory:
                try:
                    frappe.db.set_value("IT Inventory", row.it_inventory, {
                        "assigned_to": self.employee,
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




# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt


IT_TEAM_EMAIL = "it@ppecon.com"


def notify_on_asset_return(doc, method):
    before_doc = doc.get_doc_before_save()

    # Purani rows ka "returned" status map bana lo (row.name -> returned)
    before_returned_map = {}
    if before_doc:
        for row in before_doc.items:
            before_returned_map[row.name] = row.returned

    for row in doc.items:
        was_returned = before_returned_map.get(row.name, 0)

        # Sirf tab mail bhejo jab pehle "Returned" nahi tha, ab hai
        if row.returned and not was_returned:
            send_asset_return_mail(doc, row)


def send_asset_return_mail(doc, row):
    document_link = frappe.utils.get_url_to_form("IT Asset Clearance", doc.name)

    subject = f"IT Asset Returned: {row.asset_name or row.it_inventory}"

    recipients = [IT_TEAM_EMAIL]
    if row.returned_to:
        recipients.append(row.returned_to)

    fields_to_show = [
        ("Employee", doc.employee_name or doc.employee),
        ("Department", doc.department),
        ("IT Inventory", row.it_inventory),
        ("Asset Name", row.asset_name),
        ("Type", row.type),
        ("Serial No.", row.sn),
        ("Condition", row.condition),
        ("Returned To", frappe.db.get_value("User", row.returned_to, "full_name") or row.returned_to),
        ("Remarks", row.remarks),
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

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        now=True
    )