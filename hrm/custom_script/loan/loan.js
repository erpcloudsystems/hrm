frappe.ui.form.on('Loan', {
	refresh: function(frm) {
		if (frm.is_new())
        {
            frappe.db.get_value('Employee', {'name': cur_frm.doc.applicant}, 'employee_name', (r) => {
                if (r) {
                    frm.set_value('applicant_name', r.employee_name);
                }
            });
            
        }
        
	}
});