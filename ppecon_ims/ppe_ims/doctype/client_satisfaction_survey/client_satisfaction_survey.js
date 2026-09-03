frappe.ui.form.on("Client Satisfaction Survey", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status !== "Completed") {
			frm.add_custom_button("Send Feedback Request", () => {
				frappe.call({
					method: "ppecon_ims.ppe_ims.api.send_feedback_request",
					args: { docname: frm.doc.name },
					freeze: true,
					freeze_message: "Sending email...",
					callback: () => {
						frappe.msgprint("Feedback request sent to " + frm.doc.email);
						frm.reload_doc();
					},
				});
			});
		}

		if (frm.doc.status === "Completed") {
			render_response_summary(frm);
		}
	},
});

function render_response_summary(frm) {
	const rating_groups = [
		{
			title: "Part 1: Service Quality",
			fields: [
				[
					"design_requirements_rating",
					"Satisfaction with design requirements and expectations",
				],
				[
					"coordination_design_operation_rating",
					"Satisfaction with coordination between Design & Operation",
				],
				["hse_commitment_rating", "Satisfaction with HSE commitment during execution"],
				["project_duration_rating", "Satisfaction with the project duration"],
				["weekly_reports_rating", "Satisfaction with progress weekly reports"],
			],
		},
		{
			title: "Part 2: Project Outcome and Satisfaction",
			fields: [
				["functionality_rating", "Functionality of the completed design"],
				[
					"quality_compliance_rating",
					"Quality compliance with approved design and specifications",
				],
				["snags_taking_rating", "Taking of snags"],
				["snags_closing_rating", "Closing of snags"],
			],
		},
		{
			title: "Part 3: Overall Experience",
			fields: [
				["delivery_rating", "Satisfaction with project delivery"],
				[
					"warranty_aftersales_rating",
					"Satisfaction with warranty and after sales services",
				],
				["work_again_rating", "Potential to work with us again"],
				["recommend_rating", "Potential to recommend us to others"],
			],
		},
		{
			title: "Part 4: Communication",
			fields: [
				["comm_tender_rating", "Communication during tender launching phase"],
				["comm_proposal_rating", "Communication during proposal negotiation phase"],
				["comm_design_prep_rating", "Communication during design preparation phase"],
				["comm_execution_rating", "Communication during execution phase"],
				["comm_snags_handover_rating", "Communication during snags & handover phase"],
				["comm_aftersales_rating", "Communication during after sales service phase"],
				["comm_invoicing_rating", "Communication during invoicing and collection phase"],
				["material_delivery_rating", "Material delivery time & quality"],
			],
		},
	];

	function color(val) {
		if (["4", "5"].includes(val)) return "#38a169";
		if (val === "3") return "#d69e2e";
		if (["1", "2"].includes(val)) return "#e53e3e";
		return "#718096";
	}

	let low_ratings = [];
	let groups_html = rating_groups
		.map((g) => {
			let rows = g.fields
				.map(([fname, label]) => {
					let val = frm.doc[fname] || "-";
					if (["1", "2"].includes(val)) low_ratings.push(label);
					return `<tr>
                <td style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;">${label}</td>
                <td style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;text-align:center;font-weight:bold;color:${color(val)};">${val}</td>
            </tr>`;
				})
				.join("");
			return `
            <h4 style="font-size:14px;color:#1e4e8c;margin:18px 0 8px;border-bottom:2px solid #e2e8f0;padding-bottom:5px;">${g.title}</h4>
            <table style="width:100%;border-collapse:collapse;margin-bottom:5px;">
                <tr style="background:#f7f9fc;">
                    <th style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;text-align:left;">Question</th>
                    <th style="padding:8px 10px;border:1px solid #e2e8f0;font-size:13px;">Rating</th>
                </tr>
                ${rows}
            </table>`;
		})
		.join("");

	let alert_html = "";
	if (low_ratings.length) {
		let items = low_ratings.map((l) => `<li>${frappe.utils.escape_html(l)}</li>`).join("");
		alert_html = `<div style="background:#fff5f5;border-left:4px solid #e53e3e;padding:12px 16px;margin:15px 0;border-radius:4px;">
            <strong style="color:#c53030;">⚠ Attention needed — low ratings on:</strong>
            <ul style="margin:8px 0 0;padding-left:20px;color:#742a2a;font-size:13px;">${items}</ul>
        </div>`;
	}

	let html = `
        <div style="font-family:'Segoe UI',Arial,sans-serif;width:100%;box-sizing:border-box;">
		    <div style="background:linear-gradient(135deg,#1e4e8c,#2b6cb0);color:#fff;padding:16px 20px;border-radius:8px 8px 0 0;">
                <strong style="font-size:15px;">Client Response Summary</strong><br>
                <span style="font-size:12px;opacity:0.9;">Responded on: ${frm.doc.responded_on || "-"}</span>
            </div>
            <div style="border:1px solid #e2e8f0;border-top:none;padding:16px 20px;border-radius:0 0 8px 8px;">
                ${alert_html}
                ${groups_html}
                <h4 style="font-size:14px;color:#1e4e8c;margin:18px 0 8px;border-bottom:2px solid #e2e8f0;padding-bottom:5px;">Overall Feedback</h4>
                <p style="font-size:13px;color:#333;background:#f9fafb;padding:12px;border-radius:6px;">
                    ${frm.doc.feedback ? frappe.utils.escape_html(frm.doc.feedback) : "No additional feedback provided."}
                </p>
            </div>
        </div>
    `;

	$(frm.fields_dict.response_summary_html.wrapper).html(html);
}
