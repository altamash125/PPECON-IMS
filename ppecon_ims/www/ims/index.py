# =========================================================================
#  ppecon_ims/www/ims/index.py
#  IMS portal dashboard backend  (v3.1 — fixed)
#  Sections: IMS/ISO · Sales & Marketing (CRM) · Procurement
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
    """Return (from_date, to_date) for a named period or a custom range."""
    t = getdate(today())

    if from_date and to_date:
        f, e = getdate(from_date), getdate(to_date)
        # FIX: swap if the user picks them the wrong way round
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
    else:  # this_year
        start, end = t.replace(month=1, day=1), t

    return start, end


def _month_buckets(start, end, max_points=12):
    """
    Month buckets between start and end.
    FIX: when the range is longer than max_points, keep the MOST RECENT
    months (the old version kept the oldest, so 'All Time' showed year 2000).
    """
    out = []
    cur = getdate(start).replace(day=1)
    last = getdate(end).replace(day=1)
    guard = 0
    while cur <= last and guard < 600:          # guard against runaway loops
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


def _date_field(doctype):
    """Best date field for period filtering."""
    for f in ("transaction_date", "posting_date", "schedule_date", "date"):
        if _has_field(doctype, f):
            return f
    return "creation"


def _group_by(doctype, field, start=None, end=None, limit=15, extra=""):
    """GROUP BY count with optional period filter. Returns [] on any failure."""
    if not _has_field(doctype, field):
        return []
    try:
        params = {}
        where = "docstatus < 2"
        if start and end:
            df = _date_field(doctype)
            # FIX: creation is a datetime — add a day so the end date is inclusive
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

    # FIX: cache per period for 5 minutes — 'All Time' on a big DB was slow
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
    """Call this if you want fresh numbers immediately."""
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
    """FIX: one grouped query instead of 12 separate ones — much faster."""
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
    rows = _group_by("Risk And Opportunity", "status") or \
           _group_by("Risk And Opportunity", "workflow_state")
    return rows


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

        # FIX: Supplier.disabled may not exist on older versions
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