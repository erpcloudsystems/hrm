# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
# from frappe.model.delete_doc import raise_link_exists_exception
from frappe.utils import cint, flt, getdate, formatdate
from hrm.custom_script.common_code import raise_link_exists_exception

class OverlapError(frappe.ValidationError): pass


def validate(doc, method):
	if validate_ss_processed(doc.employee,doc.from_date) or  validate_ss_processed(doc.employee,doc.to_date) : frappe.throw("Can not create or edit leave application, Salary is already processed for this month")
	
	validate_leave_overlap(doc)

def validate_ss_processed(employee, date):
	ss_list = frappe.db.sql("""
			select t1.name, t1.salary_structure from `tabSalary Slip` t1
			where t1.docstatus = 1 and t1.actual_attendance_start_date <= %s and t1.actual_attendance_end_date >= %s and t1.employee = %s
		""" % ('%s', '%s', '%s'), (date, date, employee), as_dict=True)
	# frappe.errprint(["ss",ss_list])
	if len(ss_list) : return True
	return False

def validate_leave_overlap(doc):
	if not doc.name:
		# hack! if name is null, it could cause problems with !=
		doc.name = "New Leave Application"
	employee = None
	
	if doc.doctype == "Vacation Leave Application":
		
		employee = doc.employee_id
	else:
		
		employee = doc.employee

	
	# Check Vacation Leave Application exists in database
	for d in frappe.db.sql("""
		select
			name, leave_type, posting_date, from_date, to_date, total_leave_days, 'Vacation Leave Application' as 'doctype'
		from `tabVacation Leave Application`
		where employee_id = %(employee)s and docstatus < 2 and status in ("Open", "Approved")
		and to_date >= %(from_date)s and from_date <= %(to_date)s
		and name != %(name)s""", {
			"employee": employee,
			"from_date": doc.from_date,
			"to_date": doc.to_date,
			"name": doc.name if doc.doctype !='Leave Application' else doc.vacation_leave_application 
		}, as_dict = 1):
		
		if d :
			throw_overlap_error(doc,d)

	# Check Leave Request exists in database
	for d in frappe.db.sql("""
		select
			name, leave_type, posting_date, from_date, to_date, total_leave_days, half_day_date, half_day, 'Leave Request' as 'doctype'
		from `tabLeave Request`
		where employee = %(employee)s and docstatus < 2 and status in ("Open", "Approved")
		and to_date >= %(from_date)s and from_date <= %(to_date)s
		and name != %(name)s""", {
			"employee": employee,
			"from_date": doc.from_date,
			"to_date": doc.to_date,
			"name":  doc.name if doc.doctype !='Leave Application' else doc.leave_request 
		}, as_dict = 1):
	
		validate_half_day_leave(doc,d)
		
	
	# Check Leave Application exists in database
	for d in frappe.db.sql("""
		select
			name, leave_type, posting_date, from_date, to_date, total_leave_days, half_day_date, half_day, 'Leave Application' as 'doctype'
		from `tabLeave Application`
		where employee = %(employee)s and docstatus < 2 and status in ("Open", "Approved")
		and to_date >= %(from_date)s and from_date <= %(to_date)s
		and ifnull(leave_request,'') = '' and ifnull(vacation_leave_application,'') = ''
		and name != %(name)s""", {
			"employee": employee,
			"from_date": doc.from_date,
			"to_date": doc.to_date,
			"name": doc.name
		}, as_dict = 1):

		validate_half_day_leave(doc,d)
		# if cint(doc.half_day)==cint(d.half_day) and getdate(doc.half_day_date) == getdate(d.half_day_date) and (
		# 	flt(doc.total_leave_days)==0.5
		# 	or getdate(doc.from_date) == getdate(d.to_date)
		# 	or getdate(doc.to_date) == getdate(d.from_date)):

		# 	total_leaves_on_half_day = get_total_leaves_on_half_day(doc)
		# 	if total_leaves_on_half_day >= 1:
		# 		throw_overlap_error(doc, d)
		# else:
		# 	throw_overlap_error(doc, d)

def validate_half_day_leave(doc,d):
	if doc.doctype !="Vacation Leave Application" :
		
		if cint(doc.half_day)==cint(d.half_day) and getdate(doc.half_day_date) == getdate(d.half_day_date) and (
		flt(doc.total_leave_days)==0.5
		and (getdate(doc.from_date) == getdate(d.to_date)
		or getdate(doc.to_date) == getdate(d.from_date))):
			total_leaves_on_half_day = doc.get_total_leaves_on_half_day()
			if total_leaves_on_half_day >= 1:
				
				throw_overlap_error(doc,d)
		else:
			
			throw_overlap_error(doc,d)
	else:
		
		throw_overlap_error(doc,d)

def throw_overlap_error(doc, d):
	employee=None
	if doc.doctype == "Vacation Leave Application":
		employee = doc.employee_id
	else:
		employee = doc.employee
	msg = _("Employee {0} has already applied for {1} between {2} and {3} : ").format(employee,
		d['leave_type'], formatdate(d['from_date']), formatdate(d['to_date'])) \
		+ """ <b><a href="#Form/{1}/{0}">{0}</a></b>""".format(d["name"],d.doctype)
	frappe.throw(msg, OverlapError)

