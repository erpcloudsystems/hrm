

from __future__ import unicode_literals
import frappe
from collections import OrderedDict
from frappe.utils import formatdate, getdate
from frappe import _


@frappe.whitelist()
def chart_data(company):
	data = {'name': company,
		'catogery': 'Company',
		'children': []
	}

	def get_department(data_dict, department=None):
		condition = ""
		if department:
			condition += "AND parent_department = '{}'".format(department)
		
		_department = """SELECT name
			FROM `tabDepartment`
			WHERE company='{}' {}""".format(company, condition)
		_department = frappe.db.sql(_department, as_dict=True)

		for row in _department:
			new_dict = {
				'name': row.get('name'),
				'catogery': 'Department',
				'children': []
			}
			data_dict.append(new_dict)

			get_department(new_dict.get('children'), row.get('name'))
	
	get_department(data_dict=data.get('children'))

	return [data]


@frappe.whitelist()
def absent_details(company, from_date, to_date):
	attendance  = """SELECT `E`.`name` AS `employee`, `E`.`employee_name`, `E`.`enroll_number`, `E`.`department`, `A`.`attendance_date`
		FROM `tabAttendance` AS `A`
		INNER JOIN `tabEmployee` AS `E`
			ON `A`.`employee` = `E`.`name`
		WHERE `E`.`company` = '{0}'
		AND `A`.`docstatus` = 1
		AND `A`.`status` = 'Absent'
		AND `A`.`leave_type` IS NULL
		AND `E`.`date_of_joining` <= '{1}'
		AND (`E`.`relieving_date` IS NULL
			OR `E`.`relieving_date` >= '{2}')
		AND `A`.`attendance_date` BETWEEN '{1}' AND '{2}'
	ORDER BY `A`.`attendance_date`""".format(company, from_date, to_date)
	attendance = frappe.db.sql(attendance, as_dict=True)

	result_dict = []
	for att in attendance:
		attendance_data = OrderedDict()
		attendance_data['Absent Date'] = formatdate(att.get('attendance_date')) or ''
		attendance_data['Employee'] = att.get('employee') or ''
		attendance_data['Employee Name'] = att.get('employee_name') or ''
		attendance_data['Enrollment Number'] = att.get('enroll_number') or ''
		attendance_data['Department'] = att.get('department') or ''
		result_dict.append(attendance_data)
	
	if not attendance:
		attendance_data = OrderedDict()
		attendance_data['Employee'] = None
		attendance_data['Employee Name'] = None
		attendance_data['Enrollment Number'] = None
		attendance_data['Department'] = None
		attendance_data['Absent Date'] = None
		result_dict.append(attendance_data)
	
	return result_dict


