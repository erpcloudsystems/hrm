// Copyright (c) 2021, aavu and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Schedular', {
    fetch_table: function(frm) {
       $(frm.fields_dict.employee_table.wrapper).empty();
        frm.employee_table_holder = $('<div>')
        .appendTo(frm.fields_dict.employee_table.wrapper);
        if( frm.doc.period_from && frm.doc.branch)
      { 
        frm.employee_table_wrapper = new erpnext.EmployeeSchedule(frm, frm.employee_table_holder);}
    },
    fetch_date: function(frm){
        // if(!frm.doc.period_from) {
            frappe.call({
            "method": "hrm.hrm.doctype.shift_schedular.shift_schedular.get_dates",
            async: true,
            args:{
                "branch":me.frm.doc.branch
            },
            callback: function (r) {
                // frm.doc.set_value();
               $(frm.fields_dict.employee_table.wrapper).empty();

                if(r.message.length==0)
                frm.set_df_property("period_from","read_only",0);
                else{
                frm.set_df_property("period_from","read_only",1);
                frm.doc.period_from = r.message[0]["period_to"];
                frm.trigger("period_from");
                frm.trigger("fetch_table");
            }}
        }); 
    //  }
        // else{
         
        // }  
    },
	refresh: function(frm) {

if(window.getComputedStyle(document.querySelector('.layout-side-section')).display =="block"){
 var a = document.getElementsByClassName("sidebar-toggle-btn")[0];
    console.log(window.getComputedStyle(document.querySelector('.layout-side-section')).display);
    a.click();    
}

        if(frm.doc.__islocal == 1 && frm.doc.employee_schedule)
        {
        for(var i = 0;i<frm.doc.employee_schedule.length;i++){
            if(frm.doc.employee_schedule[i].shift_assignment!="" ||frm.doc.employee_schedule[i].shift_assignment){
                frm.doc.employee_schedule[i].shift_assignment=""; 
            }
        }
        }
        if(frm.doc.docstatus==1)
        frm.add_custom_button(__("Notify Employee"), function() {
            // When this button is clicked, do this
    
            frappe.call({
                "method": "notify_employee",
                async: true,
                doc:frm.doc,
                callback: function (r) {
                    // frm.doc.set_value();
                  
                }            }); 
        });
		$(frm.fields_dict.employee_table.wrapper).empty();
        frm.employee_table_holder = $('<div>')
        .appendTo(frm.fields_dict.employee_table.wrapper);
        
        if(frm.doc.branch)
       { 
    //    frm.trigger("fetch_date"); 
       frm.trigger("fetch_table");
      }
	},
    shift_type: function(frm) {
        // if(frm.doc.shift_type)
        // frm.employee_table_wrapper = new erpnext.EmployeeSchedule(frm, frm.employee_table_holder);
        var box = document.getElementsByClassName("box");
        for(var i = 0;i<box.length;i++){
            $(box[i]).prop("checked",false);
        }
        for(var i = 0;i<frm.doc.employee_schedule.length;i++){
            var date = frm.doc.employee_schedule[i].date.split("-");
            date = parseInt(date[0])+"-"+ parseInt(date[1])+"-"+ parseInt(date[2]);
           var a = document.querySelectorAll('[data-module="'+frm.doc.employee_schedule[i].employee+'"][date="'+date+'"]');
           var div =$($(a).closest("td").find(".shifts")[0]);
           div.html('<div style="background-color:#bbbbbb;">'+frm.doc.employee_schedule[i].shift_type+'</div>');
           if(frm.doc.employee_schedule[i].shift_type == frm.doc.shift_type)
          { 
            $(a).prop("checked",true);}
        }
    },
    branch: function(frm) {
        me.frm.doc.employee_schedule =[];
        if(frm.doc.branch)
        frm.trigger("fetch_date"); 
    },
    period_from: function(frm){
        if(frm.doc.period_from){
            var date = new Date(frm.doc.period_from);
            date.setDate(date.getDate() + 6);
            frm.doc.period_to = date.getFullYear()+"-"+ (date.getMonth()+1)+"-"+date.getDate() ;
            frm.refresh_fields();
            frm.trigger("fetch_table");

        }
    },
    before_submit:function(frm){
        var a = document.querySelectorAll('.employee-col');
        if((a.length-1)*7 > frm.doc.employee_schedule.length)
        frappe.throw("Select Shift for all employees for all selected days");
        
    }
    
});

