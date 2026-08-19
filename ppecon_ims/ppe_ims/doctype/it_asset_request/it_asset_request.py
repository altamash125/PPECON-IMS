
import frappe
from frappe.model.document import Document


class ITAssetRequest(Document):
    pass


def on_asset_request_submit(doc, method):
    """Runs when IT Asset Request is submitted (docstatus = 1)"""
    create_or_update_it_supply(doc)
    rebuild_employee_custody(doc.employee)


def create_or_update_it_supply(doc):
    """Push each row from item_details (child table: IT Supplier Item)
    into IT Supply (stock doctype)"""
    for row in doc.item_details:
        if not row.asset_name:
            continue

        existing = frappe.db.get_value(
            "IT Supply",
            {"request_reference": doc.name, "asset_name": row.asset_name},
            "name"
        )

        supply_data = {
            "asset_name": row.asset_name,
            "sn": row.sn,
            "asset_type": row.asset_type,
            "model_no": row.model_no,
            "manufacturerbrand": row.manufacturerbrand,
            "hddssd": row.hddssd,
            "ram": row.ram,
            "os": row.os,
            "processor": row.processor,
            "purchase_date": row.purchase_date,
            "specification": row.specification,
            "status": "Assigned",
            "assigned_to": doc.employee,
            "assigned_date": frappe.utils.nowdate(),
            "request_reference": doc.name,
        }

        if existing:
            supply = frappe.get_doc("IT Supply", existing)
            supply.update(supply_data)
            supply.save(ignore_permissions=True)
        else:
            supply = frappe.get_doc({"doctype": "IT Supply", **supply_data})
            supply.insert(ignore_permissions=True)

    frappe.db.commit()


def rebuild_employee_custody(employee):
    """Build HTML table of all assets currently assigned to this employee
    (pulled from IT Supply) and push to Employee.employee_custody"""
    if not employee:
        return

    assets = frappe.get_all(
        "IT Supply",
        filters={"assigned_to": employee, "status": "Assigned"},
        fields=[
            "asset_name", "sn", "asset_type", "model_no",
            "manufacturerbrand", "hddssd", "ram", "os",
            "processor", "specification", "purchase_date"
        ]
    )

    if not assets:
        frappe.db.set_value("Employee", employee, "employee_custody", "")
        return

    field_labels = [
        ("Asset Name", "asset_name"),
        ("S/N", "sn"),
        ("Asset Type", "asset_type"),
        ("Model No", "model_no"),
        ("Brand", "manufacturerbrand"),
        ("HDD/SSD", "hddssd"),
        ("RAM", "ram"),
        ("OS", "os"),
        ("Processor", "processor"),
        ("Specification", "specification"),
        ("Purchase Date", "purchase_date"),
    ]

    active_cols = [(label, fname) for label, fname in field_labels
                   if any(a.get(fname) for a in assets)]

    header = "".join(f"<th>{label}</th>" for label, _ in active_cols)
    rows_html = ""
    for a in assets:
        cells = "".join(f"<td>{a.get(fname) or '-'}</td>" for _, fname in active_cols)
        rows_html += f"<tr>{cells}</tr>"

    html = f"""
    <table class="table table-bordered table-sm">
        <thead><tr>{header}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    """

    frappe.db.set_value("Employee", employee, "employee_custody", html)
    frappe.db.commit()