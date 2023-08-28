// Copyright (c) 2020, AVU and contributors
// For license information, please see license.txt

frappe.ui.form.on('Benefit Type for EOS', {
	refresh: function(frm) {
		frm.trigger('toggle_mandatory');
	},

	is_not_applicable_all_components: function(frm) {
		frm.trigger('toggle_mandatory');
		frm.set_value('applicable_salary_components', []);
	},

	toggle_mandatory: function(frm) {
		frm.toggle_reqd('applicable_salary_components', cur_frm.doc.is_not_applicable_all_components || 0);
	}
});
