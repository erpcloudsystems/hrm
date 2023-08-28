# -*- coding: utf-8 -*-
# Copyright (c) 2020, avu and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.user import add_role
import datetime
import json

class WorkflowDelegation(Document):
	def validate(self):
		delegated_user_list =[]
		if self.from_date > self.to_date:
			frappe.throw("From Date Should Be Less Than To Date")
		self.validation_workflow()
		if self.get("workflow_delegation_details"):
			for i in self.get("workflow_delegation_details"):
				if i.delegated_role:
					delegated_user_list.append(i.delegated_role)
				sql = "select W.from_date,W.to_date,WD.delegated_role from `tabWorkflow Delegation` W left join `tabWorkflow Delegation Details` WD  on WD.parent=W.name where ('{1}' between W.from_date and W.to_date or '{2}' between W.from_date and W.to_date) and W.docstatus=1 and WD.delegated_role = '{0}' and WD.user_role='{3}'".format(i.delegated_role,self.from_date,self.to_date,i.user_role)
				result_sql=frappe.db.sql(sql,as_dict=True)
				if result_sql:
					frappe.throw("Workflow Delegation Is Already Exist Of User <b>{0}</b> Between Date <b>{1}</b> and <b>{2}</b> For User Role <b>{4}</b> In Row <b>{3}</b>".format(i.delegated_role,self.from_date,self.to_date,i.idx,i.user_role) )
			if len(delegated_user_list)==0:
				# frappe.throw("Assign Atleast One User Role To Delegated User")
				frappe.throw("Select Atleast One User Role In Assign To")
			else:
				self.validate_same_user()

	def validation_workflow(self):
		if self.employee and self.reference_id!=None:
			workflow_result = get_user_role(self.employee)
			if not workflow_result:
				frappe.throw("Workflow Is Not Active Or Not Assign Any Workflow To Existing Employee")	
	def validate_same_user(self):
		emp_doc = frappe.get_doc("Employee",self.employee)
		if emp_doc.user_id:
			if self.get("workflow_delegation_details"):
				for p in self.get("workflow_delegation_details"):
					if p.delegated_role==emp_doc.user_id:
						frappe.throw("Assign To Cannot Same As Emplyee User ID In Row <b>{0}</b>".format(p.idx))



	def on_submit(self):
		if self.reference_id:
			leave_app_doc = frappe.get_doc(self.reference_page,self.reference_id)
			leave_app_doc.workflow_delegation_id = self.name
			leave_app_doc.flags.ignore_validate = True
			leave_app_doc.flags.ignore_on_update = True
			# leave_app_doc.db_update()
			#Convert datetime to string
			leave_app_doc.from_date =  leave_app_doc.from_date.strftime("%Y-%m-%d") 
			leave_app_doc.to_date =  leave_app_doc.to_date.strftime("%Y-%m-%d")
			leave_app_doc.save()

					  
	def before_cancel(self):
		if self.get("update_workflow_delegation_log"):
			for r in self.get("update_workflow_delegation_log"):
				clear_role(r.user,r.assign_role)
				remove_receipent(r.user,r.doctype_name)
		self.set('update_workflow_delegation_log', [])
		if self.reference_id:
			check_leave = "select name from `tab{1}` where name ='{0}' and docstatus=1".format(str(self.reference_id), str(self.reference_page))
			check_leave_data = frappe.db.sql(check_leave,as_dict=True)
			if check_leave_data:
				frappe.throw("{1} Is Submitted Against Workflow Delegation <b>{0}</b>. Cancel {1} First.".format(self.name, self.reference_page))
			else:
				leave_app_doc = frappe.get_doc(self.reference_page,self.reference_id)
				leave_app_doc.workflow_delegation_id = None
				# frappe.msgprint(str(leave_app_doc.workflow_delegation_id))
				leave_app_doc.flags.ignore_validate = True
				leave_app_doc.flags.ignore_on_update = True
				# leave_app_doc.save()
				leave_app_doc.db_update()
				
	
	def on_trash(self):
		if self.reference_id:
			check_leave = "select name from `tab{1}` where name ='{0}' and docstatus=2".format(self.reference_id, self.reference_page)
			check_leave_data = frappe.db.sql(check_leave,as_dict=True)
			if check_leave_data:
				frappe.throw("{1} Is Found Against Workflow Delegation <b>{0}</b>. Delete {1} First.".format(self.name, self.reference_page))


	
	def cancel_workflw_deleg(self):
		if self.reference_id:
			doc = frappe.get_doc(self.reference_page,self.reference_id)
			doc.workflow_delegation_id = None
			doc.save()
	
