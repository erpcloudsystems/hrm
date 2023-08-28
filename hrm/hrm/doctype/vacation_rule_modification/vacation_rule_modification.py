# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils.data import getdate

class VacationRuleModification(Document):
	def validate(self):
		self.validate_posting_date()
		self.validate_same_rule()
		self.validate_no_rule()
	
	def on_submit(self):
		self.update_employee(self.new_rule)

	def before_cancel(self):
		result = self.get_valid_date()
		if result and getdate(str(result)) > getdate(str(self.posting_date)):
			frappe.throw("Application cannot be cancelled")
	
	def on_cancel(self):
		self.update_employee(self.rule)
	
	def get_current_rule(self):
		vacation_m = "SELECT new_rule \
			FROM `tabVacation Rule Modification` \
			WHERE docstatus = 1 \
			AND employee = '{0}' \
			ORDER BY posting_date DESC \
			LIMIT 1".format(self.employee)
		get_vacation_m = frappe.db.sql(vacation_m,as_dict = True)

		if get_vacation_m:
			self.rule = get_vacation_m[0]['new_rule']
		else:
			employee = "SELECT vacation_rule \
				FROM `tabEmployee` \
				WHERE name = '{0}'".format(self.employee)
			get_employee = frappe.db.sql(employee,as_dict = True)
			if get_employee:
				self.rule = get_employee[0]['vacation_rule']
	
	def validate_posting_date(self):
		result = self.get_valid_date()
		if result:
			frappe.throw("Vacation Rule Modification Date Should be greater then {0}".format(result))

	def validate_same_rule(self):
		if self.rule and self.new_rule and self.rule == self.new_rule:
			frappe.throw("New Rule cannot be same as existing data")
	
	def validate_no_rule(self):
		if not self.rule or self.rule == None:
			frappe.throw("There is no rule attached to employee {0} which can be updated".format(self.employee))
	
	def get_valid_date(self):
		posting_date = None

		last_vacation = "SELECT to_date \
			FROM `tabVacation Leave Application` \
			WHERE docstatus < 2 \
			AND (status != 'Rejected' \
			OR (docstatus = 0 \
				AND status = 'Rejected')) \
			AND employee_id = '{0}' \
			ORDER BY to_date DESC \
			LIMIT 1".format(self.employee)
		last_vacation = frappe.db.sql(last_vacation,as_dict = True)
		if last_vacation:
			posting_date = last_vacation[0]['to_date']

		last_chg_date = "SELECT posting_date \
			FROM `tabVacation Rule Modification` \
			WHERE docstatus < 2 \
			AND employee = '{0}' \
			AND name != '{1}' \
			ORDER BY posting_date DESC \
			LIMIT 1".format(self.employee,self.name)
		last_chg_date = frappe.db.sql(last_chg_date,as_dict = True)

		if last_chg_date:
			if not posting_date or ( posting_date and posting_date < last_chg_date[0]['posting_date']):
				posting_date = last_chg_date[0]['posting_date']
		else:
			employee = "SELECT date_of_joining,rejoining_date \
				FROM `tabEmployee` \
				WHERE name = '{0}'".format(self.employee)
			get_employee = frappe.db.sql(employee,as_dict = True)
			if get_employee and not posting_date:
				if not get_employee[0]['rejoining_date']:
					posting_date = get_employee[0]['date_of_joining']
				else:
					posting_date = get_employee[0]['rejoining_date']

		
		if posting_date and getdate(str(posting_date)) >= getdate(str(self.posting_date)):
			return posting_date
		else:
			return
	
	def update_employee(self, rule):
		doc_obj = frappe.get_doc('Employee', self.employee)
		if doc_obj:
			doc_obj.applied_vacation_rule = rule
			doc_obj.save()