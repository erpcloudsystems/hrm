frappe.ui.form.on("Designation", {
	setup: function(frm) {
		frm.set_query('ot_rule', function(doc) {
			return {
				filters: {
					docstatus: 1
				}
			}
		});
	}
});