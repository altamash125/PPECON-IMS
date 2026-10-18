// apps/ppecon_ims/ppecon_ims/ppecon_ims/doctype/supplier_evaluation/supplier_evaluation.js

const CRITERIA_FIELDS = [
	"quality_of_product",
	"timelines_of_deliveries",
	"communication_and_responsiveness",
	"problem_resolution",
	"consistency_and_reliability",
	"adhere_to_contract_terms",
	"professionalism",
	"overall_satisfaction",
];

// Ratings sirf assigned evaluator ke liye mandatory (assign karne wale ke liye nahi)
function toggle_criteria_reqd(frm) {
	const is_evaluator =
		!frm.is_new() && !!frm.doc.assigned_user && frappe.session.user === frm.doc.assigned_user;

	CRITERIA_FIELDS.forEach((field) => {
		frm.set_df_property(field, "reqd", is_evaluator ? 1 : 0);
	});
}

frappe.ui.form.on("Supplier Evaluation", {
	refresh(frm) {
		toggle_criteria_reqd(frm);
	},

	assigned_user(frm) {
		toggle_criteria_reqd(frm);
	},
});
