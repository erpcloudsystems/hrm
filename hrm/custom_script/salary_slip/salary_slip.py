# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from frappe.utils import flt, rounded, money_in_words, get_first_day, getdate, formatdate, month_diff, add_years, add_days, date_diff
from copy import deepcopy
from hrm.custom_methods import set_comp_val, get_comp_name, get_leve_name
from hrm.hrm.doctype.leave_request.leave_request import get_leave_rule, compenstation_percent
from hrm import month_30days


def validate(doc, method):
	# validate_future(doc)
	salary_component_value(doc)

	doc.gross_pay = doc.get_component_totals("earnings")
	doc.total_deduction = doc.get_component_totals("deductions")
	doc.net_pay = flt(doc.get('gross_pay')) - (flt(doc.get('total_deduction')) + flt(doc.get('total_loan_repayment')))
	doc.rounded_total = rounded(doc.get('net_pay'))

	company_currency = erpnext.get_company_currency(doc.company)
	doc.total_in_words = money_in_words(doc.rounded_total, company_currency)


def salary_component_value(doc, include_current=False):
	payroll_dict = get_payroll_period(company=doc.company, start_date=doc.start_date, end_date=doc.end_date, actual_period=int(include_current))
	if not include_current:
		doc.actual_attendance_start_date = payroll_dict.get('start_date')
		doc.actual_attendance_end_date = payroll_dict.get('end_date')
	else:
		doc.payroll_period = payroll_dict.get('name')
		doc.actual_attendance_end_date = doc.pay_end_date
		doc.end_date = doc.pay_end_date
		doc.pay_end_date = None

	struct_assig, prev_sal_ded = get_actual_structure(doc, payroll_dict)
	if not struct_assig: return
	get_component_amt(doc, payroll_dict, prev_sal_ded, include_current)
	get_ot_amt(doc, payroll_dict, prev_sal_ded, include_current)
	late_coming_amt(doc, payroll_dict, prev_sal_ded, include_current)
	early_going_amt(doc, payroll_dict, prev_sal_ded, include_current)

	# include current_period_salary
	if doc.get('pay_end_date'):
		# doc.pay_end_date = None
		salary_component_value(doc, True)
	a= []
	b =[]
	for structure in doc.earnings :
		if structure.amount >0 :
			a.append(structure)
	for structure in doc.deductions :
		if structure.amount >0 :
			b.append(structure)
	doc.earnings = a
	doc.deductions = b

def validate_future(doc):
	sys_date = getdate()
	sys_start_date = get_first_day(sys_date)

	if getdate(doc.start_date) >= sys_start_date:
		frappe.throw(_("Salary Slip cannot be generated for future date"))


def get_payroll_period(company, start_date, end_date, actual_period=0):
	if actual_period:
		field = "start_date, end_date"
	else:
		field = "IFNULL(actual_start_date, start_date) start_date, IFNULL(actual_end_date, end_date) end_date"
	
	sel_payroll = """SELECT name, {3}
		FROM `tabPayroll Period`
		WHERE company = '{0}'
		AND start_date = '{1}'
		AND end_date = '{2}'""".format(company, start_date, end_date, field)
	get_payroll = frappe.db.sql(sel_payroll, as_dict=True)

	if get_payroll:
		return get_payroll[0]
	else:
		frappe.throw(_("There is no Payroll Period Set for {} - {}".format(formatdate(start_date), formatdate(end_date))))


def get_actual_structure(doc, payroll_dict):
	salary_slip = frappe.new_doc('Salary Slip')

	prev_sal_ded = {}

	joining_date, relieving_date = frappe.get_cached_value("Employee", doc.employee,
				["date_of_joining", "relieving_date"])
	
	struct = check_sal_struct(doc, joining_date, relieving_date, payroll_dict)

	if struct and struct.get('salary_structure'):
		doc._actual_salary_structure_doc = frappe.get_doc('Salary Structure', struct.get('salary_structure'))
	else:
		return False, prev_sal_ded
	
	
	data = get_data_for_eval(doc, struct.get('salary_structure'),struct.get('name'))
	for key in ('earnings', 'deductions'):
		for struct_row in doc._actual_salary_structure_doc.get(key):
			amount = salary_slip.eval_condition_and_formula(struct_row, data)
			prev_sal_ded.setdefault(key, {})\
				.setdefault(struct_row.get('salary_component'), {
					'default_amount': amount,
					'salary_component': struct_row.get('salary_component')
					})
	
	return struct.get('name'), prev_sal_ded


