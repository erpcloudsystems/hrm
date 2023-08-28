frappe.ui.form.on('Shift Request', {
    refresh:function(frm){
console.log("in")
    },
    before_cancel:function(frm){
        if(cur_frm.doc.shift_allocations!=undefined){

        
        frappe.call({
            method: "hrm.custom_script.shift_request.shift_request.oncancel",
            async:false,
            args: {
                "shift_allocation":cur_frm.doc.shift_allocations
            },
            callback: function(r) {
                console.log("in callback")
                if (r.message){
                    console.log(r.message)
                    var data=r.message
                    console.log(data)
                    // frappe.throw("Shift Request cannot be cancelled as it is linked with Shift Allocation <b><a href='#Form/Shift Allocation/"+shift_allocation+"'>"+shift_allocation+"</a></b>")
                    if(data==1){
                        console.log("if")
                        msgprint(__("Shift Request cannot be cancelled as it is linked with Shift Allocation <b><a href='#Form/Shift Allocation/"+cur_frm.doc.shift_allocations+"'>"+cur_frm.doc.shift_allocations+"</a></b>"));
                        validated=false;
                        return false;
                    }
                }
               
            }
        })
    }
    }
});