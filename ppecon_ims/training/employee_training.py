# =========================================================================
#  ppecon_ims/training/employee_training.py
#  Live training history for an Employee, read straight from Training Event.
#  No data duplication — Training Event stays the single source of truth.
# =========================================================================
import frappe
from frappe.utils import flt


def _has(doctype, field):
    try:
        return frappe.get_meta(doctype).has_field(field)
    except Exception:
        return False


@frappe.whitelist()
def get_employee_trainings(employee):
    """Return every Training Event this employee is listed in."""
    if not employee:
        return []

    if not frappe.db.exists("DocType", "Training Event"):
        return []

    # build the child-table columns that actually exist
    child = "Training Event Employee"
    child_cols = []
    for f in ("status", "attendance", "department", "rating"):
        if _has(child, f):
            child_cols.append("tee.`{f}` AS emp_{f}".format(f=f))
    child_select = (", " + ", ".join(child_cols)) if child_cols else ""

    # parent columns that exist
    parent_map = {
        "event_name": "te.event_name",
        "type": "te.`type`",
        "event_status": "te.event_status",
        "level": "te.`level`",
        "start_time": "te.start_time",
        "end_time": "te.end_time",
        "location": "te.location",
        "course": "te.course",
        "trainer_name": "te.trainer_name",
        "supplier": "te.supplier",
        "has_certificate": "te.has_certificate",
    }
    parent_select = ", ".join(
        "%s AS %s" % (expr, alias)
        for alias, expr in parent_map.items()
        if _has("Training Event", alias)
    )

    try:
        rows = frappe.db.sql(
            """
            SELECT te.name AS training_event, te.docstatus {parent_sep} {parent_select} {child_select}
            FROM `tabTraining Event Employee` tee
            INNER JOIN `tabTraining Event` te ON te.name = tee.parent
            WHERE tee.employee = %s
              AND tee.parenttype = 'Training Event'
              AND te.docstatus < 2
            ORDER BY te.start_time DESC
            """.format(
                parent_sep="," if parent_select else "",
                parent_select=parent_select,
                child_select=child_select,
            ),
            (employee,),
            as_dict=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Employee training fetch")
        return []

    # attach the score from Training Result if it exists
    if frappe.db.exists("DocType", "Training Result Employee"):
        for r in rows:
            try:
                res = frappe.db.sql(
                    """SELECT tre.grade, tre.hours
                       FROM `tabTraining Result Employee` tre
                       INNER JOIN `tabTraining Result` tr ON tr.name = tre.parent
                       WHERE tre.employee = %s AND tr.training_event = %s
                         AND tr.docstatus = 1 LIMIT 1""",
                    (employee, r.training_event), as_dict=True,
                )
                if res:
                    r["grade"] = res[0].get("grade")
                    r["hours"] = flt(res[0].get("hours"))
            except Exception:
                pass

    return rows


@frappe.whitelist()
def get_training_summary(employee):
    """Small stats block for the header of the HTML field."""
    rows = get_employee_trainings(employee)
    total = len(rows)
    completed = len([r for r in rows if (r.get("event_status") == "Completed"
                                         or r.get("emp_status") == "Completed")])
    scheduled = len([r for r in rows if r.get("event_status") == "Scheduled"])
    hours = sum(flt(r.get("hours")) for r in rows)
    return {
        "total": total,
        "completed": completed,
        "scheduled": scheduled,
        "hours": hours,
        "rows": rows,
    }