// Copyright (c) 2021, AVU and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Allocation', {
	refresh: function(frm) {
        $("button[data-fieldname=get_employee]").addClass("btn-primary");
	},
    onload:function(frm){
        $("button[data-fieldname=get_employee]").addClass("btn-primary");
    },
    get_employee:function(frm){
        if(cur_frm.doc.company){
            frappe.call({
                method: "get_employee",
                doc: frm.doc,
                args: {
                },
                callback: function(r) {
                    if (r.message){
                        console.log(r.message)
                        var data=r.message
                        cur_frm.clear_table("employee_details");
                        for(var i=0;i<data.length;i++){
                            
                            var row = cur_frm.fields_dict.employee_details.grid.add_new_row();
                            frappe.model.set_value(row.doctype, row.name, "employee", data[i].employee);
                            frappe.model.set_value(row.doctype, row.name, "employee_name", data[i].employee_name);
                            frappe.model.set_value(row.doctype, row.name, "department", data[i].department);

                        }
                        cur_frm.refresh_fields();
                    }
                   
                }
            })
        }
        else
		{
			cur_frm.clear_table("employee_details");
			cur_frm.refresh_fields();
		}
    }

});
