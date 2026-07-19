# # ---------------------------------------------------------------------------
# # PPECON IMS Portal — backend for /ims
# # Location: ppecon_ims/www/ims/index.py
# # ---------------------------------------------------------------------------

# import frappe


# def get_context(context):
#     if frappe.session.user == "Guest":
#         frappe.throw(frappe._("Please login to access IMS Portal"), frappe.PermissionError)

#     context.no_cache = 1
#     return context


# @frappe.whitelist()
# def get_dashboard_counts():
#     """Dashboard card counts. safe_count() ki wajah se page kabhi break
#     nahi hoga — jo DocType abhi nahi bana, wahan 0 aayega."""

#     def safe_count(doctype, filters=None):
#         try:
#             return frappe.db.count(doctype, filters or {})
#         except Exception:
#             return 0

#     return {
#         # NOTE: apne actual DocType names ke mutabiq adjust karein
#         "risks": safe_count("Risk Opportunity", {"status": ["!=", "Closed"]}),
#         "contexts": safe_count("Context Of Organisation", {"status": "Approved"}),
#         "audit_findings": safe_count("Audit Finding", {"status": ["!=", "Closed"]}),
#         "nc": safe_count("Non Conformance", {"status": ["!=", "Closed"]}),
#     }



# ---------------------------------------------------------------------------
# PPECON IMS Portal — backend for /ims
# Location: ppecon_ims/www/ims/index.py
# ---------------------------------------------------------------------------

import frappe


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Please login to access IMS Portal"), frappe.PermissionError)

	context.no_cache = 1
	return context


@frappe.whitelist()
def get_dashboard_counts():
	"""
	Dashboard card counts, broken down by docstatus (Draft / Submitted / Cancelled).

	safe_status_count() ki wajah se page kabhi break nahi hoga — jo DocType
	abhi nahi bana ya submittable nahi hai, wahan bhi safe defaults aayenge.

	docstatus mapping (Frappe standard):
	    0 = Draft
	    1 = Submitted
	    2 = Cancelled
	"""

	def safe_status_count(doctype, base_filters=None):
		result = {"draft": 0, "submitted": 0, "cancelled": 0, "total": 0}
		try:
			if not frappe.db.exists("DocType", doctype):
				return result

			filters = dict(base_filters or {})
			rows = frappe.db.get_all(
				doctype,
				filters=filters,
				fields=["docstatus", "count(name) as count"],
				group_by="docstatus",
			)
			for r in rows:
				result["total"] += r.count
				if r.docstatus == 0:
					result["draft"] = r.count
				elif r.docstatus == 1:
					result["submitted"] = r.count
				elif r.docstatus == 2:
					result["cancelled"] = r.count
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"IMS Dashboard Count Error: {doctype}")
		return result

	return {
		# NOTE: apne actual DocType names / filters ke mutabiq adjust karein
		"risks": safe_status_count("Risk Opportunity", {"status": ["!=", "Closed"]}),
		"contexts": safe_status_count("Context Of Organisation", {"status": "Approved"}),
		"audit_findings": safe_status_count("Audit Finding", {"status": ["!=", "Closed"]}),
		"nc": safe_status_count("Non Conformance", {"status": ["!=", "Closed"]}),
	}