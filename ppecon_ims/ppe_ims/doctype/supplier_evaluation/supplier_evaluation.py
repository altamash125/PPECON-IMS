# Copyright (c) 2026, altamash@ppecon.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

# apps/ppecon_ims/ppecon_ims/ppecon_ims/doctype/supplier_evaluation/supplier_evaluation.py
# Server-side calc — score tamper-proof rahega chahe client script bypass ho

import re
import frappe
from frappe.model.document import Document

CRITERIA_FIELDS = [
    "quality_of_product",
    "timelines_of_deliveries",
    "communication_and_responsiveness",
    "problem_resolution",
    "consistency_and_reliability",
    "adhere_to_contract_terms",
    "professionalism",
    "overall_satisfaction",
]


def get_points(value):
    if not value:
        return 0
    m = re.search(r"\((\d)\s*pts?\)", value, re.I)
    return int(m.group(1)) if m else 0


def get_rating(total):
    if total >= 36:
        return "Excellent"
    if total >= 26:
        return "Satisfactory"
    if total >= 21:
        return "Average"
    return "Poor"


class SupplierEvaluation(Document):
    def validate(self):
        missing = [f for f in CRITERIA_FIELDS if not self.get(f)]
        if missing and self.docstatus == 1:
            frappe.throw("All 8 criteria must be scored before submission.")

        total = sum(get_points(self.get(f)) for f in CRITERIA_FIELDS)
        self.total_score = total
        self.percentage = round(total / 40 * 100, 1)
        self.rating = get_rating(total) if not missing else ""

