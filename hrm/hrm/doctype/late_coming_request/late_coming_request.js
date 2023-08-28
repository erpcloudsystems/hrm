// Copyright (c) 2020, AVU and contributors
// For license information, please see license.txt

frappe.ui.form.on('Late Coming Request', {
	setup: (frm) => {
		frm.set_query("leave_approver", function() {
			return {
				query: "hrms.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: frm.doc.employee,
					doctype: 'Leave Application'
				}
			};
		});

		frm.set_query("employee", erpnext.queries.employee);
	},
	
	onload: function(frm) {
		frm.trigger("set_leave_approver");
	},

	refresh: function(frm) {
		frappe.db.get_value('Employee', {
			'user_id': frappe.session.user
		}, 'name',
		(r) => {
			frm.toggle_enable('employee', !(r && r.name));
		});
	},

	employee: function(frm) {
		frm.trigger("set_leave_approver");
		frm.trigger("get_default_value");
	},

	attendance_date: function(frm) {
		frm.trigger("get_default_value");
	},

	number_of_minutes_late: function(frm) {
		frm.set_value('approved_number_of_minutes_late', frm.doc.number_of_minutes_late);
	},

	set_leave_approver: function(frm) {
		if(frm.doc.employee) {
			// server call is done to include holidays in leave days calculations
			return frappe.call({
				method: 'hrms.hr.doctype.leave_application.leave_application.get_leave_approver',
				args: {
					"employee": frm.doc.employee,
				},
				async: false,
				callback: function(r) {
					if (r && r.message) {
						frm.set_value('leave_approver', r.message);
					}
				}
			});
		}
	},

	leave_approver: (frm) => {
		frm.set_value("leave_approver_name", undefined);

		if(frm.doc.leave_approver) {
			frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
		}
	},

	get_default_value: (frm) => {
		if (!frm.doc.employee || !frm.doc.attendance_date) return;

		frappe.call({
			method: 'att_application',
			doc: frm.doc,
			args: {
				"validate": 0,
			},
			freeze: true,
			freeze_message: __('Get Dafault Late Coming'),
			callback: function(r) {
				frm.set_value('number_of_minutes_late', frm.doc.actual_number_of_minutes_late);
				frm.set_value('approved_number_of_minutes_late', frm.doc.actual_number_of_minutes_late);
				frm.refresh_fields();
			}
		});
	}
});