def get_total_leaves_on_half_day(doc):
	leave_count_on_half_day_date = frappe.db.sql("""select count(name) from `tabLeave Application`
		where employee = %(employee)s
		and docstatus < 2
		and status in ("Open", "Approved")
		and half_day = 1
		and half_day_date = %(half_day_date)s
		and name != %(name)s""", {
			"employee": doc.employee,
			"half_day_date": doc.half_day_date,
			"name": doc.name
		})[0][0]

	return leave_count_on_half_day_date * 0.5



@frappe.whitelist()
def on_submit(doc, method):
	update_attendance(doc)

@frappe.whitelist()
def before_cancel(doc, method):
	doc.validate_salary_processed_days()
	cancel_wf_doc(doc,method)

@frappe.whitelist()
def on_cancel(doc, method):
	link_field(doc)
	update_attendance_cancel(doc)

@frappe.whitelist()
def on_trash(doc, method):
	if doc.from_date and  doc.employee and doc.to_date and validate_ss_processed(doc.employee,doc.from_date) or  validate_ss_processed(doc.employee,doc.to_date) : 
		frappe.throw("Can not delete leave application, Salary is already processed for this month")
	# cannot_cancel(doc)
	attendace_delete(doc)
	link_field(doc)
	doc.validate_salary_processed_days()
	delete_wf(doc,method)

def update_attendance_cancel(doc):
	attendance = frappe.db.sql("""select *
		from `tabAttendance`
		where employee = %s
		and (attendance_date between %s and %s)
		and docstatus < 2""",(doc.employee, doc.from_date, doc.to_date), as_dict=1)
	if attendance:
		for i in attendance:
			status = i.status
			frm_date = str(doc.from_date)
			to_date = str(doc.to_date)
			if status == "Absent" or "On Leave":
				sql = """update `tabAttendance`
					set leave_type = '', leave_application='', status = 'Absent', status2 = 'Absent'
					where employee = '{}'
					and attendance_date between '{}' and '{}'""".format(doc.employee, frm_date, to_date)
				frappe.db.sql(sql)

def update_attendance(doc):
	if doc.status == "Approved":
		attendance = frappe.db.sql("""select *
			from `tabAttendance`
			where employee = %s
			and (attendance_date between %s and %s)
			and docstatus < 2""",(doc.employee, doc.from_date, doc.to_date), as_dict=1)
		if attendance:
			for d in attendance:
				status = d.status
				if status == "Present":
					frappe.msgprint("Attendance already marked as present", raise_exception=True)
				elif status == "Absent" or "On Leave" or "Half Day":
					if status == "Absent":
						status = "On Leave"
					elif status == "On Leave":
						status = "On Leave"
					else:
						status = "Half Day"
				frappe.db.sql("""update `tabAttendance` set status = %s,status2 = %s, leave_type = %s\
						where name = %s""",(status, doc.leave_type, doc.leave_type, d.name))

def cannot_cancel(doc):
	attendance = frappe.db.sql("""select *
		from `tabAttendance`
		where employee = %s
		and (attendance_date between %s and %s)
		and docstatus < 2""",(doc.employee, doc.from_date, doc.to_date), as_dict=1)
	if len(attendance) > 0 and doc.get('auto_cancel_from_attendance', 0) == 0:
		frappe.throw("Cannot Delete or Cancel It is Linked With Attendance <a href='#Form/Attendance/{0}'>{0}</a>".format(attendance[0]["name"]))
	# if doc.reference_doctype=="Attendance Amend Request":
	# 	frappe.throw("Cannot Delete or Cancel It is Linked With Attendance Amend Request {0}".format(doc.reference_id))
def attendace_delete(doc):
	attendance = frappe.db.sql("""select name
		from `tabAttendance`
		where employee = %s and leave_application = %s
		and (attendance_date between %s and %s)""",(doc.employee,doc.name, doc.from_date, doc.to_date), as_dict=1)
	if attendance:
		# sql = frappe.db.sql("""update `tabAttendance` 
		# set leave_application=''
		# where employee = %s
		# and (attendance_date between %s and %s)
		#  """,(doc.employee, doc.from_date, doc.to_date), as_dict=1)
		for d in attendance:
			att = frappe.get_doc("Attendance", d["name"])
			att.leave_application = None
			att.db_update()
			if att.docstatus == 1:
				att.cancel()
			att.delete()

def link_field(doc):
	doc_name = 'Leave Request' if doc.get('leave_request') else 'Vacation Leave Application'
	doc_id = doc.get('leave_request') or doc.get('vacation_leave_application')
	if doc_id and frappe.db.exists(doc_name, doc_id):
		raise_link_exists_exception(doc, doc_name, doc_id)

