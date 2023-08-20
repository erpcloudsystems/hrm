frappe.ui.form.on("Loan Application", {
	onload: function(frm){
		frm.trigger('default_loan_type');
		if (frm.doc.__islocal){
			if (frappe.session.user)
			{
				frappe.call({
					method: 'frappe.client.get_value',
					args: {
						'doctype': 'Employee',
						'filters': {'user_id': frappe.session.user},
						'fieldname': ['name']
					},
					callback: function(r) {
						if(r.message){
							frm.set_value("applicant",r.message.name)
						}
						else{
							frappe.msgprint("Employee Id Not Found for User Id "+ frappe.session.user)
						}
					}
				});
			}
			else
			{
				frappe.msgprint("Session User Not Found")
			}
		}
	},

	refresh: function(frm) {
		if (!frm.is_new()) return;
		frm.trigger('applicant');
	},

	applicant: function(frm) {
		frm.trigger('existing_loan');
		frm.trigger('eos_amt');
	},

	existing_loan: function(frm) {
		frm.set_value('existing_loan_amount', 0);
		if (!frm.doc.applicant) return;
		frappe.call({
			method: 'hrm.custom_script.loan_application.loan_application.get_balance_loan',
			args: {
				applicant: frm.doc.applicant
			},
			callback: function(r) {
				frm.set_value('existing_loan_amount', r.message);
			}
		});
	},

	required_by_date: function(frm) {
		frm.trigger('eos_amt');
	},

	eos_amt: function(frm) {
		frm.set_value('eos_amount', 0);
		if (!frm.doc.applicant || !frm.doc.required_by_date || !frm) return;
		frappe.call({
			method: 'hrm.custom_script.loan_application.loan_application.eos_amount',
			args: {
				applicant: frm.doc.applicant,
				required_date: frm.doc.required_by_date,
				company: frm.doc.company
			},
			callback: function(r) {
				frm.set_value('eos_amount', r.message);
			}
		});
	},

	default_loan_type: function(frm) {
		if(!frm.is_new()) return;
		frappe.db.get_value('Loan Type', {'default': 1, 'disabled': 0}, 'name', (r) => {
			if (r) {
				frm.set_value('loan_type', r.name);
			}
		});
	}
});