erpnext.EmployeeSchedule = Class.extend({
	init: function(frm, wrapper) {
		this.frm = frm;
		this.wrapper = wrapper;
		// this.employee_data = {};
		this.make();
	},

	make: function() {
		var me = this;
		$(this.wrapper).empty();
        const date = new Date(me.frm.doc.period_from);
        var dates      = [date.getDate()+"-"+ (date.getMonth()+1)+"-"+ date.getFullYear()];
        for(var i =0 ;i<6;i++){
            date.setDate(date.getDate() + 1);
            dates.push([date.getDate()+"-"+ (date.getMonth()+1)+"-"+ date.getFullYear()])
        }
        var html ="<style>th,td{text-align:center; border:solid; padding:5px;} .shifts{min-height:20px;} .all-shift{height:20px;} .employee-col{text-align:left;}</style><table style='width: 100%;'><tr style='height: 45px;'><th class='employee-col' style='width:40%;'>Employee</th><th></th><th>"+dates[0]+"</th>"+"<th>"+dates[1]+"</th><th>"+dates[2]+"</th><th>"+dates[3]+"</th><th>"+dates[4]+"</th><th>"+dates[5]+"</th><th>"+dates[6]+"</th></tr>";
        html +="<tbody id='table_body'></tbody></table>"
        this.wrapper.html(html);
        frappe.call({
            "method": "hrm.hrm.doctype.shift_schedular.shift_schedular.get_employee",
            async: true,
            args:{
                "branch":me.frm.doc.branch
            },
            callback: function (r) {
                var body=""
                for (var i=0; i<r.message.length;i++){
                    body +='<tr><th class="employee-col">'+ r.message[i][1] +"("+r.message[i][0]+')'+'</th><td><button type="checkbox" style="margin-top:0px;" class="all-box btn btn-primary btn-sm ">Make Default</button><div class="all-shift"></div></td>';
                for (var j=0; j<dates.length;j++)
                  { 
                      var a = dates[j] + '';
                    var b = a.split("-");
                    var c = b[2];
                    b[2]=b[0];
                    b[0]=c;
                    b= b.join("-");
                    // b= new Date(b.join("-"))  ;
                    body += '<td><input type="checkbox" style="margin-top:0px;" class="box" data-module="'+r.message[i][0]+'" date="'+b+'"';
                   
                    if(me.frm.doc.docstatus ==1 ||me.frm.doc.docstatus ==2)
                    body +='disabled checked>'
                    else
                    body +='>'
                    body +='<div class="shifts"></div></td>';
                }
                    body +=   '</tr>';
                    
                }
             
                document.getElementById('table_body').innerHTML=body;

                var box = document.getElementsByClassName(".box");
                for(var i = 0;i<box.length;i++){
                    $(box[i]).prop("checked",false);
                    if(me.frm.doc.docstatus ==1 ||me.frm.doc.docstatus ==2)
                    {box[i].disabled = true;
                        $(box[i]).prop("checked",true);
                    
                    }
                }
                for(var i = 0;i<me.frm.doc.employee_schedule.length;i++){
                    var date = me.frm.doc.employee_schedule[i].date.split("-");
                    date = parseInt(date[0])+"-"+ parseInt(date[1])+"-"+ parseInt(date[2]);
                   var a = document.querySelectorAll('[data-module="'+me.frm.doc.employee_schedule[i].employee+'"][date="'+date+'"]');
                   var div =$($(a).closest("td").find(".shifts")[0]);
                   div.html('<div style= "background: #bbbbbb;">' +me.frm.doc.employee_schedule[i].shift_type+  '</div>');
                   if(me.frm.doc.employee_schedule[i].shift_type == me.frm.doc.shift_type)
                  { 
                      
                    $(a).prop("checked",true);}
                }
            }
        });
        if(me.frm.doc.docstatus ==0 )
        this.bind();

	},

	set_data: function(data) {
		
	},
    bind: function() {
		var me = this;
		this.wrapper.on("change", ".box", function() {
            if(me.frm.doc.shift_type)
         {   // var div =$(this).closest(".shifts");
            var div =$($(this).closest("td").find(".shifts")[0]);
			var employee = $(this).attr('data-module');
			var date = $(this).attr('date');
            me.frm.doc.employee_schedule = $.map(me.frm.doc.employee_schedule || [], function(d) {
                if (!(d.employee == employee && d.date == date)) {
                    return d;
                }
            });
			if($(this).prop("checked")) {
				me.frm.add_child("employee_schedule", {"employee": employee,"date": date,"shift_type":me.frm.doc.shift_type});
                div.html('<div style= "background: #b3f3b3;">' + me.frm.doc.shift_type+ '</div>');			
			} else {
                div.html("");			
			}
            }
            else{
                $(this).prop("checked",false);
                frappe.throw("Select Shift Type");
            }
		});

		this.wrapper.on("click", ".all-box", function() {
            if(me.frm.doc.shift_type)
          {  var row = $(this).closest("tr").find(".shifts");
            console.log(row,row.length,row[0]);
            for(var i =0; i<row.length;i++)
            {
                console.log(row[i],$(row[i]).html(),i)
                if($(row[i]).html()=="")
                {
                   var check = $($(row[i]).closest("td").find(".box")[0]);
                   $(check).trigger('click');
                }
            }}
            else{
                frappe.throw("Select Shift Type");
            }
		});

	}
});