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