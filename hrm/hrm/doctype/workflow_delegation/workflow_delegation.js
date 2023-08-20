// Copyright (c) 2020, avu and contributors
// For license information, please see license.txt

frappe.ui.form.on('Workflow Delegation', {
    refresh: function(frm) 
   {    
       cur_frm.set_df_property("workflow_delegation_details","read_only",1)
       cur_frm.set_df_property("update_workflow_delegation_log","read_only",1)
       if(cur_frm.doc.__islocal)
       {
           cur_frm.set_value("update_workflow_delegation_log",[])
       }
       if(cur_frm.doc.reference_id)
       { 
           $("li > a:contains('Duplicate')").hide()
           cur_frm.set_df_property("employee","read_only",1)
           cur_frm.set_df_property("from_date","read_only",1)
           cur_frm.set_df_property("to_date","read_only",1)
       }
       else{
           cur_frm.set_df_property("employee","read_only",0)
           cur_frm.set_df_property("from_date","read_only",0)
           cur_frm.set_df_property("to_date","read_only",0)
       }
       if(cur_frm.doc.docstatus==1)
       {
           frm.add_custom_button(__("Schedule WorkFlow Delegation"), function() {
               cur_frm.trigger('scheduler_trigger');
           }).addClass("btn-primary");
       }
       cur_frm.set_query("employee", function() {
           return {
               filters: [
                   ["Employee","status","=",'Active']
               ]
           };
       });
   },
   setup:function(frm)
   {
       cur_frm.set_query("employee", function() {
           return {
               filters: [
                   ["Employee","status","=",'Active']
               ]
           };
       });
   },
   onload:function(frm)
   {
       if(cur_frm.doc.employee && cur_frm.doc.reference_id && cur_frm.doc.__islocal && cur_frm.doc.amended_from==undefined)
       {
           frappe.call({
               method:"hrm.hrm.doctype.workflow_delegation.workflow_delegation.get_user_role",
               args:{"employee":cur_frm.doc.employee},
               callback:function(r)
               {
                   if(r.message.length>0)
                   {
                       cur_frm.set_df_property("workflow_delegation_details_section","hidden",0)
                       cur_frm.set_value("workflow_delegation_details",r.message)
                   }
                   else{
                       cur_frm.set_value("employee_name",undefined)
                       cur_frm.set_value("workflow_delegation_details",[])
                   }
                  
               }
           })
       }
   },
   employee:function(frm)
   {
       if(cur_frm.doc.employee && cur_frm.doc.amended_from==undefined)
       {
           frappe.call({
               method:"hrm.hrm.doctype.workflow_delegation.workflow_delegation.get_user_role",
               args:{"employee":cur_frm.doc.employee},
               callback:function(r)
               {
                  if(r.message.length>0)
                  {
                       cur_frm.set_value("workflow_delegation_details",r.message)
                  }
                  else
                  {
                      cur_frm.set_value("employee",undefined)
                      frappe.throw("Workflow Is Not Active Or Not Assign Any Workflow To Existing Employee")
                  }
                   
               }
           })
       }
       else{
           cur_frm.set_value("employee_name",undefined)
           cur_frm.set_value("workflow_delegation_details",[])
       }
   },

   setup:function(frm)
   {
       cur_frm.set_query("user_role", "workflow_delegation_details", function(doc, cdt, cdn) {
           var child = locals[cdt][cdn]
           return {
               query: "hrm.hrm.doctype.workflow_delegation.workflow_delegation.get_element",  
               filters: {
                   parent: child.workflow_name,
                   doctype:child.workflow_doctype
               }
           };
       });
       cur_frm.set_query("delegated_role", "workflow_delegation_details", function(doc, cdt, cdn) {
           // var child = locals[cdt][cdn]
           return {
               // query: "stira.stira.doctype.workflow_delegation.workflow_delegation.get_username", 
                filters: {"enabled":1}
               
           };
       })
   
   },
   from_date:function(frm)
   {
       cur_frm.trigger("date_validate")
   },
   to_date:function(frm)
   {
       cur_frm.trigger("date_validate")
   },
  
   date_validate(frm)
   {
       if(cur_frm.doc.from_date && cur_frm.doc.to_date)
       {
           if(cur_frm.doc.from_date>cur_frm.doc.to_date)
           {
               frappe.throw("From Date Should Be Less Than To Date")
           }
       }
   },
   scheduler_trigger:function(frm)
   {
       frappe.call({
           method:"hrm.hrm.doctype.workflow_delegation.workflow_delegation.assign_delegated_role",
           args:{},
           callback:function(r)
           {

           }
       })
   }
});


frappe.ui.form.on('Workflow Delegation Details', {
   delegated_role:function(frm,cdt,cdn)
   {
       var row = locals[cdt][cdn]  
       if(row.delegated_role==undefined)
       {
           row.user_email_id=undefined
           cur_frm.refresh_fields("workflow_delegation_details")
       }
   }
})
