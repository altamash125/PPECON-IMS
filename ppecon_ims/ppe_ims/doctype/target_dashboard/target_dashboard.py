# =========================================================================
#  apps/ppecon_ims/ppecon_ims/ppe_ims/doctype/target_dashboard/target_dashboard.py
#
#  Calculates Sales Order Amount for the calendar year (1 Jan - 31 Dec)
#  of the selected Year, optionally filtered by Sales Person.
# =========================================================================
import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class TargetDashboard(Document):
    def validate(self):
        self.sync_achievement()

    def sync_achievement(self):
        if not self.year:
            return

        year_start = "%s-01-01" % self.year
        year_end = "%s-12-31" % self.year

        if self.sales_person:
            # per Sales Person: sum via the "Sales Team" child table on Sales Order
            rows = frappe.db.sql(
                """
                SELECT st.allocated_amount, st.allocated_percentage, so.base_grand_total
                FROM `tabSales Team` st
                INNER JOIN `tabSales Order` so ON so.name = st.parent
                WHERE st.parenttype = 'Sales Order'
                  AND st.sales_person = %s
                  AND so.docstatus = 1
                  AND so.transaction_date BETWEEN %s AND %s
                """,
                (self.sales_person, year_start, year_end),
                as_dict=True,
            )
            total = 0.0
            for r in rows:
                if flt(r.allocated_amount):
                    total += flt(r.allocated_amount)
                elif flt(r.allocated_percentage):
                    total += flt(r.base_grand_total) * flt(r.allocated_percentage) / 100.0
        else:
            # company-wide: sum of all submitted Sales Orders that year
            total = flt(frappe.db.sql(
                """
                SELECT COALESCE(SUM(base_grand_total), 0) FROM `tabSales Order`
                WHERE docstatus = 1 AND transaction_date BETWEEN %s AND %s
                """,
                (year_start, year_end),
            )[0][0])

        self.sales_order_amount = total
        self.remaining_target = max(flt(self.annual_target) - total, 0)
        self.achievement = round((total / self.annual_target) * 100, 1) if self.annual_target else 0
        self.last_synced = now_datetime()


# =========================================================================
#  WHITELISTED APIs
# =========================================================================
@frappe.whitelist()
def resync(name):
    """Manual refresh button on the form."""
    doc = frappe.get_doc("Target Dashboard", name)
    doc.sync_achievement()
    doc.save()
    return {
        "sales_order_amount": doc.sales_order_amount,
        "remaining_target": doc.remaining_target,
        "achievement": doc.achievement,
    }


@frappe.whitelist()
def quick_set_target(year, annual_target, sales_person=None):
    """
    Called from the popup dialog.
    Creates the record if it doesn't exist for this year (+ sales_person),
    otherwise updates the target amount — then recalculates instantly.
    """
    year = int(year)
    filters = {"year": year}
    if sales_person:
        filters["sales_person"] = sales_person
    else:
        filters["sales_person"] = ("in", ["", None])

    existing = frappe.db.get_value("Target Dashboard", filters, "name")

    if existing:
        doc = frappe.get_doc("Target Dashboard", existing)
        doc.annual_target = flt(annual_target)
    else:
        doc = frappe.get_doc({
            "doctype": "Target Dashboard",
            "year": year,
            "sales_person": sales_person,
            "annual_target": flt(annual_target),
        })

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "name": doc.name,
        "year": doc.year,
        "sales_person": doc.sales_person,
        "annual_target": doc.annual_target,
        "sales_order_amount": doc.sales_order_amount,
        "remaining_target": doc.remaining_target,
        "achievement": doc.achievement,
        "currency": doc.currency,
    }


@frappe.whitelist()
def get_team_overview(year):
    """All targets (company-wide + any per-person) for a year."""
    return frappe.get_all(
        "Target Dashboard",
        filters={"year": year},
        fields=["name", "sales_person", "annual_target", "sales_order_amount",
                "remaining_target", "achievement"],
        order_by="achievement desc",
    )