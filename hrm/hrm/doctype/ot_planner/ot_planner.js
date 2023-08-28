// Copyright (c) 2020, AVU and contributors
// For license information, please see license.txt

frappe.ui.form.on('OT Planner', {
	setup: function(frm) {
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

	employee: function(frm) {
		frm.trigger("set_leave_approver");
		frm.trigger('ot_rule');
	},

	set_leave_approver: function(frm) {
		if(frm.doc.employee) {
			// server call is done to include holidays in leave days calculations
			return frappe.call({
				method: 'hrms.hr.doctype.leave_application.leave_application.get_leave_approver',
				args: {
					"employee": frm.doc.employee,
				},
				callback: function(r) {
					if (r && r.message) {
						frm.set_value('leave_approver', r.message);
					}
				}
			});
		}
	},

	leave_approver: function(frm) {
		if(frm.doc.leave_approver) {
			frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
		}
	},

	planned_number_of_minutes_ot_per_day: function(frm) {
		frm.set_value('approved_maximum_ot_allowed_per_day', frm.doc.planned_number_of_minutes_ot_per_day);
	},

	from_date: function(frm) {
		frm.trigger('ot_rule');
	},

	ot_rule: function(frm) {
		if (!frm.doc.employee || !frm.doc.from_date) return
		frappe.call({
			method: 'valid_ot_rule',
			args: {	},
			doc: frm.doc,
			callback: function(r) {
				frm.refresh_fields();
			}
		})
	}
});
