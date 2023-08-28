// Copyright (c) 2018, Digitalprizm and contributors
// For license information, please see license.txt
cur_frm.add_fetch("employee", "employee_name", "employee_name");
cur_frm.add_fetch("reported_to", "employee_name", "investigation_reporter_name"); 
cur_frm.add_fetch("employee", "employee_name", "incident_reported_againce");   
frappe.ui.form.on('Employee Complaint Form', {
	on_submit:function(frm) {
	   cur_frm.add_custom_button(__('Issue Warning'), function() {
			frappe.set_route("Form", "Warning Letter","New Warning Letter",{"complaint_id":cur_frm.doc.name,"employee_id":cur_frm.doc.employee});
		});
	},
	employee: function(frm){
		cur_frm.set_query("employee", function () {
			return{
				filters: { 'status': 'Active' }
			}
		});
	}
});