@frappe.whitelist()
def short_time_details(company, from_date, to_date):
	attendance  = """SELECT `E`.`name` AS `employee`, `E`.`employee_name`, `E`.`enroll_number`, `E`.`department`, `A`.`late_coming_minutes`, `A`.`early_going_minutes`,  `A`.`attendance_date`
	, IF(`LCR`.`docstatus`=1, `LCR`.`name`, NULL) AS `late_coming_id`
	, IF(`EGR`.`docstatus`=1, `EGR`.`name`, NULL) AS `early_going_id`
		FROM `tabAttendance` AS `A`
		INNER JOIN `tabEmployee` AS `E`
			ON `A`.`employee` = `E`.`name`
		LEFT JOIN `tabLate Coming Request` AS `LCR`
			ON `LCR`.`attendance` = `A`.`name`
		LEFT JOIN `tabEarly Going Request` AS `EGR`
			ON `EGR`.`attendance` = `A`.`name`
		WHERE `E`.`company` = '{0}'
		AND `A`.`docstatus` = 1
		AND `E`.`date_of_joining` <= '{1}'
		AND (`E`.`relieving_date` IS NULL
			OR `E`.`relieving_date` >= '{2}')
		AND (`A`.`late_coming_minutes` > 0
			OR `A`.`early_going_minutes` > 0)
		AND `A`.`attendance_date` BETWEEN '{1}' AND '{2}'
		ORDER BY `A`.`attendance_date`""".format(company, from_date, to_date)
	attendance = frappe.db.sql(attendance, as_dict=True)

	late_dict, early_dict = [], []
	for att in attendance:
		attendance_data = OrderedDict()
		attendance_data['Attendance Date'] = formatdate(att.get('attendance_date')) or ''
		attendance_data['Employee'] = att.get('employee') or ''
		attendance_data['Employee Name'] = att.get('employee_name') or ''
		attendance_data['Enrollment Number'] = att.get('enroll_number') or ''
		attendance_data['Department'] = att.get('department') or ''
		if att.get('late_coming_minutes') > 0:
			attendance_data['Late Coming By'] = att.get('late_coming_minutes')
			attendance_data['Late Coming ID'] = att.get('late_coming_id') or ''
			late_dict.append(attendance_data)
		else:
			attendance_data['Early Going By'] = att.get('early_going_minutes')
			attendance_data['Early Going ID'] = att.get('early_going_id') or ''
			early_dict.append(attendance_data)
	
	if not late_dict:
		attendance_data = OrderedDict()
		attendance_data['Employee'] = None
		attendance_data['Employee Name'] = None
		attendance_data['Enrollment Number'] = None
		attendance_data['Department'] = None
		attendance_data['Late Coming By'] = None
		attendance_data['Late Coming Request ID'] = None
		late_dict.append(attendance_data)
	
	if not early_dict:
		attendance_data = OrderedDict()
		attendance_data['Employee'] = None
		attendance_data['Employee Name'] = None
		attendance_data['Enrollment Number'] = None
		attendance_data['Department'] = None
		attendance_data['Early Going By'] = None
		attendance_data['Early Going Request ID'] = None
		early_dict.append(attendance_data)
	
	return {'late_coming': late_dict, 'early_going': early_dict}


@frappe.whitelist()
def employee_status(company, from_date, to_date):
	employee = """SELECT `E`.`employee`, `E`.`employee_name`, `E`.`enroll_number`, `E`.`department`, `E`.`designation`, `E`.`date_of_joining`, `E`.`relieving_date`
	, IF(`E`.`date_of_joining`='{1}', 1, 0) AS join_flag, `SC`.`name` AS `eos_id`
		FROM `tabEmployee` AS `E`
		LEFT JOIN `tabService Closing` AS `SC`
			ON `SC`.`docstatus` = 1
			AND `SC`.`employee` = `E`.`name`
		WHERE `E`.`company` = '{0}'
		AND (`E`.`date_of_joining` BETWEEN '{1}' AND '{2}'
			OR `E`.`relieving_date` BETWEEN '{1}' AND '{2}')""".format(company, from_date, to_date)
	employee = frappe.db.sql(employee, as_dict=True)

	joined_dict, relived_dict = [], []
	for emp in employee:
		if emp.get('join_flag'):
			joined_data = OrderedDict()
			joined_data['Employee'] = emp.get('employee') or ''
			joined_data['Employee Name'] = emp.get('employee_name') or ''
			joined_data['Date of Joining'] = formatdate(emp.get('date_of_joining')) or ''
			joined_data['Enrollment Number'] = emp.get('enroll_number') or ''
			joined_data['Department'] = emp.get('department') or ''
			joined_data['Designation'] = emp.get('designation') or ''
			joined_dict.append(joined_data)
		else:
			relived_data = OrderedDict()
			relived_data['Employee'] = emp.get('employee') or ''
			relived_data['Employee Name'] = emp.get('employee_name') or ''
			relived_data['Relieving Date'] = formatdate(emp.get('relieving_date')) or ''
			relived_data['Enrollment Number'] = emp.get('enroll_number') or ''
			relived_data['Department'] = emp.get('department') or ''
			relived_data['Designation'] = emp.get('designation') or ''
			relived_data['EOS ID'] = emp.get('eos_id') or ''
			relived_dict.append(relived_data)
	
	if not joined_dict:
		joined_data = OrderedDict()
		joined_data['Employee'] = None
		joined_data['Employee Name'] = None
		joined_data['Date of Joining'] = None
		joined_data['Enrollment Number'] = None
		joined_data['Department'] = None
		joined_data['Designation'] = None
		joined_dict.append(joined_data)
	
	if not relived_dict:
		relived_data = OrderedDict()
		relived_data['Employee'] = None
		relived_data['Employee Name'] = None
		relived_data['Relieving Date'] = None
		relived_data['Enrollment Number'] = None
		relived_data['Department'] = None
		relived_data['Designation'] = None
		relived_data['EOS ID'] = None
		relived_dict.append(relived_data)
	
	return {'joined': joined_dict,
	'relived': relived_dict}