def get_component_amt(doc, payroll_dict, prev_sal_ded, include_current):
	attendance = get_attendance(doc, payroll_dict)
	# frappe.errprint(str(attendance))
	# compensation based on leave request
	leave_dict = attendance.get('On Leave', {})
	leave_days = 0
	for leave_type in leave_dict.keys():
		compensation = get_compansation(doc, leave_dict.get(leave_type), payroll_dict)
		leave_days += compensation_amt(prev_sal_ded.get('earnings', {}), compensation, payroll_dict, leave_type)
	
	if include_current:
		doc.lwp = leave_days
	else:
		doc.previous_leave_without_pay = leave_days

	# compensation based on Absent
	absent_dict = attendance.get('Absent', {})
	absent_days = 0
	for ab_dict in absent_dict.values():
		compensation = get_absent_compansation(doc, payroll_dict, ab_dict)
		abs_days = compensation_amt(prev_sal_ded.get('earnings', {}), compensation, payroll_dict, ab_dict.get('leave_type') or 'Absent')

		# remove weakoff
		if ab_dict.get('leave_type'): abs_days = 0
		
		absent_days += abs_days
	
	if include_current:
		doc.custom_absent_days = absent_days
	else:
		doc.previous_absent = absent_days
	
	adjust_component_value(doc, prev_sal_ded, include_current)
	# frappe.errprint(str(prev_sal_ded))


def get_attendance(doc, payroll_dict):
	attendance_list = """SELECT status, leave_type, count(*) attendance, GROUP_CONCAT(DISTINCT leave_application) as application, GROUP_CONCAT(DISTINCT attendance_date) as dates
		FROM `tabAttendance`
		WHERE docstatus = 1
		AND employee = '{}'
		AND attendance_date BETWEEN '{}' and '{}'
		GROUP BY status, leave_type""".format(doc.employee, payroll_dict.get('start_date'), payroll_dict.get('end_date'))
	attendance_list = frappe.db.sql(attendance_list, as_dict=True)

	attendance_dict = {}
	for row in attendance_list:
		# if not row.get('leave_type'):
		# 	attendance_dict.setdefault(row.get('status'), row)
		# else:
		attendance_dict.setdefault(row.get('status'), {})\
			.setdefault(row.get('leave_type') or row.get('status'), row)
	
	return attendance_dict


def get_compansation(doc, leave, payroll_dict):
	compansation_dict = {}
	for leave_appl in leave.get('application', '').split(','):
		leave_appl = """SELECT leave_request
			FROM `tabLeave Application`
			WHERE name = '{}'""".format(leave_appl)
		leave_appl = frappe.db.sql(leave_appl, as_dict=True)

		if leave_appl:
			componsation = process_compansation(doc, leave_appl[0].get('leave_request'), payroll_dict)
			for leave_rule in componsation.keys():
				compansation_dict.setdefault(leave_rule, {})
				comp_dict = componsation[leave_rule]
				for k_com in comp_dict.keys():
					compansation_dict[leave_rule][k_com] = compansation_dict[leave_rule].get(k_com, 0) + comp_dict[k_com]
	
	return compansation_dict


