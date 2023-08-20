# -*- coding: utf-8 -*-
# Copyright (c) 2019, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import datetime
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import calendar
from frappe.utils import cint, cstr, date_diff, flt, formatdate, get_first_day, get_last_day, getdate
from erpnext.hr.doctype.leave_application.leave_application import get_leave_balance_on
from hrm.custom_methods import get_comp_name, get_leve_name
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from hrm.custom_script.salary_slip.salary_slip import get_actual_structure, get_payroll_period
from hrm.hrm.doctype.vacation_leave_application.vacation_leave_application import calculate_vacation
from hrm.hrm.doctype.vacation_leave_encashment.vacation_leave_encashment import vacation_encash_amount


class ServiceClosing(Document):
	def onload(self):
		self.get("__onload").journal_entry = self.get_jv()
	

	def validate(self):
		# self.eos_validation()
		self.service_detail(ignore=0)


	def on_submit(self):
		self.mandatory_fild()
		self.update_employee("Left")
		
		doc = self.create_salary_slip()
		doc.flags.ignore_validate = True
		doc.submit()

		self.salary_slip = doc.name
		self.db_update()


	def on_cancel(self):
		if self.salary_slip:
			sql = "select * from `tabSalary Slip` where name = '"+self.salary_slip+"'"
			sal_slip = frappe.db.sql(sql,as_dict=1)
			if sal_slip:
				salary_slip = frappe.get_doc("Salary Slip",self.salary_slip)
				if salary_slip:
					salary_slip.cancel()
		
		if self.journal_entry:
			sql = "select * from `tabJournal Entry` where name = '"+self.journal_entry+"'"
			jv_data = frappe.db.sql(sql,as_dict=1)
			if jv_data:
				journal_entry = frappe.get_doc("Journal Entry",self.journal_entry)
				if journal_entry:
					if journal_entry.docstatus == 1:
						journal_entry.cancel()
					else:
						journal_entry.delete()

		self.update_employee("Active")
	

	def on_trash(self):
		# if self.salary_slip:
		# 	sql = "select * from `tabSalary Slip` where name = '"+self.salary_slip+"'"
		# 	sal_slip = frappe.db.sql(sql,as_dict=1)
		# 	if sal_slip:
		# 		salary_slip = frappe.get_doc("Salary Slip",self.salary_slip)
		# 		if salary_slip:
		# 			salary_slip.delete()
		
		if self.journal_entry:
			sql = "select * from `tabJournal Entry` where name = '"+self.journal_entry+"'"
			jv_data = frappe.db.sql(sql,as_dict=1)
			if jv_data:
				journal_entry = frappe.get_doc("Journal Entry",self.journal_entry)
				if journal_entry:
					journal_entry.delete()


	# def eos_validation(self):
	# 	if self.termination_date and self.posting_date and (self.termination_date < self.posting_date):
	# 		frappe.throw("EOS Date Cannot be lesser than Posting Date")
	

	def update_employee(self, status):
		# Update employee status to Left after submit
		employee = frappe.get_doc("Employee", self.get('employee'))
		employee.status = status
		employee.relieving_date = self.get('termination_date') if status and status == "Left" else None
		employee.save()


	def mandatory_fild(self):
		if not self.payment_account or not self.expense_account:
			frappe.throw("Please fill the mandatory field ['Expense Account', 'Payment Account']")


	def service_detail(self, ignore=1):
		self.service_period()
		self.salary_structure_detail()
		self.leave_balance()
		self.calculate_sal()
		self.service_awd(ignore)
		self.validate_adjustment(ignore)
		self.calc_total_amount()


	def salary_structure_detail(self):
		service_closing = """SELECT *
			FROM `tabService Closing`
			WHERE employee = '{0}'
			AND docstatus != 2
			AND name != '{1}'""".format(self.get('employee'), self.get('name'))
		service_closing = frappe.db.sql(service_closing, as_dict=True)

		if not service_closing:
			start_date = get_first_day(self.get('termination_date') or self.get('posting_date'))
			end_date = get_last_day(start_date)

			payroll_dict = get_payroll_period(company=self.get('company'), start_date=start_date, end_date=end_date, actual_period=1)
			struct_assig, earning_deduction = get_actual_structure(self, payroll_dict)

			self._earning_deduction_dict = earning_deduction

			if not struct_assig:
				frappe.throw(_("There is no Salary Structure for the selected Employee"))
			
			earnings = earning_deduction.get('earnings', {})

			self.basic_salary = frappe.db.get_value("Salary Structure Assignment",
				{"name": struct_assig}, 'base') or 0
			self.gross_pay_amount = sum([row.get('default_amount') for row in earnings.values()])
		else:
			frappe.throw(_("Service Closing already created for this Employee"))

	def cal_date(self):
		if not self.get('termination_date'):
			frappe.throw(_("Please Select EOS Date"))
		
		if getdate(self.get('termination_date')) < getdate(self.get('joining_date')):
			frappe.throw(_("EOS Date Cannot be Lesser than Joining Date"))
		
		return relativedelta(getdate(self.get('termination_date')), getdate(self.get('joining_date')))


	def service_period(self):
		diff_in_yrs = self.cal_date()
		str_year = "Years" if diff_in_yrs.years > 1 else "Year"
		str_month = "Months" if diff_in_yrs.months > 1 else "Month"
		str_day = "Days" if diff_in_yrs.days > 1 else "Day"
		diff = "{} {} {} {} {} {}".format(diff_in_yrs.years, str_year, diff_in_yrs.months, str_month, diff_in_yrs.days, str_day)
		self.total_service_period = diff or ""
	

	def component_amount(self, name):
		comp_all = 1
		comp_element = []
		if frappe.db.get_value("Benefit Type for EOS", name, "is_not_applicable_all_components"):
			component = """SELECT salary_component
				FROM `tabSalary Compensation Component`
				WHERE parent = '{}'""".format(name)
			comp_element = frappe.db.sql_list(component)
			comp_all = 0
		if not self.get('_earning_deduction_dict'): 
			self.salary_structure_detail()
		
		earnings = self.get('_earning_deduction_dict', {}).get('earnings', {})

		amount = 0
		for comp, row in earnings.items():
			if comp_all == 0 and not comp in comp_element:
				continue
			amount += row.get('default_amount', 0)

		return amount
	

	def service_awd(self,ignore = 1):
		if ignore :
			diff = self.cal_date()
			years = float('{}.{}'.format(str(diff.years), str(diff.months)))

			day_working = self.working_days()
			self.eligible_days_edays = day_working
		self.calculate_service_awd()
	@frappe.whitelist()
	def calculate_service_awd(self):
		day_working = self.eligible_days_edays
		award_list = """SELECT `S`.*
			FROM (SELECT `SAD`.*, row_number() OVER(PARTITION BY `SAD`.`benefit_type`, `SAR`.`name` ORDER BY `SAD`.`tenure_upto`) AS row_idx
				FROM `tabService Award Details` SAD
				INNER JOIN (SELECT *
					FROM `tabService Award Rule`
					WHERE `company` = '{0}'
					AND `effective_from` <= '{1}'
					AND `eos_type` = '{2}'
					AND `docstatus` = 1
					ORDER BY `effective_from` DESC
					LIMIT 1) SAR
					ON `SAD`.`parent` = `SAR`.`name`
				WHERE `SAD`.`tenure_upto` >= {3}) AS `S`
			WHERE `S`.`row_idx` = 1""".format(self.get('company'), self.get('termination_date'), self.get('termination_type'), day_working)
		slab = frappe.db.sql(award_list, as_dict=True)
		
		list_return = []
		total_amount = 0

		for _slab in slab:
			sarvice_awd_amt = self.component_amount(_slab.get('eos_benefit_type'))

			eval_dict = {
				'EDAYS': day_working,
				'ECOMP': sarvice_awd_amt
			}

			service_amt = eval(str(_slab.get('formula')), eval_dict)
			list_return.append({"service_award_rule": _slab.get('parent'),
				"eos_benefit_type": _slab.get('eos_benefit_type'),
				"benefit_type": _slab.get('benefit_type'),
				"amount": (service_amt or 0),
				"formula": _slab.get('formula')
			})
			total_amount += (service_amt or 0)
		
		self.set('service_award', list_return)
		self.sa_total_amount = flt(total_amount, 2)
	

	def validate_adjustment(self, ignore):
		if ignore == 1: return

		total_additional, total_deducation = 0, 0

		for row in self.get('service_closing_adjustment'):
			additional_amount = row.get('additional_amount') or 0
			deduction_amount = row.get('deduction_amount') or 0
			if additional_amount < 0:
				frappe.throw(_("Addition Amount Cannot be Less then Zero at Row {}".format(row.get('idx'))))

			if deduction_amount < 0:
				frappe.throw(_("Deduction Amount Cannot be Less then Zero at Row {}".format(row.get('idx'))))
			
			if additional_amount > 0 and deduction_amount > 0:
				frappe.throw(_("Both The Amount Cannot Be Assigned at Row {}".format(row.get('idx'))))
			
			total_additional += additional_amount
			total_deducation += deduction_amount

		self.total_additional_amount = total_additional
		self.total_deduction_amount = total_deducation
	

	def	calc_total_amount(self):
		total_amount = (self.get('total_leave_encashment_amount') or 0) + (self.get('sa_total_amount') or 0) + (self.get('total_salary_amount') or 0) + (self.get('total_additional_amount') or 0) - (self.get('total_deduction_amount') or 0)

		self.total_amount = flt(total_amount, 2)
		self.net_payable = flt(total_amount, 2)
	

	def working_days(self):
		days_working = date_diff(self.get('termination_date'), self.get('joining_date')) + 1
		self.total_service_period_in_days = days_working

		absent = """SELECT COUNT(*) days
			FROM `tabAttendance`
			WHERE employee = '{}'
			AND docstatus = 1
			AND status = 'Absent'
			AND leave_type IS NULL
			AND attendance_date BETWEEN '{}' AND '{}'""".format(self.get('employee'), self.get('joining_date'), self.get('termination_date'))
		absent = frappe.db.sql(absent, as_dict=True)
		absent = (absent[0]['days'] if absent else 0)
		self.total_absent_days = absent

		return days_working - absent

	def leave_balance(self):
		leave_list = []
		
		vacation_rule = frappe.db.get_value("Employee", self.get('employee'), "vacation_rule")
		if vacation_rule:
			leave_ledg = calculate_vacation(employee=self.get('employee'), from_date=self.get('termination_date'))
			leave_days = leave_ledg.get('eligible_days', 0)
			
			if self.get("leave_encashment_balance"):
				for i in self.get("leave_encashment_balance"):
					self.salary_structure_detail()
					leave_days=i.get("leave_balance")
						
			earnings = self.get('_earning_deduction_dict', {}).get('earnings', {})
			deductions = self.get('_earning_deduction_dict', {}).get('deductions', {})

			leave_list.append({"leave_type": get_leve_name("V"),
				"leave_balance": leave_days,
				"encashment_amount": vacation_encash_amount(earnings, leave_days) - vacation_encash_amount(deductions, leave_days)
			})
			# frappe.errprint([vacation_encash_amount(earnings, leave_days), vacation_encash_amount(deductions, leave_days),earnings,deductions,leave_days])
		self.set("leave_encashment_balance", leave_list)
		
		self.total_leave_encashment_amount = sum([row.get('encashment_amount') for row in leave_list])

	def calculate_sal(self):
		emp = frappe.get_doc("Employee", self.get('employee'))
		emp.relieving_date = self.termination_date
		emp.save()
		
		doc = self.create_salary_slip()

		# closing_comp = frappe.db.sql_list("SELECT name FROM `tabSalary Component` WHERE service_closing = 1")

		# sal_amount = add_component_val(doc.earnings,closing_comp) - add_component_val(doc.deductions,closing_comp)
		# salary_amount = round(float(sal_amount),2)
		
		sql = "select sum(total_payment) as total_pay, (total_interest_payable) as total_interest , sum(total_amount_paid) as total_paid from `tabLoan` where applicant = '"+self.employee+"' and docstatus = 1 and repay_from_salary = 1"
		loan = frappe.db.sql(sql,as_dict=1)
		# if loan:
		total_loan = 0
		total_interest = 0
		total_paid = 0
		for i in loan:
			total_loan = i['total_pay'] if i['total_pay'] else 0
			total_interest = i['total_interest']	if	i['total_interest']	else	0
			total_paid =  i['total_paid'] if i['total_paid'] else 0
		# sql1 = "select SL.name,sum(SLO.total_payment) as repaid from `tabSalary Slip` SL Left join `tabSalary Slip Loan` SLO on SL.name = SLO.parent where SL.employee = '"+self.employee+"'"
		# repaid = frappe.db.sql(sql1,as_dict=1)
		# if repaid:
		# 	for i in repaid:
		# 		repaid_amt = i['repaid'] if i['repaid'] else 0
		
		loan_pending = total_loan + total_interest - total_paid
		loan_advance = round(float(loan_pending),2)

		loan_amount = doc.total_loan_repayment
		
		self.attendance_count()
		# self.salary_amount = salary_amount
		# frappe.errprint([doc.get('gross_pay'), doc.get('total_deduction'), doc.deductions])
		self.total_salary_amt = doc.get('gross_pay') - doc.get('total_deduction')- doc.get("total_loan_repayment")
		self.loan_amount = loan_amount
		self.loan_advance = loan_advance
		self.ot_amount = round(float(add_component_val(doc.earnings, [get_comp_name("OT")])), 2)
		self.total_salary_amount = self.total_salary_amt - self.loan_advance
		self.ot_hours = doc.get('ot_hours') or 0
		
		doc.delete()
		
		deleted_document = frappe.db.sql("select name from `tabDeleted Document` where deleted_doctype = 'Salary Slip' and deleted_name = '"+doc.name+"' order by creation desc",as_dict=1)
		if deleted_document:
			del_doc = frappe.get_doc("Deleted Document", deleted_document[0].name)
			del_doc.delete()
		
		emp = frappe.get_doc("Employee", self.employee)
		emp.relieving_date = None
		emp.save()


	def attendance_count(self):
		to_date = self.get('termination_date') or self.get('posting_date')
		from_date = get_first_day(to_date)

		attendance = """select *
			from `tabAttendance`
			where employee = '{0}'
			and attendance_date between '{1}' and '{2}'
			and docstatus = 1""".format(self.employee, from_date, to_date)
		attendance = frappe.db.sql(attendance, as_dict=1)

		self.present_days = sum((1 if (row.status == 'Present' or row.status == 'Absent') else 0) for row in attendance)

		if len(attendance) != date_diff(to_date, from_date) + 1:
			frappe.throw(_("Attendance is not marked till EOS Date"))
	

	def create_salary_slip(self):
		start_date = get_first_day(self.get('termination_date') or self.get('posting_date'))
		end_date = get_last_day(start_date)
		# frappe.errprint([start_date,end_date,self.get('termination_date') or self.get('posting_date')])
		doc = frappe.new_doc("Salary Slip")
		doc.posting_date = self.posting_date
		doc.employee = self.employee
		doc.employee_name = self.employee_name
		doc.company = self.company
		doc.start_date = start_date
		doc.end_date = end_date
		doc.pay_end_date = self.get('termination_date') or self.get('posting_date')
		doc.service_closing = self.name
		doc.series = "Sal Slip/"+self.employee+"/.#####"
		doc.save()
		return doc
	
	def make_jv_entry(self):
		self.check_permission('write')
		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Journal Entry'
		journal_entry.user_remark = _("Accrual Journal Entry for Settlement for Employee "+self.employee+"")
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		# journal_entry.company_series = frappe.db.get_value("Company", self.company, "series")
		accounts = []
		
		accounts.append({
			"account": self.payment_account,
			"debit_in_account_currency": self.net_payable,
			# "cost_center": cost_center,
			"party_type": "Employee",
			"party": self.employee,
			"reference_type": 'Manual Payroll Entry',
		})	
		accounts.append({
			"account": self.expense_account,
			# "cost_center": cost_center,
			"credit_in_account_currency": self.net_payable,
			"reference_type": 'Manual Payroll Entry',
		})
		
		journal_entry.set("accounts", accounts)
		journal_entry.cheque_no = self.name
		journal_entry.doctype_id = self.name
		journal_entry.doctype_reference = self.doctype
		journal_entry.cheque_date = self.posting_date
		journal_entry.title = self.expense_account
		journal_entry.flags.ignore_mandatory = True
		
		return journal_entry.as_dict()

	def get_jv(self):
		journal_entry = """Select *
			from `tabJournal Entry`
			where doctype_id = '{}'
			and doctype_reference = '{}'""".format(self.name, self.doctype)
		journal_entry = frappe.db.sql(journal_entry, as_dict=True)

		return journal_entry[0]['name'] if journal_entry else None


def add_component_val(comp_dict, comp_list):
	amount = 0
	for row in comp_dict:
		if row.get('salary_component') in comp_list:
			amount += row.get('amount')
	
	return amount