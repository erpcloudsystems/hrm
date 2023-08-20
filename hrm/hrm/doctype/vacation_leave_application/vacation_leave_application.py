# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from hrm.custom_methods import get_leve_name
from frappe.utils import flt, date_diff, formatdate, add_days, getdate, add_months, add_years, get_first_day
from copy import deepcopy
from frappe.model.workflow import apply_workflow
from hrm.custom_script.leave_application.leave_application import validate_leave_overlap

class OverlapError(frappe.ValidationError): pass

class VacationLeaveApplication(Document):
	def validate(self):
		if self.validate_ss_processed(self.employee_id,self.from_date) or  self.validate_ss_processed(self.employee_id,self.to_date) : 
			frappe.throw("Can not create or edit Vacation leave application, Salary is already processed for this month")
		self.new_get_accrual_till()
		# self.validate_leave_overlap()
		validate_leave_overlap(self)
		self.validate_period()

		special_leav = 0
		if self.total_leave_days > self.eligible_days:
			if self.eligible_days > 0:
				special_leav = flt(self.total_leave_days - self.eligible_days, self.precision('eligible_days'))
			else:
				special_leav = self.total_leave_days
		
		if special_leav > 0:
			msg = "Employee {} has applied for Special leave for {} days".format(self.get('employee_id'), special_leav)
			if self.warning_msg:
				self.warning_msg += "<br>"+msg
			else:
				self.warning_msg = msg
	def validate_ss_processed(self,employee, date):
		ss_list = frappe.db.sql("""
				select t1.name, t1.salary_structure from `tabSalary Slip` t1
				where t1.docstatus = 1 and t1.actual_attendance_start_date <= %s and t1.actual_attendance_end_date >= %s and t1.employee = %s
			""" % ('%s', '%s', '%s'), (date, date, employee), as_dict=True)
		# frappe.errprint(["ss",ss_list])
		if len(ss_list) : return True
		return False
	def on_submit(self):
		if self.status == "Open":
			frappe.throw(_("Only Leave Applications with status 'Approved' and 'Rejected' can be submitted"))
		
		if self.status == "Approved":
			self.validate_allocation()
			self.leave_allocation()
			self.insert_in_leav_appl()
		
		
		
		# if self.status == "Rejected":
		# 	self.remove_allocation(status=1)
	
	def on_cancel(self):
		self.cancel_leave_application(status=1)
		self.remove_allocation(status=1)
		self.status = "Cancelled"
		self.db_update()
		self.load_from_db()

	def before_save(self):
		workflow = []
		workflow_del = frappe.db.get_value("HR Settings", None, "enable_workflow_delegation")
		if int(workflow_del)==1:
			emp_doc = frappe.get_doc("Employee",self.employee_id)
			user_role = frappe.get_roles(emp_doc.user_id)
			if emp_doc.user_id:
				if user_role:
					for i in user_role:
						workflow_list = frappe.get_list("Workflow Document State", filters={"allow_edit":i}, fields = ["parent","allow_edit"])
						if workflow_list:
							for j in workflow_list:
								# frappe.msgprint(str(j.allow_edit))
								workflow.append(j.parent)
				if len(workflow)>0 and self.doctype=="Vacation Leave Application" and self.ignore_workflow_delegation==0 and self.workflow_delegation_id==None and self.status=="Open":
					self.flags.ignore_on_update=True
					frappe.msgprint("Please Make <b>Workflow Delegation</b>")

	def before_cancel(self):
		if self.validate_ss_processed(self.employee_id,self.from_date) or  self.validate_ss_processed(self.employee_id,self.to_date) : 
			frappe.throw("Can not cancel Vacation leave application, Salary is already processed for this month")	
		if self.workflow_delegation_id:
			wf_doc = frappe.get_doc("Workflow Delegation",self.workflow_delegation_id)
			wf_id = wf_doc.reference_id
			if wf_doc.docstatus == 1:
				wf_doc.reference_id = None 
				wf_doc.cancel()
				# wf_doc.reference_id = wf_id
				frappe.db.sql("UPDATE `tabWorkflow Delegation` SET reference_id ='{0}' where name ='{1}' ".format(wf_id, self.workflow_delegation_id))
			else:
				wf_doc.reference_id = ""
				wf_doc.db_update()
				wf_doc.delete()

	def before_submit(self):
		workflow = []
		workflow_del = frappe.db.get_value("HR Settings", None, "enable_workflow_delegation")
		if int(workflow_del)==1:
			emp_doc = frappe.get_doc("Employee",self.employee_id)
			user_role = frappe.get_roles(emp_doc.user_id)
			if user_role:
				for i in user_role:
					workflow_list = frappe.get_list("Workflow Document State", filters={"allow_edit":i}, fields = ["parent","allow_edit"])
					if workflow_list:
						for j in workflow_list:
							# frappe.msgprint(str(j.allow_edit))
							workflow.append(j.parent)
			if len(workflow)>0 and self.doctype=="Vacation Leave Application" and self.workflow_delegation_id==None and self.ignore_workflow_delegation==0 and self.status=="Approved":
				self.flags.ignore_validate = True
				self.flags.ignore_on_update=True
				frappe.throw("Please Make <b>Workflow Delegation</b>")
			else:
				self.run_method('on_update')

	def on_trash(self):
		if self.validate_ss_processed(self.employee_id,self.from_date) or  self.validate_ss_processed(self.employee_id,self.to_date) : 
			frappe.throw("Can not cancel Vacation leave application, Salary is already processed for this month")	
		self.cancel_leave_application(status=2)
		self.remove_allocation(status=2)
		self.delete_wf()

	def delete_wf(self):
		wd_list="select name from `tabWorkflow Delegation` where reference_id='{0}' order by name desc".format(self.name)
		wd_list_data = frappe.db.sql(wd_list,as_dict=True)
		if wd_list_data:
			for w in wd_list_data:
				# frappe.msgprint(str(w.name))
				wf_doc = frappe.get_doc("Workflow Delegation",w.name)
				wf_id = wf_doc.reference_id 
				wf_doc.reference_id = None
				if wf_doc.docstatus == 1:
					wf_doc.cancel()
					wf_doc.delete() 
				else:
					# frappe.throw(str(wf_doc.reference_id))
					wf_doc.reference_id = ""
					wf_doc.db_update()
					wf_doc.delete()
	
	def validate_eligible_employee(self):
		eligible_emp = """SELECT eligible_for_airline_ticket, year, mode_of_reimbursement, origin_airport, destination_airport, eligible_cash, class
			FROM `tabEmployee`
			WHERE name = '{0}'""".format(self.employee_id)
		eligible_emp = frappe.db.sql(eligible_emp, as_dict=True)
		return eligible_emp
	
	def validate_allocation(self):
		if self.request_advance_leave == 0:
			if self.eligible_days == 0:
				frappe.throw("You cannot take any more leave")

			# if self.total_leave_days > self.eligible_days:
			# 	frappe.throw("Vacation Leave cannot be greater then Eligible days")

	
	def insert_in_leav_appl(self):
		doc = frappe.new_doc("Leave Application")
		doc.employee = self.employee_id
		doc.company = self.company
		doc.leave_type = self.leave_type
		doc.vacation_leave_application = self.name
		doc.posting_date = self.posting_date
		doc.status = self.status
		doc.description = self.reason
		doc.from_date = self.from_date
		doc.to_date = self.to_date
		doc.total_leave_days = self.total_leave_days
		doc.leave_approver = self.leave_approver
		doc.ignore_workflow_delegation = 1

		# doc.insert(ignore_permissions=True)
		doc.flags.ignore_permissions = True
		doc.submit()
		state = {'Approved': 'Approve', 'Rejected': 'Reject'}
		leave_sql=frappe.db.sql("select * from `tabWorkflow` where document_type='Leave Application'  and is_active=1")
		if leave_sql:
			while True:
				apply_workflow(doc, state.get(self.status))
				if doc.docstatus == 1: break
	
	def cancel_leave_application(self, status):
		sql = "select name, docstatus from `tabLeave Application` where vacation_leave_application = '{0}'".format(self.name)
		data = frappe.db.sql(sql, as_dict=True)
		if data:
			for i in data:
				name = i['name']
				d_status = i['docstatus']
				doc = frappe.get_doc("Leave Application", name)
				doc.vacation_leave_application = None
				frappe.errprint([doc.docstatus,status,self.docstatus,'docstatus'])
				if d_status == 1 and status == 1:
					# doc.cancel()
					# doc.vacation_leave_application = self.name
					# # doc.workflow_state = self.workflow_state
					# doc.db_update()
					leave_sql=frappe.db.sql("select * from `tabWorkflow` where document_type='Leave Application'  and is_active=1")
					if leave_sql:
						while True:
							state = {'Approved': 'Approve', 'Rejected': 'Reject','Cancelled':'Cancel'}
							apply_workflow(doc, state.get(self.status))
							if doc.docstatus == 2: break
					else:
						doc.cancel()
						doc.vacation_leave_application = self.name
						# doc.workflow_state = self.workflow_state
						doc.db_update()		
				else:
					doc.db_update()    
					if d_status == 1:
						doc.cancel()
					
					doc.delete()
	
	def leave_allocation(self):
		# leave for 1 day
		if frappe.db.get_value("Leave Type", self.leave_type, "allow_negative")!=1: 
			frappe.throw("In Leave Type allow negative is unchecked")
		adjust_day = 1 if getdate(self.from_date) == getdate(self.to_date) else 0
		
		ledg = frappe.new_doc("Leave Allocation")

		ledg.employee = self.employee_id
		ledg.leave_type = get_leve_name('V')
		ledg.from_date = self.from_date
		ledg.to_date = add_days(self.to_date, adjust_day)
		ledg.new_leaves_allocated = self.total_leave_days

		# ledg.insert()
		ledg.flags.ignore_permissions = True
		ledg.submit()
	
	def remove_allocation(self, status):
		# leave for 1 day
		adjust_day = 1 if getdate(self.from_date) == getdate(self.to_date) else 0

		remo_sql = """SELECT name, docstatus
			FROM `tabLeave Allocation`
			WHERE leave_type = '{0}'
			AND employee = '{1}'
			AND from_date = '{2}'
			AND to_date = '{3}'
			AND docstatus = {4}""".format(get_leve_name('V'), self.employee_id, self.from_date, add_days(self.to_date, adjust_day), status)
		data = frappe.db.sql(remo_sql, as_dict=True)

		if data:
			for i in data:
				name = i['name']
				d_status = i['docstatus']
				doc = frappe.get_doc("Leave Allocation", name)
				if d_status == 1 and status == 1:
					doc.cancel()
				else:
					if d_status == 1:
						doc.cancel()
					doc.delete()

	def validate_period(self):
		if date_diff(self.to_date, self.from_date) < 0:
			frappe.throw(_("To Date cannot be less then From Date"))
		# if date_diff(self.to_date, self.from_date) == 0:
		# 	frappe.throw(_("Vacation leave cannot be created for 1 day"))

	# def validate_leave_overlap(self):
	# 	if not self.name:
	# 		# hack! if name is null, it could cause problems with !=
	# 		self.name = "New Leave Application"
		
	# 	for d in frappe.db.sql("""
	# 		select
	# 			name, leave_type, posting_date, from_date, to_date, total_leave_days, half_day_date
	# 		from `tabLeave Application`
	# 		where employee = %(employee)s and docstatus < 2 and status in ("Open", "Approved")
	# 		and to_date >= %(from_date)s and from_date <= %(to_date)s
	# 		and name != %(name)s""", {
	# 			"employee": self.employee_id,
	# 			"from_date": self.from_date,
	# 			"to_date": self.to_date if self.to_date else self.from_date,
	# 			"name": self.name
	# 		}, as_dict=1):
	# 		if d:
	# 			self.throw_overlap_error(d)
	# 	for d in frappe.db.sql("""
	# 		select
	# 			name, leave_type, posting_date, from_date, to_date, total_leave_days, half_day_date
	# 		from `tabLeave Request`
	# 		where employee = %(employee)s and docstatus < 2 and status in ("Open", "Approved")
	# 		and to_date >= %(from_date)s and from_date <= %(to_date)s
	# 		and name != %(name)s""", {
	# 			"employee": self.employee_id,
	# 			"from_date": self.from_date,
	# 			"to_date": self.to_date if self.to_date else self.from_date,
	# 			"name": self.name
	# 		}, as_dict=1):
	# 		if d:
	# 			self.throw_overlap_error(d,doctype = "Leave Request")
	# 	for d in frappe.db.sql("""
	# 		select
	# 			name, leave_type, posting_date, from_date, to_date, total_leave_days
	# 		from `tabVacation Leave Application`
	# 		where employee_id = %(employee)s and docstatus < 2 and status in ("Open", "Approved")
	# 		and to_date >= %(from_date)s and from_date <= %(to_date)s
	# 		and name != %(name)s""", {
	# 			"employee": self.employee_id,
	# 			"from_date": self.from_date,
	# 			"to_date": self.to_date if self.to_date else self.from_date,
	# 			"name": self.name
	# 		}, as_dict=1):
	# 		if d:
	# 			self.throw_overlap_error(d,doctype = "Vacation Leave Application")

	# def throw_overlap_error(self, d,doctype = "Leave Application"):
	# 	msg = _("Employee {0} has already applied for {1} between {2} and {3}").format(self.employee_id,
	# 		d['leave_type'], formatdate(d['from_date']), formatdate(d['to_date'])) \
	# 		+ """ <br><b><a href="#Form/{1}/{0}">{0}</a></b>""".format(d["name"],doctype)
	# 	frappe.throw(msg, OverlapError)

	def new_get_accrual_till(self):
		if self.employee_id and self.from_date:
			self.eligible_days = 0
			# self.validate_leave_overlap()

			result_dict = calculate_vacation(employee=self.employee_id, from_date=self.from_date, doctype=self.name)
			self.eligible_days = result_dict.get('eligible_days', 0)
			self.applied_rule = result_dict.get('applied_rule')
			self.last_vacation = result_dict.get('last_vacation')
			self.total_working_days = result_dict.get('working_days', 0)
			self.warning_msg = result_dict.get('warning_msg', None)
	
	def airline_ticket_request(self, emp):
		air_doc = frappe.new_doc('Airline Ticket Request')

		air_doc.employee = self.get('employee_id')
		air_doc.reason = self.get('leave_type')
		air_doc.from_date = self.get('from_date')
		air_doc.to_date = self.get('to_date')
		air_doc.origin_airport = emp.get('origin_airport')
		air_doc.destination_airport = emp.get('destination_airport')
		air_doc.set('class', emp.get('class'))

		return air_doc.as_dict()
	
	def exit_reentry_visa(self):
		visa_doc = frappe.new_doc('Exit ReEntry Visa')

		visa_doc.employee = self.get('employee_id')
		visa_doc.reason = self.get('leave_type')
		visa_doc.from_date = self.get('from_date')
		visa_doc.to_date = self.get('to_date')

		return visa_doc.as_dict()

