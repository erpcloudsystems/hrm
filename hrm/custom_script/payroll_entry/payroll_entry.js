frappe.ui.form.on('Payroll Entry', {
	setup: function (frm) {
    	frm.set_query("payroll_period", function () {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});
    },
    company: function (frm) {
        frm.doc.payroll_period = "";
		frm.refresh_field('payroll_period');

    }
});