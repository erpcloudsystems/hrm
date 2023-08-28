
# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class ExitReEntryVisa(Document):

	def validate(self):
		self.validate_entry()
	
	def validate_entry(self):
		if self.from_date and self.to_date and (getdate(str(self.from_date)) >= getdate(str(self.to_date))):
			frappe.throw("To Date Should not be less than or equal to From Date")

		if (self.reentry_charges or 0) < 0:
			frappe.throw("Re-Entry charges Cannot Be Negative.")
		
		if (self.number_of_reentries_required or 0) <= 0:
			frappe.throw("Number Re-Entry Cannot Be Zero.")
	
	def family_members(self):
		passanger_detail = "Name     Gender     Date of Birth\n"

		family_sql = """
		(SELECT employee_name AS name, gender, DATE_FORMAT(date_of_birth, "%d-%m-%Y") AS date_of_birth
		FROM `tabEmployee`
		WHERE name = '{0}'
		LIMIT 1)
		
		UNION ALL
		
		(SELECT member_name AS name, gender, DATE_FORMAT(date_of_birth, "%d-%m-%Y") AS date_of_birth
		FROM `tabFamily Details`
		WHERE parent = '{0}'
		{1} LIMIT 0
		)""".format(self.employee, '--' if (self.number_of_reentries_required or 0) > 1 else '')
		family_sql_res = frappe.db.sql(family_sql, as_dict=0)

		if family_sql_res: self.passenger_names = passanger_detail + '\n'.join('     '.join(map(str, row)) for row in family_sql_res)