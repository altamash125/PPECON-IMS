// Copyright (c) 2026, altamash@ppecon.com and contributors
// For license information, please see license.txt

// frappe.ui.form.on("BOQ", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("BOQ", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Approved") {
			frm.add_custom_button(
				__("Quotation"),
				() => {
					frappe.model.open_mapped_doc({
						method: "ppecon_ims.ppe_ims.doctype.boq.boq.make_quotation",
						frm: frm,
					});
				},
				__("Create"),
			);
		}
	},
});
