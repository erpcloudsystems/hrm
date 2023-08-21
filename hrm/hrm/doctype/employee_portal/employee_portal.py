# -*- coding: utf-8 -*-
# Copyright (c) 2020, avu and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import json
from collections import OrderedDict
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leaves_for_period#, get_pending_leaves_for_period
from frappe.utils import flt, nowdate, getdate, get_first_day, get_last_day, formatdate, now_datetime
from datetime import datetime
from hrm.custom_methods import get_leve_name


class EmployeePortal(Document):
	def employee_detail_json(self):
		emp_detail = OrderedDict()
		
		profile_data = self.employee_profile()
		leave_data = get_leave_details(self.get('employee'), nowdate()) if self.get('employee') else {}
		
		emp_detail['General'] = {'method': 'general_tab', 'data': profile_data}
		emp_detail['Leave Details'] = {'method': 'leave_tab', 'data': leave_data}
		emp_detail['Leave History'] = {'method': 'leave_history_tab', 'data': self.leave_history()}
		emp_detail['Salary Details'] = {'method': 'cardview_tab', 'data': self.salary_detail()}

		return json.dumps({'employee_detail': emp_detail, 'profile_detail': profile_data})
	

	def employee_profile(self):
		employee = """select * from `tabEmployee` where name = '{0}'""".format(self.get('employee'))
		employee = frappe.db.sql(employee, as_dict=True)

		employee = employee[0] if employee else {}

		bi_data = OrderedDict()
		
		bi_data['Date of Joining'] = str(formatdate(employee.get('date_of_joining')) or '')
		bi_data['Date of Birth'] = str(formatdate(employee.get('date_of_birth')) or '')
		bi_data['Company'] = employee.get('company') or ''
		bi_data['User ID'] = employee.get('user_id') or ''
		bi_data['Gender'] = employee.get('gender') or ''
		bi_data['Status'] = employee.get('status') or ''
		bi_data['Employment Type'] = employee.get('employment_type') or ''
		bi_data['Branch'] = employee.get('branch') or ''
		bi_data['Department'] = employee.get('department') or ''
		bi_data['Designation'] = employee.get('designation') or ''
		bi_data['Shift Type'] = employee.get('shift_type') or ''
		bi_data['Shift Name'] = employee.get('default_shift') or ''
		bi_data['Country'] = employee.get('country') or ''
		bi_data['Nationality'] = employee.get('nationality') or ''
		bi_data['ID Number'] = employee.get('id_number') or ''
		bi_data['Driving License No'] = employee.get('driving_license_no') or ''
		bi_data['Driving License Issue Date'] = employee.get('driving_license_issue_date') or ''
		bi_data['Driving License Expiry Date'] = employee.get('driving_license_expiry_date') or ''
		bi_data['Emergency Phone No.'] = employee.get('emergency_phone_number') or ''
		bi_data['Current Address'] = employee.get('current_address') or ''
		bi_data['Personal Email ID'] = employee.get('personal_email') or ''
		bi_data['Cell Number'] = employee.get('cell_number') or ''
		bi_data['Enroll Number'] = employee.get('enroll_number') or ''

		return {'profile_img': employee.get('image'),
			'profile_name': employee.get('employee_name') or "",
			'profile_tab': {
				'data': bi_data,
				'link': [{
					'label': _("Leave"),
					'action': "form_route",
					'method': "create_leave_request"
				},
				{
					'label': _("Late Coming"),
					'action': "form_route",
					'method': "create_late_request"
				},
				{
					'label': _("Early Going"),
					'action': "form_route",
					'method': "create_early_request"
				},
				{
					'label': _("Vacation Leave"),
					'action': "form_route",
					'method': "create_vacation_appl"
				},
				{
					'label': _("Vacation Rejoining"),
					'action': "form_route",
					'method': "create_vacation_rejoining_appl"
				},
				{
					'label': _("Overtime"),
					'action': "form_route",
					'method': "create_ot_request"
				},
				{
					'label': _("Loan Application"),
					'action': "form_route",
					'method': "create_loan_appl"
				},
				{
					'label': _("Master Data Change"),
					'action': "form_route",
					'method': "employee_data_change"
				},
				{
					'label': _("Pending Approval List"),
					'action': "form_list",
					'method': "create_workflow_action"
				}]
			}
		}
	

	def salary_detail(self, payroll_period=None):
		payroll_dict = self.get_payroll_period(payroll_period)
		
		return {
			'payroll_period': payroll_dict.get('name'),
			'data': {
				'attendance-card': self.attendance_detail(payroll_dict),
				'salary-slip-card': self.salary_slip(payroll_dict)
			}}
	

	def get_payroll_period(self, payroll_period):
		if payroll_period:
			payroll = """SELECT * FROM `tabPayroll Period` WHERE name = '{}'""".format(payroll_period)
		else:
			payroll = """SELECT `PP`.*
				FROM `tabPayroll Period` AS `PP`
				LEFT JOIN `tabEmployee` AS `E`
					ON `E`.`name` = '{}'
					AND `E`.`company` = `PP`.`company`
				WHERE `PP`.`start_date` = '{}'
				AND `PP`.`end_date` = '{}'""".format(self.get('employee'), get_first_day(getdate()), get_last_day(getdate()))
		payroll = frappe.db.sql(payroll, as_dict=True)
		
		return payroll[0] if payroll else frappe.throw("Payroll Period is not configured for Current Month")


	def attendance_detail(self, payroll_dict):
		attendance = """select COUNT(IF(status='On Leave' and leave_type='{3}', status, NULL)) AS vacation,
			COUNT(IF(status='On Leave' and leave_type!='{3}', status, NULL)) AS on_leave,
			COUNT(IF(status='Absent' AND leave_type IS NULL, status, NULL)) AS absent,
			COUNT(IF(status='Absent' AND leave_type='{4}', status, NULL)) AS weekoff,
			COUNT(IF(status='Absent' AND leave_type='{5}', status, NULL)) AS holiday,
			COUNT(IF(status='Present', status, NULL)) AS present,
			SUM(late_coming_minutes / 60) AS late_coming_minutes,
			SUM(early_going_minutes / 60) AS early_going_minutes,
			SUM(ot_hours) AS ot_hours
			from`tabAttendance`
			where employee = '{0}'
			and docstatus < 2
			and attendance_date between '{1}' and '{2}'""".format(self.get('employee'), payroll_dict.get('actual_start_date'), payroll_dict.get('actual_end_date'), get_leve_name('V'), get_leve_name('WO'), get_leve_name('H'))
		attendance = frappe.db.sql(attendance, as_dict=True)
		attendance = attendance[0] if attendance else {}

		attendance_data = OrderedDict()
		
		attendance_data['Present Days'] = attendance.get('present') or 0
		attendance_data['Absent Days'] = attendance.get('absent') or 0
		attendance_data['Weekoff Days'] = attendance.get('weekoff') or 0
		attendance_data['Holidays'] = attendance.get('holiday') or 0
		attendance_data['Leave Days'] = attendance.get('on_leave') or 0
		attendance_data['Vaction Days'] = attendance.get('vacation') or 0
		attendance_data['Total Overtime hrs'] = convert(attendance.get('ot_hours') or 0)
		attendance_data['Total Late coming hrs'] = convert(attendance.get('late_coming_minutes') or 0)
		attendance_data['Total Early going hrs'] = convert(attendance.get('early_going_minutes') or 0)

		return {
			'data': attendance_data,
			'period': '{} - {}'.format(formatdate(payroll_dict.get('actual_start_date')),formatdate(payroll_dict.get('actual_end_date'))),
			'link': {
				'label': 'Attendance List',
				'action': 'custom_doctype',
				'option': {
					# Report Name
					'name': "Attendance",
					'company': frappe.db.get_value('Employee', self.get('employee'), 'company'),
					'employee': self.get('employee'),
                    'start_date':payroll_dict.get('actual_start_date').strftime('%m-%d-%Y'),
                    'end_date':payroll_dict.get('actual_end_date').strftime('%m-%d-%Y')
					# 'month': datetime.strftime(payroll_dict.get('actual_start_date'), "%b"),
					# 'year': datetime.strftime(payroll_dict.get('actual_start_date'), "%Y")
				}
			}
		}
	

	def salary_slip(self, payroll_dict):
		sal_slip = """select *
		from `tabSalary Slip`
		where docstatus = 1
		and employee = '{0}'
		and start_date = '{1}'
		and end_date = '{2}'""".format(self.get('employee'), payroll_dict.get('start_date'), payroll_dict.get('end_date'))
		sal_slip = frappe.db.sql(sal_slip, as_dict=True)
		sal_slip = sal_slip[0] if sal_slip else {}

		sal_data = OrderedDict()
		
		sal_data['Basic Salary'] = self.salary_structure(datetime.strftime(payroll_dict.get('end_date'), "%m"), datetime.strftime(payroll_dict.get('end_date'), "%Y")).get('base') or 0
		sal_data['Gross Pay'] = sal_slip.get('gross_pay') or 0
		sal_data['Total Deduction'] = sal_slip.get('total_deduction') or 0
		sal_data['Total Loan Repayment'] = sal_slip.get('total_loan_repayment') or 0
		sal_data['Net Pay'] = sal_slip.get('net_pay') or 0

		salary_detail = """SELECT salary_component, IF(parentfield='earnings', amount, 0) AS 'earning', IF(parentfield='deductions', amount, 0) AS 'deduction'
			FROM `tabSalary Detail`
			WHERE parent = '{}'
			AND amount > 0
			ORDER BY parentfield DESC, idx""".format(sal_slip.get('name'))
		salary_detail = frappe.db.sql(salary_detail, as_dict=True)

		
		return {
			'data': sal_data,
			'table_data': salary_detail,
			'period': '{} - {}'.format(formatdate(payroll_dict.get('start_date')),formatdate(payroll_dict.get('end_date'))),
			'link': {
				'label': 'Print Salary Slip',
				'action': 'custom_print_format',
				'option': {
					'doctype': 'Salary Slip',
					'name': sal_slip.get('name')
				}
			}
		}


	def salary_structure(self, month, year):
		sal_str = """select base
			from `tabSalary Structure Assignment`
			where employee = '{0}'
			and docstatus = 1
			and (year(from_date) < '{2}'
				or (month(from_date) <= '{1}'
					and year(from_date) = '{2}'))
			order by from_date desc
			limit 1""".format(self.get('employee'), month, year)
		sal_str = frappe.db.sql(sal_str, as_dict=True)
		return sal_str[0] if sal_str else {}

	
	def leave_history(self):
		leave_appl = """select leave_type, name, cast(DATE_FORMAT(from_date, '%d-%m-%Y') as char) as from_date, cast(DATE_FORMAT(to_date, '%d-%m-%Y') as char) as to_date, total_leave_days, workflow_state as status
			from `tabLeave Application`
			where employee = '{}'""".format(self.get('employee'))
		
		return frappe.db.sql(leave_appl, as_dict=True)
	

	def employee_data_change(self):
		edc_doc = frappe.new_doc('Employee Data Changes')
		edc_doc.employee = self.get('employee')

		return edc_doc.as_dict()
	

	def create_late_request(self):
		clr_doc = frappe.new_doc('Late Coming Request')
		clr_doc.employee = self.get('employee')
		clr_doc.employee_name = frappe.db.get_value('Employee', self.get('employee'), 'employee_name')

		return clr_doc.as_dict()
	

	def create_early_request(self):
		cer_doc = frappe.new_doc('Early Going Request')
		cer_doc.employee = self.get('employee')
		cer_doc.employee_name = frappe.db.get_value('Employee', self.get('employee'), 'employee_name')

		return cer_doc.as_dict()
	

	def create_vacation_appl(self):
		vac_doc = frappe.new_doc('Vacation Leave Application')
		vac_doc.employee_id = self.get('employee')
		vac_doc.employee_name = frappe.db.get_value('Employee', self.get('employee'), 'employee_name')

		return vac_doc.as_dict()

	def create_vacation_rejoining_appl(self):
		vac_rejoin_doc = frappe.new_doc('Vacation Rejoining')
		vac_rejoin_doc.employee_id = self.get('employee')
		vac_rejoin_doc.employee_name = frappe.db.get_value('Employee', self.get('employee'), 'employee_name')
		vac_rejoin_doc.company = frappe.db.get_value('Employee', self.get('employee'), 'company')

		return vac_rejoin_doc.as_dict()

	def create_ot_request(self):
		ot_doc = frappe.new_doc('OT Request')
		ot_doc.applicant = self.get('employee')
		ot_doc.applicant_name = frappe.db.get_value('Employee', self.get('employee'), 'employee_name')
		ot_doc.from_time = now_datetime().strftime('%H:%M:%S')
		ot_doc.to_time = now_datetime().strftime('%H:%M:%S')

		return ot_doc.as_dict()


	def create_leave_request(self):
		leave_doc = frappe.new_doc('Leave Request')
		leave_doc.employee = self.get('employee')
		leave_doc.employee_name = frappe.db.get_value('Employee', self.get('employee'), 'employee_name')

		return leave_doc.as_dict()
	
	def create_loan_appl(self):
		loan_doc = frappe.new_doc('Loan Application')
		loan_doc.applicant = self.get('employee')

		return loan_doc.as_dict()

	def create_workflow_action(self):
		WA_doc = frappe.new_doc('Workflow Action')
		WA_doc.status = 'Open'

		return WA_doc.as_dict()		

