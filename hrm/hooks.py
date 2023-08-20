# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "hrm"
app_title = "HRM"
app_publisher = "AVU"
app_description = "HRM"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "avu.etoserp.com"
app_license = "MIT"
fixtures = ['Custom Field', 'Property Setter']

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = ["//cdn.datatables.net/1.10.19/css/jquery.dataTables.min.css"]
app_include_js = ["//cdn.datatables.net/1.10.19/js/jquery.dataTables.min.js"]

# include js, css files in header of web template
# web_include_css = "/assets/hrm/css/hrm.css"
# web_include_js = "/assets/hrm/js/hrm.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Employee": ["custom_script/employee/employee.js"],
	"Company": ["custom_script/company/company.js"],
	"Attendance": ["custom_script/attendance/attendance.js"],
	"Salary Slip": ["custom_script/salary_slip/salary_slip.js"],
	"Leave Application": "custom_script/leave_application/leave_application.js",
	"Payroll Entry": "custom_script/payroll_entry/payroll_entry.js",
	"Designation": "custom_script/designation/designation.js",
	"Holiday List": "custom_script/holiday_list/holiday_list.js",
	"Loan Application": "custom_script/loan_application/loan_application.js",
	"Shift Request": "custom_script/shift_request/shift_request.js",
	"Shift Type": "custom_script/shift_type/shift_type.js",
	"Timesheet": "custom_script/timesheet/timesheet.js",
	"Loan": "custom_script/Loan/Loan.js"
}

doctype_list_js = {
	"Loan Application": "custom_script/loan_application/loan_application_list.js",
	"Attendance" : "custom_script/attendance/attendance_list.js"
}
override_doctype_class = {
	"Shift Assignment": "hrm.custom_script.shift_assignment.shift_assignment.CustomShiftAssignment"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "hrm.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "hrm.install.before_install"
# after_install = "hrm.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hrm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Employee": {
		"onload": ["hrm.custom_script.employee.employee.onload"],
		"validate": ["hrm.custom_script.employee.employee.validate"]
	},
	"Payroll Period": {
		"validate": "hrm.custom_script.payroll_period.payroll_period.validate"
	},
	"Salary Slip": {
		"validate" : "hrm.custom_script.salary_slip.salary_slip.validate"
		# "after_insert" : ["hrm.custom_script.salary_slip.salary_slip.after_insert"],
		# "on_submit" : ["hrm.custom_script.salary_slip.salary_slip.on_submit"],
		# "on_cancel" : ["hrm.custom_script.salary_slip.salary_slip.on_cancel"],
		# "on_trash" : ["hrm.custom_script.salary_slip.salary_slip.on_trash"]
	},
	"Attendance": {
		"validate": "hrm.custom_script.attendance.attendance.validate",
		"on_cancel": "hrm.custom_script.attendance.attendance.on_cancel",
		"after_insert": "hrm.custom_script.attendance.attendance.after_insert",
	# 	"on_submit": ["hrm.custom_script.attendance.attendance.on_submit"],
	# 	"before_cancel": ["hrm.custom_script.attendance.attendance.before_cancel"],
		"on_trash": ["hrm.custom_script.attendance.attendance.on_trash"],
	# 	"on_change": ["hrm.custom_script.attendance.attendance.on_change"]
	},
	'Timesheet': {
		"on_submit": "hrm.custom_script.timesheet.timesheet.on_submit",
		# "on_submit": "hrm.custom_script.timesheet.timesheet.create_attendance"
        "on_cancel":"hrm.custom_script.timesheet.timesheet.on_cancel",
        "validate":"hrm.custom_script.timesheet.timesheet.validate",
        "before_save":"hrm.custom_script.timesheet.timesheet.before_save"
	},
	'Employee Checkin': {
		"validate": "hrm.custom_script.employee_checkin.employee_checkin.validate"
	},
	'Loan Application': {
		"validate": "hrm.custom_script.loan_application.loan_application.validate"
	},
	'Loan Type': {
		"validate": "hrm.custom_script.loan_type.loan_type.validate"
	},
	'Leave Type': {
		"on_change": "hrm.custom_script.leave_type.leave_type.on_change",
		"on_trash": "hrm.custom_script.leave_type.leave_type.on_trash"
	},
    # 'Shift Request':{
    #     "on_cancel":"hrm.custom_script.shift_request.shift_request.oncancel"
    # }
	"Leave Application": {
		"validate": "hrm.custom_script.leave_application.leave_application.validate",
		"before_cancel": "hrm.custom_script.leave_application.leave_application.before_cancel",
		"on_cancel": "hrm.custom_script.leave_application.leave_application.on_cancel",
		"on_trash": "hrm.custom_script.leave_application.leave_application.on_trash",
        "before_save" : "hrm.custom_script.leave_application.leave_application.get_user_role",
		# "before_cancel" :"hrm.custom_script.leave_application.leave_application.cancel_wf_doc",
		# "on_trash":"hrm.custom_script.leave_application.leave_application.delete_wf",
		"before_submit":"hrm.custom_script.leave_application.leave_application.get_user_role_validation"
	},
	"Loan": {
		"validate": "hrm.custom_script.loan.loan.validate",
		"on_cancel": "hrm.custom_script.loan.loan.on_cancel",
		"on_trash": ["hrm.custom_script.loan.loan.on_trash"],
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	# "all": [
	# 	"hrm.tasks.all"
	# ],
	"daily": [
		"hrm.hrm.doctype.workflow_delegation.workflow_delegation.assign_delegated_role"
	],
	"hourly": [
		"hrm.custom_script.attendance.holiday_attendance.holiday_attendance"
	],
	# "weekly": [
	# 	"hrm.tasks.weekly"
	# ]
	# "monthly": [
	# 	"hrm.tasks.monthly"
	# ]
}

# Testing
# -------

# before_tests = "hrm.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hrm.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "hrm.task.get_dashboard_data"
# }

