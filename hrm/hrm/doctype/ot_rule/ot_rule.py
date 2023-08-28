# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class OTRule(Document):
	def validate(self):
		self.validate_zero_value()
	
	def validate_zero_value(self):
		meta = frappe.get_meta(self.doctype)
		
		for field in ['minimum_ot_limit', 'ot_slab', 'maximum_ot_allowed_in_a_day', 'default_ot_allowed_in_a_day', 'working_day_ot_rate', 'non_working_day_ot_rate', 'holiday_ot_rate']:
			fieldname = meta.get_field(field).get('label', '')
			if (self.get(field) or 0) < 0:
				frappe.throw(_('{} Cannot be Less then Zero'.format(fieldname)))
			
			if field in ['working_day_ot_rate', 'non_working_day_ot_rate', 'holiday_ot_rate', 'maximum_ot_allowed_in_a_day'] and self.get(field, 0) == 0:
				frappe.throw(_('{} Should be Greater then Zero'.format(fieldname)))