def process_compansation(doc, leave_req, payroll_dict):
	compansation = """SELECT *
		FROM `tabLeave Compensation Slab`
		WHERE parent = '{}'""".format(leave_req)
	compansation = frappe.db.sql(compansation, as_dict=True)
	
	compansation_dict = {}

	for com in compansation:
		from_date = com.get('from_date')
		to_date = com.get('to_date')

		if getdate(payroll_dict.get('start_date')) > getdate(from_date):
			from_date = payroll_dict.get('start_date')

		if getdate(payroll_dict.get('end_date')) < getdate(to_date):
			to_date = payroll_dict.get('end_date')
		
		days = date_diff(to_date, from_date) + 1
		# exclude slab not in period
		if days <= 0: continue

		compansation_dict.setdefault(com.get('leave_rule'), {})
		compansation_dict[com.get('leave_rule')][com.get('approved_compensation', 0)] = compansation_dict[com.get('leave_rule')].get(com.get('approved_compensation', 0), 0) + days
	
	return compansation_dict


def compensation_amt(earnings, comp, payroll_dict, leave_type):
	# working_day = date_diff(payroll_dict.get('end_date'), payroll_dict.get('start_date')) + 1
	working_day = 30

	day_count = 0
	for leav_rule, row_comp in comp.items():
		comp_all, comp_element = get_compensation_element(leav_rule)
		for per, days in row_comp.items():
			day_count += days
			for elem, row in earnings.items():
				if comp_all == 0 and not elem in comp_element:
					continue
				
				per_day = (row.get('default_amount',0) or 0) / working_day

				per_com = per_day - (per * per_day / 100)
				comp_val = per_com * days
				# frappe.errprint('leave {} day {} per_day {} percentage {} value {}'.format(leave_type, days, per_day, per, comp_val))

				row['deducation_amt'] = row.get('deducation_amt', 0) + comp_val
				if not row.get("compensation") or (row.get("compensation") and not row.get("compensation").get(leave_type)):
					row.setdefault('compensation', {})\
						.setdefault(leave_type, comp_val)
				elif(row.get("compensation") and row.get("compensation").get(leave_type)):
					row.get("compensation")[leave_type] =float(row.get("compensation")[leave_type] or 0.0 ) + comp_val
				
	
	return day_count

def get_compensation_element(leav_rule):
	comp_all = 1
	comp_element = []
	if frappe.db.get_value("Leave Rule", leav_rule, "is_not_applicable_all_components"):
		comp_element = """SELECT salary_component
			FROM `tabSalary Compensation Component`
			WHERE parent = '{}'""".format(leav_rule)
		comp_element = frappe.db.sql_list(comp_element)
		comp_all = 0
	
	return comp_all, comp_element


def check_sal_struct(doc, joining_date, relieving_date, payroll_dict):
	cond = """and sa.employee=%(employee)s and (sa.from_date <= %(start_date)s or
			sa.from_date <= %(end_date)s or sa.from_date <= %(joining_date)s)"""
	if doc.get('payroll_frequency'):
		cond += """and ss.payroll_frequency = '%(payroll_frequency)s'""" % {"payroll_frequency": doc.get('payroll_frequency')}

	st_name = frappe.db.sql("""
		select sa.name, sa.salary_structure
		from `tabSalary Structure Assignment` sa join `tabSalary Structure` ss
		where sa.salary_structure=ss.name
			and sa.docstatus = 1 and ss.docstatus = 1 and ss.is_active ='Yes' %s
		order by sa.from_date desc
		limit 1
	""" %cond, {'employee': doc.get('employee'), 'start_date': payroll_dict.get('start_date'),
		'end_date': payroll_dict.get('end_date'), 'joining_date': joining_date}, as_dict=True)
	
	if st_name:
		return st_name[0]

	else:
		frappe.msgprint(_("No active or default Salary Structure found for employee {0} for the given dates")
			.format(doc.get('employee')), title=_('Salary Structure Missing'))

