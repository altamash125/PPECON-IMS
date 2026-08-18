// Copyright (c) 2026, altamash@ppecon.com and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Target Dashboard", {
// 	refresh(frm) {

// 	},
// });

// =========================================================================
//  apps/ppecon_ims/ppecon_ims/ppe_ims/doctype/target_dashboard/target_dashboard.js
//  1) Live gauge on the form
//  2) "Set Target" popup dialog (from the List View) — enter amount,
//     result (achievement so far) shows instantly inside the same popup
// =========================================================================

// ---------------------------------------------------------------
//  1. FORM — gauge rendering (same as before)
// ---------------------------------------------------------------
frappe.ui.form.on("Target Dashboard", {
	refresh(frm) {
		render_gauge(frm);
		if (!frm.is_new()) {
			frm.add_custom_button(__("Refresh from Sales Orders"), () => {
				frappe.call({
					method: "ppecon_ims.ppe_ims.doctype.target_dashboard.target_dashboard.resync",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Recalculating..."),
					callback: (r) => {
						if (r.message) {
							frm.reload_doc();
							frappe.show_alert({
								message: __("Target updated"),
								indicator: "green",
							});
						}
					},
				});
			});
		}
	},
	annual_target(frm) {
		render_gauge(frm);
	},
});

function td_band(pct) {
	if (pct >= 100) return { color: "#178a5c", bg: "#e7f4ee", label: "Target Achieved" };
	if (pct >= 75) return { color: "#1b6bc4", bg: "#e8f0f7", label: "On Track" };
	if (pct >= 50) return { color: "#b97b0f", bg: "#f9f1e2", label: "Needs Push" };
	return { color: "#c2402a", bg: "#f9ece9", label: "Behind Target" };
}

function td_money(v, currency) {
	if (v == null) v = 0;
	const fmt = (n) => n.toLocaleString(undefined, { maximumFractionDigits: 0 });
	if (Math.abs(v) >= 1e7) return `${currency || ""} ${(v / 1e7).toFixed(2)} Cr`;
	if (Math.abs(v) >= 1e5) return `${currency || ""} ${(v / 1e5).toFixed(2)} L`;
	return `${currency || ""} ${fmt(v)}`;
}

// builds the gauge HTML — used by BOTH the form field and the popup dialog
function td_gauge_html(target, achieved, remaining, currency, last_synced) {
	target = flt(target);
	achieved = flt(achieved);
	remaining = flt(remaining);
	const raw_pct = target ? (achieved / target) * 100 : 0;
	const pct = Math.min(raw_pct, 100);
	const band = td_band(raw_pct);
	const angle = pct * 1.8;

	if (!target) {
		return `<div style="padding:24px;text-align:center;color:#98a4b0;
			border:1px dashed #d8dde2;border-radius:8px;font-size:13px;">
			Set an Annual Target to see progress.</div>`;
	}

	return `
	<div style="font-family:'Segoe UI',Arial,sans-serif;font-size:13px;">
	  <div style="display:grid;grid-template-columns:200px 1fr;gap:18px;align-items:center;">
	    <div style="text-align:center;">
	      <div style="position:relative;width:200px;height:110px;margin:0 auto;overflow:hidden;">
	        <div style="width:200px;height:200px;border-radius:50%;
	            background:conic-gradient(${band.color} 0deg ${angle}deg, #e9edf1 ${angle}deg 180deg, transparent 180deg 360deg);
	            transform:rotate(-90deg);"></div>
	        <div style="position:absolute;top:34px;left:34px;width:132px;height:132px;
	            border-radius:50%;background:#fff;"></div>
	        <div style="position:absolute;inset:0;display:flex;flex-direction:column;
	            align-items:center;justify-content:flex-end;padding-bottom:8px;">
	          <div style="font-size:24px;font-weight:800;color:${band.color};">${raw_pct.toFixed(1)}%</div>
	          <div style="font-size:10.5px;color:#8d99a6;">of target</div>
	        </div>
	      </div>
	      <div style="display:inline-block;margin-top:6px;padding:4px 14px;border-radius:20px;
	          background:${band.color};color:#fff;font-weight:700;font-size:12px;">${band.label}</div>
	    </div>
	    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;">
	      <div style="border:1px solid #e2e6ea;border-radius:8px;padding:10px 12px;">
	        <div style="font-size:10px;text-transform:uppercase;color:#8d99a6;font-weight:600;">Target</div>
	        <div style="font-size:16px;font-weight:700;color:#1f272e;">${td_money(target, currency)}</div>
	      </div>
	      <div style="border:1px solid #e2e6ea;border-radius:8px;padding:10px 12px;background:${band.bg};">
	        <div style="font-size:10px;text-transform:uppercase;color:#8d99a6;font-weight:600;">Achieved</div>
	        <div style="font-size:16px;font-weight:700;color:${band.color};">${td_money(achieved, currency)}</div>
	      </div>
	      <div style="border:1px solid #e2e6ea;border-radius:8px;padding:10px 12px;">
	        <div style="font-size:10px;text-transform:uppercase;color:#8d99a6;font-weight:600;">Remaining</div>
	        <div style="font-size:16px;font-weight:700;color:#1f272e;">${td_money(remaining, currency)}</div>
	      </div>
	    </div>
	  </div>
	  <div style="height:9px;background:#e9edf1;border-radius:5px;overflow:hidden;margin-top:14px;">
	    <div style="height:100%;width:${pct}%;background:${band.color};transition:width .4s ease;"></div>
	  </div>
	  ${
			last_synced
				? `<div style="font-size:11px;color:#98a4b0;margin-top:5px;">
	      Last synced: ${frappe.datetime.str_to_user(last_synced)}</div>`
				: ""
		}
	</div>`;
}