import calendar

def days360(start_date, end_date, method_eu=False):

	start_day = start_date.day
	start_month = start_date.month
	start_year = start_date.year
	end_day = end_date.day
	end_month = end_date.month
	end_year = end_date.year

	if (
		start_day == 31 or
		(
			method_eu is False and
			start_month == 2 and (
				start_day == 29 or (
					start_day == 28 and
					calendar.isleap(start_year) is False
				)
			)
		)
	):
		start_day = 30

	if end_day == 31:
		if method_eu is False and start_day != 30:
			end_day = 1

			if end_month == 12:
				end_year += 1
				end_month = 1
			else:
				end_month += 1
		else:
			end_day = 30

	return (
		end_day + end_month * 30 + end_year * 360 -
		start_day - start_month * 30 - start_year * 360)


# --------------------------- calculate -----------------------------------------


def check_vacation_rule(employee_dict):
	emp_date = "SELECT IF(rejoining_date, rejoining_date, date_of_joining) AS start_date, date_of_joining, vacation_rule, IF(rejoining_date, vacation_opening_balance, 0) eligible_days \
		FROM `tabEmployee` \
		WHERE name = '{0}'".format(str(employee_dict['employee']))
	emp_date = frappe.db.sql(emp_date, as_dict=True)

	if emp_date:
		emp_date = emp_date[0]
		if emp_date['vacation_rule']:
			employee_dict['applied_rule'] = emp_date['vacation_rule']
			employee_dict['eligible_days'] = emp_date['eligible_days']
			# employee_dict['credit'] += emp_date['eligible_days']
			
			emp_start_date = getdate(emp_date['start_date'])
			if emp_date['eligible_days'] != 0:
				employee_dict['slab_list'].append({
					'to_date' : add_days(emp_start_date, -1),
					'employee': employee_dict['employee'],
					'opening_balance': emp_date['eligible_days']
				})

			if emp_start_date > employee_dict['max_range']:
				frappe.throw("Employee Joining Date is Greater than Vacation From Date")
			else:
				return employee_dict.update({
					'applied_date' : emp_date['date_of_joining'],
					'start_date'   : emp_start_date
				})
		else:
			frappe.throw("Vacation Leave Rule is not assigned to Employee '{0}'".format(employee_dict['employee']))
	else:
		frappe.throw("Please Enter Valid Employee ID")

