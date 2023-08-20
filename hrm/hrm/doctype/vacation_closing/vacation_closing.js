// Copyright (c) 2019, Digitalprizm and contributors
// For license information, please see license.txt
//Written by Jayesh & Vishnu

frappe.ui.form.on('Vacation Closing', {
	setup: function (frm) {
		frm.add_fetch('leave_application_reference','employee_id','employee');
		frm.add_fetch('leave_application_reference','eligible_days','previous_leave_balance');
		frm.add_fetch('leave_application_reference','total_leave_days','vacation_days');
		
		frm.set_query("payment_account", function () {
			return {
				filters: [
					["company", "=", frm.doc.company],
					["is_group", "=", 0] 
				]
			}
		});

		frm.set_query("employee_loan_account", function () {
			return {
				filters: [
					["company", "=", frm.doc.company],
					["is_group", "=", 0]
				]
			}
		});

		frm.set_query("interest_income_account", function () {
			return {
				filters: [
					["company", "=", frm.doc.company],
					["is_group", "=", 0]
				]
			}
		});

		frm.set_query("leave_application_reference", function () {
			return {
				query: "hrm.hrm.doctype.vacation_closing.vacation_closing.get_leave_application",
				filters: {
					'company': frm.doc.company,
					'name': frm.doc.name
				}
			}
		});
	},

	refresh: function (frm) {
		frm.set_df_property ('salary_end_date', 'read_only',1);
		frm.set_df_property('earnings','read_only',1);
		frm.set_df_property('deductions','read_only',1);

		frm.trigger('toggle_salary_date');
		$('li:contains("Duplicate")').hide()
		
		if (frm.doc.docstatus == 1) {
			if (frm.custom_buttons) frm.clear_custom_buttons();
			if (frm.doc.ignore_account_effect != 1) frm.events.add_context_buttons(frm);
		}
	},

	onload: function(frm) {
		if(frm.doc.__islocal == 1){
			frm.set_value('employee_loan_reference',undefined);

			if (frm.doc.amended_from == undefined) {
				frm.set_value('temp_reference',undefined);
			}
		}
	},

	add_context_buttons: function(frm) {
		frappe.call({
			method: 'has_jv_entries',
			doc: frm.doc,
			args: {	},
			async: false,
			callback: function(r) {
				if (r.message && r.message.submitted) {
					frm.add_custom_button("View Disbursement Entry",
						function() {
							frappe.set_route("Form", 'Journal Entry', r.message.submitted);
						});
				}
				else {
					frm.add_custom_button("Make Disbursement Entry",
						function() {
							frm.trigger("make_jv");
						}).addClass("btn-primary");
				}
			}
		});
	},

	make_jv: function (frm) {
		frappe.call({
			doc: frm.doc,
			method: "make_jv_entry",
			async: false,
			callback: function (r) {
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
			}
		})
	},

	company: function (frm) {
		frm.set_value("leave_application_reference", undefined);
	},

	leave_application_reference: function (frm) {
		if (!frm.doc.leave_application_reference) {
			['advance_amount','different_ticket','grand_total','leave_from','leave_to','repayment_date','previous_leave_balance','total_leave_balance','vacation_days','basic_salary','attendance_days','salary_processed_amount','present_day_salary','mode_of_payment','employee_loan_account','payment_account','interest_income_account','iquama_no','employee','employee','joining_date','nationality','last_rejoining_date','salary_start_date','salary_end_date','earnings','deductions'].forEach(field => {
				frm.set_value(field, undefined);
			});
			frm.refresh_fields();
		}
	},

	ultra_trigger: function (frm) {
		if(frm.doc.employee) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Employee",
					fieldname: ["date_of_joining", "iqama_no","nationality"],
					filters: {
						name: frm.doc.employee
					},
				},
				async: false,
				callback: function (r) {
					if (r.message) {
						var data = r.message;
						frm.set_value("iquama_no", data["iqama_no"]);
						frm.set_value("joining_date", data["date_of_joining"]);
						frm.set_value("nationality", data["nationality"]);
						refresh_many(['iquama_no','joining_date','nationality']);
					}
				}
			});
		}
	},

	salary_start_date: function (frm) {
		frm.trigger('employee');
	},


	salary_end_date: function (frm) {
		frm.trigger('employee');
	},

	enable_salary_date: function(frm) {
		frm.trigger('employee');
		frm.trigger('toggle_salary_date');
	},
	toggle_salary_date: function(frm) {
		if(frm.doc.enable_salary_date == 0) {
			frm.set_value('salary_end_date',undefined);
			frm.refresh_field('salary_end_date');
			frm.set_df_property('salary_end_date','reqd',0);
			frm.set_df_property('salary_end_date', 'read_only',1);
		
		}
		else if(frm.doc.enable_salary_date == 1) {
			frm.set_df_property('salary_end_date','reqd',1);
			frm.set_df_property('salary_end_date', 'read_only',0);
		}
		
	},
	employee: function (frm) {
		frm.trigger('ultra_trigger');
		frm.set_value('salary_start_date',frm.doc.leave_from ? moment(frm.doc.leave_from).startOf("month").format() : undefined)
		
		if (frm.doc.employee && (frm.doc.salary_start_date || frm.doc.leave_from) && (frm.doc.salary_end_date|| frm.doc.leave_to)) {
			frappe.call({
				method: "get_sal_and_attendance",
				doc: frm.doc,
				args: {	},
				async: false,
				callback: function (r) {
					refresh_many(['last_rejoining_date','attendance_days','present_day_salary','salary_processed_amount','grand_total','earnings','deductions']);
				}
			});
		}
		
		
	},

	advance_amount: function (frm) {
		if (frm.doc.advance_amount < 0) {
			frm.set_value('advance_amount', 0.0);
			frm.refresh_field('advance_amount');
			frappe.msgprint("Advance can't be negative");
		}
		frm.trigger('set_grand_total');
	},

	different_ticket: function(frm) {
		if (frm.doc.different_ticket < 0) {
			frm.set_value('different_ticket', 0.0);
			frm.refresh_field('different_ticket');
			frappe.msgprint("Different Ticket can't be negative");
		}
		frm.trigger('set_grand_total');
	},

	set_grand_total: function(frm) {
		frm.set_value('grand_total', parseFloat(frm.doc.advance_amount || 0.0) + parseFloat(frm.doc.salary_processed_amount || 0.0) + parseFloat(frm.doc.present_day_salary || 0.0) - parseFloat(frm.doc.different_ticket || 0));
		frm.refresh_field('grand_total');
	},

	previous_leave_balance: function(frm) {
		// console.log('in')
		if(frm.doc.previous_leave_balance && frm.doc.vacation_days) {
			frm.set_value('total_leave_balance',frm.doc.previous_leave_balance - frm.doc.vacation_days)
		}
	}
});