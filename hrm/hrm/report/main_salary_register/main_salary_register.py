# Copyright (c) 2013, AVU and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	
	from_date, to_date = frappe.db.get_value("Payroll Period", filters.get("payroll_period"), ["start_date", "end_date"]) if filters.get("payroll_period") else ['', '']
	filters.update({"from_date": from_date, "to_date": to_date})
	
	salary_slips = get_salary_slips(filters)
	if not salary_slips: return [], []
	
	default_value = salary_component()

	columns, earning_types, ded_types = get_columns(salary_slips)
	ss_earning_map = get_ss_earning_map(salary_slips, default_value)
	ss_ded_map = get_ss_ded_map(salary_slips, default_value)
	doj_map = get_employee_doj_map()

	data = []
	for ss in salary_slips:
		row = [ss.employee, ss.employee_name, ss.payment_days]

		for e in earning_types:
			value = 0
			earning_dict = ss_earning_map.get(ss.name, default_value)
			if e.get('formula_base'):
				value = (frappe.safe_eval(e.get('formula'), None, earning_dict) if e.get('formula') and len(str(e.get('formula')).strip()) > 0 else 0) or 0
			else:
				value = earning_dict.get(e.get('name'))
			row.append(value)

		row += [ss.gross_pay]

		for d in ded_types:
			deducation_dict = ss_ded_map.get(ss.name, default_value)
			if d.get('formula_base'):
				value = (frappe.safe_eval(d.get('formula'), None, deducation_dict) if d.get('formula') and len(str(d.get('formula')).strip()) > 0 else 0) or 0
			else:
				value = deducation_dict.get(d.get('name'))
			row.append(value)

		row.append(ss.total_loan_repayment)

		row += [ss.total_deduction+ss.total_loan_repayment, ss.net_pay]

		data.append(row)

	return columns, data

def get_columns(salary_slips):
	"""
	columns = [
		_("Salary Slip ID") + ":Link/Salary Slip:150",_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140",
		_("Date of Joining") + "::80", _("Branch") + ":Link/Branch:120", _("Department") + ":Link/Department:120",
		_("Designation") + ":Link/Designation:120", _("Company") + ":Link/Company:120", _("Start Date") + "::80",
		_("End Date") + "::80", _("Leave Without Pay") + ":Float:130", _("Payment Days") + ":Float:120"
	]
	"""
	columns = [
		_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140",
		_("Payment Days") + ":Float:100"
	]

	salary_components = {_("Earning"): [], _("Deduction"): []}

	for component in frappe.db.sql("""select distinct ifnull(sc.name, scd.name) as name
		, ifnull(sc.type, scd.type) as type
 		, if(sc.name is not null, sc.formula, 0) as formula
 		, if(sc.name is not null, 1, 0) as formula_base
		 , if(sc.name is not null, sc.order_index, scd.order_index) as order_idx
		from `tabSalary Detail` sd
		inner join `tabSalary Component` scd
			on scd.name = sd.salary_component
			and sd.amount != 0
		left join `tabSalary Component` sc
			on sc.amount_based_on_formula = 1
			and sc.statistical_component = 1
			and sc.salary_register_caption_field = 1
			and locate(scd.salary_component_abbr, sc.formula) > 0
		where sd.parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1):
		salary_components[_(component.type)].insert(component.order_idx, component)
	
	salary_components[_("Earning")].sort(key = lambda i: i['order_idx'])
	salary_components[_("Deduction")].sort(key = lambda i: i['order_idx'])
	
	columns = columns + [(e.get('name') + ":Currency:120") for e in salary_components[_("Earning")]] + \
		[_("Gross Pay") + ":Currency:120"] + [(d.get('name') + ":Currency:120") for d in salary_components[_("Deduction")]] + \
		[_("Loan Repayment") + ":Currency:120", _("Total Deduction") + ":Currency:120", _("Net Pay") + ":Currency:120"]

	return columns, salary_components[_("Earning")], salary_components[_("Deduction")]

def get_salary_slips(filters):
	filters.update({"from_date": filters.get("from_date"), "to_date":filters.get("to_date")})
	conditions, filters = get_conditions(filters)
	salary_slips = frappe.db.sql("""select * from `tabSalary Slip` where %s
		order by employee""" % conditions, filters, as_dict=1)

	return salary_slips or []

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

def get_employee_doj_map():
	return	frappe._dict(frappe.db.sql("""
				SELECT
					employee,
					date_of_joining
				FROM `tabEmployee`
				"""))

def get_ss_earning_map(salary_slips, default_value):
	ss_earnings = frappe.db.sql("""select sd.parent, sd.salary_component, sd.amount, sc.salary_component_abbr
		from `tabSalary Detail` sd
		inner join `tabSalary Component` sc
			on sc.name = sd.salary_component
		where sd.parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

	ss_earning_map = {}
	for d in ss_earnings:
		ss_earning_map.setdefault(d.parent,  frappe._dict(default_value)).setdefault(d.salary_component, 0)
		ss_earning_map[d.parent][d.salary_component] = flt(d.amount)
		ss_earning_map[d.parent][d.salary_component_abbr] = flt(d.amount)

	return ss_earning_map

def get_ss_ded_map(salary_slips, default_value):
	ss_deductions = frappe.db.sql("""select sd.parent, sd.salary_component, sd.amount, sc.salary_component_abbr
		from `tabSalary Detail` sd
		inner join `tabSalary Component` sc
			on sc.name = sd.salary_component
		where sd.parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

	ss_ded_map = {}
	for d in ss_deductions:
		ss_ded_map.setdefault(d.parent, frappe._dict(default_value)).setdefault(d.salary_component, 0)
		ss_ded_map[d.parent][d.salary_component] = flt(d.amount)
		ss_ded_map[d.parent][d.salary_component_abbr] = flt(d.amount)

	return ss_ded_map


def salary_component():
	sal_comp = """SELECT name, salary_component_abbr FROM `tabSalary Component`"""
	sal_comp = frappe.db.sql(sal_comp, as_dict=True)

	sal_comp_dict = {}
	for comp in sal_comp:
		sal_comp_dict.setdefault(comp.salary_component_abbr, 0)
	
	return sal_comp_dict