function render_gauge(frm) {
	const field = frm.get_field("progress_html");
	if (!field) return;
	field.$wrapper.html(
		td_gauge_html(
			frm.doc.annual_target,
			frm.doc.sales_order_amount,
			frm.doc.remaining_target,
			frm.doc.currency,
			frm.doc.last_synced,
		),
	);
}

// ---------------------------------------------------------------
//  2. LIST VIEW — "Set Target" popup
// ---------------------------------------------------------------
frappe.listview_settings["Target Dashboard"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Set Target"), () => open_set_target_dialog());
	},
};

function open_set_target_dialog() {
	const d = new frappe.ui.Dialog({
		title: __("Set Sales Target"),
		fields: [
			{
				fieldname: "year",
				fieldtype: "Int",
				label: __("Year"),
				default: new Date().getFullYear(),
				reqd: 1,
			},
			{
				fieldname: "sales_person",
				fieldtype: "Link",
				options: "Sales Person",
				label: __("Sales Team / Person"),
				description: __("Leave blank for a company-wide target"),
			},
			{ fieldname: "cb1", fieldtype: "Column Break" },
			{
				fieldname: "annual_target",
				fieldtype: "Currency",
				label: __("Annual Target"),
				reqd: 1,
			},
			{ fieldname: "sec_result", fieldtype: "Section Break", label: __("Result") },
			{ fieldname: "result_html", fieldtype: "HTML" },
		],
		primary_action_label: __("Calculate"),
		primary_action(values) {
			d.set_primary_action(__("Calculating..."), null);
			frappe.call({
				method: "ppecon_ims.ppe_ims.doctype.target_dashboard.target_dashboard.quick_set_target",
				args: {
					year: values.year,
					annual_target: values.annual_target,
					sales_person: values.sales_person || null,
				},
				callback(r) {
					d.set_primary_action(__("Calculate"), () =>
						d.get_primary_btn().trigger("click"),
					);
					if (!r.message) return;
					const m = r.message;

					d.fields_dict.result_html.$wrapper.html(
						td_gauge_html(
							m.annual_target,
							m.sales_order_amount,
							m.remaining_target,
							m.currency,
							frappe.datetime.now_datetime(),
						),
					);

					d.set_primary_action(__("Open Record"), () => {
						d.hide();
						frappe.set_route("Form", "Target Dashboard", m.name);
					});

					if (cur_list) cur_list.refresh();
				},
				error() {
					d.set_primary_action(__("Calculate"), () =>
						d.get_primary_btn().trigger("click"),
					);
				},
			});
		},
	});
	d.show();
}
