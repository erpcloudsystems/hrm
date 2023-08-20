# -*- coding: utf-8 -*-
# Copyright (c) 2019, avu and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils.data import flt
from hrm.hrm.doctype.vacation_leave_application.vacation_leave_application import calculate_vacation
from frappe.utils import getdate, add_days, get_first_day, get_last_day
from hrm.custom_script.salary_slip.salary_slip import get_actual_structure, get_payroll_period

class VacationLeaveEncashment(Document):

	def validate(self):
		self.get_from_date()
		self.calcuate_days(0)
		self.calcuate_days_and_amount()

		if flt(self.amount or 0) <= 0:
			frappe.throw("Vacation Leave Encashment Cannot be Created for value Less then or Equal to Zero")
		
		if flt(self.pay_days) <= 0:
			frappe.throw("Pay Days Cannot be Less than or Equal to Zero")
		
		if flt(self.pay_days, 3) > flt(self.days, 3):
			frappe.throw("Pay Days Cannot be Greater than Eligible Days")
		
		if getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw("To Date Cannot be Less than or Equal to From Date")
		
		if getdate() < getdate(self.to_date):
			frappe.throw("Vacation Leave Encashment Cannot be Applied to Future Date")
		
		self.balance_days = flt(self.days, 3) - flt(self.pay_days, 3)
	
	def before_cancel(self):
		last_encash = self.valid_from_date('cancel') or self.to_date
		last_vecation = self.leave_vacation() or self.to_date
		if getdate(last_vecation) > getdate(last_encash):
			last_encash = last_vecation
		
		if getdate(last_encash) > self.to_date:
			frappe.throw("Application cannot be cancelled")

	def get_from_date(self):
		self.from_date = self.valid_from_date()
	
	def valid_from_date(self, cancel=None):
		prev_vac_leav_encash = """
			SELECT to_date,docstatus,name
			FROM `tabVacation Leave Encashment`
			WHERE docstatus < 2
			AND employee = '{0}'
			AND name != '{1}'
			ORDER BY to_date DESC
			LIMIT 1""".format(self.employee, self.name)
		res_vac_leav_encash = frappe.db.sql(prev_vac_leav_encash, as_dict=True)

		if res_vac_leav_encash:
			res_vac_leav_encash = res_vac_leav_encash[0]
			
			if res_vac_leav_encash['docstatus'] == 0 and not cancel:
				frappe.throw('Vacation Leave Encashment Is Not Approved For Application <a href="#Form/Vacation Leave Encashment/{0}">{0}</a>'.format(res_vac_leav_encash['name']))
			return res_vac_leav_encash['to_date']
		else:
			select_emp = """
				SELECT IF(rejoining_date, rejoining_date, date_of_joining) AS from_date
				FROM `tabEmployee`
				WHERE employee = '{0}'
				""".format(self.employee)
			emp_res = frappe.db.sql(select_emp, as_dict=True)
			if emp_res:
				return emp_res[0]['from_date']

	def calcuate_days(self, set_pay=1):
		self.days = calculate_vacation(self.employee, self.to_date, self.name, 1)['eligible_days']
		if set_pay:
			self.pay_days = self.days
			self.calcuate_days_and_amount()
	
	def calcuate_days_and_amount(self):
		try:
			start_date = get_first_day(self.get('posting_date'))
			end_date = get_last_day(start_date)

			payroll_dict = get_payroll_period(company=self.get('company'), start_date=start_date, end_date=end_date, actual_period=1)
			struct_assig, earning_deduction = get_actual_structure(self, payroll_dict)
			
			if not struct_assig:
				frappe.throw(_("There is no Salary Structure for the selected Employee"))
				
			earnings = earning_deduction.get('earnings', {})
			gross_ear = vacation_encash_amount(earnings, (self.pay_days if self.pay_days > 0 else 0))

			deductions = earning_deduction.get('deductions', {})
			gross_ded = vacation_encash_amount(deductions, (self.pay_days if self.pay_days > 0 else 0))

			self.amount = gross_ear - gross_ded
		except Exception as e:
			frappe.as_unicode(frappe.get_traceback())
			frappe.throw(str(e))
	
	def make_journal_entry(self):
		self.check_permission('write')

		# if self.get("__unsaved") == 1:
		# 	frappe.throw(_("Save the Changes"))

		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.voucher_type = 'Journal Entry'
		journal_entry.user_remark = _('Journal Entry of {0} from {1} to {2}')\
			.format(self.doctype, self.from_date, self.to_date)
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		# journal_entry.project = self.project
		# journal_entry.journal_entry_series = 'JE'
		# journal_entry.company_series = self.get_company_series()
		journal_entry.doctype_reference = self.doctype
		journal_entry.doctype_id = self.name
		payment_amount = flt(self.amount, precision)

		journal_entry.set("accounts", [
			{
				"account": self.payment_account,
				"credit_in_account_currency": payment_amount,
				# "reference_type": self.doctype,
				# "reference_name": self.name
			},
			{
				"account": self.expense_account,
				"debit_in_account_currency": payment_amount,
				# "reference_type": self.doctype,
				# "reference_name": self.name
			}
		])
		return journal_entry.as_dict()
		

	def get_company_series(self):
		series = frappe.db.get_value("Company",
			{"company_name": self.company}, "series")

		if not series:
			frappe.throw(_("Please set Series in Company {0}")
				.format(self.company))

		return series

	def leave_encashment_has_jv_entries(self):
		response = {}

		journal_entries = self.get_leave_encashment_entry_journal_entries()
		response['submitted'] = journal_entries[0]['name'] if journal_entries else 0

		return response
	
	def get_leave_encashment_entry_journal_entries(self):
		journal_entries = frappe.db.sql("""SELECT J.name
			FROM `tabJournal Entry` J
			WHERE J.docstatus < 2
			AND J.doctype_reference = '{1}'
			AND J.doctype_id = '{0}'""".format( self.name, self.doctype), as_dict=1)

		return journal_entries

	def leave_vacation(self):
		last_vacation = """SELECT `VR`.`vacation_rejoining_date`
			FROM `tabVacation Leave Application` AS V
			LEFT JOIN `tabVacation Rejoining` AS VR
				ON `V`.`name` = `VR`.`vacation_leave_application`
				AND `VR`.`docstatus` < 2
			WHERE `V`.`docstatus` < 2
			AND (`V`.`status` != 'Rejected'
			OR (`V`.`docstatus` = 0 
				AND `V`.`status` = 'Rejected'))
			AND `VR`.`vacation_rejoining_date` IS NOT NULL
			AND `V`.`employee_id` = '{0}'
			ORDER BY `V`.`from_date` DESC
			LIMIT 1""".format(self.employee)
		last_vacation = frappe.db.sql(last_vacation, as_dict=True)
		if last_vacation:
			return last_vacation[0]['vacation_rejoining_date']


def vacation_encash_amount(component_dict, payable_days):
	closing_comp = frappe.db.sql_list("SELECT name FROM `tabSalary Component` WHERE vacation_closing = 1")
	total_vacation_amt = 0
	for comp, row in component_dict.items():
		if comp in closing_comp:
			row['vacation_amount'] = (row.get('default_amount', 0)/(360/12)) * payable_days
		else:
			row['vacation_amount'] = 0
		
		total_vacation_amt += row.get('vacation_amount')
	
	return total_vacation_amt