@frappe.whitelist()
def desigination_data(company, from_date, to_date, department=None):
	desigination_list = frappe.db.sql_list("SELECT name FROM `tabDesignation`")

	label, value = [], []
	for des in desigination_list:
		condition = ""
		if department:
			condition += " AND department = '{}'".format(department)
	
		desigination_data = """SELECT COUNT(*) AS count
		FROM `tabEmployee` AS `E`
		WHERE `E`.`company` = '{0}'
		AND `E`.`date_of_joining` <= '{1}'
		AND (`E`.`relieving_date` IS NULL
			OR `E`.`relieving_date` >= '{2}')
		AND `E`.`designation` = '{3}'
		{4}""".format(company, from_date, to_date, des, condition)
		desigination_data = frappe.db.sql(desigination_data, as_dict=True)

		desigination_data = desigination_data[0] if desigination_data else {}
		label.append(des)
		value.append(desigination_data.get('count') or 0)
	
	return {'label': label, 'value': value}


@frappe.whitelist()
def employee_count(company, from_date, to_date, department=None):
	condition = ""
	if department:
		condition += " AND department = '{}'".format(department)

	result = {}

	for gender in ['Male', 'Female']:
		emp_count_gw = """SELECT COUNT(*) AS count
			FROM `tabEmployee` AS `E`
			WHERE `E`.`company` = '{0}'
			AND `E`.`gender` = '{4}'
			AND `E`.`date_of_joining` <= '{1}'
			AND (`E`.`relieving_date` IS NULL
				OR `E`.`relieving_date` >= '{2}')
			{3}""".format(company, from_date, to_date, condition, gender)
		emp_count_gw = frappe.db.sql(emp_count_gw, as_dict=True)
		
		emp_count_gw = emp_count_gw[0] if emp_count_gw else {}

		result[gender] = emp_count_gw.get('count') or 0

	return result


@frappe.whitelist()
def get_salary_amount(company, payroll_from, payroll_to, amount_category, group_category):
	start_date, end_date = get_payroll_date(payroll_from, payroll_to)

	result_list = []
	for category in frappe.db.sql_list('SELECT name FROM `tab{}`'.format(group_category)):
		target_field = 'gross_pay' if amount_category == 'Gross Salary' else 'net_pay'
		salary = """SELECT SUM(`SS`.`{5}`) AS {5}
			FROM `tabSalary Slip` AS `SS`
			INNER JOIN `tabEmployee` AS `E`
				ON `SS`.`employee` = `E`.`name`
			WHERE `SS`.`docstatus` = 1
			AND `E`.`company` = '{0}'
			AND `E`.`{1}` = '{2}'
			AND `SS`.`{5}` > 0
			AND ('{3}' BETWEEN `SS`.`start_date` AND `SS`.`end_date`
				OR '{4}' BETWEEN `SS`.`start_date` AND `SS`.`end_date`
				OR `SS`.`start_date` BETWEEN '{3}' AND '{4}'
				OR `SS`.`end_date` BETWEEN '{3}' AND '{4}')""".format(company, group_category.lower(), category, start_date, end_date, target_field)
		salary = frappe.db.sql(salary, as_dict=True)
		salary = salary[0] if salary else {}

		amount = salary.get(target_field) or 0
		if amount > 0:
			result_list.append({
				'name': category,
				'value': amount
			})
	
	return result_list


