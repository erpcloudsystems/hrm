// Copyright (c) 2016, AVU and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Bank Salary Register"] = {
	"filters": [
        {
			"fieldname":"payroll_period",
			"label": __("Payroll Period"),
			"fieldtype": "Link",
			"options": "Payroll Period",
			"reqd": 1
		},
		{
			"fieldname":"employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"docstatus",
			"label":__("Document Status"),
			"fieldtype":"Select",
			"options":["Draft", "Submitted", "Cancelled"],
			"default":"Submitted"
		}

	]
    ,
	"formatter":function(value, row, column, data, default_formatter) {
		var stop_loop = setInterval(()=>{
			$(".datatable").attr("dir", "rtl")
			clearInterval(stop_loop)
		})
		value = default_formatter(value, row, column, data);
		
		return value;
	}

};
