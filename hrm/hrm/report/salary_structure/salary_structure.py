# Copyright (c) 2013, avu and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from hrm.hrm.report import *

def execute(filters=None):

	if not filters: filters = {}
	# filters.update({
	# 	"from_date": filters.get("date_range") and filters.get("date_range")[0],
	# 	"to_date": filters.get("date_range") and filters.get("date_range")[1]
	# 	})

	nationality = 1 if filters.get('nationality') == 'Saudi' else 0 if filters.get('nationality') else None

	get_emp = "CALL salary_structure({0}, {1}, {2}, {3})".format(json.dumps(filters.get('company')), json.dumps(filters.get('employee')), json.dumps(filters.get('from_date')), json.dumps(nationality))
	get_emp = frappe.db.sql(get_emp,as_dict = True)

	component_order =  frappe.db.sql_list("""SELECT DISTINCT `SC`.`salary_component_abbr` AS `abbr`
											FROM `tabSalary Detail` AS `SD`
												INNER JOIN `tabSalary Component` AS `SC`
													ON `SC`.`name` = `SD`.`salary_component`
											WHERE `SD`.`docstatus` = 1 AND `SD`.`parenttype` = 'Salary Structure'
											GROUP BY `SD`.`salary_component`, `SD`.`parentfield`
											ORDER BY `SD`.`parentfield` DESC, `SC`.`name`, `SD`.`idx`;""")

	for row in get_emp:
		# frappe.errprint(row)
		# frappe.errprint(row.keys())
		total_amount = 0
		for _key in component_order:
			# idx = int(key[:key.find('#') if key.find('#') > 0 else 0] or 0)
			if (isinstance(row[_key],str) or not row[_key]):
				row[_key] = (frappe.safe_eval(row[_key], None, row) if row[_key] and len(str(row[_key]).strip()) > 0 else 0) or 0

		for key in sorted(row.keys()):
			# frappe.errprint(key)
			idx = int(key[:key.find('#') if key.find('#') > 0 else 0] or 0)
			if (idx > 6 or idx == 0) and (isinstance(row[key],str) or not row[key]):
				row[key] = (frappe.safe_eval(row[key], None, row) if row[key] and len(str(row[key]).strip()) > 0 else 0) or 0
				if key.find("#") > -1: total_amount += row[key]
		row["99#Total Amount:Currency:100"] = total_amount
	
	columns = get_columns(get_emp, 0)
	data = get_values_list(get_emp, 0)

	return columns, data
