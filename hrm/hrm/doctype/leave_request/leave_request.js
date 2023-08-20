// Copyright (c) 2020, AVU and contributors
// For license information, please see license.txt

cur_frm.add_fetch('employee','employee_name','employee_name');
cur_frm.add_fetch('employee','company','company');

frappe.ui.form.on("Leave Request", {
	setup: function(frm) {
		frm.set_query("leave_approver", function() {
			return {
				query: "erpnext.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: frm.doc.employee,
					doctype: frm.doc.doctype
				}
			};
		});
		frm.set_query("leave_type", function() {
			return {
				filters: {
					is_default: 0
				}
			}
		});

		frm.set_query("employee", erpnext.queries.employee);
	},
	onload: function(frm) {

		// Ignore cancellation of doctype on cancel all.
		frm.ignore_doctypes_on_cancel_all = ["Leave Ledger Entry"];

		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", frappe.datetime.get_today());
		}
		if (frm.doc.docstatus == 0) {
			return frappe.call({
				method: "hrm.hrm.doctype.leave_request.leave_request.get_mandatory_approval",
				args: {
					doctype: frm.doc.doctype,
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						frm.toggle_reqd("leave_approver", true);
					}
				}
			});
		}
	},

	validate: function(frm) {
		if (frm.doc.from_date == frm.doc.to_date && frm.doc.half_day == 1){
			frm.doc.half_day_date = frm.doc.from_date;
		}else if (frm.doc.half_day == 0){
			frm.doc.half_day_date = "";
		}
		frm.toggle_reqd("half_day_date", frm.doc.half_day == 1);
	},

	make_dashboard: function(frm) {
		var leave_details;
		let lwps;
		if (frm.doc.employee) {
			frappe.call({
				method: "hrm.hrm.doctype.leave_request.leave_request.get_leave_details",
				async: false,
				args: {
					employee: frm.doc.employee,
					date: frm.doc.from_date || frm.doc.posting_date
				},
				callback: function(r) {
					if (!r.exc && r.message['leave_allocation']) {
						leave_details = r.message['leave_allocation'];
					}
					if (!r.exc && r.message['leave_approver']) {
						frm.set_value('leave_approver', r.message['leave_approver']);
					}
					lwps = r.message["lwps"];
				}
			});
			$("div").remove(".form-dashboard-section.custom");
			frm.dashboard.add_section(
				frappe.render_template('leave_application_dashboard', {
					data: leave_details
				}),
				__("Allocated Leaves")
			);
			frm.dashboard.show();
			let allowed_leave_types =  Object.keys(leave_details);

			// lwps should be allowed, lwps don't have any allocation
			allowed_leave_types = allowed_leave_types.concat(lwps);

			frm.set_query('leave_type', function(){
				return {
					filters : [
						['leave_type_name', 'in', allowed_leave_types]
					]
				};
			});
		}
	},

	refresh: function(frm) {
        if(cur_frm.doc.__islocal)
        {
            cur_frm.set_value("workflow_delegation_id",undefined)
        }
        var hr_setting = frappe.db.get_single_value('HR Settings', 'enable_workflow_delegation')
        var p = Promise.resolve(hr_setting);
        p.then(function(v) {
            var enable_setting = v;
            if(enable_setting==0) {
                cur_frm.set_df_property("ignore_workflow_delegation","hidden",1)
            }
            else {
                if(enable_setting==1) {
                    cur_frm.set_df_property("ignore_workflow_delegation","hidden",0)
                }
            }
            if(enable_setting==1 && cur_frm.doc.ignore_workflow_delegation==0 && cur_frm.doc.workflow_delegation_id == undefined && cur_frm.doc.docstatus==0 && cur_frm.doc.__islocal==undefined && cur_frm.doc.status=="Open") {
                frm.add_custom_button(__("Make WorkFlow Delegation"), function() {
                    cur_frm.trigger('make_workflow_delegation');
                }).addClass("btn-primary");
            }
            
                      
		});
      
		if (cur_frm.doc.workflow_delegation_id) {
			frm.add_custom_button(__("View Workflow Delegation"), function() {
				frappe.set_route("List", "Workflow Delegation",{"reference_id":cur_frm.doc.name})
			}).addClass("btn-primary");
        }

		if (frm.is_new()) {
			frm.trigger("calculate_total_days");
			if(frm.doc.employee) {
				frm.trigger('employee');
			}
            frm.set_value("status","Open")
		}
		cur_frm.set_intro("");
		if(frm.doc.__islocal && !in_list(frappe.user_roles, "Employee")) {
			frm.set_intro(__("Fill the form and save it"));
		}

		if (!frm.doc.employee && frappe.defaults.get_user_permissions()) {
			const perm = frappe.defaults.get_user_permissions();
			if (perm && perm['Employee']) {
				frm.set_value('employee', perm['Employee'].map(perm_doc => perm_doc.doc)[0]);
			}
		}
        frm.toggle_enable('attach_document', 0);
		frm.toggle_enable('salary_days_compensation', 0);
	},
    make_workflow_delegation: function(frm){
		frappe.call({
			method: "hrm.hrm.doctype.leave_request.leave_request.make_workflow_delegation",
			// doc: frm.doc,
            args: {
				"name":cur_frm.doc.name,
				"employee":cur_frm.doc.employee,
				"employee_name":cur_frm.doc.employee_name,
				"from_date":cur_frm.doc.from_date,
				"to_date":cur_frm.doc.to_date
			},
			callback: function(r) {
				if (r.message){
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
			}
		})
	},
	employee: function(frm) {
		// frm.trigger("make_dashboard");
		frm.trigger("get_leave_balance");
		frm.trigger("set_leave_approver");
		frm.trigger("get_workflow_delegation");
	},

	leave_approver: function(frm) {
		if(frm.doc.leave_approver){
			frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
		}
	},
	get_workflow_delegation:function(frm){
        if(frm.doc.employee && frm.doc.from_date && frm.doc.to_date){
            frappe.call({
                method:'hrm.hrm.doctype.leave_request.leave_request.get_workflow_delegation',
                args:{
                    "employee":frm.doc.employee,
                    "from_date":frm.doc.from_date,
                    "to_date":frm.doc.to_date,
                    "doctype":frm.doc.doctype
                },
                callback:function(r){
					console.log(r,'eee')
                    if(r.message){
                        // console.log("in> ",r.message)
                        cur_frm.set_value('ignore_workflow_delegation', r.message);
                        // cur_frm.refresh_fields();
                    }
                }
            })
        }
    },
	leave_type: function(frm) {
		frm.trigger("get_leave_balance");
	},

	half_day: function(frm) {
		if (frm.doc.half_day) {
			if (frm.doc.from_date == frm.doc.to_date) {
				frm.set_value("half_day_date", frm.doc.from_date);
			}
			else {
				frm.trigger("half_day_datepicker");
			}
		}
		else {
			frm.set_value("half_day_date", "");
		}
		frm.trigger("calculate_total_days");
	},

	from_date: function(frm) {
		// frm.trigger("make_dashboard");
		frm.trigger("half_day_datepicker");
		frm.trigger("calculate_total_days");
		frm.trigger("get_workflow_delegation");
	},

	to_date: function(frm) {
		frm.trigger("half_day_datepicker");
		frm.trigger("calculate_total_days"); 
		frm.trigger("get_workflow_delegation");
	},

	half_day_date(frm) {
		frm.trigger("calculate_total_days");
	},

	half_day_datepicker: function(frm) {
		frm.set_value('half_day_date', '');
		var half_day_datepicker = frm.fields_dict.half_day_date.datepicker;
		half_day_datepicker.update({
			minDate: frappe.datetime.str_to_obj(frm.doc.from_date),
			maxDate: frappe.datetime.str_to_obj(frm.doc.to_date)
		})
	},

	get_leave_balance: function(frm) {
		if(frm.doc.docstatus==0 && frm.doc.employee && frm.doc.leave_type && frm.doc.from_date && frm.doc.to_date) {
			frm.set_value('leave_balance',0)
			// return 
			frappe.call({
				method: "get_leave_balance_on",
				// args: {self:frm.doc},
				doc: frm.doc,
				callback: function(r) {
					console.log(r.message,'sdfsd')
					// if (!r.exc && r.message) {
					// 	frm.set_value('leave_balance', r.message);
					// }
					// else {
					// 	frm.set_value('leave_balance', 0);
					// }
					frm.refresh_fields();
				}
			});
		}
		// if(frm.doc.docstatus==0 && frm.doc.employee && frm.doc.leave_type && frm.doc.from_date && frm.doc.to_date) {
		// 	return frappe.call({
		// 		method: "erpnext.hr.doctype.leave_application.leave_application.get_leave_balance_on",
		// 		args: {
		// 			employee: frm.doc.employee,
		// 			leave_type: frm.doc.leave_type,
		// 			date: frm.doc.from_date
		// 		},
		// 		callback: function(r) {
		// 			console.log(r.message,'rrr')
		// 			if (!r.exc && r.message) {
		// 				frm.set_value('leave_balance', r.message);
		// 			}
		// 			else {
		// 				frm.set_value('leave_balance', "0");
		// 			}
		// 		}
		// 	});
		// }
	},

	calculate_total_days: function(frm) {
		if(frm.doc.from_date && frm.doc.to_date && frm.doc.employee && frm.doc.leave_type) {

			var from_date = Date.parse(frm.doc.from_date);
			var to_date = Date.parse(frm.doc.to_date);

			if(to_date < from_date){
				frappe.msgprint(__("To Date cannot be less than From Date"));
				frm.set_value('to_date', '');
				return;
			}
			// server call is done to include holidays in leave days calculations
			return frappe.call({
				method: 'hrm.hrm.doctype.leave_request.leave_request.get_number_of_leave_days',
				args: {
					"employee": frm.doc.employee,
					"leave_type": frm.doc.leave_type,
					"from_date": frm.doc.from_date,
					"to_date": frm.doc.to_date,
					"half_day": frm.doc.half_day,
					"half_day_date": frm.doc.half_day_date,
				},
				callback: function(r) {
					if (r && r.message) {
						frm.set_value('total_leave_days', r.message);
						frm.trigger("get_leave_balance");
					}
				}
			});
		}
	},

	set_leave_approver: function(frm) {
		if(frm.doc.employee) {
			// server call is done to include holidays in leave days calculations
			return frappe.call({
				method: 'hrm.hrm.doctype.leave_request.leave_request.get_leave_approver',
				args: {
					"employee": frm.doc.employee,
				},
				callback: function(r) {
					if (r && r.message) {
						frm.set_value('leave_approver', r.message);
					}
				}
			});
		}
	}
});

