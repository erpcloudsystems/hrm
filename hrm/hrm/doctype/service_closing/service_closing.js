// Copyright (c) 2019, Digitalprizm and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Closing', {
	setup: function(frm) {
		frm.set_query("employee", function () {
			return{
				filters: {
					company: frm.doc.company,
					status: 'Active'
				}
			}
		});

		frm.set_query("payment_account", function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});

		frm.set_query("expense_account", function() {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});
	},

	refresh: function(frm) {
		//Clear JV Entry and Salary slip Reference
		if(frm.doc.__islocal && frm.doc.amended_from) {
			frm.set_value("salary_slip", undefined);
			frm.set_value("journal_entry", undefined);
			
		}
		
		frm.trigger('make_disbursement');
	},

	make_disbursement: function(frm) {
		if (frm.is_new() || frm.doc.docstatus != 1) return;

		if(frm.doc.__onload && frm.doc.__onload.journal_entry) {
			frm.add_custom_button(__("View Disbursement Entry"), function() {
				frappe.set_route("List", "Journal Entry", { "name": frm.doc.__onload.journal_entry });
			}).addClass("btn-primary");
		}
		else {
			frm.add_custom_button(__("Make Disbursement Entry"), function() {
				frm.trigger("make_jv");
			}).addClass("btn-primary");
		}
	},

	make_jv: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "make_jv_entry",
			callback: function(r) {
				if (r.message)
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
			}
		});
	},

	employee: function(frm) {
		if(frm.doc.employee) {
			// if(frm.doc.__islocal) {
			// 	frappe.msgprint("Please Check the Attendance Process for employee "+frm.doc.employee+" has been Processed for the EOS Month")
			// }
			
			frm.trigger('service_detail');
		}
		else {
			clear_fields(frm, "employee");
		}
	},
	
	termination_date: function(frm) {
		frm.trigger('service_detail');
	},

	termination_type: function(frm) {
		frm.trigger('service_detail');
	},

	service_detail: function(frm) {
		if (!frm.doc.employee || !frm.doc.termination_date || !frm.doc.termination_type)
			return
		
		frappe.call({
			method: "service_detail",
			doc: frm.doc,
			args: { },
			freeze: true,
			freeze_message: "Loading....",
			callback: function(r) {
				frm.refresh_fields();
			}
		});
	},

	company: function(frm) {
		clear_fields(frm,"company");
	},

	total_adjustment: function(frm) {
		var total_additional = 0;
		var total_deducation = 0;

		(frm.doc.service_closing_adjustment || []).forEach((row) => {
			total_additional += (row.additional_amount || 0);
			total_deducation += (row.deduction_amount || 0);
		});

		frm.set_value('total_additional_amount', total_additional);
		frm.set_value('total_deduction_amount', total_deducation);

		var amount = (frm.doc.total_leave_encashment_amount || 0) + (frm.doc.sa_total_amount || 0) + (frm.doc.total_salary_amount || 0) + (frm.doc.total_additional_amount || 0) - (frm.doc.total_deduction_amount || 0);

		frm.set_value('total_amount', amount);
		frm.set_value('net_payable', amount);
	},
	total_service_period_in_days: function(frm) {
		if(frm.doc.total_service_period_in_days && (frm.doc.total_absent_days || frm.doc.total_absent_days == 0 )){
		frm.set_value("eligible_days_edays", frm.doc.total_service_period_in_days - frm.doc.total_absent_days);

		}
	},
	total_absent_days: function(frm) {
		if(frm.doc.total_service_period_in_days && (frm.doc.total_absent_days || frm.doc.total_absent_days == 0 )){
		frm.set_value("eligible_days_edays", frm.doc.total_service_period_in_days - frm.doc.total_absent_days);

		}
	},
	eligible_days_edays: function(frm) {
		if(frm.doc.total_absent_days>frm.doc.total_service_period_in_days)
		{
			frm.set_value("total_absent_days", 0);
			frappe.throw("Absent Days should'nt be more than or e Total Service Period Days");
		}
		else
		frappe.call({
			method: "calculate_service_awd",
			doc: frm.doc,
			args: { },
			callback: function(r) {
				frm.refresh_fields();
			}
		});
	}
});

function clear_fields(frm, source) {
	frm.set_value("joining_date", undefined);
	frm.set_value("iquama_no", undefined);
	frm.set_value("employee_name", undefined);
	frm.set_value("designation", undefined);
	frm.set_value("termination_type", "");
	frm.set_value("basic_salary", 0);
	frm.set_value("gross_pay_amount", 0);
	frm.set_value("total_service_period", "");
	frm.set_value("leave_encashment_balance", []);
	frm.set_value("total_leave_encashment_amount", 0);
	frm.set_value("present_days", 0);
	frm.set_value("salary_amount", 0);
	frm.set_value("ot_hours", 0);
	frm.set_value("ot_amount", 0);
	frm.set_value("loan_amount", 0);
	frm.set_value("total_salary_amt", 0);
	frm.set_value("loan_amount", 0);
	frm.set_value("service_award", []);
	frm.set_value("sa_total_amount", 0);
	frm.set_value("loan_advance", 0);
	frm.set_value("total_salary_amount", 0);
	frm.set_value("total_additional_amount", 0);
	frm.set_value("total_deduction_amount", 0);
	frm.set_value("total_amount", 0);
	frm.set_value("net_payable", 0);

	frm.set_value("total_service_period_in_days", 0);
	frm.set_value("total_absent_days", 0);
	frm.set_value("eligible_days_edays", 0);
	
	if(source == "company") {
		frm.set_value("employee", undefined);
		frm.set_value("payment_account", undefined);
		frm.set_value("expense_account", undefined);
	}

	frm.refresh_fields();
}


frappe.ui.form.on('Service Closing Adjustment', {
	service_closing_adjustment_remove: function(frm) {
		frm.trigger('total_adjustment');
	},

	additional_amount: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];

		if (row.additional_amount < 0) {
			row.additional_amount = 0;
			frappe.msgprint("Addition Amount Cannot be Less then Zero")
		}

		validate_either_value(row, 'additional_amount');
		frm.trigger('total_adjustment');
	},

	deduction_amount: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];

		if (row.deduction_amount < 0) {
			row.deduction_amount = 0;
			frappe.msgprint("Deduction Amount Cannot be Less then Zero")
		}

		validate_either_value(row, 'deduction_amount');
		frm.trigger('total_adjustment');
	}
});
frappe.ui.form.on('Service Closing Leave', {
	leave_balance:function(frm,cdt,cdn){
		
		frappe.call({
			method: "leave_balance",
			doc: frm.doc,
			args: { },
			freeze: true,
			freeze_message: "Loading....",
			callback: function(r) {
				
				frm.refresh_field("leave_encashment_balance");
			}
		});
	}
});

var validate_either_value = function(row, field) {
	if (row.additional_amount > 0 && row.deduction_amount > 0) {
		row[field] = 0
		frappe.msgprint("Both The Amount Cannot Be Assigned")
	}
}