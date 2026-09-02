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

    if not doc_data.get("client_name"):
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": "Client Name is required."}

    if not doc_data.get("project"):
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": "Project Name is required."}

    try:
        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "name": doc.name}
    except frappe.MandatoryError as e:
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": f"Please fill all required fields. ({e})"}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Client Satisfaction Survey Submission Failed")
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": "Something went wrong. Please try again later."}







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

    if not doc_data.get("client_name"):
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": "Client Name is required."}

    if not doc_data.get("project"):
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": "Project Name is required."}

    try:
        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            send_notification_email(doc)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Client Satisfaction Survey Email Failed")

        return {"status": "success", "name": doc.name}
    except frappe.MandatoryError as e:
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": f"Please fill all required fields. ({e})"}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Client Satisfaction Survey Submission Failed")
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": "Something went wrong. Please try again later."}


def send_notification_email(doc):
    recipients = ["bdm@ppecon.com", "jquebral@ppecon.com", "georges.makdissi@ppecon.com"]

    rating_labels = {
        "design_requirements_rating": "Design requirements and expectations",
        "coordination_design_operation_rating": "Coordination between Design & Operation",
        "hse_commitment_rating": "HSE commitment during execution",
        "project_duration_rating": "Project duration",
        "weekly_reports_rating": "Weekly progress reports",
        "functionality_rating": "Functionality of the completed design",
        "quality_compliance_rating": "Quality compliance with approved design",
        "snags_taking_rating": "Taking of snags",
        "snags_closing_rating": "Closing of snags",
        "delivery_rating": "Project delivery",
        "warranty_aftersales_rating": "Warranty and after sales services",
        "work_again_rating": "Potential to work with us again",
        "recommend_rating": "Potential to recommend us to others",
        "comm_tender_rating": "Communication - tender launching phase",
        "comm_proposal_rating": "Communication - proposal negotiation phase",
        "comm_design_prep_rating": "Communication - design preparation phase",
        "comm_execution_rating": "Communication - execution phase",
        "comm_snags_handover_rating": "Communication - snags & handover phase",
        "comm_aftersales_rating": "Communication - after sales service phase",
        "comm_invoicing_rating": "Communication - invoicing and collection phase",
        "material_delivery_rating": "Material delivery time & quality",
    }

    def rating_row(field, label):
        val = doc.get(field) or "-"
        color = "#38a169" if val in ("4", "5") else ("#d69e2e" if val == "3" else ("#e53e3e" if val in ("1", "2") else "#718096"))
        return f"""
        <tr>
            <td style="padding:6px 10px;border:1px solid #e2e8f0;font-size:13px;">{label}</td>
            <td style="padding:6px 10px;border:1px solid #e2e8f0;font-size:13px;text-align:center;font-weight:bold;color:{color};">{val}</td>
        </tr>"""

    ratings_html = "".join(rating_row(f, l) for f, l in rating_labels.items())

    low_ratings = [l for f, l in rating_labels.items() if doc.get(f) in ("1", "2")]
    alert_html = ""
    if low_ratings:
        items = "".join(f"<li>{l}</li>" for l in low_ratings)
        alert_html = f"""
        <div style="background:#fff5f5;border-left:4px solid #e53e3e;padding:12px 16px;margin:15px 0;border-radius:4px;">
            <strong style="color:#c53030;">⚠ Attention needed — low ratings on:</strong>
            <ul style="margin:8px 0 0;padding-left:20px;color:#742a2a;font-size:13px;">{items}</ul>
        </div>"""

    message = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#1e4e8c,#2b6cb0);color:#fff;padding:20px 25px;border-radius:8px 8px 0 0;">
            <h2 style="margin:0;font-size:18px;">New Client Satisfaction Survey Submitted</h2>
            <p style="margin:5px 0 0;font-size:13px;opacity:0.9;">Record: {doc.name}</p>
        </div>
        <div style="border:1px solid #e2e8f0;border-top:none;padding:20px 25px;border-radius:0 0 8px 8px;">
            <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                <tr><td style="padding:6px 0;font-size:13px;color:#555;width:150px;"><strong>Client Name</strong></td><td style="padding:6px 0;font-size:13px;">{doc.client_name or '-'}</td></tr>
                <tr><td style="padding:6px 0;font-size:13px;color:#555;"><strong>Project Name</strong></td><td style="padding:6px 0;font-size:13px;">{doc.project or '-'}</td></tr>
                <tr><td style="padding:6px 0;font-size:13px;color:#555;"><strong>Project Type</strong></td><td style="padding:6px 0;font-size:13px;">{doc.project_type or '-'}</td></tr>
                <tr><td style="padding:6px 0;font-size:13px;color:#555;"><strong>Submitted By</strong></td><td style="padding:6px 0;font-size:13px;">{doc.signature_name or '-'}</td></tr>
                <tr><td style="padding:6px 0;font-size:13px;color:#555;"><strong>Email</strong></td><td style="padding:6px 0;font-size:13px;">{doc.email or '-'}</td></tr>
                <tr><td style="padding:6px 0;font-size:13px;color:#555;"><strong>Mobile</strong></td><td style="padding:6px 0;font-size:13px;">{doc.mobile or '-'}</td></tr>
            </table>

            {alert_html}

            <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">Ratings Summary</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                <tr style="background:#f7f9fc;">
                    <th style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;text-align:left;">Question</th>
                    <th style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;">Rating</th>
                </tr>
                {ratings_html}
            </table>

            <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">Feedback</h3>
            <p style="font-size:13px;color:#333;background:#f9fafb;padding:12px;border-radius:6px;">{doc.feedback or 'No additional feedback provided.'}</p>

            <p style="margin-top:20px;">
                <a href="{frappe.utils.get_url()}/app/client-satisfaction-survey/{doc.name}"
                   style="background:#2b6cb0;color:#fff;padding:9px 20px;border-radius:20px;text-decoration:none;font-size:13px;">
                   View in ERP
                </a>
            </p>
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=f"New Client Satisfaction Survey — {doc.project or doc.client_name} ({doc.name})",
        message=message,
        now=True,
    )

















