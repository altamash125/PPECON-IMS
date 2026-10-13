import secrets

import frappe
from frappe.utils import escape_html, get_url, getdate, now

# =====================================================================
# Config
# =====================================================================

CLIENT_SURVEY_RECIPIENTS = [
    "bdm@ppecon.com",
    "jquebral@ppecon.com",
    "georges.makdissi@ppecon.com",
    "altamash@ppecon.com"
]

# HR Manager role users + these always receive employee survey notifications
EMPLOYEE_SURVEY_EXTRA_RECIPIENTS = ["jquebral@ppecon.com"]

CLIENT_RATING_LABELS = {
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

EMPLOYEE_RATING_LABELS = {
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

EMPLOYEE_TEXT_FIELDS = {
    "recommendations": "Recommendations",
    "what_you_like": "What they like",
    "areas_improvement": "Areas needing improvement",
    "suggestions_satisfaction": "Suggestions for employee satisfaction",
    "professional_growth_support": "Support for professional growth",
}


# =====================================================================
# Shared email helpers (all user-entered text is HTML-escaped)
# =====================================================================

def _safe(text):
    """Escape user text for HTML email and keep line breaks."""
    if not text:
        return "-"
    return escape_html(str(text)).replace("\n", "<br>")


def _rating_color(val):
    if val in ("4", "5"):
        return "#38a169"
    if val == "3":
        return "#d69e2e"
    if val in ("1", "2"):
        return "#e53e3e"
    return "#718096"


def _ratings_table_html(doc, labels):
    rows = ""
    for field, label in labels.items():
        val = doc.get(field) or "-"
        rows += f"""
        <tr>
            <td style="padding:6px 10px;border:1px solid #e2e8f0;font-size:13px;">{escape_html(label)}</td>
            <td style="padding:6px 10px;border:1px solid #e2e8f0;font-size:13px;text-align:center;font-weight:bold;color:{_rating_color(val)};">{escape_html(val)}</td>
        </tr>"""
    return f"""
    <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">Ratings Summary</h3>
    <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
        <tr style="background:#f7f9fc;">
            <th style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;text-align:left;">Question</th>
            <th style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;">Rating</th>
        </tr>
        {rows}
    </table>"""


def _low_rating_alert_html(doc, labels):
    low = [label for field, label in labels.items() if doc.get(field) in ("1", "2")]
    if not low:
        return ""
    items = "".join(f"<li>{escape_html(l)}</li>" for l in low)
    return f"""
    <div style="background:#fff5f5;border-left:4px solid #e53e3e;padding:12px 16px;margin:15px 0;border-radius:4px;">
        <strong style="color:#c53030;">&#9888; Attention needed — low ratings on:</strong>
        <ul style="margin:8px 0 0;padding-left:20px;color:#742a2a;font-size:13px;">{items}</ul>
    </div>"""


def _text_block_html(title, text):
    return f"""
    <h3 style="font-size:14px;color:#1e4e8c;border-bottom:2px solid #e2e8f0;padding-bottom:6px;">{escape_html(title)}</h3>
    <p style="font-size:13px;color:#333;background:#f9fafb;padding:12px;border-radius:6px;">{_safe(text)}</p>"""


def _email_shell(title, subtitle, body_html):
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#1e4e8c,#2b6cb0);color:#fff;padding:20px 25px;border-radius:8px 8px 0 0;">
            <h2 style="margin:0;font-size:18px;">{escape_html(title)}</h2>
            <p style="margin:5px 0 0;font-size:13px;opacity:0.9;">{escape_html(subtitle)}</p>
        </div>
        <div style="border:1px solid #e2e8f0;border-top:none;padding:20px 25px;border-radius:0 0 8px 8px;">
            {body_html}
        </div>
    </div>"""


def _view_in_erp_button(route):
    return f"""
    <p style="margin-top:20px;">
        <a href="{get_url()}/app/{route}"
           style="background:#2b6cb0;color:#fff;padding:9px 20px;border-radius:20px;text-decoration:none;font-size:13px;">
           View in ERP
        </a>
    </p>"""


def _feedback_link_error(status, validity_end_date):
    """Return an error message if a client feedback link can no longer be used."""
    if status == "Completed":
        return "This feedback has already been submitted. Thank you!"
    if validity_end_date and getdate(validity_end_date) < getdate():
        return "This feedback link has expired."
    return None


# =====================================================================
# CLIENT SATISFACTION SURVEY (token based, pre-filled by Sales/Marketing)
# =====================================================================

@frappe.whitelist()
def send_feedback_request(docname):
    doc = frappe.get_doc("Client Satisfaction Survey", docname)
    doc.check_permission("write")

    if doc.status == "Completed":
        frappe.throw("This feedback request is already completed.")
    if not doc.email:
        frappe.throw("Customer Email is required to send the feedback request.")
    if doc.validity_end_date and getdate(doc.validity_end_date) < getdate():
        frappe.throw("Validity End Date has already passed. Please extend it first.")

    token = doc.response_token or secrets.token_urlsafe(24)
    link = f"{get_url()}/client_satisfaction?token={token}"

    sender_user = frappe.get_doc("User", frappe.session.user)
    sender_name = sender_user.full_name or frappe.session.user
    sender_email = sender_user.email or frappe.session.user

    intro = doc.description or (
        "Please take a few minutes to give us feedback about our service "
        "by filling in this short Customer Feedback Form."
    )

    message = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#2d3748;">
        <p>Hi {escape_html(doc.client_name or '')},</p>
        <p>{_safe(intro)}</p>
        <p>We are conducting this research in order to measure your level of satisfaction with the quality of our service. We thank you for your participation.</p>
        <p>Please click here to fill the survey: <a href="{link}" style="color:#2b6cb0;">click here</a></p>
        <p>Thanks,<br>{escape_html(sender_name)}.<br>On behalf of:<br>{escape_html(sender_email)}</p>
    </div>
    """

    frappe.sendmail(
        recipients=[doc.email],
        sender=sender_email,
        subject=f"{doc.questionnaire_title or 'Customer Satisfaction Survey'} - Pioneer Projects Executer Customer Feedback",
        message=message,
        now=True,
    )

    # Only mark as In Progress after the email was actually sent
    doc.db_set({"response_token": token, "status": "In Progress"})
    frappe.db.commit()
    return {"status": "success"}


@frappe.whitelist(allow_guest=True)
def get_feedback_details(token):
    doc = frappe.db.get_value(
        "Client Satisfaction Survey",
        {"response_token": token},
        ["name", "client_name", "project", "project_type", "status", "validity_end_date"],
        as_dict=True,
    )
    if not doc:
        frappe.local.response["http_status_code"] = 404
        return {"status": "error", "message": "Invalid or expired link."}

    error = _feedback_link_error(doc.status, doc.validity_end_date)
    if error:
        return {"status": "error", "message": error}

    return {"status": "success", "data": doc}


@frappe.whitelist(allow_guest=True)
def submit_feedback_response(**kwargs):
    token = kwargs.get("token")
    if not token:
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": "Missing token."}

    docname = frappe.db.get_value("Client Satisfaction Survey", {"response_token": token}, "name")
    if not docname:
        frappe.local.response["http_status_code"] = 404
        return {"status": "error", "message": "Invalid or expired link."}

    # Row lock: stops double-submit / parallel submit
    status, validity_end_date = frappe.db.get_value(
        "Client Satisfaction Survey", docname, ["status", "validity_end_date"], for_update=True
    )
    error = _feedback_link_error(status, validity_end_date)
    if error:
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": error}

    allowed_fields = list(CLIENT_RATING_LABELS) + ["feedback"]

    try:
        doc = frappe.get_doc("Client Satisfaction Survey", docname)
        for field in allowed_fields:
            if field in kwargs:
                doc.set(field, kwargs.get(field))

        doc.status = "Completed"
        doc.responded_on = now()
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except frappe.ValidationError as e:
        frappe.db.rollback()
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": f"Please check your answers. ({e})"}
    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Client Feedback Submission Failed")
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": "Something went wrong. Please try again later."}

    # Emails are best-effort: never fail the submission because of them
    try:
        send_notification_email(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Client Satisfaction Survey Email Failed")

    try:
        send_thankyou_email(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Client Thank You Email Failed")

    return {"status": "success"}


def send_notification_email(doc):
    """Internal notification when a client completes the survey."""
    details = [
        ("Client Name", doc.client_name),
        ("Project Name", doc.project),
        ("Project Type", doc.project_type),
        ("Submitted By", doc.signature_name),
        ("Email", doc.email),
        ("Mobile", doc.mobile),
    ]
    details_rows = "".join(
        f"""<tr>
            <td style="padding:6px 0;font-size:13px;color:#555;width:150px;"><strong>{escape_html(label)}</strong></td>
            <td style="padding:6px 0;font-size:13px;">{_safe(value)}</td>
        </tr>"""
        for label, value in details
    )

    body = f"""
    <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">{details_rows}</table>
    {_low_rating_alert_html(doc, CLIENT_RATING_LABELS)}
    {_ratings_table_html(doc, CLIENT_RATING_LABELS)}
    {_text_block_html("Feedback", doc.feedback or "No additional feedback provided.")}
    {_view_in_erp_button("client-satisfaction-survey/" + doc.name)}
    """

    frappe.sendmail(
        recipients=CLIENT_SURVEY_RECIPIENTS,
        subject=f"New Client Satisfaction Survey — {doc.project or doc.client_name} ({doc.name})",
        message=_email_shell(
            "New Client Satisfaction Survey Submitted", f"Record: {doc.name}", body
        ),
        now=True,
    )


def send_thankyou_email(doc):
    if not doc.email:
        return
    message = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#2d3748;">
        <p>Dear {escape_html(doc.client_name or '')},</p>
        <p>Thank you for taking the time to complete our Customer Satisfaction Survey for <strong>{escape_html(doc.project or '')}</strong>. Your feedback is greatly appreciated and helps us continue to improve our service.</p>
        <p>Best regards,<br>Pioneer Projects Executer</p>
    </div>
    """
    frappe.sendmail(
        recipients=[doc.email],
        subject="Thank You for Your Feedback - Pioneer Projects Executer",
        message=message,
        now=True,
    )


# =====================================================================
# EMPLOYEE SATISFACTION SURVEY (anonymous, one-time personal link)
# =====================================================================

@frappe.whitelist(allow_guest=True)
def validate_employee_survey_token(token):
    inv = frappe.db.get_value(
        "Employee Survey Invitation", {"token": token}, ["name", "used"], as_dict=True
    )
    if not inv:
        frappe.local.response["http_status_code"] = 404
        return {"status": "error", "message": "This survey link is invalid."}
    if inv.used:
        return {
            "status": "error",
            "message": "This survey link has already been used. Thank you for your response!",
        }
    return {"status": "success"}


@frappe.whitelist(allow_guest=True)
def submit_employee_satisfaction(**kwargs):
    token = kwargs.get("token")
    if not token:
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": "Invalid survey link."}

    inv_name = frappe.db.get_value("Employee Survey Invitation", {"token": token}, "name")
    if not inv_name:
        frappe.local.response["http_status_code"] = 404
        return {"status": "error", "message": "Invalid survey link."}

    # Row lock: stops double-click / parallel submit with the same link
    used = frappe.db.get_value("Employee Survey Invitation", inv_name, "used", for_update=True)
    if used:
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": "This survey link has already been used."}

    allowed_fields = list(EMPLOYEE_RATING_LABELS) + list(EMPLOYEE_TEXT_FIELDS)
    doc_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    doc_data["doctype"] = "Employee Satisfaction Survey"

    try:
        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)
        # update_modified=False so the invitation timestamp can't be matched to the response
        frappe.db.set_value(
            "Employee Survey Invitation", inv_name, "used", 1, update_modified=False
        )
        frappe.db.commit()
    except frappe.MandatoryError as e:
        frappe.db.rollback()
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": f"Please answer all required questions. ({e})"}
    except frappe.ValidationError as e:
        frappe.db.rollback()
        frappe.local.response["http_status_code"] = 400
        return {"status": "error", "message": f"Please check your answers. ({e})"}
    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Employee Survey Submission Failed")
        frappe.local.response["http_status_code"] = 500
        return {"status": "error", "message": "Something went wrong. Please try again later."}

    try:
        send_employee_survey_email(doc)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Employee Survey Email Failed")

    return {"status": "success", "name": doc.name}


def get_hr_manager_emails():
    users = frappe.get_all(
        "Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"],
    )
    emails = list(EMPLOYEE_SURVEY_EXTRA_RECIPIENTS)
    for u in users:
        user = frappe.db.get_value("User", u.parent, ["email", "enabled"], as_dict=True)
        if user and user.enabled and user.email:
            emails.append(user.email)
    return list(set(emails))


def send_employee_survey_email(doc):
    """HR notification for a completed (anonymous) employee survey."""
    recipients = get_hr_manager_emails()

    text_blocks = "".join(
        _text_block_html(label, doc.get(field)) for field, label in EMPLOYEE_TEXT_FIELDS.items()
    )

    body = f"""
    {_low_rating_alert_html(doc, EMPLOYEE_RATING_LABELS)}
    {_ratings_table_html(doc, EMPLOYEE_RATING_LABELS)}
    {text_blocks}
    {_view_in_erp_button("employee-satisfaction-survey/" + doc.name)}
    """

    frappe.sendmail(
        recipients=recipients,
        subject=f"New Employee Satisfaction Survey Submitted ({doc.name})",
        message=_email_shell(
            "New Employee Satisfaction Survey Submitted", f"Record: {doc.name} (Anonymous)", body
        ),
        now=True,
    )


@frappe.whitelist()
def send_employee_survey_links(survey_round):
    frappe.only_for(["HR Manager", "System Manager"])

    survey_round = (survey_round or "").strip()
    if not survey_round:
        frappe.throw("Survey Round is required.")

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "company_email", "personal_email", "user_id"],
    )

    sent, no_email, already_used, failed = 0, 0, 0, 0
    first_error = None

    for emp in employees:
        email = emp.company_email or emp.user_id or emp.personal_email
        if not email:
            no_email += 1
            continue

        existing = frappe.db.get_value(
            "Employee Survey Invitation",
            {"employee_email": email, "survey_round": survey_round},
            ["name", "token", "used"],
            as_dict=True,
        )

        if existing and existing.used:
            already_used += 1
            continue

        if existing:
            token = existing.token  # resend with the same link
        else:
            token = secrets.token_urlsafe(24)
            frappe.get_doc(
                {
                    "doctype": "Employee Survey Invitation",
                    "employee_email": email,
                    "survey_round": survey_round,
                    "token": token,
                }
            ).insert(ignore_permissions=True)
            # Commit BEFORE emailing, so a sent link always exists in the database
            frappe.db.commit()

        link = f"{get_url()}/employee_satisfaction?token={token}"
        message = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#2d3748;">
            <p>Dear {escape_html(emp.employee_name or '')},</p>
            <p>You are invited to take part in the <strong>Employee Satisfaction Survey</strong> at Pioneer Projects Executer Company.</p>
            <p>The survey is <strong>completely anonymous</strong> and takes only a few minutes. This is a personal, one-time link and can be used only once.</p>
            <p><a href="{link}" style="background:#2b6cb0;color:#fff;padding:10px 22px;border-radius:20px;text-decoration:none;">Start Survey</a></p>
            <p>Thank you,<br>Human Resources</p>
        </div>
        """
        try:
            frappe.sendmail(
                recipients=[email],
                subject="Employee Satisfaction Survey - Your Personal Link",
                message=message,
                now=True,
            )
            sent += 1
        except Exception as e:
            failed += 1
            first_error = first_error or str(e)
            frappe.log_error(frappe.get_traceback(), "Employee Survey Link Email Failed")

    return {
        "sent": sent,
        "no_email": no_email,
        "already_used": already_used,
        "failed": failed,
        "first_error": first_error,
    }