def get_vacation_rule(employee_dict):
	get_rule = "SELECT days, eligible_after AS range_date, redirect_after_year, redirect_to_rule, frequency, maximum_carry_forward_days AS carryforward_day, carry_forward_days_need_to_be_availed_in_how_many_days AS carryforward_expiry, carry_forward_allowed \
		FROM `tabVacation Leave Rule` \
		WHERE docstatus = 1 \
		AND name ='{0}'".format(employee_dict['applied_rule'])
	get_rule = frappe.db.sql(get_rule, as_dict=True)
	
	if get_rule:
		get_rule = get_rule[0]
		employee_dict['rule'] = get_rule

		# dynaminc frequency
		frequency = get_rule['range_date']
		# monthly frequency
		if employee_dict['monthly_credit'] and float(get_rule['frequency']) > 0:
			frequency = get_rule['frequency']

		period_to = add_months(employee_dict['start_date'], frequency)

		# credit at the end of every month
		if employee_dict['iterate_loop'] == 1:
			period_to = get_first_day(period_to)

		employee_dict['to_date'] = add_days(period_to, -1)

		# monthly credit
		to_date = add_months(employee_dict['start_date'], get_rule['range_date'])
		if employee_dict['monthly_credit'] and employee_dict['iterate_loop'] == 1 and employee_dict['max_range'] < to_date and employee_dict['eligible_days'] == 0:
			employee_dict['warning_msg'] = _("As Per Vacation Rule, Employee {} is eligible from {}".format(employee_dict['employee'], formatdate(to_date)))
			frappe.msgprint(employee_dict['warning_msg'])

		
		if get_rule['carry_forward_allowed']:
			if not employee_dict.__contains__('carryforward') or (employee_dict['carryforward'] and add_days(employee_dict['carryforward']['to_date'], 1) == employee_dict['start_date']):
				employee_dict['carryforward'] = {
					'from_date': employee_dict['start_date'],
					'to_date': add_days(to_date, -1),
					'carryforward_day': get_rule['carryforward_day'],
					'carryforward_expiry': add_months(to_date, get_rule['carryforward_expiry']) if get_rule['carryforward_expiry'] > 0 else None
				}
		else:
			employee_dict['carryforward'] = {}

		# redirect condition
		if get_rule['redirect_after_year'] and float(get_rule['redirect_after_year']) > 0:
			emp_new_effective_dt = add_years(employee_dict['applied_date'], get_rule['redirect_after_year'])
			employee_dict['rule']['redirect_date'] = emp_new_effective_dt
			new_count_diff = date_diff(employee_dict['start_date'], str(emp_new_effective_dt))

			if int(new_count_diff) >= 0:
				employee_dict.update({
					'applied_rule' : get_rule['redirect_to_rule'],
					'applied_date' : emp_new_effective_dt
				})
				get_vacation_rule(employee_dict)
			else:
				between_date = emp_new_effective_dt
				date_between_range(employee_dict, between_date)
		
		if not employee_dict['monthly_credit']:
			# to skip the future advance in case of advance
			between_date = employee_dict['encashed_max_range']
			date_between_range(employee_dict, between_date, 1)

			# dynamic date between range
			between_date = add_days(employee_dict['max_range'], -1 * employee_dict['day_adjust'])
			date_between_range(employee_dict, between_date)
		
		return employee_dict
	else:
		frappe.throw("Invalid Vacation Rule")