# Employee Survey Submission API

@frappe.whitelist(allow_guest=True)
def submit_employee_satisfaction(**kwargs):
    allowed_fields = [
        "we_comfortable_rating", "we_clean_safe_rating", "we_resources_rating",
        "js_role_responsibilities_rating", "js_personal_achievement_rating", "js_motivated_rating",
        "ml_supported_manager_rating", "ml_communication_rating", "ml_feedback_rating",
        "cb_compensation_rating", "cb_competitive_benefits_rating",
        "cg_opportunities_rating", "cg_training_rating", "cg_advancement_rating",
        "wlb_good_balance_rating", "wlb_flexible_schedule_rating",
        "recommendations", "what_you_like", "areas_improvement",
        "suggestions_satisfaction", "professional_growth_support"
    ]
    doc_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    doc_data["doctype"] = "Employee Satisfaction Survey"

    try:
        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            send_employee_survey_email(doc)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Employee Survey Email Failed")

        return {"status": "success", "name": doc.name}
    except frappe.MandatoryError as e:
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": f"Please answer all required questions. ({e})"}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Employee Survey Submission Failed")
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": "Something went wrong. Please try again later."}




def get_hr_manager_emails():
    users = frappe.get_all(
        "Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"]
    )
    emails = []
    for u in users:
        user_doc = frappe.db.get_value("User", u.parent, ["email", "enabled"], as_dict=True)
        if user_doc and user_doc.enabled and user_doc.email:
            emails.append(user_doc.email)

    emails.append("jquebral@ppecon.com")
    return list(set(emails))