@frappe.whitelist()				
def assign_delegated_role():
	current_date = frappe.utils.nowdate()
	# time = frappe.utils.now()
	# frappe.msgprint(str(time))
	remove_role()
	sql = "select name from `tabWorkflow Delegation` where '{0}' between from_date and to_date and docstatus=1".format(current_date)
	
    # we wilchange query if cliet said its update employee again and again
    # sql = "select W.name from `tabWorkflow Delegation` W left join `tabUpdate Workflow Delegation Log`U  on U.parent=W.name  where '{0}' between W.from_date and W.to_date and W.docstatus=1 and U.name is null".format(current_date)
	sql_list = frappe.db.sql(sql,as_dict=True)
	frappe.errprint("workflow>> "+str(sql_list))

	if sql_list:
		for i in sql_list:
			doc = frappe.get_doc("Workflow Delegation",i.name)
			if doc:
				if doc.workflow_delegation_details:
					for j in doc.workflow_delegation_details:
						if j.delegated_role:
							assigned_role = frappe.get_roles(j.delegated_role)
							if j.user_role not in assigned_role:
								add_role(j.delegated_role, j.user_role)	
								doc.append('update_workflow_delegation_log', {"doctype_name":j.workflow_doctype,"user":j.delegated_role,"assign_role":j.user_role,"from_date":doc.from_date,"to_date":doc.to_date})
								doc.save()
								n_sql = "select * from `tabNotification Recipient`"
								notify_sql = frappe.db.sql(n_sql,as_dict=True)
								if notify_sql:
									for k in notify_sql:
										emp_doc = frappe.get_doc("Employee",doc.employee)
										if emp_doc.user_id:
											if k.cc:
												if emp_doc.user_id in k.cc:	
													# frappe.msgprint(str(k.parent))
													noti_doc = frappe.get_doc("Notification",k.parent)
													if noti_doc:
														if noti_doc.document_type==j.workflow_doctype:
															if noti_doc.recipients: 
																if j.delegated_role not in k.cc:
																	r = k.cc + ",\n" + j.delegated_role
																	for n in noti_doc.recipients:
																		n.cc = r
													noti_doc.save()
												# frappe.db.commit()
	
@frappe.whitelist()				
def remove_role():
	# frappe.msgprint("hii")
	current_date = frappe.utils.nowdate()
	r_sql = "select * from `tabUpdate Workflow Delegation Log` where '{0}' not between from_date and to_date and docstatus=1".format(current_date)	
	frappe.errprint(str(r_sql))
	r_sql_list = frappe.db.sql(r_sql,as_dict=True)
	frappe.errprint("update>> "+str(r_sql_list))
	if r_sql_list:
		# frappe.msgprint(str(r_sql_list))
		for r in r_sql_list:
			clear_role(r.user,r.assign_role)
			remove_receipent(r.user,r.doctype_name)
			doc = frappe.get_doc("Workflow Delegation",r.parent)
			if doc:
				doc.set('update_workflow_delegation_log', [])
				doc.save()


@frappe.whitelist()
def get_element(doctype, txt, searchfield, start, page_len, filters):
	element_sql = """select distinct(allow_edit) from `tabWorkflow Document State` WS left join `tabWorkflow` W on W.name = WS.parent and W.is_active=1 and WS.docstatus=0 where WS.parent='{0}' and W.document_type='{1}' and WS.allow_edit LIKE %(txt)s""".format(filters.get("parent"),filters.get("doctype"))
	return frappe.db.sql(element_sql,{
		'txt': "%%%s%%" %(txt)
	})

@frappe.whitelist()
def get_user_role(employee):
	workflow = []
	workflow_del = frappe.db.get_value("HR Settings", None, "enable_workflow_delegation")
	# frappe.msgprint(str(workflow_del))
	emp_doc = frappe.get_doc("Employee",employee)
	if emp_doc.user_id:
		user_doc = frappe.get_doc("User",emp_doc.user_id)
		if user_doc.enabled==1:
			user_role = frappe.get_roles(emp_doc.user_id)
			if user_role:
				for i in user_role:
					workflow_query="select distinct(WS.allow_edit) as allow_edit ,WS.parent as parent,W.document_type as document_type from `tabWorkflow Document State` WS left join `tabWorkflow` W on W.name = WS.parent where WS.allow_edit='{0}' and W.is_active=1 ".format(i)
					workflow_list = frappe.db.sql(workflow_query,as_dict=True)
					if workflow_list:
						for j in workflow_list:
							workflow.append({"workflow_name":j.parent,"workflow_doctype":j.document_type,"user_role":j.allow_edit})
				return workflow
		else:
			frapppe.throw("User ID Not Active Againce Existing Employee")
	else:
		frappe.throw("User Id Not Assign To Employee: <b>{0}</b>".format(employee))
					
				  
@frappe.whitelist()
def clear_role(email,role):
	role="delete from `tabHas Role` where parent in ('{0}') and role='{1}' ".format(email,role)
	role_del = frappe.db.sql(role)
	frappe.clear_cache()


@frappe.whitelist()
def remove_receipent(user,workflow_doctype):
	n_sql = "select * from `tabNotification Recipient`"
	notify_sql = frappe.db.sql(n_sql,as_dict=True)
	if notify_sql:
		for k in notify_sql:
			if k.cc:
				if user in k.cc:	
					noti_doc = frappe.get_doc("Notification",k.parent)
					if noti_doc:
						if noti_doc.recipients and noti_doc.document_type==workflow_doctype:
							r = ",\n" + user
							# frappe.msgprint(str(r))
							for n in noti_doc.recipients:
								n.cc = n.cc.replace(r," ")
					noti_doc.save()