# Copyright (c) 2013, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
import json
from frappe import _
from stira.stira.report.utils import get_columns, get_values_list

def execute(filters=None):
	from_date, to_date = frappe.db.get_value("Payroll Period", filters.get("payroll_period"), ["start_date", "end_date"]) if filters.get("payroll_period") else ['', '']
	filters.update({"from_date": from_date, "to_date": to_date})
	frappe.errprint(str(filters))
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
	# if not filters: filters = {}
	sql="call BankSalaryRegister({0},{1},{2},'{3}','{4}')".format(json.dumps(filters.get('company')),json.dumps(filters.get('employee')),json.dumps(doc_status[filters.get("docstatus")]),filters.get('from_date'),filters.get('to_date'))
	frappe.errprint(str(sql))
	dict = frappe.db.sql(sql, as_dict=1)
	columns = get_columns(dict)
	data = get_values_list(dict)
	return columns, data

def get_conditions(filters):
	conditions = ""
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

	if filters.get("docstatus"):
		conditions += "docstatus = {0}".format(doc_status[filters.get("docstatus")])

	if filters.get("from_date"): conditions += " and start_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and end_date <= %(to_date)s"
	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters

