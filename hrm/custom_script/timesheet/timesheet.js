frappe.ui.form.on('Timesheet', {
    refresh:function(frm){
        if (frm.is_new()){
            $.each(frm.doc.time_logs,function(i,v){
                v.confirm_yes_no=""
            });
        }
    },
    onload:function(frm){
            cur_frm.toggle_display("validate_punches",cur_frm.doc.workflow_state!="Approved")
    },
    validate_punches:function(frm){
        var items=cur_frm.doc.time_logs
        var flag=0;
        if(cur_frm.doc.time_logs.length==0){
            frappe.msgprint("Please Enter Details to Validate Punches!!!")
        }
        $.each(items,function(i,entry){
            frappe.call({
                method:'hrm.doctype_triggers.hr.timesheet.timesheet.set_check',
                async:true,
                args:{employee:cur_frm.doc.employee,
                    from_time:entry.from_time,
                    to_time:entry.to_time},
                callback:function(r){
                    console.log(r.message)
                    entry.employee_check=r.message[0]
                    entry.list_of_checkin=r.message[1]
                    if (r.message[0]==1){
                        frappe.confirm('Do you want to consider the Timsheet punches and ignore Employee Checkin which is between <b>'+entry.from_time+' to '+entry.to_time+'</b><br>'+r.message[1]+'',
                        function(){
                            // frappe.model.set_value(doctype,name,'confirm_check',1)
                            entry.confirm_yes_no="Yes"

                            // action to perform if Yes is selected
                            // flag=1;
                            if(cur_frm.doc.time_logs.length==entry.idx){
                                frappe.msgprint("Punches Validated Successfully!!")
                            }
                        }, function() {
                            entry.confirm_yes_no="No"
                            // flag=1;
                            if(cur_frm.doc.time_logs.length==entry.idx){
                                frappe.msgprint("Punches Validated Successfully!!")
                            }
                        })
                       
                    }
                    else if(r.message[0]==0 ){
                        entry.confirm_yes_no="Yes"
                        // flag=1;
                        if(cur_frm.doc.time_logs.length==entry.idx){
                            frappe.msgprint("Punches Validated Successfully!!")
                        }
                    }
                    // console.log(cur_frm.doc.time_logs.length,entry.idx)

                }
            })
            cur_frm.refresh_fields("time_logs")

        });
        // if(flag==1){
        //     frappe.msgprint("Punches Validated Successfully!!")
        // }

    }
});