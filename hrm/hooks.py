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
fixtures = ["Custom Field", "Property Setter"]

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
    "Employee": ["doctype_triggers/hr/employee/employee.js"],
    "Company": ["doctype_triggers/hr/company/company.js"],
    "Attendance": ["doctype_triggers/hr/attendance/attendance.js"],
    "Salary Slip": ["doctype_triggers/hr/salary_slip/salary_slip.js"],
    "Leave Application": "doctype_triggers/hr/leave_application/leave_application.js",
    "Payroll Entry": "doctype_triggers/hr/payroll_entry/payroll_entry.js",
    "Designation": "doctype_triggers/hr/designation/designation.js",
    "Holiday List": "doctype_triggers/hr/holiday_list/holiday_list.js",
    "Loan Application": "doctype_triggers/hr/loan_application/loan_application.js",
    "Shift Request": "doctype_triggers/hr/shift_request/shift_request.js",
    "Shift Type": "doctype_triggers/hr/shift_type/shift_type.js",
    "Timesheet": "doctype_triggers/hr/timesheet/timesheet.js",
    "Loan": "doctype_triggers/hr/Loan/Loan.js",
}

doctype_list_js = {
    "Loan Application": "doctype_triggers/hr/loan_application/loan_application_list.js",
    "Attendance": "doctype_triggers/hr/attendance/attendance_list.js",
}
override_doctype_class = {
    "Shift Assignment": "hrm.doctype_triggers.hr.shift_assignment.shift_assignment.CustomShiftAssignment"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
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
        "onload": ["hrm.doctype_triggers.hr.employee.employee.onload"],
        "validate": ["hrm.doctype_triggers.hr.employee.employee.validate"],
    },
    "Payroll Period": {
        "validate": "hrm.doctype_triggers.hr.payroll_period.payroll_period.validate"
    },
    "Salary Slip": {
        "validate": "hrm.doctype_triggers.hr.salary_slip.salary_slip.validate"
        # "after_insert" : ["hrm.doctype_triggers.salary_slip.salary_slip.after_insert"],
        # "on_submit" : ["hrm.doctype_triggers.salary_slip.salary_slip.on_submit"],
        # "on_cancel" : ["hrm.doctype_triggers.salary_slip.salary_slip.on_cancel"],
        # "on_trash" : ["hrm.doctype_triggers.salary_slip.salary_slip.on_trash"]
    },
    "Attendance": {
        "validate": "hrm.doctype_triggers.hr.attendance.attendance.validate",
        "on_cancel": "hrm.doctype_triggers.hr.attendance.attendance.on_cancel",
        "after_insert": "hrm.doctype_triggers.hr.attendance.attendance.after_insert",
        # 	"on_submit": ["hrm.doctype_triggers.attendance.attendance.on_submit"],
        # 	"before_cancel": ["hrm.doctype_triggers.attendance.attendance.before_cancel"],
        "on_trash": ["hrm.doctype_triggers.hr.attendance.attendance.on_trash"],
        # 	"on_change": ["hrm.doctype_triggers.attendance.attendance.on_change"]
    },
    "Timesheet": {
        "on_submit": "hrm.doctype_triggers.hr.timesheet.timesheet.on_submit",
        # "on_submit": "hrm.doctype_triggers.timesheet.timesheet.create_attendance"
        "on_cancel": "hrm.doctype_triggers.hr.timesheet.timesheet.on_cancel",
        "validate": "hrm.doctype_triggers.hr.timesheet.timesheet.validate",
        "before_save": "hrm.doctype_triggers.hr.timesheet.timesheet.before_save",
    },
    "Employee Checkin": {
        "validate": "hrm.doctype_triggers.hr.employee_checkin.employee_checkin.validate"
    },
    "Loan Application": {
        "validate": "hrm.doctype_triggers.hr.loan_application.loan_application.validate"
    },
    "Loan Type": {"validate": "hrm.doctype_triggers.hr.loan_type.loan_type.validate"},
    "Leave Type": {
        "on_change": "hrm.doctype_triggers.hr.leave_type.leave_type.on_change",
        "on_trash": "hrm.doctype_triggers.hr.leave_type.leave_type.on_trash",
    },
    # 'Shift Request':{
    #     "on_cancel":"hrm.doctype_triggers.shift_request.shift_request.oncancel"
    # }
    "Leave Application": {
        "validate": "hrm.doctype_triggers.hr.leave_application.leave_application.validate",
        "before_cancel": "hrm.doctype_triggers.hr.leave_application.leave_application.before_cancel",
        "on_cancel": "hrm.doctype_triggers.hr.leave_application.leave_application.on_cancel",
        "on_trash": "hrm.doctype_triggers.hr.leave_application.leave_application.on_trash",
        "before_save": "hrm.doctype_triggers.hr.leave_application.leave_application.get_user_role",
        # "before_cancel" :"hrm.doctype_triggers.leave_application.leave_application.cancel_wf_doc",
        # "on_trash":"hrm.doctype_triggers.leave_application.leave_application.delete_wf",
        "before_submit": "hrm.doctype_triggers.hr.leave_application.leave_application.get_user_role_validation",
    },
    "Loan": {
        "validate": "hrm.doctype_triggers.hr.loan.loan.validate",
        "on_cancel": "hrm.doctype_triggers.hr.loan.loan.on_cancel",
        "on_trash": ["hrm.doctype_triggers.hr.loan.loan.on_trash"],
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
        "hrm.doctype_triggers.hr.attendance.holiday_attendance.holiday_attendance"
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