def get_data_for_eval(doc, salary_structure,struct):
	'''Returns data for evaluating formula'''
	data = frappe._dict()
	
	data.update(frappe.get_doc("Salary Structure Assignment",
		{"employee": doc.employee, "salary_structure": salary_structure,"name":struct}).as_dict())
		
	frappe.errprint([struct,"@@@@@@@@@@@"])
	
	data.update(frappe.get_doc("Employee", doc.employee).as_dict())
	data.update(doc.as_dict())
	frappe.errprint([doc,"<<<<<<<<<<",data])
	# set values for components
	salary_components = frappe.get_all("Salary Component", fields=["salary_component_abbr"])
	for sc in salary_components:
		data.setdefault(sc.salary_component_abbr, 0)
	
	return data


def working_days(doc):
	joining_date, relieving_date = frappe.get_cached_value("Employee", doc.employee,
				["date_of_joining", "relieving_date"])
	
	start_date = getdate(doc.get('start_date'))
	if joining_date:
		if getdate(doc.get('start_date')) <= joining_date <= getdate(doc.get('end_date')):
			start_date = joining_date
		elif joining_date > getdate(doc.get('end_date')):
			return

	end_date = getdate(doc.get('end_date'))
	if relieving_date:
		if getdate(doc.get('start_date')) <= relieving_date <= getdate(doc.get('end_date')):
			end_date = relieving_date
			if not doc.get('_load_amt'):
				doc.pay_end_date = relieving_date
				doc._load_amt = 1
	
	if doc.get('pay_end_date'):
		end_date = doc.get('pay_end_date')
		
	actual_working = date_diff(end_date, start_date) + 1

	return month_30days(doc.get('start_date'), doc.get('end_date'), actual_working)


def default_comp_amount(doc):
	days_working = working_days(doc)
	# actual_working = date_diff(getdate(doc.get('end_date')), getdate(doc.get('start_date'))) + 1
	actual_working = 30

	for row in doc.get('earnings'):
		if not row.get('default_amount'): continue
		row.amount = ((row.get('default_amount') or 0) / actual_working) * days_working


def deducation_component(doc, prev_sal_ded, include_current):
	prev_earn = prev_sal_ded.get('earnings')

	comp_att = {}
	for row in prev_earn.values():
		for leave, val in row.get('compensation', {}).items():
			comp_att[leave] = (comp_att.get(leave) or 0) + val

	ab_amt = sum(comp_att.values())
	
	ab_comp = frappe.db.get_single_value('HR Settings', 'absent_component')
	if not ab_comp:
		frappe.throw(_('Absent Component not Setted in HR Settings'))
	
	set_comp_val(doc, 'Deduction', ab_comp, ab_amt, include_current)


def adjust_component_value(doc, prev_sal_ded, include_current):
	if not include_current: default_comp_amount(doc)

	deducation_component(doc, prev_sal_ded, include_current)

	# prev_earn = deepcopy(prev_sal_ded.get('earnings'))
	# for row in doc.get('earnings'):
	# 	deduct_amt = prev_earn.get(row.salary_component, {}).get('deducation_amt', 0)

	# 	if deduct_amt == 0: continue
		
	# 	default_amount = row.get('amount')

	# 	if deduct_amt <= default_amount:
	# 		row.amount = default_amount - deduct_amt
	# 	else:
	# 		row.amount = 0
	# 		prev_earn.get(row.salary_component, {})['deducation_amt'] = deduct_amt - default_amount
	# 		continue
		
	# 	if row.salary_component in prev_earn:
	# 		del prev_earn[row.salary_component]
	
	# other_deducation = 0
	# for row in prev_earn.values():
	# 	other_deducation += row.get('deducation_amt', 0)
	
	# set_comp_val(doc, 'Deduction', get_comp_name('OD'), other_deducation)


# ---------------------------- OT -------------------------------

