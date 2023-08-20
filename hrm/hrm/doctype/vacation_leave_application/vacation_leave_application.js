// // Copyright (c) 2018, Digitalprizm and contributors
// // For license information, please see license.txt

frappe.ui.form.on('Vacation Leave Application', {
	setup: (frm) => {
		frm.add_fetch('employee_id', 'employee_name', 'employee_name');
		frm.add_fetch('employee_id', 'company', 'company');

		frm.set_query('employee_id', () => {
			return {
				query: "hrm.hrm.doctype.vacation_leave_application.vacation_leave_application.filter_employee"
			}
		});

		frm.set_query("leave_approver", () => {
			return {
				query: "erpnext.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: frm.doc.employee_id,
					doctype: 'Leave Application'
				}
			};
		});
	},

	refresh: (frm) => {
		if (frm.is_new() && frm.doc.employee_id) {
			frm.trigger('employee_id');
            
		}
        if(frm.is_new()){
            frm.set_value("status","Open")
        }

		if (!frm.doc.employee_id && frappe.defaults.get_user_permissions()) {
			const perm = frappe.defaults.get_user_permissions();
			if (perm && perm['Employee']) {
				frm.set_value('employee_id', perm['Employee']["docs"][0]);
			}
		}

		if(frm.doc.docstatus == 1) {
			frm.trigger('val_ticket');
		}

		frm.dashboard.clear_headline();
		if(frm.doc.__islocal) {
			frm.trigger('clear_field');
			frm.set_value('from_date', undefined);
			frm.set_value('to_date', undefined);
			frm.set_value('warning_msg', undefined);
			frm.refresh_fields();
		}
		else {
			var msg = "";
			if (frm.doc.warning_msg && frm.doc.docstatus < 2) msg = repl(`<span style="color: red; font-weight: bold;">%(msg)s</span>`, {msg : frm.doc.warning_msg});
			frm.dashboard.set_headline(msg);
		}
	},

	employee_id: (frm) => {
		frm.trigger('get_ledg_record');
		frm.trigger("set_leave_approver");

		if(!frm.doc.employee_id) {
			frm.set_value("employee_name", undefined);
		}
	},

	to_date: (frm) => {
		frm.trigger('validate_date');
	},

	from_date: (frm) => {
		frm.trigger('get_ledg_record');
		frm.trigger('validate_date');
	},

	get_ledg_record: (frm) => {
		frappe.run_serially([
			() => frm.trigger('clear_field'),
			() => {
				if (frm.doc.from_date && frm.doc.employee_id) {
					frappe.call({
						method: "new_get_accrual_till",
						doc: frm.doc,
						args: {	},
						async: false,
						callback: (r) => {	}
					});
				}
			},
			() => frm.refresh_fields()
		]);
	},
	
	clear_field: function(frm){
		frm.set_value("eligible_days", 0);
		frm.set_value("applied_rule", undefined);
		frm.set_value("last_vacation", undefined);
		frm.set_value("total_working_days", 0);
	},

	set_leave_approver: (frm) => {
		if(frm.doc.employee_id) {
			// server call is done to include holidays in leave days calculations
			return frappe.call({
				method: 'erpnext.hr.doctype.leave_application.leave_application.get_leave_approver',
				args: {
					"employee": frm.doc.employee_id,
				},
				callback: (r) => {
					if (r && r.message) {
						frm.set_value('leave_approver', r.message);
					}
				}
			});
		}
	},

	validate_date: (frm) => {
		frm.set_value("total_leave_days", undefined);
		
		if(frm.doc.to_date && frm.doc.from_date) {
			if(frm.doc.from_date > frm.doc.to_date) {
				frappe.throw({ title:"Warning",
					message:"To Date cannot be less then From Date"
				});
			}
			else {
				var date_diff = moment.duration(moment(frm.doc.to_date,'YYYY-MM-DD').diff(moment(frm.doc.from_date,'YYYY-MM-DD'))).asDays() + 1;
				frm.set_value("total_leave_days", date_diff);
			}
		}
	},

	leave_approver: (frm) => {
		frm.set_value("leave_approver_name", undefined);

		if(frm.doc.leave_approver) {
			frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
		}
	},

	// validate: function(frm) {
	// 	var special_leav = Number();

	// 	if (Number(frm.doc.total_leave_days) > Number(frm.doc.eligible_days)) {
	// 		if(Number(frm.doc.eligible_days) > 0) {
	// 			special_leav = frm.doc.total_leave_days - frm.doc.eligible_days;
	// 		}
	// 		else {
	// 			special_leav = frm.doc.total_leave_days;
	// 		}
	// 	}
		
	// 	if((frm.selected_workflow_action=='Approved' || (!frm.selected_workflow_action && frm.doc.status == 'Approved')) && Number(special_leav) > 0) {
	// 		frappe.confirm(
	// 				"Employee " + frm.doc.employee_id + " has applied for Special leave for " + flt(special_leav, precision('eligible_days')) + " days",
	// 			() => {
	// 				frm.set_value('request_advance_leave', 1);
	// 				},
	// 			() => {
	// 				frm.set_value('request_advance_leave', 0);
	// 			}
	// 		)
	// 	}
	// },

	val_ticket: (frm) => {
		frm.clear_custom_buttons();

		if(frm.doc.employee_id && frm.doc.status == "Approved") {
			frappe.call({
				method: 'validate_eligible_employee',
				doc: frm.doc,
				args: {	},
				async: false,
				callback: (r) => {
					var employee_data = r.message[0];
					if(employee_data && employee_data.eligible_for_airline_ticket == 1) {
						if(employee_data.mode_of_reimbursement == "Ticket") {
							make_ticket_booking(frm, employee_data);
						}
						if(employee_data.mode_of_reimbursement == "Cash") {
							make_cash_reimbursement(frm, employee_data);
						}
						make_re_entry(frm);
					}
				}
			});
		}
	}
});

let make_ticket_booking = (frm, emp) => {
	frm.add_custom_button(__('Ticket'), () => {
		frappe.call({
			method: "airline_ticket_request",
			args: {
				emp: emp
			},
			doc: frm.doc,
			callback: function (r) {
				var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		});
	});
}

let make_cash_reimbursement = (frm,emp) => {
	frm.add_custom_button(__('Send Alert'), () => {
		var dialog = new frappe.ui.Dialog({
			title: __("Cash Reimbursement"),
			fields: [{'fieldname': 'Cash', 'fieldtype': 'Int', 'default': emp.eligible_cash,'label': 'Cash'},
				{'fieldname': 'Notify', 'fieldtype': 'Button','label': 'Notify'}]
		});

		dialog.fields_dict.Notify.input.onclick = () => {
			var cash = $("input[data-fieldname='Cash']").val();

			new frappe.views.CommunicationComposer({
				sender: "jagdishn@avu.net.in",
				subject: "Re: cash",
				recipients: "jagdishr@avu.net.in",
				message: "The above employee has been allocated respective amount as traving expance" + cash
			});
		}
		dialog.show();
	});
}

let make_re_entry = (frm) => {
	frm.add_custom_button(__('Exit ReEntry Visa'), () => {
		frappe.call({
			method: "exit_reentry_visa",
			doc: frm.doc,
			callback: function (r) {
				var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		});
	});
}