def get_leave_details(employee, date):
	allocation_records = get_leave_allocation_records(employee)
	leave_allocation = {}
	for d in allocation_records:
		allocation = allocation_records.get(d, frappe._dict())
		remaining_leaves = get_leave_balance_on(employee, d, date, to_date = allocation.to_date,
			consider_all_leaves_in_the_allocation_period=True)
		end_date = allocation.to_date
		leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, end_date) * -1
		#leaves_pending = get_pending_leaves_for_period(employee, d, allocation.from_date, end_date)

		leave_allocation[d] = {
			"current_year_allocation": allocation.new_leaves_allocated,
			"balance_carry_foward": allocation.unused_leaves,
			"leaves_taken": leaves_taken,
			#"pending_leaves": leaves_pending,
			"remaining_leaves": remaining_leaves}

	return leave_allocation


def get_leave_allocation_records(employee):
	''' returns the total allocated leaves and carry forwarded leaves based on ledger entries '''

	allocation_details = frappe.db.sql("""
		SELECT
			SUM(CASE WHEN is_carry_forward = 1 THEN leaves ELSE 0 END) as cf_leaves,
			SUM(CASE WHEN is_carry_forward = 0 THEN leaves ELSE 0 END) as new_leaves,
			MIN(from_date) as from_date,
			MAX(to_date) as to_date,
			leave_type
		FROM `tabLeave Ledger Entry`
		WHERE docstatus=1
			AND transaction_type="Leave Allocation"
			AND employee=%(employee)s
			AND is_expired=0
			AND is_lwp=0
		GROUP BY employee, leave_type
	""", dict(employee=employee), as_dict=1) #nosec

	allocated_leaves = frappe._dict()
	for d in allocation_details:
		allocated_leaves.setdefault(d.leave_type, frappe._dict({
			"from_date": d.from_date,
			"to_date": d.to_date,
			"total_leaves_allocated": flt(d.cf_leaves) + flt(d.new_leaves),
			"unused_leaves": d.cf_leaves,
			"new_leaves_allocated": d.new_leaves,
			"leave_type": d.leave_type
		}))
	return allocated_leaves


def convert(time):
	time_str = str(float(time)).split('.')
	return '{:02}:{:.2}'.format(int(time_str[0]), str(int(time_str[-1]) * 60))