@frappe.whitelist()
def validate_salary_processed_days(doc, method):
	last_processed_pay_slip = frappe.db.sql("""
		select start_date, end_date from `tabSalary Slip`
		where docstatus = 1 and employee = %s
		and %s between start_date and end_date
		order by modified desc limit 1
	""",(doc.employee, doc.from_date))
	last_processed_pay_slip2 = frappe.db.sql("""
		select start_date, end_date from `tabSalary Slip`
		where docstatus = 1 and employee = %s
		and %s between start_date and end_date
		order by modified desc limit 1
	""",(doc.employee, doc.to_date))
	if last_processed_pay_slip:
		frappe.throw(_("Salary already processed for period between {0} and {1}, You Cannot Change Leave Application between this date range.").format(formatdate(last_processed_pay_slip[0][0]), formatdate(last_processed_pay_slip[0][1])))
	if last_processed_pay_slip2:
		frappe.throw(_("Salary already processed for period between {0} and {1}, You Cannot Change Leave Application between this date range.").format(formatdate(last_processed_pay_slip[0][0]), formatdate(last_processed_pay_slip[0][1])))

@frappe.whitelist()
def get_user_role(doc,method):
	workflow = []
	workflow_del = frappe.db.get_value("HR Settings", None, "enable_workflow_delegation")
	if int(workflow_del or 0)==1:
		emp_doc = frappe.get_doc("Employee",doc.employee)
		user_role = frappe.get_roles(emp_doc.user_id)
		if emp_doc.user_id:
			if user_role:
				for i in user_role:
					workflow_list = frappe.get_list("Workflow Document State", filters={"allow_edit":i}, fields = ["parent","allow_edit"])
					if workflow_list:
						for j in workflow_list:
							# frappe.msgprint(str(j.allow_edit))
							workflow.append(j.parent)
			if len(workflow)>0 and doc.doctype=="Leave Application" and doc.ignore_workflow_delegation==0 and doc.workflow_delegation_id==None and doc.status=="Open":
				doc.flags.ignore_on_update=True
				frappe.msgprint("Please Make <b>Workflow Delegation</b>")


@frappe.whitelist()
def get_user_role_validation(doc,method):
	workflow = []
	workflow_del = frappe.db.get_value("HR Settings", None, "enable_workflow_delegation")
	if int(workflow_del or 0)==1:
		emp_doc = frappe.get_doc("Employee",doc.employee)
		user_role = frappe.get_roles(emp_doc.user_id)
		if user_role:
			for i in user_role:
				workflow_list = frappe.get_list("Workflow Document State", filters={"allow_edit":i}, fields = ["parent","allow_edit"])
				if workflow_list:
					for j in workflow_list:
						# frappe.msgprint(str(j.allow_edit))
						workflow.append(j.parent)
		if len(workflow)>0 and doc.doctype=="Leave Application" and doc.workflow_delegation_id==None and doc.ignore_workflow_delegation==0 and doc.status=="Approved":
			doc.flags.ignore_validate = True
			doc.flags.ignore_on_update=True
			frappe.throw("Please Make <b>Workflow Delegation</b>")
		else:
			doc.run_method('on_update')

@frappe.whitelist()			   
def cancel_wf_doc(doc,method):
	if doc.workflow_delegation_id:
		wf_doc = frappe.get_doc("Workflow Delegation",doc.workflow_delegation_id)
		wf_id = wf_doc.reference_id
		if wf_doc.docstatus == 1:
			wf_doc.reference_id = None 
			wf_doc.cancel()
			# wf_doc.reference_id = wf_id
			frappe.db.sql("UPDATE `tabWorkflow Delegation` SET reference_id ='{0}' where name ='{1}' ".format(wf_id,doc.workflow_delegation_id))
		else:
			wf_doc.reference_id = ""
			wf_doc.db_update()
			wf_doc.delete()

@frappe.whitelist()			   
def delete_wf(doc,method):
	# if doc.workflow_delegation_id:
	wd_list="select name from `tabWorkflow Delegation` where reference_id='{0}' order by name desc".format(doc.name)
	wd_list_data = frappe.db.sql(wd_list,as_dict=True)
	if wd_list_data:
		for w in wd_list_data:
			# frappe.msgprint(str(w.name))
			wf_doc = frappe.get_doc("Workflow Delegation",w.name)
			wf_id = wf_doc.reference_id 
			wf_doc.reference_id = None
			if wf_doc.docstatus == 1:
				wf_doc.cancel()
				wf_doc.delete() 
			else:
				# frappe.throw(str(wf_doc.reference_id))
				wf_doc.reference_id = ""
				wf_doc.db_update()
				wf_doc.delete()
		# wf_doc.reference_id = wf_id
		# frappe.db.sql("UPDATE `tabWorkflow Delegation` SET reference_id ='{0}'".format(wf_id))
		
	

@frappe.whitelist()
def make_workflow_delegation(name,employee,employee_name,from_date,to_date):
	workflow_delegation = frappe.new_doc('Workflow Delegation')
	workflow_delegation.employee=employee
	workflow_delegation.employee_name=employee_name
	workflow_delegation.reference_page="Leave Application"
	workflow_delegation.reference_id=name
	workflow_delegation.from_date=from_date
	workflow_delegation.to_date=to_date
	return workflow_delegation.as_dict()
