// Copyright (c) 2016, avu and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Salary Structure"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1,
			"on_change": function() {
				// frappe.query_report_filters_by_name.employee.set_value(undefined);
				frappe.query_report.refresh();
			}
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			// "get_query": function() {
			// 	var company = frappe.query_report_filters_by_name.company.get_value();
			// 	return {
			// 		"doctype": "Employee",
			// 		"filters": {
			// 			"company": company
			// 		}
			// 	}
			// }
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": [frappe.datetime.month_start()]
		},
		// {
		// 	"fieldname": "date_range",
		// 	"label": __("Between Date"),
		// 	"fieldtype": "DateRange",
		// 	"default": [frappe.datetime.month_start(), frappe.datetime.month_end()]
		// },
		{
			"fieldname": "nationality",
			"label": __("Nationality"),
			"fieldtype": "Select",
			"options": "\nSaudi\nNon Saudi",
		}
	]
};