@frappe.whitelist()
def new_joining_employee(company, payroll_from, payroll_to, group_category):
	start_date, end_date = get_payroll_date(payroll_from, payroll_to)

	label_list = []
	value_list = []
	joined_dict = []
	for category in frappe.db.sql_list('SELECT name FROM `tab{}`'.format(group_category)):
		employee = """SELECT `E`.`name` AS employee, `E`.`employee_name`, `E`.`enroll_number`, `E`.`date_of_joining`
			FROM `tabEmployee` AS `E`
			WHERE `E`.`company` = '{0}'
			AND `E`.`{1}` = '{2}'
			AND `E`.`date_of_joining` BETWEEN '{3}' AND '{4}'""".format(company, group_category.lower(), category, start_date, end_date)
		employee = frappe.db.sql(employee, as_dict=True)

		label_list.append(category)
		value_list.append(len(employee) or 0)

		for emp in employee:
			joined_data = OrderedDict()
			joined_data['Employee'] = emp.get('employee') or ''
			joined_data['Employee Name'] = emp.get('employee_name') or ''
			joined_data['Enrollment Number'] = emp.get('enroll_number') or ''
			joined_data['Date of Joining'] = formatdate(emp.get('date_of_joining')) or ''
			joined_data[group_category] = category
			joined_dict.append(joined_data)
	
	if not joined_dict:
		joined_data = OrderedDict()
		joined_data['Employee'] = None
		joined_data['Employee Name'] = None
		joined_data['Enrollment Number'] = None
		joined_data['Date of Joining'] = None
		joined_data[group_category] = None
		joined_dict.append(joined_data)
	
	return {'label': label_list, 'value': value_list, 'joined_dict': joined_dict}


@frappe.whitelist()
def get_overtime_amount(company, payroll_from, payroll_to, group_category):
	start_date, end_date = get_payroll_date(payroll_from, payroll_to)

	ot_comp = frappe.db.get_single_value('HR Settings', 'overtime_component')
	if not ot_comp:
		frappe.throw(_('Overtime Component not Setted in HR Settings'))

	result_list = []
	for category in frappe.db.sql_list('SELECT name FROM `tab{}`'.format(group_category)):
		salary = """SELECT SUM(`SD`.`amount`) AS amount
			FROM `tabSalary Detail` AS `SD`
			INNER JOIN `tabSalary Slip` AS `SS`
				ON `SD`.`parent` = `SS`.`name`
			INNER JOIN `tabEmployee` AS `E`
				ON `SS`.`employee` = `E`.`name`
			WHERE `SS`.`docstatus` = 1
			AND `SD`.`salary_component` = '{5}'
			AND `SD`.`amount` > 0
			AND `E`.`company` = '{0}'
			AND `E`.`{1}` = '{2}'
			AND ('{3}' BETWEEN `SS`.`start_date` AND `SS`.`end_date`
				OR '{4}' BETWEEN `SS`.`start_date` AND `SS`.`end_date`
				OR `SS`.`start_date` BETWEEN '{3}' AND '{4}'
				OR `SS`.`end_date` BETWEEN '{3}' AND '{4}')""".format(company, group_category.lower(), category, start_date, end_date, ot_comp)
		salary = frappe.db.sql(salary, as_dict=True)
		salary = salary[0] if salary else {}

		amount = salary.get('amount') or 0
		if amount > 0:
			result_list.append({
			'name': category,
			'value': amount
		})
	
	return result_list


@frappe.whitelist()
def relieving_employee(company, payroll_from, payroll_to, group_category):
	start_date, end_date = get_payroll_date(payroll_from, payroll_to)

	label_list = []
	value_list = []
	relieved_dict = []
	for category in frappe.db.sql_list('SELECT name FROM `tab{}`'.format(group_category)):
		employee = """SELECT `E`.`name` AS employee, `E`.`employee_name`, `E`.`enroll_number`, `E`.`relieving_date`
			FROM `tabEmployee` AS `E`
			LEFT JOIN `tabService Closing` AS `SC`
				ON `SC`.`docstatus` = 1
				AND `SC`.`employee` = `E`.`name`
			WHERE `E`.`company` = '{0}'
			AND `E`.`{1}` = '{2}'
			AND `E`.`relieving_date` BETWEEN '{3}' AND '{4}'""".format(company, group_category.lower(), category, start_date, end_date)
		employee = frappe.db.sql(employee, as_dict=True)

		label_list.append(category)
		value_list.append(len(employee) or 0)

		for emp in employee:
			joined_data = OrderedDict()
			joined_data['Employee'] = emp.get('employee') or ''
			joined_data['Employee Name'] = emp.get('employee_name') or ''
			joined_data['Enrollment Number'] = emp.get('enroll_number') or ''
			joined_data['EOS On'] = formatdate(emp.get('relieving_date')) or ''
			joined_data[group_category] = category
			relieved_dict.append(joined_data)
	
	if not relieved_dict:
		joined_data = OrderedDict()
		joined_data['Employee'] = None
		joined_data['Employee Name'] = None
		joined_data['Enrollment Number'] = None
		joined_data['EOS On'] = None
		joined_data[group_category] = None
		relieved_dict.append(joined_data)
	
	return {'label': label_list, 'value': value_list, 'relieved_dict': relieved_dict}

