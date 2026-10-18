# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document

import frappe
from frappe import _
from frappe.utils import nowdate


class BOQ(Document):
	pass



def validate(self):
    self.total_cost = self.total_selling = 0
    for d in self.items:
        d.cost_amount = (d.qty or 0) * (d.cost_rate or 0)
        d.selling_amount = (d.qty or 0) * (d.selling_rate or 0)
        self.total_cost += d.cost_amount
        self.total_selling += d.selling_amount
    self.margin_amount = self.total_selling - self.total_cost
    self.margin_percent = round(self.margin_amount / self.total_selling * 100, 2) if self.total_selling else 0






@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
    boq = frappe.get_doc("BOQ", source_name)

    if boq.status != "Approved":
        frappe.throw(_("Quotation sirf Approved BOQ se ban sakta hai"))
    if not boq.customer:
        frappe.throw(_("Pehle BOQ mein Customer select karo"))

    existing = frappe.db.get_value("Quotation", {"boq": boq.name, "docstatus": ["<", 2]}, "name")
    if existing:
        frappe.throw(_("Is BOQ ka Quotation pehle se hai: {0}").format(existing))

    qtn = frappe.new_doc("Quotation")
    qtn.quotation_to = "Customer"
    qtn.party_name = boq.customer
    qtn.transaction_date = nowdate()
    qtn.currency = boq.currency
    qtn.boq = boq.name
    if boq.project and frappe.get_meta("Quotation").has_field("project"):
        qtn.project = boq.project

    # Section first-appearance order maintain 
    sections = {}
    for d in boq.items:
        sections.setdefault(d.section or "General", []).append(d)

    for section, rows in sections.items():
        for d in rows:
            qtn.append("items", {
                "item_code": "BOQ Work Item",
                "item_name": (d.description or "")[:140],
                "description": f"[{section}] {d.description}",
                "qty": d.qty,
                "uom": d.uom,
                "conversion_factor": 1,
                "price_list_rate": d.selling_rate,
                "rate": d.selling_rate,
            })

    qtn.run_method("set_missing_values")
    return qtn