// Copyright (c) 2020, AVU and contributors
// For license information, please see license.txt

frappe.ui.form.on('Leave Rule', {
	refresh: function(frm) {
		frm.trigger('toggle_mandatory');
		// frm.events.toggle_leave_allowed(frm, frm.doc.__islocal || 0);
	},

	toggle_mandatory: function(frm) {
		// frm.toggle_reqd('salary_compensation_component', frm.doc.is_not_applicable_all_components || 0);
		// frm.toggle_reqd('frequency_based_on', frm.doc.is_slab_applicable || 0);
		// frm.toggle_reqd('compensation_rule', frm.doc.is_slab_applicable || 0);
		// frm.trigger('toggle_description');
	},

	is_not_applicable_all_components: function(frm) {
		frm.trigger('toggle_mandatory');
		frm.set_value('salary_compensation_component', []);
	},

	is_slab_applicable: function(frm) {
		frm.trigger('toggle_mandatory');
		frm.set_value('frequency_based_on', undefined);
		frm.set_value('compensation_rule', []);
	},

	frequency_based_on: function(frm) {
		frm.trigger('toggle_description');
	},

	toggle_description: function(frm) {
		var description = {'Number of Days availed': 'eg:- 01-30 days 100%; 31-90 days 75%; 91-120 days 0%',
			'Number of Months worked': 'eg:- 0 month to 1 month 0%; 1 month to 3 month 50%; 3 month to 999 year 100%',
			'Number of Years worked': 'eg:- 0 year to 1 year 0%; 1 year to 3 year 50%; 3 year to 999 year 100%'};
		frm.set_df_property('frequency_based_on', 'description', description[frm.doc.frequency_based_on] || "");
	},

	// leave_type: function(frm) {
	// 	frm.events.toggle_leave_allowed(frm, 1);
	// },

	// toggle_leave_allowed: function(frm, reset=1) {
	// 	frappe.db.get_value('Leave Type', {'name': cur_frm.doc.leave_type}, 'allow_negative', (r) => {
	// 		var flag = (r && r.allow_negative)
	// 		frm.toggle_display('max_leaves_allowed', !flag);
	// 		if (reset==1)
	// 			frm.set_value('max_leaves_allowed', 0);
	// 	});
	// }
});