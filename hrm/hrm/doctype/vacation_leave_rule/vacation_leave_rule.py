# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.delete_doc import check_if_doc_is_linked

class VacationLeaveRule(Document):

	def validate(self):
		self.validate_zero_value()
	

	def on_cancel(self):
		check_if_doc_is_linked(self, 'Delete')


	def validate_zero_value(self):
		meta = frappe.get_meta(self.doctype)
		
		for field in ['eligible_after', 'days', 'redirect_after_year', 'maximum_carry_forward_days', 'carry_forward_days_need_to_be_availed_in_how_many_days', 'frequency']:
			fieldname = meta.get_field(field).get('label', '')
			if (self.get(field) or 0) < 0:
				frappe.throw(_('{} Cannot be Less then Zero'.format(fieldname)))
			
			if field in ['eligible_after', 'days'] and (self.get(field) or 0) == 0:
				frappe.throw(_('{} Should be Greater then Zero'.format(fieldname)))