def get_payroll_date(payroll_from, payroll_to):
	start_date = frappe.db.get_value('Payroll Period', {'name': payroll_from}, ['start_date'])
	end_date = frappe.db.get_value('Payroll Period', {'name': payroll_to}, ['end_date'])

	if getdate(start_date) > getdate(end_date):
		frappe.throw(_('Payroll From Date Cannot be Greater then Payroll To Date'))

	return start_date, end_date


@frappe.whitelist()
def get_payroll_period(company):
	payroll_period = """SELECT *
		FROM `tabPayroll Period`
		WHERE company = '{}'
		ORDER BY start_date
		LIMIT 1""".format(company)
	
	payroll_period = frappe.db.sql(payroll_period, as_dict=True)
	payroll_period = payroll_period[0] if payroll_period else {}

	return payroll_period.get('name')


@frappe.whitelist()
def payroll_completion_detail(company, payroll_period):
	start_date, end_date = frappe.db.get_value('Payroll Period', {'name': payroll_period}, ['actual_start_date', 'actual_end_date'])

	label, data = [], []
	# result_list = []
	attendance = """SELECT *
		FROM `tabAttendance`
		WHERE docstatus = 1
		AND status = 'Absent'
		AND leave_type IS NULL
		AND attendance_date BETWEEN '{0}' AND '{1}'""".format(start_date, end_date)
	attendance = frappe.db.sql(attendance, as_dict=True)

	# label.append('Absent')
	# data.append(len(attendance))

	# result_list.append({
	# 	'name': 'Absent',
	# 	'value': len(attendance)
	# })
	attendance_count = len(attendance)
	attendance_dict = []
	for att in attendance:
		attendance_data = OrderedDict()
		attendance_data['Employee'] = att.get('employee') or ''
		attendance_data['Employee Name'] = att.get('employee_name') or ''
		attendance_data['Absent Date'] = formatdate(att.get('attendance_date')) or ''
		attendance_dict.append(attendance_data)
	
	if not attendance:
		attendance_data = OrderedDict()
		attendance_data['Employee'] = None
		attendance_data['Employee Name'] = None
		attendance_data['Absent Date'] = None
		attendance_dict.append(attendance_data)

	leave_applicaton = """SELECT leave_type, name, employee, employee_name, from_date, to_date, total_leave_days, workflow_state
		FROM `tabLeave Request`
		WHERE docstatus = 0
		AND '{0}' BETWEEN from_date AND to_date
		AND '{1}' BETWEEN from_date AND to_date
		AND from_date BETWEEN '{0}' AND '{1}'
		AND to_date BETWEEN '{0}' AND '{1}'
		
		UNION ALL

		SELECT leave_type, name, employee_id AS employee, employee_name, from_date, to_date, total_leave_days, workflow_state
		FROM `tabVacation Leave Application`
		WHERE docstatus = 0
		AND '{0}' BETWEEN from_date AND to_date
		AND '{1}' BETWEEN from_date AND to_date
		AND from_date BETWEEN '{0}' AND '{1}'
		AND to_date BETWEEN '{0}' AND '{1}'""".format(start_date, end_date)
	leave_applicaton = frappe.db.sql(leave_applicaton, as_dict=True)
	
	# label.append('Pending Leave Approval')
	# data.append(len(leave_applicaton))

	# result_list.append({
	# 	'name': 'Pending Leave Approval',
	# 	'value': len(leave_applicaton)
	# })

	leave_count = len(leave_applicaton)
	leave_dict = []
	for la in leave_applicaton:
		leave_data = OrderedDict()
		leave_data['Leave Type'] = la.get('leave_type') or ''
		leave_data['Application No.'] = la.get('name') or ''
		leave_data['Employee'] = la.get('employee') or ''
		leave_data['Employee Name'] = la.get('employee_name') or ''
		leave_data['Start Date'] = formatdate(la.get('from_date')) or ''
		leave_data['End Date'] = formatdate(la.get('to_date')) or ''
		leave_data['Total Days'] = la.get('total_leave_days') or ''
		leave_data['Status'] = formatdate(la.get('workflow_state')) or ''
		leave_dict.append(leave_data)
	
	if not leave_dict:
		leave_data = OrderedDict()
		leave_data['Leave Type'] = None
		leave_data['Application No.'] = None
		leave_data['Employee'] = None
		leave_data['Employee Name'] = None
		leave_data['Start Date'] = None
		leave_data['End Date'] = None
		leave_data['Total Days'] = None
		leave_data['Status'] = None
		leave_dict.append(leave_data)


	late_coming = """SELECT *
		FROM `tabLate Coming Request`
		WHERE docstatus = 0
		AND attendance_date BETWEEN '{0}' AND '{1}'""".format(start_date, end_date)
	late_coming = frappe.db.sql(late_coming, as_dict=True)

	# label.append('Pending Late Coming Request')
	# data.append(len(late_coming))

	# 	result_list.append({
	# 	'name': 'Pending Late Coming Request',
	# 	'value': len(late_coming)
	# })

	late_coming_count = len(late_coming)
	late_coming_dict = []
	for lc in late_coming:
		late_coming_data = OrderedDict()
		late_coming_data['Application No.'] = lc.get('name') or ''
		late_coming_data['Employee'] = lc.get('employee') or ''
		late_coming_data['Employee Name'] = lc.get('employee_name') or ''
		late_coming_data['For Date'] = formatdate(lc.get('attendance_date')) or ''
		late_coming_data['Status'] = formatdate(lc.get('status')) or ''
		late_coming_dict.append(late_coming_data)
	
	if not late_coming_dict:
		late_coming_data = OrderedDict()
		late_coming_data['Application No.'] = None
		late_coming_data['Employee'] = None
		late_coming_data['Employee Name'] = None
		late_coming_data['For Date'] = None
		late_coming_data['Status'] = None
		late_coming_dict.append(late_coming_data)

	early_going = """SELECT *
		FROM `tabEarly Going Request`
		WHERE docstatus = 0
		AND attendance_date BETWEEN '{0}' AND '{1}'""".format(start_date, end_date)
	early_going = frappe.db.sql(early_going, as_dict=True)

	# label.append('Pending Early Going Request')
	# data.append(len(early_going))

	# result_list.append({
	# 	'name': 'Pending Early Going Request',
	# 	'value': len(early_going)
	# })

	# return result_list

	early_going_count = len(early_going)
	early_going_dict = []
	for eg in early_going:
		early_going_data = OrderedDict()
		early_going_data['Application No.'] = eg.get('name') or ''
		early_going_data['Employee'] = eg.get('employee') or ''
		early_going_data['Employee Name'] = eg.get('employee_name') or ''
		early_going_data['For Date'] = formatdate(eg.get('attendance_date')) or ''
		early_going_data['Status'] = formatdate(eg.get('status')) or ''
		early_going_dict.append(early_going_data)
	
	if not early_going_dict:
		early_going_data = OrderedDict()
		early_going_data['Application No.'] = None
		early_going_data['Employee'] = None
		early_going_data['Employee Name'] = None
		early_going_data['For Date'] = None
		early_going_data['Status'] = None
		early_going_dict.append(early_going_data)

	# return label, data

	return {'attendance': attendance_dict,
		'attendance_count': attendance_count,
		'leave': leave_dict,
		'leave_count': leave_count,
		'late_coming': late_coming_dict,
		'late_coming_count': late_coming_count,
		'early_going': early_going_dict,
		'early_going_count': early_going_count}