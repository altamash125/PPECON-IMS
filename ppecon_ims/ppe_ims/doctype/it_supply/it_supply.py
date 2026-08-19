import frappe
from frappe.model.document import Document
from ppecon_ims.ppe_ims.doctype.it_asset_request.it_asset_request import rebuild_employee_custody


class ITSupply(Document):
    pass


def on_it_supply_update(doc, method):
    """Whenever IT Supply changes (new assignment, status change, return, etc.)
    re-sync the Employee custody display"""
    if doc.assigned_to:
        rebuild_employee_custody(doc.assigned_to)