def date_between_range(employee_dict, between_date, encash_abj=0):
	if employee_dict['start_date'] <= between_date <= employee_dict['to_date']:
		employee_dict['to_date'] = add_days(between_date, -1)

		# stop looping between advance encashment days
		if encash_abj:
			employee_dict['encashed_max_range'] = add_days(employee_dict['encashed_max_range'], -1)

def rule_change_select(order=None):
	return """SELECT name, docstatus, new_rule, posting_date
		FROM `tabVacation Rule Modification`
		WHERE docstatus < 2
		AND employee = '{0}'
		AND posting_date BETWEEN '{1}' AND '{2}'
		ORDER BY posting_date %s
		LIMIT 1
	"""% (order if order else 'ASC')

def rule_change_date(employee_dict):
	rule_change = rule_change_select().format(employee_dict['employee'], add_days(employee_dict['start_date'], 1), employee_dict['to_date'])
	rule_change = frappe.db.sql(rule_change, as_dict=True)
	
	if rule_change:
		rule_change = rule_change[0]
		employee_dict['rule_change'] = rule_change
		
		if rule_change['docstatus'] == 0 and employee_dict['ignore_msg'] == 0:
			frappe.throw('Vacation Rule Modification Is Not Submitted For Application {0}'.format(rule_change['name']))

		employee_dict['new_rule']     = rule_change['new_rule']
		employee_dict['applied_date'] = rule_change['posting_date']
		employee_dict['to_date']      = add_days(rule_change['posting_date'], -1)

	return employee_dict

