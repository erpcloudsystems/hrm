# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate

class LeaveRule(Document):
	def validate(self):
		self.validate_effective_date()
		self.validate_slab()
		self.validate_components()

		if self.get('max_leaves_allowed') < 0:
			frappe.throw(_('Max Leaves Allowed Cannot be Negative'))
	
	def on_cancel(self):
		self.stop_cancel()
	
	def validate_effective_date(self):
		effective_date = """SELECT *
			FROM `tabLeave Rule`
			WHERE docstatus < 2
			AND leave_type = '{}'
			AND effective_from = '{}'
			AND name != '{}'""".format(self.get('leave_type'), self.get('effective_from'), self.get('name'))

		effective_date = frappe.db.sql(effective_date, as_dict=True)

		if effective_date:
			frappe.throw(_('Leave Rule Cannot be Created at {} form Leave Type {}'.format(formatdate(self.get('effective_from')), self.get('leave_type'))))


	def validate_slab(self):
		if self.get('is_slab_applicable') != 1: return

		if not self.get('frequency_based_on'):
			frappe.throw(_('Frequency Based on is Required for Compensation Rule'))

		interval = 0
		if self.get('frequency_based_on') == 'Number of Days availed':
			interval = 1

		previous = {}
		for row in self.get('compensation_rule'):
			start_unit = (previous.get('ending_unit', 0) + interval)
			if start_unit != row.get('starting_unit'):
				frappe.throw(_('Starting Unit Should be {} at Row {}'.format(start_unit, row.get('idx'))))

			if not row.get('ending_unit') > row.get('starting_unit'):
				frappe.throw(_('Ending Unit Should be Greater From Starting Unit at Row {}'.format(row.get('idx'))))
			
			if not 0 <= row.get('percentage_of_compensation') <= 100:
				frappe.throw(_('Percentage of Compensation should be between 0 to 100 at Row {}'.format(row.get('idx'))))
			
			# if self.get('frequency_based_on') == 'Number of Days availed' and len(self.get('compensation_rule')) == row.get('idx') and row.get('ending_unit') != self.get('max_leaves_allowed') and not frappe.db.get_value("Leave Type", self.get('leave_type'), "allow_negative"):
			if self.get('frequency_based_on') == 'Number of Days availed' and len(self.get('compensation_rule')) == row.get('idx') and row.get('ending_unit') != self.get('max_leaves_allowed'):
				frappe.throw(_('Ending Unit Should be {} at Row {}'.format(self.get('max_leaves_allowed', 0), row.get('idx'))))

			previous = row


	def validate_components(self):
		if self.get('is_not_applicable_all_components') != 1: return

		component = set()
		for row in self.get('salary_compensation_component'):
			component.add(row.get('salary_component'))

			if len(component) != int(row.get('idx')):
				frappe.throw(_('Salary Compensation Component {} Should be Unique'.format(row.get('salary_component'))))
	
	def stop_cancel(self):
		future_appl = """SELECT * FROM `tabLeave Request` WHERE docstatus < 2 and leave_type = '{}' and from_date >= '{}'""".format(self.get('leave_type'), self.get('effective_from'))
		future_appl = frappe.db.sql(future_appl, as_dict=True)
		
		if future_appl:
			frappe.throw(_('Leave Rule Cannot be Cancelled'))