def send_employee_survey_email(doc):
    recipients = get_hr_manager_emails()
    if not recipients:
        frappe.log_error("No users with HR Manager role found to notify.", "Employee Survey Email Failed")
        return
    
    rating_labels = {
        "we_comfortable_rating": "Comfortable in work environment",
        "we_clean_safe_rating": "Workplace clean and safe",
        "we_resources_rating": "Resources and equipment adequate",
        "js_role_responsibilities_rating": "Satisfied with role and responsibilities",
        "js_personal_achievement_rating": "Sense of personal achievement",
        "js_motivated_rating": "Motivated to do best work",
        "ml_supported_manager_rating": "Supported by manager/supervisor",
        "ml_communication_rating": "Management communicates effectively",
        "ml_feedback_rating": "Receives regular performance feedback",
        "cb_compensation_rating": "Satisfied with compensation",
        "cb_competitive_benefits_rating": "Benefits competitive vs. other employers",
        "cg_opportunities_rating": "Opportunities for professional development",
        "cg_training_rating": "Satisfied with training provided",
        "cg_advancement_rating": "Potential for career advancement",
        "wlb_good_balance_rating": "Good work-life balance",
        "wlb_flexible_schedule_rating": "Company flexible with schedule",
    }

    def rating_row(field, label):
        val = doc.get(field) or "-"
        color = "#38a169" if val in ("4", "5") else ("#d69e2e" if val == "3" else "#e53e3e")
        return f"""<tr>
            <td style="padding:6px 10px;border:1px solid #e2e8f0;font-size:13px;">{label}</td>
            <td style="padding:6px 10px;border:1px solid #e2e8f0;font-size:13px;text-align:center;font-weight:bold;color:{color};">{val}</td>
        </tr>"""

    ratings_html = "".join(rating_row(f, l) for f, l in rating_labels.items())

    low_ratings = [l for f, l in rating_labels.items() if doc.get(f) in ("1", "2")]
    alert_html = ""
    if low_ratings:
        items = "".join(f"<li>{l}</li>" for l in low_ratings)
        alert_html = f"""<div style="background:#fff5f5;border-left:4px solid #e53e3e;padding:12px 16px;margin:15px 0;border-radius:4px;">
            <strong style="color:#c53030;">⚠ Attention needed — low ratings on:</strong>
            <ul style="margin:8px 0 0;padding-left:20px;color:#742a2a;font-size:13px;">{items}</ul>
        </div>"""

    message = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#1e4e8c,#2b6cb0);color:#fff;padding:20px 25px;border-radius:8px 8px 0 0;">
            <h2 style="margin:0;font-size:18px;">New Employee Satisfaction Survey Submitted</h2>
            <p style="margin:5px 0 0;font-size:13px;opacity:0.9;">Record: {doc.name} (Anonymous)</p>
        </div>
        <div style="border:1px solid #e2e8f0;border-top:none;padding:20px 25px;border-radius:0 0 8px 8px;">
            {alert_html}
            <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">Ratings Summary</h3>
            <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                <tr style="background:#f7f9fc;">
                    <th style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;text-align:left;">Question</th>
                    <th style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;">Rating</th>
                </tr>
                {ratings_html}
            </table>
            <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">Recommendations</h3>
            <p style="font-size:13px;color:#333;background:#f9fafb;padding:12px;border-radius:6px;">{doc.recommendations or '-'}</p>
            <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">What they like</h3>
            <p style="font-size:13px;color:#333;background:#f9fafb;padding:12px;border-radius:6px;">{doc.what_you_like or '-'}</p>
            <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">Areas needing improvement</h3>
            <p style="font-size:13px;color:#333;background:#f9fafb;padding:12px;border-radius:6px;">{doc.areas_improvement or '-'}</p>
            <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">Suggestions for employee satisfaction</h3>
            <p style="font-size:13px;color:#333;background:#f9fafb;padding:12px;border-radius:6px;">{doc.suggestions_satisfaction or '-'}</p>
            <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">Support for professional growth</h3>
            <p style="font-size:13px;color:#333;background:#f9fafb;padding:12px;border-radius:6px;">{doc.professional_growth_support or '-'}</p>
            <p style="margin-top:20px;">
                <a href="{frappe.utils.get_url()}/app/employee-satisfaction-survey/{doc.name}"
                   style="background:#2b6cb0;color:#fff;padding:9px 20px;border-radius:20px;text-decoration:none;font-size:13px;">
                   View in ERP
                </a>
            </p>
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=f"New Employee Satisfaction Survey Submitted ({doc.name})",
        message=message,
        now=True,
    )