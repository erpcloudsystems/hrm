from __future__ import unicode_literals
import frappe
from frappe import _

def get_comp_name(attr, raise_error=1):
	data = frappe.db.sql("SELECT name FROM `tabSalary Component` WHERE salary_component_abbr = '"+attr+"'", as_dict=True)
	if data:
		return data[0]['name']
	else:
		if not raise_error: return
		frappe.throw(_("Salary Component Not Found for Abbreviation -- <b> "+str(attr)+"</b>"))


def get_leve_name(attr):
	data = frappe.db.sql("SELECT name FROM `tabLeave Type` WHERE leave_type_abbr ='"+attr+"'", as_dict=True)
	if data:
		return data[0]['name']
	else:
		frappe.throw(_("Leave Type Not Found for Abbreviation --<b> "+str(attr)+"<b>"))


def set_comp_val(doc, comp_type, salary_component, value, include=False):
	if str(comp_type) in ["Deduction",'Earning']:
		field_name = str(comp_type).lower() + "s"
		flag = False
		
		for i in doc.get(field_name):
			if i.salary_component == str(salary_component):
				flag = True
				if include:
					i.amount += value
				else:
					i.amount = value
		
		if flag:
			pass
		elif value >= 0:
			row = doc.append(field_name, {})
			row.salary_component = str(salary_component)
			row.amount = float(value)
