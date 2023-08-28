# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate


class BenefitTypeforEOS(Document):
	def validate(self):
		self.validate_duplicate()
		self.validate_components()
	
	def validate_duplicate(self):
		duplicate = """select *
			from `tabBenefit Type for EOS`
			where docstatus = 1
			and benefit_type = '{}'
			and effective_from = '{}'
			and name != '{}'""".format(self.get('benefit_type'), self.get('effective_from'), self.get('name'))
		duplicate = frappe.db.sql(duplicate, as_dict=True)
		
		if duplicate:
			frappe.throw(_("EOS Benefit Type of {} Already Created for Date {}".format(self.get('benefit_type'), formatdate(self.get('effective_from')))))
	
	def validate_components(self):
		if not self.get('is_not_applicable_all_components'): return

		component = set()
		i = 0
		for row in self.get('applicable_salary_components'):
			component.add(row.get('salary_component'))
			i+=1
			## We For checking Unique salary componentes are added By Tushar
			# if len(component) != len(self.get('applicable_salary_components')):
			if len(component) != i:
				frappe.throw(_('Salary Compensation Component {} Should be Unique'.format(row.get('salary_component'))))