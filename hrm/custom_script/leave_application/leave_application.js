frappe.ui.form.on('Leave Application', {
	refresh: function(frm) {
		// frm.trigger('leave_type');
		if(frm.is_new())
		frappe.msgprint("Please create Leave Application from Leave Request or Vacation Leave Application");
	},
	
	leave_type: function(frm) {
		if(frm.doc.leave_type && frm.doc.leave_type == 'Vacation') {
			frm.disable_save();
		}
		else {
			frm.enable_save();
		}
	},
	before_save: function(frm){
		if(frm.is_new())
		frappe.throw("Please create Leave Application from Leave Request or Vacation Leave Application");
	},
	before_cancel: function(frm){
		if(frm.doc.leave_request || frm.doc.vacation_leave_application)
		frappe.throw("Please cancel Leave Application from Leave Request or Vacation Leave Application");
	}
}); 