def get_upl_leave(employee_dict, start_date, end_date):
	get_upl_sql = """SELECT `l`.`from_date`, `l`.`to_date`
		FROM `tabLeave Application` AS l
		LEFT JOIN `tabLeave Type` AS lt
			ON `l`.`leave_type` = `lt`.`name`
		WHERE `l`.`docstatus` < 2
		AND `lt`.`leave_type_abbr` != 'V'
		AND (`l`.`status` != 'Rejected'
				OR (`l`.`docstatus` = 0
					AND `l`.`status` = 'Rejected'))
		AND `lt`.`exclude_from_vacation_leave_count` = 1
		AND `l`.`employee` = '{0}'
		AND `l`.`from_date` BETWEEN '{1}' AND '{2}'""".format(employee_dict['employee'], start_date, end_date)

	get_upl_sql = frappe.db.sql(get_upl_sql, as_dict=True)

	employee_dict['exclude_entry'] += get_upl_sql

def get_exclude_count(employee_dict):
	count = 0

	to_date = employee_dict['max_range']
	if employee_dict.__contains__('to_date'):
		to_date = employee_dict['to_date']

	for idx in range(len(employee_dict['exclude_entry']) - 1, -1 , -1):
		row = employee_dict['exclude_entry'][idx]
		if row['to_date'] > to_date:
			count += days360(row['from_date'], add_days(to_date, 1))
			row['from_date'] = add_days(to_date, 1)
		else:
			count += days360(row['from_date'], add_days(row['to_date'], 1))
			employee_dict['exclude_entry'].pop(idx)
	
	return count

