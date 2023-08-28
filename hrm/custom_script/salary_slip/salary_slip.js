frappe.ui.form.on('Salary Slip', {
	setup: function(frm) {
		frm.set_query('payroll_period', function() {
			return {
				filters: {
					'company': frm.doc.company
				}
			};
		});

		frm.add_fetch('payroll_period', 'start_date', 'start_date');
		frm.add_fetch('payroll_period', 'end_date', 'end_date');
	},

	validate: function(frm) {
		// var sy_date = moment(moment().format('YYYY-MM')+'-01').add(1,'M').format('YYYY-MM-DD');
		// if(frm.doc.start_date >= sy_date) {
		// 	frappe.throw('Salary Slip cannot be generated for future date');
		// }
		//Added by Rafik for Validating Amended from service closing
		if(frm.doc.__islocal && frm.doc.amended_from && frm.doc.service_closing) {
			frappe.throw('Cannot Amend Document Created From Service Closing');
		}
	},
	before_submit: function(frm) {
		frm.doc.earnings = []
		frm.doc.deductions = []
		frm.save();
		// console.log("before submit",frm.doc.earnings,frm.doc.deductions);

	},

	// refresh: function(frm) {
	// 	if (frm.doc.status == 'Paid') {
	// 		$($('span:contains("Cancel")', frm.$wrapper).parent('button')).css('display', 'none');
	// 	}
	// 	else {
	// 		$($('span:contains("Cancel")', frm.$wrapper).parent('button')).css('display', '');
	// 	}
	// 	frm.set_df_property('leave_without_pay', 'hidden', 1);

	// 	if(frm.doc.__islocal)
	// 		frm.set_value('custom_payroll_entry', undefined);
	// },

	company: function(frm) {
		frm.set_value('payroll_period', undefined);
	},

	payroll_period: function(frm) {
		if (!frm.doc.payroll_period) {
			frm.set_value('start_date', undefined);
			frm.set_value('end_date', undefined);
		}
	},

	// salary_slip_based_on_timesheet: function(frm) {
	// 	frm.set_df_property('leave_without_pay', 'hidden', 1);
	// },

	// payroll_frequency: function(frm) {
	// 	frm.set_df_property('leave_without_pay', 'hidden', 1);
	// }
})