def get_ot_amt(doc, payroll_dict, prev_sal_ded, include_current):
	attendance_list = """SELECT `A`.`ot_rule`, `A`.`shift`
		-- , `A`.`leave_type` AS week_off
		, IF(`H`.`is_weekoff` IS NOT NULL, 
			(SELECT name
			FROM `tabLeave Type`
			WHERE leave_type_abbr = IF(`H`.`is_weekoff` = 1, 'WO', 'H'))
			, NULL) AS week_off
		, SUM(`A`.`ot_hours`) ot
		,IF(CHAR_LENGTH(`A`.`shift`) > 0
			, TIME_TO_SEC(TIMEDIFF(
				CAST(CONCAT(IF(`ST`.`start_time` >= `ST`.`end_time`
					, DATE_ADD(`A`.`attendance_date`, INTERVAL 1 DAY)
					, `A`.`attendance_date`), " ", `ST`.`end_time`) AS DATETIME)
				, CAST(CONCAT(`A`.`attendance_date`, " ", `ST`.`start_time`) AS DATETIME)
				)) / 3600
			, 1) AS working_hrs
		FROM `tabAttendance` AS `A`
		INNER JOIN `tabEmployee` AS `E`
			ON `A`.`employee` = `E`.`name`
		LEFT JOIN `tabShift Type` AS `ST`
			ON `A`.`shift` = `ST`.`name`
		LEFT JOIN `tabCompany` AS `C`
			ON `E`.`company` = `C`.`name`
		LEFT JOIN `tabHoliday` AS `H`
			ON IF(CHAR_LENGTH(`E`.`holiday_list`) > 0
				, `E`.`holiday_list`
				, IF(CHAR_LENGTH(`ST`.`holiday_list`) > 0
					, `ST`.`holiday_list`
					, `C`.`default_holiday_list`)) = `H`.`parent`
			AND `H`.`holiday_date` = `A`.`attendance_date`
		WHERE `A`.`docstatus` = 1
		-- AND `A`.`status` = 'Present'
		AND `A`.`employee` = '{}'
		AND `A`.`attendance_date` BETWEEN '{}' and '{}'
		GROUP BY `A`.`ot_rule`, `A`.`shift`, `H`.`is_weekoff`
		-- , `A`.`leave_type`
		HAVING SUM(`A`.`ot_hours`) > 0""".format(doc.employee, payroll_dict.get('start_date'), payroll_dict.get('end_date'))
	attendance_list = frappe.db.sql(attendance_list, as_dict=True)

	leave_type = get_leve_name('OT')
	leave_rule = get_leave_rule(date=payroll_dict.get('end_date'), leave_type=leave_type)
	if not leave_rule: return
	leave_rule = leave_rule[0]

	# working_day = date_diff(payroll_dict.get('end_date'), payroll_dict.get('start_date')) + 1
	working_day = 30
	earnings = prev_sal_ded.get('earnings', {})
	component_val = composition_amt(leave_rule.get('name'), earnings, working_day)

	ot_amt = 0
	ot_hours = 0
	for ot_row in attendance_list:
		if not ot_row.get('ot_rule'): continue
		
		ot_hours += ot_row.get('ot')

		ot_rule_doc = frappe.get_doc('OT Rule', ot_row.get('ot_rule'))
		daily_working_hrs = ot_row.get('working_hrs', 1)
		override_hrs = frappe.db.get_value("Shift Type", ot_row.get('shift', 1), "override_working_hours")
		if override_hrs and override_hrs > daily_working_hrs:
			daily_working_hrs = override_hrs
		if ot_row.get('week_off') == get_leve_name('WO'):
			ot_amt += (ot_row.get('ot') * ot_rule_doc.get('non_working_day_ot_rate') * (component_val / daily_working_hrs))
		elif ot_row.get('week_off') == get_leve_name('H'):
			ot_amt += (ot_row.get('ot') * ot_rule_doc.get('holiday_ot_rate') * (component_val / daily_working_hrs))
		else:
			ot_amt += (ot_row.get('ot') * ot_rule_doc.get('working_day_ot_rate') * (component_val / daily_working_hrs))
	
	if include_current:
		doc.ot_hours = ot_hours
	else:
		doc.previous_ot_hours = ot_hours
	
	ot_comp = frappe.db.get_single_value('HR Settings', 'overtime_component')
	if not ot_comp:
		frappe.throw(_('Overtime Component not Setted in HR Settings'))
	
	set_comp_val(doc, 'Earning', ot_comp, ot_amt, include_current)


