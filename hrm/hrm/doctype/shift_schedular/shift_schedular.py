# Copyright (c) 2021, aavu and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
class ShiftSchedular(Document):
	def before_submit(self):
		for assignment in self.employee_schedule:
			doc = frappe.new_doc("Shift Assignment")
			doc.start_date = assignment.date		
			doc.shift_type = assignment.shift_type
			doc.employee = assignment.employee
			doc.status = "Active"
			doc.save()
			doc.submit()
			frappe.db.commit()
			sql = """update `tabShift Assignment` a set a.end_date='{}' where a.name = '{}'""".format(assignment.date,doc.name)
			frappe.db.sql(sql)
		
			assignment.shift_assignment=doc.name
	def before_cancel(self):
		# from datetime import date
		# from datetime import datetime
		# today = date.today()
		# if today >= datetime.strptime(str(self.period_from),"%Y-%m-%d").date() :
		# 	frappe.throw("Shift Schedular can not be cancelled for past days")
		pass
	def on_cancel(self):
		for assignment in self.employee_schedule:
			if assignment.shift_assignment :
				doc = frappe.get_doc("Shift Assignment",assignment.shift_assignment)
				# assignment.shift_assignment = ""
				doc.cancel()
	
	@frappe.whitelist()
	def notify_employee(self):
		template = frappe.db.get_single_value('HR Settings', 'shift_scheduled_notification_template')
		if not template:
			frappe.msgprint(_("Please set default template for Shift Scheduled Notification in HR Settings."))
			return
			
		if template:
			email_template = frappe.get_doc("Email Template", template)
			employees = """select distinct employee from `tabEmployee Shift Schedule` where parent = '{}'   order by employee,date """.format(self.name)
			emp = frappe.db.sql(employees)
			sent_mail =False
			for employee in emp :
				user = frappe.db.get_value('Employee', employee[0],'user_id')
				emp_name = frappe.db.get_value('Employee', employee[0],'employee_name')
				if user:
					sql = """select employee, date, shift_type from `tabEmployee Shift Schedule` where parent = '{}' and employee = '{}'  order by employee,date """.format(self.name,employee[0])
					shifts = frappe.db.sql(sql,as_dict=True)
					grid = "<style>table{border-spacing:0px; min-width:500px;} th,td{border:solid;padding:5px;border-width: 1px; }</style><div>Hello,<br>"+emp_name+"<br>  Following Shifts has been assigned to you.</div><br><table>"
					grid +="<tr><th>Date</th><th>Shift</th></tr>"
					for shift in shifts :  
						grid +="<tr><td>"+shift["date"].strftime("%d/%m/%Y")+"</td><td>"+shift["shift_type"]+"</td><tr>"

					grid +="</table>"

					# message = frappe.render_template(email_template.response, args)
					message =grid
					self.notify({
						# for post in messages
						"message": message, 
						"message_to": user,
						# for email
						"subject": email_template.subject
					})
					if not sent_mail:
						sent_mail =True
			if sent_mail:
				frappe.msgprint(_("Emails added to email queue"))
			else :
				frappe.msgprint(_("No user found to send email"))
			
			# if self.leave_approver:
			# 	parent_doc = frappe.get_doc('Leave Request', self.name)
			# 	args = parent_doc.as_dict()

			# 	template = frappe.db.get_single_value('HR Settings', 'shift_scheduled_notification_template')
			# 	if not template:
			# 		# frappe.msgprint(_("Please set default template for Leave Approval Notification in HR Settings."))
			# 		return
			# 	if template:
			# 		email_template = frappe.get_doc("Email Template", template)
			# 		message = frappe.render_template(email_template.response, args)

			# 		self.notify({
			# 			# for post in messages
			# 			"message": message,
			# 			"message_to": self.leave_approver,
			# 			# for email
			# 			"subject": email_template.subject
			# 		})
		# return True

	def notify(self, args):
		from frappe.utils.background_jobs import enqueue
		args = frappe._dict(args)
		# args -> message, message_to, subject
		contact = args.message_to
		if not isinstance(contact, list):
			if not args.notify == "employee":
				contact = frappe.get_doc('User', contact).email or contact

		sender      	    = dict()
		sender['email']     = frappe.get_doc('User', frappe.session.user).email
		sender['full_name'] = frappe.utils.get_fullname(sender['email'])

		try:
			email_args = { "recipients" : contact,
							"sender" : sender['email'],
							"subject" : args.subject,
							"message" : args.message,
							'reference_name': self.name,
							'reference_doctype': self.doctype
						}
			enqueue(method=frappe.sendmail, queue='short', timeout=300, **email_args)

			# frappe.sendmail(
			# 	recipients = contact,
			# 	sender = sender['email'],
			# 	subject = args.subject,
			# 	message = args.message,
			# )
			# frappe.msgprint(_("Email sent to {0}").format(contact))
		except frappe.OutgoingEmailError:
			pass
@frappe.whitelist()
def get_employee(branch = None):
	employees = "select name,employee_name from `tabEmployee` where status = 'Active'"
	if branch : 
		employees += " and branch ='"+branch+"'"
	emp = frappe.db.sql(employees)
	return emp
@frappe.whitelist()
def get_dates(branch = None):
	employees = "select  DATE_ADD(period_to, INTERVAL 1 DAY) as period_to from `tabShift Schedular`"
	if branch : 
		employees += " where branch ='"+branch+"' and period_to is not null and period_to!='' and docstatus!=2 order by period_to desc limit 1"
	emp = frappe.db.sql(employees,as_dict = 1)
	return emp


