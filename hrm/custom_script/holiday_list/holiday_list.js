// Copyright (c) 2020, avu and contributors
// For license information, please see license.txt

frappe.ui.form.on('Holiday List', {
	get_weekly_off_dates: function(frm) {
		frappe.call({
			method: 'hrm.doctype_triggers.hr.holiday_list.holiday_list.update_weekoff',
			args: {
				'doc': frm.doc
			},
			async: false,
			callback: function(r) {
				frappe.model.sync(r.message);
				frm.refresh_fields();
			}
		})
	}
});
