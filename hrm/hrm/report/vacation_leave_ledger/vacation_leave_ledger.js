// Copyright (c) 2016, AVU and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Vacation Leave Ledger"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.user_defaults.company,
			"reqd": 1,
			on_change: function() {
				frappe.query_report.set_filter_value('employee', undefined);
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"reqd": 1,
			"get_query": function() {
				return {
					query: "hrm.hrm.doctype.vacation_leave_application.vacation_leave_application.filter_employee",
					filters: {
						'company': frappe.query_report.get_filter_value('company')
					}
				}
			}
		},
		{
			"fieldname": "system_date",
			"label": __("System Date"),
			"fieldtype": "Date",
			'hidden': 1
		}
	]
};
