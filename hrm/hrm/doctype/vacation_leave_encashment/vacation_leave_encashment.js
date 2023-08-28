// Copyright (c) 2019, avu and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vacation Leave Encashment', {
	setup: function(frm) {
		frm.add_fetch('employee', 'iqama_no', 'iqama_no');

		frm.set_query('expense_account', () => {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0,
					"root_type": "Expense"
				}
			}
		});

		frm.set_query('payment_account', () => {
			return {
				filters: {
					'company': frm.doc.company,
					'is_group': 0,
				}
			}
		});

		frm.set_query('employee', () => {
			return {
				query: "hrm.hrm.doctype.vacation_leave_application.vacation_leave_application.filter_employee"
			}
		});
	},

	refresh: function(frm) {
		if (frm.doc.docstatus == 1) {
			if (frm.custom_buttons) frm.clear_custom_buttons();
			frm.events.add_context_buttons(frm);
		}
		
		frm.set_df_property('payment_account','reqd', frm.doc.__islocal ? 0 : 1);
		frm.set_df_property('expense_account','reqd', frm.doc.__islocal ? 0 : 1);
	},

	company: function(frm) {
		frm.set_value('expense_account', undefined);
		frm.set_value('payment_account', undefined);
	},

	employee: function(frm) {
		// fill from-date from either employee master or vacation rejoining page--by Pranali
		frm.set_value("from_date", undefined);

		if (frm.doc.employee) {
			frappe.call({
				method: "get_from_date",
				doc: frm.doc,
				args: {	},
				async: false,
				freeze: true,
				freeze_message: "Loading...",
				callback: function(r) {
					frm.refresh_field('from_date');
				}
			});
		}
		else {
			//  Empty related fields if employee is empty
			frm.set_value("date_of_joining", undefined);
			frm.set_value("employee_name", undefined);
			// frm.set_value("iqama_no", undefined);
			frm.set_value("company", undefined);
			// ----------------------
		}
		// ----------------------------------------------------------------------------------
		frm.trigger('calculate_vacation_day');
	},

	to_date: function(frm) {
		// validate dates
		if(frm.doc.from_date && frm.doc.to_date && frm.doc.from_date > frm.doc.to_date) {
			frappe.throw("To Date Cannot be Less Than From Date");
		}
		
		frm.trigger('calculate_vacation_day');
	},

	calculate_vacation_day: function(frm) {
		frm.set_value("days", undefined);
		
		if(frm.doc.to_date && frm.doc.employee) {
			frappe.call({
				method: "calcuate_days",
				doc: frm.doc,
				args: {	},
				async: false,
				freeze: true,
				freeze_message: "Loading...",
				callback: function(r) {
					refresh_many(["days", "pay_days", "amount"]);
				}
			});
		}
	},

	pay_days: function(frm) {
		frm.set_value("amount", 0);
		
		if(frm.doc.pay_days && frm.doc.pay_days > 0 && frm.doc.pay_days <= frm.doc.days && frm.doc.employee && frm.doc.posting_date) {
			frappe.call({
				method: "calcuate_days_and_amount",
				doc: frm.doc,
				args: {	},
				async: false,
				freeze: true,
				freeze_message: "Loading...",
				callback: function(r) {
					frm.refresh_field('amount');
				}
			});
		}
		else {
			if (frm.doc.pay_days) {
				if (frm.doc.pay_days > frm.doc.days) {
					frm.set_value('pay_days', frm.doc.days);
					frappe.msgprint("Pay Days Cannot be Greater than Eligible Days");
				}
				else {
					frm.set_value('pay_days', frm.doc.days);
					frappe.msgprint("Pay Days Cannot be Less than or Equal to Zero");
				}
			}
		}

		frm.set_value('balance_days', (frm.doc.days || 0) - (frm.doc.pay_days || 0));
	},

	// mode_of_payment: function (frm) {
	// 	frm.set_value("payment_account", undefined);
	// 	if (frm.doc.company && frm.doc.mode_of_payment) {
	// 		frappe.call({
	// 			method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
	// 			args: {
	// 				"mode_of_payment": frm.doc.mode_of_payment,
	// 				"company": frm.doc.company
	// 			},
	// 			async: false,
	// 			callback: function (r) {
	// 				if (r.message) {
	// 					frm.set_value("payment_account", r.message.account);
	// 				}
	// 			}
	// 		});
	// 	}
	// },

	add_context_buttons: function(frm) {
		frappe.call({
			method: 'leave_encashment_has_jv_entries',
			doc: frm.doc,
			args: {	},
			callback: function(r) {
				if (r.message) {
					if(r.message.submitted == 0) {
						frm.add_custom_button("JV Entry",
							function() {
								make_journal_entry(frm);
							},
							__('Make')
						);
						frm.page.set_inner_btn_group_as_primary(__('Make'));
					}
					else {
						frm.add_custom_button("JV Entry",
							function() {
								frappe.set_route("Form", 'Journal Entry', r.message.submitted);
							},
							__('View')
						);
						frm.page.set_inner_btn_group_as_primary(__('View')); 
					}
				}
			}
		});
	}
});


let make_journal_entry = function (frm) {
	var doc = frm.doc;
	
	if(!doc.company){
		frappe.throw(__("Company is mandatory"));
	}
	else if(!doc.from_date){
		frappe.throw(__("From Date is mandatory"));
	}
	else if(!doc.to_date){
		frappe.throw(__("To Date is mandatory"));
	}
	else if(!doc.payment_account){
		frappe.throw(__("Payment Account is mandatory"));
	}
	else if(!doc.expense_account){
		frappe.throw(__("Expense Account is mandatory"));
	}
	
	return frappe.call({
		doc: doc,
		method: "make_journal_entry",
		freeze: true,
		freeze_message: __("Creating Journal Entries......"),
		callback: function(r) {
			if (r.message)
				var doc = frappe.model.sync(r.message)[0];
			Object.assign(doc , {'__onload': {'rounted': 1}})
			frappe.set_route("Form", doc.doctype, doc.name);
		}
	});
};