def calc_accural_rcd(employee_dict, ignore_rejoining):
	actual_to_date = add_months(employee_dict['start_date'], employee_dict['rule']['range_date'])
	actual_day_diff = days360(getdate(employee_dict['start_date']), getdate(actual_to_date))
	per_day = float(employee_dict['rule']['days']) / float(actual_day_diff)

	# monthly credit between range
	# if employee_dict['monthly_credit'] and add_days(employee_dict['max_range'], -1 * employee_dict['day_adjust']) < employee_dict['to_date']:
	# 	return
	if employee_dict['monthly_credit'] and employee_dict['encashed_max_range'] < employee_dict['to_date']:
		return

	day_diff = days360(getdate(employee_dict['start_date']), getdate(add_days(employee_dict['to_date'], 1)))
	
	# get exclude count in range
	day_diff -= get_exclude_count(employee_dict)
	
	# to stop adding of advance days in case of enchasement
	if not employee_dict['start_date'] >= employee_dict['encashed_max_range']:
		employee_dict['working_days'] = day_diff
		employee_dict['credit'] += float(day_diff) * float(per_day)
		employee_dict['eligible_days'] += float(day_diff) * float(per_day)


def carryforward_adj(employee_dict):
	if not employee_dict['carryforward']: return

	carryforward_rule = employee_dict['carryforward']

	deducat_expired_day = (employee_dict.get('carryforward_day_adj') or 0)
	if employee_dict.get('carryforward_day_expire') and deducat_expired_day > 0 and employee_dict['start_date'] <= employee_dict.get('carryforward_day_expire') <= employee_dict['to_date']:
		employee_dict['debit'] += deducat_expired_day
		employee_dict['eligible_days'] -= deducat_expired_day
		employee_dict['expired_carryforward'] = deducat_expired_day
		employee_dict['expired_carryforward_on'] = employee_dict['carryforward_day_expire']

		employee_dict['carryforward_day_expire'] = None
		employee_dict['carryforward_day_adj'] = 0
	
	if employee_dict['to_date'] == carryforward_rule['to_date']:
		# Stop Carry forward of Current period
		if carryforward_rule['carryforward_expiry'] and carryforward_rule['carryforward_expiry'] > employee_dict['encashed_max_range']:
				return
		
		# Carry Forward Allowed Days
		carryforward_rule['exclude_carryforward'] = 0
		if carryforward_rule['carryforward_day'] > 0 and employee_dict['eligible_days'] > carryforward_rule['carryforward_day']:
			employee_dict['carryforward_flag'] = 1
			adjust_day = employee_dict['eligible_days'] - carryforward_rule['carryforward_day'] 
			carryforward_rule['exclude_carryforward'] = adjust_day
			employee_dict['debit'] += adjust_day
			employee_dict['eligible_days'] -= adjust_day
		
		if employee_dict['eligible_days'] > 0 and carryforward_rule['carryforward_expiry']:
			employee_dict['carryforward_day_expire'] = carryforward_rule['carryforward_expiry']
			employee_dict['carryforward_day_adj'] = employee_dict['eligible_days']


def swap_date_rule(employee_dict):
	get_copy_dict(employee_dict)
	employee_dict['encashed_leav'] = None
	employee_dict['vacation'] = None
	employee_dict['rule_change'] = None
	employee_dict['credit'] = 0
	employee_dict['debit'] = 0
	employee_dict['carryforward_flag'] = 0
	employee_dict['expired_carryforward'] = 0
	employee_dict['expired_carryforward_on'] = None
	employee_dict['working_days'] = 0
	employee_dict['start_date'] = add_days(employee_dict['to_date'], 1)
	
	if employee_dict.__contains__('new_rule') and employee_dict['new_rule']:
		employee_dict['applied_rule'] = employee_dict['new_rule']
		employee_dict['new_rule']     = None

def get_copy_dict(employee_dict):
	copy_dict = deepcopy(employee_dict)

	for key in ['slab_list', 'docname', 'last_vacation', 'total_working', 'day_adjust', 'monthly_credit', 'max_range', 'encashed_max_range', 'iterate_loop', 'new_rule', 'warning_msg']:
		if key in copy_dict: del copy_dict[key]
	
	employee_dict['slab_list'].append(copy_dict)

def vacation_select(ignore_rejoining):
	return """
		SELECT `V`.`name`, `V`.`from_date`, %s AS vacation_rejoining_date, `V`.`total_leave_days`, `V`.`docstatus` AS `v_docstatus`, %s AS `r_docstatus`, `V`.`to_date`, IFNULL(`VR`.`extend_vacation`, 0) AS extend_vacation
		FROM `tabVacation Leave Application` AS V
		LEFT JOIN `tabVacation Rejoining` AS VR
			ON `V`.`name` = `VR`.`vacation_leave_application`
			AND `VR`.`docstatus` < 2
		WHERE `V`.`docstatus` != 2
		AND (`V`.`status` != 'Rejected'
		OR (`V`.`docstatus` = 0
			AND `V`.`status` = 'Rejected'))"""% ("IFNULL(`VR`.`vacation_rejoining_date`, DATE_ADD(`V`.`to_date`, INTERVAL 1 DAY))" if ignore_rejoining else "`VR`.`vacation_rejoining_date`", "IF(`VR`.`vacation_rejoining_date`, `VR`.`docstatus`, 1)" if ignore_rejoining else "`VR`.`docstatus`")

