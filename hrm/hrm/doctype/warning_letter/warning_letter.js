// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
cur_frm.add_fetch("employee_id", "employee_name", "employee_name");
frappe.ui.form.on('Warning Letter', {
	refresh:function(frm){
		cur_frm.set_query("employee_id", function () {
			return{
				filters: { 'status': 'Active' }
			}
		});
	},
	employee_id: function(frm) {
		if(cur_frm.doc.employee_id)
		frappe.call({
					method: 'hrm.hrm.doctype.warning_letter.warning_letter.previous_warning',
					args: { employee: frm.doc.employee_id },
					callback: function(r)

					{ 
				var data=r
				//console.log(r);
				var m =data.message
				var e=data.message[2]
				var w=data.message[1]
				var s =data.message[3]
				
			//console.log(m)
				//console.log(e)
			
			frm.set_value("warning_no",data.message[1] )
				frm.set_value("warring_issued_by", data.message[0])
				frm.set_value("last_warning_date", e)
				cur_frm.set_df_property("last_warning_date", "read_only", 1);
				cur_frm.set_df_property("warring_issued_by", "read_only", 1);
					}
			});

			if (frm.doc.employee_id) 
			{
				frm.add_fetch("employee", "employee_name", "employee_name");
			}
			else 
			{
				frm.set_value("employee_name", "") 
			}
			}
});
	




