// Copyright (c) 2018, Digitalprizm and contributors
// For license information, please see license.txt

frappe.ui.form.on('Vacation Leave Rule', {
	// validate: function(frm) {
	// 	if(frm.doc.eligible_after < 1) {
	// 		frappe.throw({ title: "Mandatory",
	// 			message: "Effective After Month field Should not be less then one"
	// 		});
	// 	}

	// 	if(frm.doc.days < 1) {
	// 		frappe.throw({ title: "Mandatory",
	// 			message: "Days field Should not be less then one"
	// 		});
	// 	}
		
	// 	if(frm.doc.redirect_after_year < 0) {
	// 		frappe.throw({ title: "Mandatory",
	// 			message: "Redirect After Year field Should not be less then Zero"
	// 		});
	// 	}
	// },

	redirect_after_year: function(frm) {
		frm.set_value('redirect_to_rule', undefined);
		frm.set_df_property('redirect_to_rule','reqd', (frm.doc.redirect_after_year && frm.doc.redirect_after_year > 0) ? 1 : 0);
	},

	eligible_after: function(frm) {
		frm.set_value('days', undefined);
		frm.set_df_property('days','reqd', (frm.doc.eligible_after && frm.doc.eligible_after > 0) ? 1 : 0);
	}
});
