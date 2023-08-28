// Copyright (c) 2018, Digitalprizm and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vacation Rule Modification', {
	setup: function(frm) {
		frm.add_fetch('employee', 'employee_name', 'employee_name');

		frm.fields_dict['new_rule'].get_query = function(doc) {
			return {
				filters: {
					"docstatus": 1
				}
			}
		}

		frm.set_query('employee', () => {
			return {
				query: "hrm.hrm.doctype.vacation_leave_application.vacation_leave_application.filter_employee"
			}
		});
	},
	refresh: function(frm) {
		if (frm.doc.__islocal && frm.doc.__islocal == 1) frm.trigger('employee');
	},
	employee: function(frm) {
		frm.set_value('rule', undefined);
		frm.set_df_property('new_rule','reqd', frm.doc.employee ? 1 : 0);

		if(frm.doc.employee) {
			frappe.call({
				method: 'get_current_rule',
				doc: frm.doc,
				async: false,
				callback: function(r) {
					frm.refresh_field('rule');
				}
			});
		}
		else {
			frm.set_value('new_rule', undefined);
		}

		if(frm.doc.posting_date) {
			frm.trigger('posting_date');
		}
	},
	posting_date: function(frm) {
		frappe.call({
			method: 'validate_posting_date',
			doc: frm.doc,
			async: false,
			callback: function(r) {	}
		})
	}
})
