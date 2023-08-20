
from __future__ import unicode_literals
import frappe
from frappe import _


def validate(doc, method):
	if validate_ss_processed(doc.applicant,doc.repayment_start_date) : 
		frappe.throw("Can not create or edit loan, salary is already processed for this month")
def on_cancel(doc, method):

	if validate_ss_processed(doc.applicant,doc.repayment_start_date) : 
		frappe.throw("Can not cancel loan, salary is already processed for this month")
def on_trash(doc, method):
	if validate_ss_processed(doc.applicant,doc.repayment_start_date) :
		 frappe.throw("Can not delete loan, salary is already processed for this month")


def validate_ss_processed(employee, date):
	ss_list = frappe.db.sql("""
			select t1.name, t1.salary_structure from `tabSalary Slip` t1
			where t1.docstatus = 1 and t1.actual_attendance_start_date <= %s and t1.actual_attendance_end_date >= %s and t1.employee = %s
		""" % ('%s', '%s', '%s'), (date, date, employee), as_dict=True)
	frappe.errprint(["ss",ss_list])
	if len(ss_list) : return True
	return False