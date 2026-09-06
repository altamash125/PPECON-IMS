# =========================================================================
#  ppecon_ims/www/ims/index.py
#  IMS portal dashboard backend  (v4.0)
#  Sections: IMS/ISO · Quality Objectives · Estimation · HSE · CRM · Procurement
# =========================================================================
import frappe
from frappe.utils import add_months, add_days, getdate, today, flt

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/ims"
        raise frappe.Redirect
    context.no_cache = 1
    return context


# =========================================================================
#  PERIOD HELPERS
# =========================================================================
def _resolve_period(period=None, from_date=None, to_date=None):
    t = getdate(today())

    if from_date and to_date:
        f, e = getdate(from_date), getdate(to_date)
        return (e, f) if f > e else (f, e)

    period = (period or "this_year").lower()

    if period == "this_month":
        start, end = t.replace(day=1), t
    elif period == "last_month":
        start = getdate(add_months(t, -1)).replace(day=1)
        end = add_days(t.replace(day=1), -1)
    elif period == "this_quarter":
        start = t.replace(month=3 * ((t.month - 1) // 3) + 1, day=1)
        end = t
    elif period == "last_quarter":
        this_q = t.replace(month=3 * ((t.month - 1) // 3) + 1, day=1)
        start = getdate(add_months(this_q, -3))
        end = add_days(this_q, -1)
    elif period == "last_6_months":
        start = getdate(add_months(t.replace(day=1), -5))
        end = t
    elif period == "last_year":
        start = t.replace(year=t.year - 1, month=1, day=1)
        end = t.replace(year=t.year - 1, month=12, day=31)
    elif period == "all_time":
        start, end = getdate("2000-01-01"), t
    else:
        start, end = t.replace(month=1, day=1), t

    return start, end


def _month_buckets(start, end, max_points=12):
    out = []
    cur = getdate(start).replace(day=1)
    last = getdate(end).replace(day=1)
    guard = 0
    while cur <= last and guard < 600:
        nxt = getdate(add_months(cur, 1))
        out.append((cur.strftime("%b %Y"), cur, nxt))
        cur = nxt
        guard += 1
    return out[-max_points:] if len(out) > max_points else out


# =========================================================================
#  GENERIC HELPERS
# =========================================================================
def _exists(doctype):
    try:
        return bool(frappe.db.exists("DocType", doctype))
    except Exception:
        return False


def _has_field(doctype, field):
    try:
        return _exists(doctype) and frappe.get_meta(doctype).has_field(field)
    except Exception:
        return False


def _safe_count(doctype, filters=None):
    try:
        if not _exists(doctype):
            return 0
        return frappe.db.count(doctype, filters or {})
    except Exception:
        return 0


def _first_existing_doctype(candidates):
    """Return the first doctype name from candidates that actually exists."""
    for d in candidates:
        if _exists(d):
            return d
    return None


def _date_field(doctype):
    for f in ("transaction_date", "posting_date", "schedule_date", "date"):
        if _has_field(doctype, f):
            return f
    return "creation"


def _group_by(doctype, field, start=None, end=None, limit=15, extra=""):
    if not _has_field(doctype, field):
        return []
    try:
        params = {}
        where = "docstatus < 2"
        if start and end:
            df = _date_field(doctype)
            if df == "creation":
                where += " AND `creation` >= %(start)s AND `creation` < %(end_x)s"
                params = {"start": start, "end_x": add_days(getdate(end), 1)}
            else:
                where += " AND `{df}` BETWEEN %(start)s AND %(end)s".format(df=df)
                params = {"start": start, "end": end}
        return frappe.db.sql(
            """
            SELECT COALESCE(NULLIF(`{f}`, ''), 'Not Set') AS label, COUNT(*) AS count
            FROM `tab{dt}`
            WHERE {where} {extra}
            GROUP BY COALESCE(NULLIF(`{f}`, ''), 'Not Set')
            ORDER BY count DESC
            LIMIT {lim}
            """.format(f=field, dt=doctype, where=where, extra=extra, lim=int(limit)),
            params, as_dict=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMS group_by %s.%s" % (doctype, field))
        return []


def _count_in_period(doctype, start, end, extra_where=""):
    if not _exists(doctype):
        return 0
    try:
        df = _date_field(doctype)
        end_x = add_days(getdate(end), 1)
        return frappe.db.sql(
            """SELECT COUNT(*) FROM `tab{dt}`
               WHERE docstatus < 2 AND `{df}` >= %s AND `{df}` < %s {extra}"""
            .format(dt=doctype, df=df, extra=extra_where),
            (start, end_x),
        )[0][0]
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMS count_in_period %s" % doctype)
        return 0


def _sum_in_period(doctype, field, start, end, extra_where=""):
    if not _has_field(doctype, field):
        return 0
    try:
        df = _date_field(doctype)
        end_x = add_days(getdate(end), 1)
        return flt(frappe.db.sql(
            """SELECT COALESCE(SUM(`{f}`), 0) FROM `tab{dt}`
               WHERE docstatus = 1 AND `{df}` >= %s AND `{df}` < %s {extra}"""
            .format(f=field, dt=doctype, df=df, extra=extra_where),
            (start, end_x),
        )[0][0])
    except Exception:
        return 0


# =========================================================================
#  COUNTS (top cards)
# =========================================================================
@frappe.whitelist()
def get_dashboard_counts():
    def breakdown(doctype):
        draft = _safe_count(doctype, {"docstatus": 0})
        submitted = _safe_count(doctype, {"docstatus": 1})
        return {"draft": draft, "submitted": submitted, "total": draft + submitted}

    return {
        "risks": breakdown("Risk And Opportunity"),
        "contexts": breakdown("Context Of Organisation"),
        "audit_findings": breakdown("Internal Audit Schedule"),
        "nc": breakdown("Non Conformance"),
    }


# =========================================================================
#  MAIN CHART PAYLOAD
# =========================================================================
@frappe.whitelist()
def get_dashboard_charts(period=None, from_date=None, to_date=None):
    start, end = _resolve_period(period, from_date, to_date)

    cache_key = "ims_dash:%s:%s" % (start, end)
    try:
        cached = frappe.cache().get_value(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    data = {
        "period": {"from": str(start), "to": str(end), "label": period or "this_year"},

        # ---- IMS / ISO ----
        "nc_trend": _trend_count("Non Conformance", start, end),
        "risk_by_status": _risk_by_status(),
        "docs_by_category": _docs_by_category(),
        "employees_by_department": _employees_by_department(),

        # ---- CRM ----
        "lead_by_status": _group_by("Lead", "status", start, end),
        "lead_by_source": _group_by("Lead", "source", start, end, limit=10),
        "opportunity_by_status": _group_by("Opportunity", "status", start, end),
        "opportunity_by_type": _opportunity_by_type(start, end),
        "quotation_by_status": _group_by("Quotation", "status", start, end),
        "quotation_value_trend": _value_trend("Quotation", "base_grand_total", start, end),
        "sales_funnel": _sales_funnel(start, end),

        # ---- ESTIMATION ----
        "estimation_summary": _estimation_summary(start, end),

        # ---- PROCUREMENT ----
        "mr_by_status": _group_by("Material Request", "status", start, end),
        "mr_by_type": _group_by("Material Request", "material_request_type", start, end),
        "sq_by_supplier": _sq_by_supplier(start, end),
        "po_by_status": _group_by("Purchase Order", "status", start, end),
        "po_value_trend": _value_trend("Purchase Order", "base_grand_total", start, end),
        "top_suppliers_by_po": _top_suppliers_by_po(start, end),
        "procurement_funnel": _procurement_funnel(start, end),
        "po_pending_delivery": _po_pending_delivery(),

        # ---- TILES ----
        "summary": _summary_tiles(),
        "crm_summary": _crm_summary(start, end),
        "procurement_summary": _procurement_summary(start, end),
    }

    try:
        frappe.cache().set_value(cache_key, data, expires_in_sec=300)
    except Exception:
        pass

    return data


@frappe.whitelist()
def clear_dashboard_cache():
    try:
        frappe.cache().delete_keys("ims_dash:")
        return {"ok": True}
    except Exception:
        return {"ok": False}


# ---------------------- shared builders ----------------------
def _trend_count(doctype, start, end):
    out = []
    if not _exists(doctype):
        return out
    try:
        df = _date_field(doctype)
        for label, m_start, m_next in _month_buckets(start, end):
            cnt = frappe.db.sql(
                """SELECT COUNT(*) FROM `tab{dt}`
                   WHERE docstatus < 2 AND `{df}` >= %s AND `{df}` < %s"""
                .format(dt=doctype, df=df),
                (m_start, m_next),
            )[0][0]
            out.append({"month": label, "count": cnt})
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMS trend %s" % doctype)
    return out


def _value_trend(doctype, amount_field, start, end):
    out = []
    if not _has_field(doctype, amount_field):
        return out
    try:
        df = _date_field(doctype)
        buckets = _month_buckets(start, end)
        if not buckets:
            return out
        b_start = buckets[0][1]
        b_end = buckets[-1][2]

        rows = frappe.db.sql(
            """SELECT DATE_FORMAT(`{df}`, '%%Y-%%m') AS ym,
                      COALESCE(SUM(`{f}`), 0) AS value, COUNT(*) AS count
               FROM `tab{dt}`
               WHERE docstatus = 1 AND `{df}` >= %s AND `{df}` < %s
               GROUP BY DATE_FORMAT(`{df}`, '%%Y-%%m')"""
            .format(f=amount_field, dt=doctype, df=df),
            (b_start, b_end), as_dict=True,
        )
        lookup = {r.ym: r for r in rows}

        for label, m_start, m_next in buckets:
            key = m_start.strftime("%Y-%m")
            r = lookup.get(key)
            out.append({
                "month": label,
                "value": flt(r.value) if r else 0,
                "count": r.count if r else 0,
            })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMS value_trend %s" % doctype)
    return out


# ---------------------- IMS ----------------------
def _risk_by_status():
    return _group_by("Risk And Opportunity", "status") or \
           _group_by("Risk And Opportunity", "workflow_state")


def _docs_by_category():
    for f in ("document_category", "category", "document_type", "type"):
        rows = _group_by("IMS Documents", f)
        if rows:
            return rows
    return []


def _employees_by_department():
    if not _exists("Employee"):
        return []
    try:
        return frappe.db.sql(
            """SELECT COALESCE(NULLIF(department, ''), 'Not Set') AS label, COUNT(*) AS count
               FROM `tabEmployee` WHERE status = 'Active'
               GROUP BY COALESCE(NULLIF(department, ''), 'Not Set')
               ORDER BY count DESC LIMIT 12""",
            as_dict=True,
        )
    except Exception:
        return []


# ---------------------- CRM ----------------------
def _opportunity_by_type(start, end):
    for f in ("custom_project_type", "project_type", "opportunity_type", "opportunity_from"):
        rows = _group_by("Opportunity", f, start, end, limit=12)
        if rows:
            return rows
    return []


def _sales_funnel(start, end):
    return [
        {"stage": "Leads", "count": _count_in_period("Lead", start, end)},
        {"stage": "Opportunities", "count": _count_in_period("Opportunity", start, end)},
        {"stage": "Quotations", "count": _count_in_period("Quotation", start, end, " AND docstatus = 1")},
        {"stage": "Sales Orders", "count": _count_in_period("Sales Order", start, end, " AND docstatus = 1")},
    ]


def _crm_summary(start, end):
    try:
        open_leads = _safe_count("Lead", {"status": ("not in", ["Converted", "Do Not Contact"])})
        open_opps = _safe_count("Opportunity", {"status": ("in", ["Open", "Replied"])})
        won = _safe_count("Opportunity", {"status": "Converted"}) or _safe_count("Quotation", {"status": "Ordered"})
        lost = _safe_count("Opportunity", {"status": "Lost"}) or _safe_count("Quotation", {"status": "Lost"})
        closed = won + lost
        win_rate = round((flt(won) / closed) * 100, 1) if closed else 0

        open_quote_value = 0
        if _has_field("Quotation", "base_grand_total"):
            open_quote_value = flt(frappe.db.sql(
                """SELECT COALESCE(SUM(base_grand_total), 0) FROM `tabQuotation`
                   WHERE docstatus = 1 AND status NOT IN ('Ordered','Lost','Cancelled')"""
            )[0][0])

        return {
            "open_leads": open_leads,
            "open_opportunities": open_opps,
            "won": won, "lost": lost, "win_rate": win_rate,
            "open_quote_value": open_quote_value,
            "quoted_in_period": _sum_in_period("Quotation", "base_grand_total", start, end),
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMS crm_summary")
        return {}


# ---------------------- ESTIMATION TURNAROUND ----------------------
def _quotation_opportunity_field():
    for f in ("opportunity", "against_opportunity", "custom_opportunity"):
        if _has_field("Quotation", f):
            return f
    return None


def _opportunity_closing_field():
    for f in ("expected_closing", "expected_closing_date"):
        if _has_field("Opportunity", f):
            return f
    return None


def _estimation_yearly():
    """Year-wise on-time vs delayed, across ALL data (ignores the period filter)."""
    field = _quotation_opportunity_field()
    closing = _opportunity_closing_field()
    if not field or not closing:
        return []

    try:
        rows = frappe.db.sql(
            """
            SELECT q.transaction_date, o.`{closing}` AS expected_closing
            FROM `tabQuotation` q
            INNER JOIN `tabOpportunity` o ON o.name = q.`{field}`
            WHERE q.docstatus < 2
              AND o.`{closing}` IS NOT NULL
            """.format(field=field, closing=closing),
            as_dict=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMS estimation_yearly")
        rows = []

    by_year = {}
    for r in rows:
        td = getdate(r.transaction_date)
        ecd = getdate(r.expected_closing)
        y = td.year
        if y not in by_year:
            by_year[y] = {"year": y, "on_time": 0, "delayed": 0}
        if td <= ecd:
            by_year[y]["on_time"] += 1
        else:
            by_year[y]["delayed"] += 1

    return [by_year[y] for y in sorted(by_year.keys())]


def _estimation_summary(start, end):
    """
    On-time vs Delayed quotation submission:
    on-time  = Quotation.transaction_date <= Opportunity.expected_closing
    delayed  = Quotation.transaction_date >  Opportunity.expected_closing
    """
    field = _quotation_opportunity_field()
    closing = _opportunity_closing_field()
    if not field or not closing:
        return {"on_time": 0, "delayed": 0, "no_reference": 0,
                "avg_delay_days": 0, "on_time_pct": 0, "total": 0, "yearly": []}

    try:
        rows = frappe.db.sql(
            """
            SELECT q.name, q.transaction_date, o.`{closing}` AS expected_closing
            FROM `tabQuotation` q
            INNER JOIN `tabOpportunity` o ON o.name = q.`{field}`
            WHERE q.docstatus < 2
              AND q.transaction_date BETWEEN %s AND %s
              AND o.`{closing}` IS NOT NULL
            """.format(field=field, closing=closing),
            (start, end), as_dict=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMS estimation_summary")
        rows = []

    on_time, delayed, delay_days = 0, 0, []
    for r in rows:
        td, ecd = getdate(r.transaction_date), getdate(r.expected_closing)
        if td <= ecd:
            on_time += 1
        else:
            delayed += 1
            delay_days.append((td - ecd).days)

    total_quotations = _count_in_period("Quotation", start, end, " AND docstatus < 2")
    no_reference = max(total_quotations - len(rows), 0)
    total = on_time + delayed

    return {
        "on_time": on_time,
        "delayed": delayed,
        "no_reference": no_reference,
        "total": total,
        "avg_delay_days": round(sum(delay_days) / len(delay_days), 1) if delay_days else 0,
        "on_time_pct": round(on_time / total * 100, 1) if total else 0,
        "yearly": _estimation_yearly(),
    }


# ---------------------- PROCUREMENT ----------------------
def _sq_by_supplier(start, end):
    if not _has_field("Supplier Quotation", "supplier"):
        return []
    try:
        return frappe.db.sql(
            """SELECT COALESCE(NULLIF(supplier, ''), 'Not Set') AS label, COUNT(*) AS count
               FROM `tabSupplier Quotation`
               WHERE docstatus < 2 AND transaction_date BETWEEN %s AND %s
               GROUP BY supplier ORDER BY count DESC LIMIT 10""",
            (start, end), as_dict=True,
        )
    except Exception:
        return []


def _top_suppliers_by_po(start, end):
    if not _has_field("Purchase Order", "base_grand_total"):
        return []
    try:
        rows = frappe.db.sql(
            """SELECT COALESCE(NULLIF(supplier, ''), 'Not Set') AS label,
                      COALESCE(SUM(base_grand_total), 0) AS value, COUNT(*) AS count
               FROM `tabPurchase Order`
               WHERE docstatus = 1 AND transaction_date BETWEEN %s AND %s
               GROUP BY supplier ORDER BY value DESC LIMIT 10""",
            (start, end), as_dict=True,
        )
        for r in rows:
            r["value"] = flt(r["value"])
        return rows
    except Exception:
        return []


def _procurement_funnel(start, end):
    return [
        {"stage": "Material Requests", "count": _count_in_period("Material Request", start, end)},
        {"stage": "RFQs", "count": _count_in_period("Request for Quotation", start, end)},
        {"stage": "Supplier Quotations", "count": _count_in_period("Supplier Quotation", start, end)},
        {"stage": "Purchase Orders", "count": _count_in_period("Purchase Order", start, end, " AND docstatus = 1")},
        {"stage": "Purchase Receipts", "count": _count_in_period("Purchase Receipt", start, end, " AND docstatus = 1")},
    ]


def _po_pending_delivery():
    if not _exists("Purchase Order"):
        return []
    try:
        rows = frappe.db.sql(
            """SELECT status AS label, COUNT(*) AS count,
                      COALESCE(SUM(base_grand_total), 0) AS value
               FROM `tabPurchase Order`
               WHERE docstatus = 1 AND status IN
                     ('To Receive and Bill','To Receive','To Bill','Delivered')
               GROUP BY status ORDER BY count DESC""",
            as_dict=True,
        )
        for r in rows:
            r["value"] = flt(r["value"])
        return rows
    except Exception:
        return []


def _procurement_summary(start, end):
    try:
        open_mr = _safe_count("Material Request",
                              {"docstatus": 1, "status": ("in", ["Pending", "Partially Ordered"])})
        pending_po = _safe_count("Purchase Order",
                                 {"docstatus": 1,
                                  "status": ("in", ["To Receive and Bill", "To Receive", "To Bill"])})
        draft_po = _safe_count("Purchase Order", {"docstatus": 0})
        po_value = _sum_in_period("Purchase Order", "base_grand_total", start, end)
        po_count = _count_in_period("Purchase Order", start, end, " AND docstatus = 1")
        avg_po = round(po_value / po_count, 2) if po_count else 0

        outstanding_payable = 0
        if _has_field("Purchase Invoice", "outstanding_amount"):
            outstanding_payable = flt(frappe.db.sql(
                """SELECT COALESCE(SUM(outstanding_amount), 0) FROM `tabPurchase Invoice`
                   WHERE docstatus = 1 AND outstanding_amount > 0"""
            )[0][0])

        suppliers = _safe_count("Supplier", {"disabled": 0}) if _has_field("Supplier", "disabled") \
            else _safe_count("Supplier")

        return {
            "open_mr": open_mr,
            "pending_po": pending_po,
            "draft_po": draft_po,
            "po_value": po_value,
            "po_count": po_count,
            "avg_po": avg_po,
            "active_suppliers": suppliers,
            "outstanding_payable": outstanding_payable,
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMS procurement_summary")
        return {}


def _summary_tiles():
    return {
        "active_employees": _safe_count("Employee", {"status": "Active"}),
        "departments": _safe_count("Department"),
        "documents": _safe_count("IMS Documents"),
        "risks": _safe_count("Risk And Opportunity"),
        "nc": _safe_count("Non Conformance"),
        "suppliers": _safe_count("Supplier"),
        "open_tasks": _safe_count("Task", {"status": "Open"}),
        "projects": _safe_count("Project"),
    }


# =========================================================================
#  SUPPLIER COMPLIANCE & TRAINING OBJECTIVES STATS
# =========================================================================
QUARTERS = [
    ("Q1", "01-01", "03-31"),
    ("Q2", "04-01", "06-30"),
    ("Q3", "07-01", "09-30"),
    ("Q4", "10-01", "12-31"),
]


def _se_date_field():
    for f in ("evaluation_date", "date_of_evaluation", "date"):
        if _has_field("Supplier Evaluation", f):
            return f
    return "creation"


@frappe.whitelist()
def get_supplier_compliance_stats(year=None):
    year = int(year or getdate(today()).year)
    out = []

    if not _exists("Supplier Evaluation"):
        return {"year": year, "quarters": []}

    df = _se_date_field()

    for q, f, t in QUARTERS:
        try:
            rows = frappe.get_all(
                "Supplier Evaluation",
                filters={
                    "docstatus": 1,
                    df: ["between", ["%s-%s" % (year, f), "%s-%s" % (year, t)]],
                },
                fields=["percentage", "rating", "total_score"],
                ignore_permissions=True,
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMS supplier_compliance %s" % q)
            rows = []

        evaluated = len(rows)
        compliant = len([r for r in rows if flt(r.percentage) >= 90])
        avg_pct = round(sum(flt(r.percentage) for r in rows) / evaluated) if evaluated else 0
        non_compliant_pct = round((evaluated - compliant) / evaluated * 100) if evaluated else 0

        out.append({
            "quarter": q,
            "evaluated": evaluated,
            "compliant": compliant,
            "compliance_rate": avg_pct,
            "target": 90,
            "non_compliant_pct": non_compliant_pct,
            "objective_met": (non_compliant_pct < 20) if evaluated else None,
        })

    return {"year": year, "quarters": out}


@frappe.whitelist()
def get_training_stats(year=None):
    """
    FIX: auto-detect the year that actually has Training Event data,
    instead of defaulting to the current calendar year (which returned
    all zeros when the training records belonged to a previous year).
    """
    total_employees = _safe_count("Employee", {"status": "Active"})
    target_count = round(total_employees * 0.5)
    out = []

    if not _exists("Training Event"):
        return {"year": None, "quarters": [], "total_employees": total_employees}

    if not year:
        try:
            row = frappe.db.sql(
                """SELECT YEAR(start_time) AS y
                   FROM `tabTraining Event`
                   WHERE docstatus < 2 AND start_time IS NOT NULL
                   GROUP BY YEAR(start_time)
                   ORDER BY y DESC LIMIT 1"""
            )
            year = row[0][0] if row else getdate(today()).year
        except Exception:
            year = getdate(today()).year

    year = int(year)

    for q, f, t in QUARTERS:
        trained = 0
        try:
            trained = frappe.db.sql(
                """
                SELECT COUNT(DISTINCT tee.employee)
                FROM `tabTraining Event Employee` tee
                JOIN `tabTraining Event` te ON te.name = tee.parent
                WHERE te.start_time >= %s AND te.start_time < %s
                  AND te.docstatus < 2
                """,
                ("%s-%s 00:00:00" % (year, f),
                 str(add_days(getdate("%s-%s" % (year, t)), 1)) + " 00:00:00"),
            )[0][0] or 0
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMS training_stats %s" % q)

        pct = round(trained / total_employees * 100, 1) if total_employees else 0
        out.append({
            "quarter": q,
            "total_employees": total_employees,
            "target": target_count,
            "trained": trained,
            "pct_trained": pct,
        })

    return {"year": year, "quarters": out, "total_employees": total_employees}


# =========================================================================
#  ELECTRICITY CONSUMPTION  (target = prior-year actual x 95%)
# =========================================================================
def _electricity_reading_field():
    for f in ("kwhf_reading", "kwh_reading", "reading", "kwh"):
        if _has_field("Electricity Consumption", f):
            return f
    return None


@frappe.whitelist()
def get_electricity_summary():
    if not _exists("Electricity Consumption"):
        return {"current_year": None, "prior_year": None, "months": []}

    field = _electricity_reading_field()
    if not field:
        return {"current_year": None, "prior_year": None, "months": []}

    try:
        row = frappe.db.sql(
            "SELECT MAX(YEAR(date)) FROM `tabElectricity Consumption` WHERE docstatus < 2"
        )
        current_year = row[0][0] if row and row[0][0] else getdate(today()).year
    except Exception:
        current_year = getdate(today()).year

    prior_year = current_year - 1

    def month_totals(year):
        try:
            rows = frappe.db.sql(
                """SELECT MONTH(date) AS m, SUM(`{f}`) AS total
                   FROM `tabElectricity Consumption`
                   WHERE docstatus < 2 AND YEAR(date) = %s
                   GROUP BY MONTH(date)""".format(f=field),
                (year,), as_dict=True,
            )
            return {r.m: flt(r.total) for r in rows}
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMS electricity %s" % year)
            return {}

    cur = month_totals(current_year)
    prior = month_totals(prior_year)

    months = []
    total_cur = total_target = 0
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for i, mname in enumerate(month_names, start=1):
        prior_actual = prior.get(i, 0)
        current_actual = cur.get(i, 0)
        target = round(prior_actual * 0.95, 2) if prior_actual else 0

        has_current = i in cur
        difference = round(current_actual - target, 2) if has_current else None
        pct_change = round((difference / target) * 100, 2) if (has_current and target) else None
        status = ("Achieved" if current_actual <= target else "Not Achieved") \
            if (has_current and target) else "-"

        months.append({
            "month": mname,
            "prior_actual": prior_actual,
            "target": target,
            "current_actual": current_actual if has_current else None,
            "difference": difference,
            "pct_change": pct_change,
            "status": status,
        })

        if has_current:
            total_cur += current_actual
        total_target += target

    overall_pct = round(((total_cur - total_target) / total_target) * 100, 2) if total_target else 0

    return {
        "current_year": current_year,
        "prior_year": prior_year,
        "months": months,
        "total_current": round(total_cur, 2),
        "total_target": round(total_target, 2),
        "total_prior": round(sum(prior.values()), 2),
        "overall_pct_change": overall_pct,
        "overall_status": "Achieved" if total_cur <= total_target else "Not Achieved",
    }


# =========================================================================
#  HSE DASHBOARD — Monitoring types + core HSE doctype totals
# =========================================================================
def _monitoring_type_field():
    for f in ("monitoring_type", "type_of_monitoring", "type"):
        if _has_field("Monitoring", f):
            return f
    return None


@frappe.whitelist()
def get_hse_summary():
    monitoring_counts = {}
    mt_field = _monitoring_type_field()
    if mt_field and _exists("Monitoring"):
        try:
            rows = frappe.db.sql(
                """SELECT `{f}` AS label, COUNT(*) AS count
                   FROM `tabMonitoring`
                   WHERE docstatus < 2 AND `{f}` IS NOT NULL AND `{f}` != ''
                   GROUP BY `{f}`""".format(f=mt_field),
                as_dict=True,
            )
            for r in rows:
                monitoring_counts[r.label] = r.count
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMS monitoring_type")

    # ensure the three known types always appear (0 if absent)
    for t in ("Air Emission Monitoring", "Water Waste Monitoring", "Solid Waste Monitoring"):
        monitoring_counts.setdefault(t, 0)

    hazard_dt = _first_existing_doctype(
        ["Hazard and Risk Assesment", "Hazard and Risk Assessment", "Hazard And Risk Assesment"])
    aspect_dt = _first_existing_doctype(
        ["Aspect - Impact Assessment", "Aspect Impact Assessment", "Aspect - Impact Assesment"])
    checklist_master_dt = _first_existing_doctype(
        ["HSE CheckList Master", "HSE Checklist Master"])
    checklist_insp_dt = _first_existing_doctype(
        ["HSE CheckList Inspection", "HSE Checklist Inspection"])

    return {
        "monitoring_by_type": monitoring_counts,
        "monitoring_total": sum(monitoring_counts.values()),
        "hazard_risk_assessment": _safe_count(hazard_dt) if hazard_dt else 0,
        "aspect_impact_assessment": _safe_count(aspect_dt) if aspect_dt else 0,
        "msds": _safe_count("Material Safety Data Sheet"),
        "hse_checklist_master": _safe_count(checklist_master_dt) if checklist_master_dt else 0,
        "hse_checklist_inspection": _safe_count(checklist_insp_dt) if checklist_insp_dt else 0,
    }