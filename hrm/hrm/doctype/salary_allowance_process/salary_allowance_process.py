# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import json
from frappe.utils.data import add_days
from frappe.utils.csvutils import UnicodeWriter, read_csv_content
from frappe.utils import cstr
import re

class SalaryAllowanceProcess(Document):
	
	def val_date(self):
		if self.payroll_period:
			sql_sal = """SELECT *
				FROM `tabSalary Allowance Process Value`
				WHERE allowance_type = 'Monthly'
				AND (end_date BETWEEN '{0}' AND '{1}'
				OR start_date BETWEEN '{0}' AND '{1}')""".format(add_days(self.from_date, 1), add_days(self.to_date, -1))
			sql_sal_adj = frappe.db.sql(sql_sal, as_dict=1)

			if sql_sal_adj:
				frappe.throw("There is already a data between this period")
	
	def get_prev_data(self):
		self.val_date()

		sql_sal_adj_prev = """SELECT employee, salary_component, value
			FROM `tabSalary Allowance Process Value`
			WHERE allowance_type = '{0}'
			AND value > 0
			AND start_date = '{1}'""".format(self.allowance_type, self.from_date)

		return frappe.db.sql(sql_sal_adj_prev, as_dict=1)

	
	def salary_slip_val(self):
		sql_val_sal_slip = """SELECT employee
			FROM `tabSalary Slip`
			WHERE docstatus = 1
			AND ( start_date = '{0}'
			OR '{0}' BETWEEN `start_date` AND `end_date` )""".format(self.from_date)
		
		return frappe.db.sql(sql_val_sal_slip, as_dict=1)


	def get_data(self):
		emp_com_list = []
		employee_sql = """
			SELECT name, employee_name, enroll_number
			FROM `tabEmployee`
			WHERE status = 'Active'
			AND (date_of_joining <= '{0}'
				OR date_of_joining <= '{1}')
			AND company = '{2}'
			AND IFNULL(`department`, 0) = IFNULL({3}, IFNULL(`department`, 0))
			AND IFNULL(`branch`, 0) = IFNULL({4}, IFNULL(`branch`, 0))
			AND IFNULL(`designation`, 0) = IFNULL({5}, IFNULL(`designation`, 0))
		""".format(self.from_date, self.to_date or self.from_date, self.company, json.dumps(self.department), json.dumps(self.branch), json.dumps(self.designation))
		val = frappe.db.sql(employee_sql, as_dict=1)
		
		com = frappe.db.sql("SELECT name, salary_component_abbr FROM `tabSalary Component` WHERE salary_allowance_process = 1", as_dict=1)

		emp_com_list.append({
			'emp_detail': val,
			'salary_component': com
		})

		return emp_com_list


	def insert_sal_adj(self, emp_id, salary_component, value):
		get_data_ifexist = """SELECT name
			FROM `tabSalary Allowance Process Value`
			WHERE employee = '{0}'
			AND salary_component = '{1}'
			AND allowance_type = '{2}'
			AND start_date = '{3}'
		""".format(emp_id,salary_component, self.allowance_type, self.from_date)
		get_data_ifexist = frappe.db.sql(get_data_ifexist, as_dict=1)
		
		if get_data_ifexist:
			get_data_ifexist = get_data_ifexist[0]
			frappe.client.set_value("Salary Allowance Process Value", get_data_ifexist['name'], 'value', value)
		else:
			if float(value) > 0:
				ledg = frappe.new_doc("Salary Allowance Process Value")				
				ledg.payroll_period = self.payroll_period
				ledg.start_date = self.from_date
				ledg.end_date = self.to_date or self.from_date
				ledg.employee = emp_id
				ledg.employee_name = frappe.db.get_value("Employee", emp_id, "employee_name")
				ledg.company = self.company
				ledg.salary_component = salary_component
				ledg.allowance_type = self.allowance_type
				ledg.value = value
				
				ledg.insert(ignore_permissions=True)
				ledg.save()

		return 'Inserted'

	def update_sal_adj(self, sal_comp_val):
		self.val_date()

		for sal_detail in sal_comp_val:
			self.insert_sal_adj(sal_detail['emp_name'], sal_detail['comp_name'].strip(), sal_detail['comp_val'])

		return "Updated Successfully"


@frappe.whitelist()
def get_template():
	args = frappe.local.form_dict
	
	if not frappe.has_permission("Salary Allowance Process", "create"):
		raise frappe.PermissionError

	w = UnicodeWriter()
	w = add_header(w)
	w = add_data(w, args)

	frappe.response['result'] = cstr(w.getvalue())
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = "Salary Allowance Process"

def _column():
	com = frappe.db.sql("SELECT name, salary_component_abbr FROM `tabSalary Component` WHERE salary_allowance_process = 1", as_dict=1)

	return ["Employee", "Employee Name"] + [com_el.get('name') for com_el in com]

def add_header(w):
	columns = _column()
	
	w.writerow(["Notes:"])
	w.writerow(["Please do not change the template headings"])
	string_comp = ",".join(columns[2:])
	w.writerow(["Salary Component Should be in [{0}]".format(string_comp)])
	w.writerow([])
	w.writerow(columns)
	return w

def add_data(w, args):
	for row in frappe.db.sql("""SELECT name, employee_name, enroll_number
		FROM `tabEmployee`
		WHERE status = 'Active'
		AND company = '{0}'
		AND '{2}' >= date_of_joining
		AND('{1}' <= date_of_retirement
			OR date_of_retirement IS NULL)""".format(str(args.get('company')), str(args.get('from_date')), str(args.get('to_date'))),as_dict=1):
		w.writerow([row.name, row.employee_name])
	return w

@frappe.whitelist()
def excel_upload():
	fname = frappe.local.uploaded_filename
	fcontent = frappe.local.uploaded_file
	if not frappe.safe_encode(fname).lower().endswith("csv".encode('utf-8')):
		frappe.throw(_("Document with extension CSV can only be uploaded"))
	
	data = read_csv_content(fcontent, False)

	excel_data = []

	columns = _column()
	col_count = 0
	for i in range(4, len(data)):
		if i == 4:
			if not len(data[i]) == len(columns):
				frappe.msgprint(_("Please Upload Standard Template"))
				return

			if data[i][0] != columns[0] or data[i][1] != columns[1] or data[i][2] != columns[2] or data[i][3] != columns[3]:
				frappe.msgprint("Please Do not Change Column Name in Template")
				return
			
			for idx in range(len(columns)):
				if data[i][idx] != columns[idx]:
					frappe.msgprint("Please Do not Change Column Name in Template")
					return

		elif len(data[i]) > 2:
			if not frappe.db.exists("Employee", {"name": data[i][0]}): continue
			
			for idx in range(len(data[i]) - 2):
				if data[i][idx + 2]:
					regexp = re.compile("^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$")
					if bool(regexp.match(data[i][idx + 2])) and float(data[i][idx + 2]) >= 0:
						excel_data.append({
							'employee': data[i][0],
							'salary_component': columns[idx + 2],
							'value': float(data[i][idx + 2])
						})
					else:
						frappe.msgprint("<b style='font-size:22px;'>Upload Failed</b><br>Amount should be of type int or float")
						return

	return excel_data