// Copyright (c) 2026, altamash@ppecon.com and contributors
// For license information, please see license.txt

// frappe.ui.form.on("IT Asset Clearance", {
// 	refresh(frm) {

// 	},
// });

// =========================================================================
//  apps/ppecon_ims/ppecon_ims/ppe_ims/doctype/it_asset_clearance/it_asset_clearance.js
// =========================================================================

frappe.ui.form.on("IT Asset Clearance", {
	refresh(frm) {
		render_fetch_button(frm);
		render_status_banner(frm);

		if (frm.doc.docstatus === 0 && frm.doc.employee) {
			frm.add_custom_button(__("Fetch Assigned Assets"), () => fetch_assets(frm));
		}
	},

	employee(frm) {
		frm.clear_table("items");
		frm.refresh_field("items");
		if (frm.doc.employee) fetch_assets(frm);
	},
});

frappe.ui.form.on("IT Asset Clearance Item", {
	returned(frm) {
		frm.doc.items.forEach((r) => {
			frappe.model.set_value(
				r.doctype,
				r.name,
				"condition",
				r.returned ? r.condition || "Good" : "",
			);
		});
		render_status_banner(frm);
	},
});

function fetch_assets(frm) {
	frappe.call({
		method: "ppecon_ims.ppe_ims.doctype.it_asset_clearance.it_asset_clearance.fetch_assigned_assets",
		args: { employee: frm.doc.employee },
		freeze: true,
		freeze_message: __("Fetching assigned assets..."),
		callback(r) {
			if (!r.message) return;
			frm.clear_table("items");
			r.message.forEach((row) => {
				const child = frm.add_child("items");
				Object.assign(child, row);
			});
			frm.refresh_field("items");
			render_status_banner(frm);

			if (!r.message.length) {
				frappe.show_alert({
					message: __("No assets currently assigned to this employee"),
					indicator: "blue",
				});
			}
		},
	});
}

function render_fetch_button(frm) {
	const field = frm.get_field("fetch_assets_html");
	if (!field) return;
	if (!frm.doc.employee) {
		field.$wrapper.html(`<div style="padding:12px;color:#98a4b0;font-size:12px;">
			Select an employee, then click "Fetch Assigned Assets" above.</div>`);
	} else {
		field.$wrapper.html("");
	}
}

function render_status_banner(frm) {
	const field = frm.get_field("fetch_assets_html");
	if (!field || !frm.doc.items || !frm.doc.items.length) return;

	const total = frm.doc.items.length;
	const returned = frm.doc.items.filter((r) => r.returned).length;
	const pct = total ? Math.round((returned / total) * 100) : 0;
	const cleared = returned === total;
	const color = cleared ? "#178a5c" : "#b97b0f";
	const bg = cleared ? "#e7f4ee" : "#f9f1e2";

	field.$wrapper.html(`
		<div style="border:1px solid #e2e6ea;border-radius:8px;padding:12px 14px;background:${bg};
			font-family:'Segoe UI',Arial,sans-serif;font-size:13px;margin-bottom:10px;">
			<b style="color:${color};">${returned} of ${total} assets returned (${pct}%)</b>
			<div style="height:6px;background:rgba(0,0,0,.08);border-radius:3px;overflow:hidden;margin-top:6px;">
				<div style="height:100%;width:${pct}%;background:${color};"></div>
			</div>
			${
				cleared
					? `<div style="margin-top:6px;color:${color};font-weight:600;">✓ All assets returned — ready to submit</div>`
					: `<div style="margin-top:6px;color:${color};">Mark each asset as Returned before submitting</div>`
			}
		</div>`);
}