def prev_vacation(employee_dict, ignore_rejoining):
	first_select = vacation_select(ignore_rejoining)
	vacation = """%s
		AND `V`.`employee_id` = '%s'
		AND `V`.`from_date` BETWEEN '%s' AND '%s'
		AND `V`.`name` != '%s'""" % (first_select, employee_dict['employee'], employee_dict['start_date'], employee_dict['to_date'], employee_dict['docname'])
	vacation = frappe.db.sql(vacation, as_dict=True)
	employee_dict['vacation'] = vacation

	total_leave_days = 0
	for v_row in vacation:
		total_leave_days += v_row.get('total_leave_days')
		employee_dict['exclude_entry'].append({
			'from_date': v_row.get('from_date'),
			'to_date': add_days(v_row.get('vacation_rejoining_date'), -1),
			})
		
		if employee_dict['ignore_msg'] == 0: validate_rejoing_appl(v_row)
		
		if employee_dict.get('carryforward_day_expire') and v_row.get('from_date') < employee_dict.get('carryforward_day_expire'):
			employee_dict['carryforward_day_adj'] -= v_row.get('total_leave_days')


	employee_dict['debit'] += total_leave_days
	employee_dict['eligible_days'] -= total_leave_days


def validate_rejoing_appl(data):
	if data['v_docstatus'] == 0:
		frappe.throw('Vacation Leave Application Is Not Approved For Application {0}'.format(data['name']))
	
	if not data['vacation_rejoining_date'] and not data['r_docstatus']:
		frappe.throw('Please Apply Vacation Rejoining Application For Application {0}'.format(data['name']))
	
	if data['vacation_rejoining_date'] and data['r_docstatus'] == 0:
		frappe.throw('Vacation Rejoining Application Is Not Approved For Application {0}'.format(data['name']))

def validate_vacation_date(employee_dict, ignore_rejoining):
	first_select = vacation_select(ignore_rejoining)
	vacation = "{0} \
		AND `V`.`employee_id` = '{1}' \
		AND `V`.`name` != '{2}' \
		ORDER BY `V`.`from_date` DESC \
		LIMIT 1".format(first_select, employee_dict['employee'], employee_dict['docname'])
	vacation = frappe.db.sql(vacation, as_dict=True)

	if vacation:
		vacation = vacation[0]
		if employee_dict['ignore_msg'] == 0: validate_rejoing_appl(vacation)
		get_upl_leave(employee_dict, vacation['vacation_rejoining_date'], employee_dict['max_range'])
		employee_dict['total_working'] = days360(getdate(vacation['vacation_rejoining_date']), employee_dict['max_range']) - get_exclude_count(employee_dict)
		employee_dict['last_vacation'] = str(vacation['from_date'])+" to "+str(vacation['to_date'])
		
		# if vacation encashed after vacation leave applied
		if ignore_rejoining:
			if vacation['from_date'] <= employee_dict['encashed_max_range'] <= vacation['vacation_rejoining_date'] and employee_dict['ignore_msg'] == 0:
				frappe.throw("Leave Encashment Range Cannot fall between Vacation Leave Application")
		
			if vacation['vacation_rejoining_date'] >= employee_dict['max_range']:
				employee_dict['max_range'] = add_days(vacation['vacation_rejoining_date'], 1)
				employee_dict['day_adjust'] = 1
		
		if getdate(add_days(vacation['vacation_rejoining_date'], -1 * vacation['extend_vacation'])) >= employee_dict['max_range'] and employee_dict['ignore_msg'] == 0:
			frappe.throw("Leave cannot be applied for date on or before {0}".format(formatdate(vacation['vacation_rejoining_date'])))
		
		valid_date_encash(employee_dict)
	else:
		get_upl_leave(employee_dict, employee_dict['start_date'], employee_dict['max_range'])
		employee_dict['total_working'] = days360(getdate(employee_dict['start_date']), employee_dict['max_range']) - get_exclude_count(employee_dict)

	leave_encashed(employee_dict, 'DESC')

def valid_date_encash(employee_dict):
	first_select = vacation_select(0)
	vacation = "{0} \
		AND `V`.`employee_id` = '{1}' \
		AND `V`.`name` != '{2}' \
		AND `VR`.`vacation_rejoining_date` IS NOT NULL \
		ORDER BY `V`.`from_date` DESC \
		LIMIT 1".format(first_select, employee_dict['employee'], employee_dict['docname'])
	vacation = frappe.db.sql(vacation, as_dict=True)

	if vacation:
		vacation = vacation[0]
		if employee_dict['ignore_msg'] == 0: validate_rejoing_appl(vacation)

		if getdate(add_days(vacation['vacation_rejoining_date'], -1 * vacation['extend_vacation'])) >= employee_dict['encashed_max_range'] and employee_dict['ignore_msg'] == 0:
			frappe.throw("Leave cannot be applied for date on or before {0}".format(formatdate(vacation['vacation_rejoining_date'])))

