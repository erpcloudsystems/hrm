# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, formatdate

class OTPlanner(Document):
	def validate(self):
		self.validate_dates()
		self.validate_duplicate()
		self.valid_ot_rule(reset=0)
		self.validate_zero_value()
	
	def on_submit(self):
		if self.get('status') == "Open":
			frappe.throw(_("Only OT Planner with status 'Approved' and 'Rejected' can be submitted"))

	def on_cancel(self):
		self.stop_cancel()
		self.status = "Cancelled"
	
	def validate_dates(self):
		if self.get('from_date') and self.get('to_date') and (getdate(self.get('to_date')) < getdate(self.get('from_date'))):
			frappe.throw(_("To date cannot be before from date"))

	def validate_zero_value(self):
		meta = frappe.get_meta(self.doctype)
		
		for field in ['approved_maximum_ot_allowed_per_day', 'planned_number_of_minutes_ot_per_day']:
			fieldname = meta.get_field(field).get('label', '')
			if self.get(field, 0) < 0:
				frappe.throw(_('{} Cannot be Less then Zero'.format(fieldname)))
			
			if field in ['planned_number_of_minutes_ot_per_day'] and self.get(field, 0) == 0:
				frappe.throw(_('{} Should be Greater then Zero'.format(fieldname)))
			
			max_fieldname =  meta.get_field('maximum_ot_allowed_per_day_as_per_ot_rule').get('label', '')
			if self.get(field) > self.get('maximum_ot_allowed_per_day_as_per_ot_rule'):
				frappe.throw(_('{} Should not exceed the {}'.format(fieldname, max_fieldname)))
	
	def validate_duplicate(self):
		duplicate = """SELECT *
			FROM `tabOT Planner`
			WHERE docstatus < 2
			AND employee = '{}'
			AND '{}' BETWEEN from_date AND to_date
			AND '{}' BETWEEN from_date AND to_date
			AND name != '{}'""".format(self.get('employee'), self.get('from_date'), self.get('to_date'), self.get('name'))
		duplicate = frappe.db.sql(duplicate, as_dict=True)

		if duplicate:
			duplicate = duplicate[0]
			frappe.throw(_("Employee has OT Planned between {} and {}".format(formatdate(duplicate.get('from_date')), formatdate(duplicate.get('to_date')))))

	def valid_ot_rule(self, reset=1):
		self.maximum_ot_allowed_per_day_as_per_ot_rule = 0
		ot_rule = applied_ot_rule(employee=self.get('employee'), to_date=self.get('from_date'))
		
		if ot_rule:
			ot_rule_doc = frappe.get_doc('OT Rule', ot_rule)
			self.maximum_ot_allowed_per_day_as_per_ot_rule = ot_rule_doc.get('maximum_ot_allowed_in_a_day', 0)
			if reset == 1:
				self.violation_action = ot_rule_doc.get('violation_action')
		else:
			frappe.throw(_('No Default OT Rule Available'))


	def stop_cancel(self):
		attendance = """SELECT *
			FROM `tabAttendance`
			WHERE docstatus = 1
			AND employee = '{}'
			AND attendance_date BETWEEN '{}' AND '{}'""".format(self.get('employee'), self.get('from_date'), self.get('to_date'))
		attendance = frappe.db.sql(attendance, as_dict=True)
		
		if attendance:
			frappe.throw(_('OT Planner Cannot be Cancelled Attendance already marked'))

def applied_ot_rule(employee, to_date):
	emp_ot_rule, designation = frappe.db.get_value('Employee', employee, ['ot_rule', 'designation'])
	
	has_promation = """SELECT `EPH`.`property`, `EPH`.`current`
		FROM `tabEmployee Promotion` AS `EP`
		LEFT JOIN `tabEmployee Property History` AS `EPH`
			ON `EP`.`name` = `EPH`.`parent`
		WHERE `EP`.`docstatus` = 1
		AND `EPH`.`property` IN ('Designation', 'OT Rule')
		AND `EP`.`employee` = '{}'
		AND `EP`.`promotion_date` > '{}'
		ORDER BY `EP`.`promotion_date`
		LIMIT 1""".format(employee, to_date)
	has_promation = frappe.db.sql(has_promation, as_dict=True)

	if has_promation:
		for prom in has_promation:
			if prom.get('property') == 'OT Rule':
				emp_ot_rule = prom.get('current')
			else:
				designation = prom.get('current')
	
	if not emp_ot_rule and not designation: return
	
	des_ot_rule = None
	if not emp_ot_rule:
		des_ot_rule = frappe.db.get_value('Designation', designation, 'ot_rule')
	
	ot_rule = emp_ot_rule or des_ot_rule

	return ot_rule