# --------------------------- Absent -----------------------------

def get_absent_compansation(doc, payroll_dict, ab_dict):
	date_of_joining = frappe.db.get_value("Employee", doc.employee, "date_of_joining")
	leave_type = get_leve_name('A')
	compansation_dict = {}

	if not ab_dict.get('leave_type'):
		for date in ab_dict.get('dates', '').split(','):
			leave_rule = get_leave_rule(leave_type=leave_type, date=date)
			if not leave_rule: continue
			leave_rule = leave_rule[0]
			leave_taken = get_absent_for_period(doc.employee, date, leave_rule)
			compansation = compenstation_percent(leave_rule=leave_rule, from_date=date, to_date=date, joining_date=date_of_joining, total_leave_days=1, leave_taken=leave_taken)
			
			for percent in compansation.keys():
				compansation_dict.setdefault(leave_rule.get('name'), {})
				compansation_dict[leave_rule.get('name')][percent] = compansation_dict[leave_rule.get('name')].get(percent, 0) + len(compansation[percent])
	
	return compansation_dict


def get_absent_for_period(employee, from_date, leave_rule):
	condition = ''
	if from_date and leave_rule.get('leave_credit_frequency') == 'Yearly':
		year_start = getdate(from_date).replace(month=1, day=1)
		year_end = getdate(from_date).replace(month=12, day=31)
		condition = " and attendance_date between '{}' and '{}'".format(year_start, year_end)

	leave_applications = frappe.db.sql("""
		select ifnull(count(*), 0) as total_leave_days
		from `tabAttendance`
		where employee=%(employee)s
		and status = 'Absent'
		and docstatus = 1
		and CHAR_LENGTH(leave_type) = 0
		 {}""".format(condition), {
		"employee": employee
	}, as_dict=1)
	
	leave_days = leave_applications[0]['total_leave_days'] if leave_applications else 0

	return leave_days




# ---------------------- Late Comming ---------------------------


def late_coming_amt(doc, payroll_dict, prev_sal_ded, include_current):
	attendance_list = """SELECT `A`.`shift`, SUM(`A`.`late_coming_minutes`) short_time
		,IF(CHAR_LENGTH(`A`.`shift`) > 0
			, TIME_TO_SEC(TIMEDIFF(
				CAST(CONCAT(IF(`ST`.`start_time` >= `ST`.`end_time`
					, DATE_ADD(`A`.`attendance_date`, INTERVAL 1 DAY)
					, `A`.`attendance_date`), " ", `ST`.`end_time`) AS DATETIME)
				, CAST(CONCAT(`A`.`attendance_date`, " ", `ST`.`start_time`) AS DATETIME)
				)) / 60
			, 1) AS working_min
		FROM `tabAttendance` AS `A`
		LEFT JOIN `tabShift Type` AS `ST`
			ON `A`.`shift` = `ST`.`name`
		WHERE `A`.`docstatus` = 1
		AND `A`.`status` = 'Present'
		AND `A`.`employee` = '{}'
		AND `A`.`attendance_date` BETWEEN '{}' and '{}'
		GROUP BY `A`.`shift`""".format(doc.employee, payroll_dict.get('start_date'), payroll_dict.get('end_date'))
	attendance_list = frappe.db.sql(attendance_list, as_dict=True)

	leave_type = get_leve_name('LC')
	leave_rule = get_leave_rule(date=payroll_dict.get('end_date'), leave_type=leave_type)
	if not leave_rule: return
	leave_rule = leave_rule[0]

	# working_day = date_diff(payroll_dict.get('end_date'), payroll_dict.get('start_date')) + 1
	working_day = 30
	earnings = prev_sal_ded.get('earnings', {})
	component_val = composition_amt(leave_rule.get('name'), earnings, working_day)
	
	st_amt = 0
	late_coming_hours = 0
	for st_row in attendance_list:
		late_coming_hours += st_row.get('short_time')
		daily_working_hrs = st_row.get('working_min', 1)
		override_hrs = frappe.db.get_value("Shift Type", st_row.get('shift', 1), "override_working_hours")
		if override_hrs*60 > daily_working_hrs:
			daily_working_hrs = override_hrs*60
		st_amt += (st_row.get('short_time') * (component_val / daily_working_hrs ))
	
	late_coming_hours = late_coming_hours / 60
	if include_current:
		doc.late_coming_hours = late_coming_hours
	else:
		doc.previous_late_coming_hours = late_coming_hours

	late_comp = frappe.db.get_single_value('HR Settings', 'late_coming_component')
	if not late_comp:
		frappe.throw(_('Late Coming Component not Setted in HR Settings'))

	set_comp_val(doc, 'Deduction', late_comp, st_amt, include_current)


