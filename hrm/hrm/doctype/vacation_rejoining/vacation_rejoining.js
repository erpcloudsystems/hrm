// Copyright (c) 2018, Digitalprizm and contributors
// For license information, please see license.txt

frappe.ui.form.on("Vacation Rejoining", {
	setup: (frm) => {
		frm.add_fetch("employee_id", "employee_name", "employee_name");
		frm.add_fetch("employee_id", "company", "company");

		frm.set_query('vacation_leave_application', () => {
			return {
				query: "hrm.hrm.doctype.vacation_rejoining.vacation_rejoining.get_leave",
				filters: {
					'employee': frm.doc.employee_id,
					'name': frm.doc.name
				}
			};
		});

		frm.set_query('employee_id', () => {
			return {
				query: "hrm.hrm.doctype.vacation_leave_application.vacation_leave_application.filter_employee"
			}
		});
	},

	employee_id: (frm) => {
		frm.set_value('vacation_leave_application', undefined);
		if( !frm.doc.employee_id) {
			frm.set_value('employee_name', undefined);
			frm.set_value('company', undefined);
		}
	},

	vacation_leave_application: (frm) => {
		if(!frm.doc.vacation_leave_application) {
			frm.set_value('start_date', undefined);
			frm.set_value('end_date', undefined);
			frm.set_value('leave_approver', undefined);
			frm.set_value('leave_approver_name', undefined);
		}
		frm.trigger('extend_vacation');
	},

	refresh: (frm) => {
		if (frm.is_new()) {
			frm.set_value('vacation_leave_application', undefined);
			frm.set_value('vacation_rejoining_date', undefined);
		}
		
		frm.set_df_property('extend_vacation', 'allow_on_submit', frm.doc.__onload ? frm.doc.__onload.read_only : 1);
		frm.set_df_property('vacation_rejoining_date', 'allow_on_submit', frm.doc.__onload ? frm.doc.__onload.read_only : 1);
	},

	extend_vacation: (frm) => {
		if (frm.doc.extend_vacation == 1 && frm.doc.end_date)
			frm.set_value('vacation_rejoining_date', frappe.datetime.add_days(frm.doc.end_date, 1));
	}
});