def vacation_encash_select(order=None):
	return """
		SELECT name, to_date, docstatus, pay_days
		FROM `tabVacation Leave Encashment`
		WHERE docstatus < 2
		AND employee = '{0}'
		%s AND to_date BETWEEN '{1}' AND '{2}'
		AND name != '{3}'
		ORDER BY to_date %s
		LIMIT 1"""% ('--' if order else "" , order if order else 'ASC')

def leave_encashed(employee_dict, order=None):
	encashed_leav = vacation_encash_select(order).format(employee_dict['employee'], employee_dict['start_date'], employee_dict['to_date'] if employee_dict.__contains__('to_date') else "", employee_dict['docname'])
	encashed_leav = frappe.db.sql(encashed_leav, as_dict=True)
	employee_dict['encashed_leav'] = encashed_leav

	for e_row in encashed_leav:
		if e_row['docstatus'] == 0 and employee_dict['ignore_msg'] == 0:
			frappe.throw('Vacation Leave Encashment Is Not Approved For Application {0}'.format(e_row['name']))

		if getdate(e_row['to_date']) >= employee_dict['max_range'] and employee_dict['ignore_msg'] == 0:
			frappe.throw("Leave cannot be applied for date on or before {0}".format(formatdate(e_row['to_date'])))
		
		if not order and e_row['docstatus'] == 1 and float(e_row['pay_days']) > 0:
			employee_dict['eligible_days'] -= float(e_row['pay_days'])
			employee_dict['debit'] += float(e_row['pay_days'])

			if employee_dict.get('carryforward_day_expire') and e_row.get('to_date') < employee_dict.get('carryforward_day_expire'):
				employee_dict['carryforward_day_adj'] -= float(e_row['pay_days'])

def calculate_vacation(employee, from_date, doctype=None, ignore_rejoining=0, ignore_msg=0):
	employee_dict = dict()

	employee_dict.update({
		'employee'           : employee,
		'max_range'          : getdate(from_date),
		'encashed_max_range' : getdate(from_date),
		'day_adjust'         : int(0),
		'credit'             : float(0),
		'debit'              : float(0),
		'working_days'       : float(0),
		'eligible_days'      : float(0),
		'total_working'      : int(0),
		'docname'            : doctype,
		'slab_list'          : [],
		'monthly_credit'     : 0,
		'iterate_loop'       : 0,
		'ignore_msg'         : ignore_msg,
		'exclude_entry'      : []
	})

	hr_setting = frappe.get_single('HR Settings')
	employee_dict['monthly_credit'] = hr_setting.get('monthly_credit')

	check_vacation_rule(employee_dict)
	validate_vacation_date(employee_dict, ignore_rejoining)

	employee_dict['exclude_entry'] = []

	if employee_dict.__contains__('applied_rule') and employee_dict.__contains__('start_date'):
		while True:
			employee_dict['iterate_loop'] += 1
			if employee_dict['iterate_loop'] == 100: break

			get_vacation_rule(employee_dict)
			rule_change_date(employee_dict)
			# leave encashment between that period
			leave_encashed(employee_dict)
			# vacation application between that period
			prev_vacation(employee_dict, ignore_rejoining)
			# reduce lwp in total days
			get_upl_leave(employee_dict, employee_dict['start_date'], employee_dict['to_date'])
			calc_accural_rcd(employee_dict, ignore_rejoining)
			carryforward_adj(employee_dict)
			swap_date_rule(employee_dict)
			
			# dynamic credit
			if employee_dict['start_date'] >= add_days(employee_dict['max_range'], -1 * employee_dict['day_adjust']): break

	# frappe.errprint(str(employee_dict['slab_list']))

	return {'eligible_days': employee_dict['eligible_days'],
			'last_vacation': employee_dict['last_vacation'] if employee_dict.__contains__('last_vacation') else None,
			'applied_rule' : employee_dict['applied_rule'],
			'working_days' : employee_dict['total_working'],
			'warning_msg' : employee_dict['warning_msg'] if  employee_dict.__contains__('warning_msg') else None,
			'slab': employee_dict['slab_list']}

# filter employee with vacation leave rule
def filter_employee(doctype, txt, searchfield, start, page_len, filters):
	"""USE IN   VACTION RULE MODIFICATION
				VACATION LEAVE ENCASHMENT
				VACATION REJOINING"""
	
	conditon = ''
	if filters and filters.get('company'):
		conditon = " AND company = '{}'".format(filters.get('company'))

	employee_list = """SELECT name, employee_name
		FROM `tabEmployee`
		WHERE status = 'Active'
		AND vacation_rule IN (SELECT name
			FROM `tabVacation Leave Rule`)
		{}
		AND ( name LIKE %(txt)s
		OR employee_name LIKE %(txt)s)
	""".format(conditon)

	return frappe.db.sql(employee_list, {
			'txt': "%%%s%%" % txt
		})