# -*- coding: utf-8 -*-
# Copyright (c) 2019, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate

class ServiceAwardRule(Document):
	def validate(self):
		self.validate_duplicate()
		self.no_data_validation()
		self.validate_child()
	

	def no_data_validation(self):
		if len(self.get("service_award_details")) == 0:
			frappe.throw(_("Please Add Some Data In Details."))


	def validate_duplicate(self):
		duplicate = """select *
			from `tabService Award Rule`
			where docstatus = 1
			and company = '{}'
			and eos_type = '{}'
			and effective_from = '{}'
			and name != '{}'""".format(self.get('company'), self.get('eos_type'), self.get('effective_from'), self.get('name'))
		duplicate = frappe.db.sql(duplicate, as_dict=True)
		
		if duplicate:
			frappe.throw(_("Service Award Rule Already Created for Date {}".format(formatdate(self.get('effective_from')))))


	def validate_child(self):
		distinct_dict = {}
		valid_benefit_type = self.benefit_type()

		for row in self.get("service_award_details"):
			if int(row.get('tenure_upto')) <= 0:
				frappe.throw(_("Tenure Upto Should Be Greater the Zero"))
			
			if not row.get('eos_benefit_type') in valid_benefit_type:
				frappe.throw(_("Please Select Valid EOS Benfit Type"))
			
			if row.get('eos_benefit_type') in distinct_dict and int(row.get('tenure_upto')) in distinct_dict.get(row.get('eos_benefit_type'), []):
				frappe.throw(_("Duplicate Tenure Upto {} For EOS Benefit Type {} at Row {}".format(row.get('tenure_upto'), row.get('eos_benefit_type'), row.get('idx'))))
			
			distinct_list = distinct_dict.setdefault(row.get('eos_benefit_type'), [])
			distinct_list.append(row.get('tenure_upto'))


	def benefit_type(self):
		benefit_type = """SELECT `BT`.`name`
			FROM (SELECT row_number() OVER(PARTITION BY benefit_type ORDER BY effective_from DESC) AS Idx, name, benefit_type
				FROM `tabBenefit Type for EOS`
				WHERE docstatus = 1
				AND effective_from <= '{}') AS BT
			WHERE `BT`.`Idx` = 1""".format(self.get('effective_from'))
		return frappe.db.sql_list(benefit_type)

def filter_benefit_type(doctype, txt, searchfield, start, page_len, filters):
	benefit_list = """SELECT `BT`.`name`, `BT`.`benefit_type`
		FROM (SELECT row_number() OVER(PARTITION BY benefit_type ORDER BY effective_from DESC) AS Idx, name, benefit_type
			FROM `tabBenefit Type for EOS`
			WHERE docstatus = 1
			AND effective_from <= '{}') AS BT
		WHERE `BT`.`Idx` = 1
		AND (name LIKE %(txt)s
			OR benefit_type LIKE %(txt)s)
	""".format(filters.get('effective_from'))

	return frappe.db.sql(benefit_list, {
			'txt': "%%%s%%" % txt
		})