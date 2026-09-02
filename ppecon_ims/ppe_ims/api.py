import frappe

@frappe.whitelist(allow_guest=True)
def submit_client_satisfaction(**kwargs):
    allowed_fields = [
        "client_name", "project", "project_type",
        "design_requirements_rating", "coordination_design_operation_rating",
        "hse_commitment_rating", "project_duration_rating", "weekly_reports_rating",
        "functionality_rating", "quality_compliance_rating", "snags_taking_rating", "snags_closing_rating",
        "delivery_rating", "warranty_aftersales_rating", "work_again_rating", "recommend_rating",
        "comm_tender_rating", "comm_proposal_rating", "comm_design_prep_rating", "comm_execution_rating",
        "comm_snags_handover_rating", "comm_aftersales_rating", "comm_invoicing_rating", "material_delivery_rating",
        "feedback", "signature_name", "email", "mobile"
    ]
    doc_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    doc_data["doctype"] = "Client Satisfaction Survey"

    doc = frappe.get_doc(doc_data)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "name": doc.name}
