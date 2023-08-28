# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days
import json

class VacationRejoining(Document):
	
	def onload(self):
		if self.is_new() == None:
			result_parm = vacation_rejoining_edit(self.employee_id, add_days(self.end_date, 1))
			self.get("__onload")["read_only"] = result_parm
	
	def on_update_after_submit(self):
		self.validate_date()
		self.onload()

		if self.get("__onload") and self.get("__onload")["read_only"] == 0:
			frappe.throw("Rejoining Date Cannot be Updated")
	
	def validate(self):
		self.validate_date()
	
	def validate_date(self):
		if  getdate(str(self.vacation_rejoining_date)) <= getdate(str(self.end_date)):
			frappe.throw("Rejoining Date Cannot be before End date")

@frappe.whitelist()
def get_leave(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("employee"):
		frappe.throw("Please select Employee Record first.")
	else:
		employee = filters.get("employee")
		name = filters.get("name")

		emp_sql = "SELECT CE.name, CE.employee_name\
			FROM `tabVacation Leave Application` CE\
			WHERE CE.docstatus = 1\
			AND employee_id = '{0}'\
			AND CE.status = 'Approved'\
			AND CE.name NOT IN (SELECT QQ.vacation_leave_application\
				FROM `tabVacation Rejoining` QQ\
				WHERE QQ.docstatus IN (0,1)\
				AND `QQ`.`name` != '{1}')".format(employee, name)
		result = frappe.db.sql(emp_sql, as_list=True)

		return result

def vacation_rejoining_edit(employee, rejoining_date=None):
	"""THIS METHOD IS USED IN EMPLOYEE"""

	future_leav = """SELECT *
		FROM `tabVacation Leave Application`
		WHERE `docstatus` != 2
		AND `employee_id` = '{0}'
		AND (`status` != 'Rejected'
			OR (`docstatus` = 0 
				AND `status` = 'Rejected'))
		AND  `from_date` >= {1}
	""".format(employee, json.dumps(str(rejoining_date)) if rejoining_date else '`from_date`')
	future_leav = frappe.db.sql(future_leav, as_list=True)

	prev_vac_leav_encash = """SELECT *
		FROM `tabVacation Leave Encashment`
		WHERE docstatus < 2
		AND employee = '{0}'
		AND to_date >= {1}
		""".format(employee, json.dumps(str(rejoining_date)) if rejoining_date else '`from_date`')
	res_vac_leav_encash = frappe.db.sql(prev_vac_leav_encash, as_dict=True)
	
	return (1 if not future_leav else 0) if not res_vac_leav_encash else 0