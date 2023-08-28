# -*- coding: utf-8 -*-
# Copyright (c) 2021, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe,json
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate, getdate

class ShiftAllocation(Document):
	def validate(self):
		self.validate_dates()
		# self.validate_shift_request_overlap_dates()

	def validate_dates(self):
		if not self.from_date or not self.to_date:
			frappe.throw(_("Please Enter From Date and To Date"))
		if self.from_date and self.to_date and (getdate(self.to_date) < getdate(self.from_date)):
			frappe.throw(_("To date cannot be before from date"))

	def get_employee(self):
		employee="select employee,employee_name,department from tabEmployee \
		where status='Active' and company='"+self.company+"' and ifnull(department,'')=ifnull("+json.dumps(self.department)+",ifnull(department,''));"
		sql_employee=frappe.db.sql(employee,as_dict=1)

		return sql_employee

	def on_submit(self):
		# date_list = self.get_working_days(self.from_date, self.to_date)
		
		for data in self.employee_details:
			request_doc = frappe.new_doc("Shift Request")
			request_doc.company = self.company
			request_doc.shift_type = self.shift_type
			request_doc.employee = data.employee
			request_doc.employee_name=data.name
			request_doc.from_date = self.from_date
			request_doc.to_date=self.to_date
			request_doc.shift_allocations = self.name
			request_doc.insert()
			request_doc.submit()

	def on_cancel(self):
		shift_request_list = frappe.get_list("Shift Request", {'shift_allocations': self.name})
		if shift_request_list:
			for shift in shift_request_list:
				shift_request_doc = frappe.get_doc("Shift Request", shift['name'])
				shift_request_doc.cancel()