def early_going_amt(doc, payroll_dict, prev_sal_ded, include_current):
	attendance_list = """SELECT `A`.`shift`, SUM(`A`.`early_going_minutes`) short_time
		,IF(CHAR_LENGTH(`A`.`shift`) > 0
			, TIME_TO_SEC(TIMEDIFF(
				CAST(CONCAT(IF(`ST`.`start_time` >= `ST`.`end_time`
					, DATE_ADD(`A`.`attendance_date`, INTERVAL 1 DAY)
					, `A`.`attendance_date`), " ", `ST`.`end_time`) AS DATETIME)
				, CAST(CONCAT(`A`.`attendance_date`, " ", `ST`.`start_time`) AS DATETIME)
				)) / 60
			, 1) AS working_min
		FROM `tabAttendance` AS `A`
		LEFT JOIN `tabShift Type` AS `ST`
			ON `A`.`shift` = `ST`.`name`
		WHERE `A`.`docstatus` = 1
		AND `A`.`status` = 'Present'
		AND `A`.`employee` = '{}'
		AND `A`.`attendance_date` BETWEEN '{}' and '{}'
		GROUP BY `A`.`shift`""".format(doc.employee, payroll_dict.get('start_date'), payroll_dict.get('end_date'))
	attendance_list = frappe.db.sql(attendance_list, as_dict=True)

	leave_type = get_leve_name('EG')
	leave_rule = get_leave_rule(date=payroll_dict.get('end_date'), leave_type=leave_type)
	if not leave_rule: return
	leave_rule = leave_rule[0]

	# working_day = date_diff(payroll_dict.get('end_date'), payroll_dict.get('start_date')) + 1
	working_day = 30
	earnings = prev_sal_ded.get('earnings', {})
	component_val = composition_amt(leave_rule.get('name'), earnings, working_day)
	
	st_amt = 0
	early_going_hours = 0
	for st_row in attendance_list:
		early_going_hours += st_row.get('short_time')
		daily_working_hrs = st_row.get('working_min', 1)
		override_hrs = frappe.db.get_value("Shift Type", st_row.get('shift', 1), "override_working_hours")
		if override_hrs*60 > daily_working_hrs:
			daily_working_hrs = override_hrs*60
		st_amt += (st_row.get('short_time') * (component_val / daily_working_hrs))
	
	early_going_hours = early_going_hours / 60
	if include_current:
		doc.early_going_hours = early_going_hours
	else:
		doc.previous_early_going_hours = early_going_hours
	
	early_comp = frappe.db.get_single_value('HR Settings', 'early_going_component')
	if not early_comp:
		frappe.throw(_('Early Going Component not Setted in HR Settings'))

	set_comp_val(doc, 'Deduction', early_comp, st_amt, include_current)


def composition_amt(leav_rule, earnings, working_day):
	comp_val = 0
	comp_all, comp_element = get_compensation_element(leav_rule)
	for elem, row in earnings.items():
		if comp_all == 0 and not elem in comp_element:
			continue

		comp_val += row.get('default_amount', 0) / working_day
	
	return comp_val