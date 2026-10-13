frappe.listview_settings['Employee Survey Invitation'] = {
    onload(listview) {
        listview.page.add_inner_button('Send Survey Links to All Employees', () => {
            frappe.prompt(
                [{ fieldname: 'survey_round', label: 'Survey Round (e.g. 2026-Q4)', fieldtype: 'Data', reqd: 1 }],
                (values) => {
                    frappe.call({
                        method: 'ppecon_ims.ppe_ims.api.send_employee_survey_links',
                        args: { survey_round: values.survey_round },
                        freeze: true,
                        freeze_message: 'Sending links...',
                        callback: (r) => {
                            frappe.msgprint(`Sent: ${r.message.sent}, Skipped: ${r.message.skipped}`);
                            listview.refresh();
                        }
                    });
                },
                'Send Employee Survey Links',
                'Send'
            );
        });
    }
};
