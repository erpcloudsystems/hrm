// Copyright (c) 2019, Digitalprizm and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Award Rule', {
	setup: function(frm) {
		frm.set_query('eos_benefit_type', 'service_award_details', function(doc, cdt, cdn) {
			return {
				query: 'hrm.hrm.doctype.service_award_rule.service_award_rule.filter_benefit_type',
				filters: {
					effective_from: frm.doc.effective_from
				}
			}
		});
	}
});