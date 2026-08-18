// Copyright (c) 2026, altamash@ppecon.com and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Compliance Obligation", {
// 	refresh(frm) {

// 	},
// });
frappe.listview_settings["Compliance Obligation"] = {
	get_indicator: function (doc) {
		if (doc.expiration_date) {
			let today = frappe.datetime.get_today();
			let one_month_later = frappe.datetime.add_months(today, 1);

			if (doc.expiration_date <= today) {
				return [__("Expired"), "red", "expiration_date,<=," + today];
			} else if (doc.expiration_date <= one_month_later) {
				return [__("Expiring Soon"), "orange", "expiration_date,<=," + one_month_later];
			}
		}
		return [__(doc.status || "Active"), "green", "status,=," + (doc.status || "")];
	},
};
