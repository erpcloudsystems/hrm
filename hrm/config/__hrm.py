from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Employee"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Employment Type",
				},
				{
					"type": "doctype",
					"name": "Branch",
				},
				{
					"type": "doctype",
					"name": "Department",
				},
				{
					"type": "doctype",
					"name": "Designation",
				},
				{
					"type": "doctype",
					"name": "Employee Grade",
				},
				{
					"type": "doctype",
					"name": "Employee Group",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Health Insurance"
				},
				{
					"type": "doctype",
					"name": "Employee Portal"
				},
				{
					"type": "page",
					"name": "hr-dashboard",
					"label": _("HR Dashboard")
				}
			]
		},
		{
			"label": _("Attendance"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Attendance Tool",
					"hide_count": True,
					"onboard": 1,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Attendance",
					"onboard": 1,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Attendance Request",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Upload Attendance",
					"hide_count": True,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Checkin",
					"hide_count": True,
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Attendance Amendment",
					"hide_count": True,
					"dependencies": ["Employee"]
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Monthly Attendance Sheet",
					"doctype": "Attendance"
				},
				{
					"type": "doctype",
					"name": "OT Rule",
					"label": _("Overtime Rule"),
					"description": _("OT Rule.")
				},
				{
					"type": "doctype",
					"name": "OT Planner",
					"label": _("Overtime Planner"),
					"description": _("OT Planner.")
				},
				{
					"type": "doctype",
					"name": "OT Request",
					"label": _("Overtime Request"),
					"description": _("OT Request.")
				},
				{
					"type": "doctype",
					"name": "Late Coming Request",
					"label": _("Late Coming Request"),
					"description": _("Late Coming Request.")
				},
				{
					"type": "doctype",
					"name": "Early Going Request",
					"label": _("Early Going Request"),
					"description": _("Early Going Request.")
				}
			]
		},
		{
			"label": _("Leaves"),
			"items": [
				{
					"type": "doctype",
					"name": "Leave Allocation",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Leave Policy",
					"dependencies": ["Leave Type"]
				},
				{
					"type": "doctype",
					"name": "Leave Period",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name":"Leave Type",
				},
				{
					"type": "doctype",
					"name": "Holiday List",
				},
				{
					"type": "doctype",
					"name": "Leave Block List",
				},
				{
					"type": "doctype",
					"name": "Leave Rule",
					"description": _("Leave Rule.")
				},
				{
					"type": "doctype",
					"name": "Leave Request",
					"description": _("Leave Request.")
				},
				# {
				# 	"type": "doctype",
				# 	"name": "Violation Type",
				# 	"description": _("Violation Type.")
				# },
				# {
				# 	"type": "doctype",
				# 	"name": "Violation Settings",
				# 	"description": _("Violation Settings.")
				# },
				# {
				# 	"type": "doctype",
				# 	"name": "Violation Approver Grid",
				# 	"description": _("Violation Approver Grid.")
				# },
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Leave Balance",
					"doctype": "Leave Application"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Leave Ledger Entry",
					"doctype": "Leave Ledger Entry"
				},
			]
		},
		{
			"label": _("Vacation Leave"),
			"items": [
				{
					"type": "doctype",
					"name": "Vacation Leave Rule",
					"description": _("Vacation Leave Rule.")
				},
				{
					"type": "doctype",
					"name": "Vacation Rule Modification",
					"description": _("Vacation Rule Modification.")
				},
				{
					"type": "doctype",
					"name": "Vacation Leave Application",
					"description": _("Vacation Leave Application.")
				},
				{
					"type": "doctype",
					"name": "Vacation Rejoining",
					"description": _("Vacation Rejoining.")
				},
				{
					"type": "doctype",
					"name": "Vacation Leave Encashment",
					"description": _("Vacation Leave Encashment.")
				},
				{
					"type": "doctype",
					"name": "Vacation Closing",
					"description": _("Vacation Closing."),
				},
				{
					"type": "doctype",
					"name": "Airline Travel Agent",
					"description": _("Airline Travel Agent.")
				},
				{
					"type": "doctype",
					"name": "Airline Ticket Request",
					"description": _("Airline Ticket Request.")
				},
				{
					"type": "doctype",
					"name": "Exit ReEntry Visa",
					"description": _("Exit ReEntry Visa.")
				},
				{
					"type": "report",
					"name": "Vacation Leave Ledger",
					"doctype": "Vacation Leave Rule",
					"is_query_report": True
				}
			]
		},
		{
			"label": _("Payroll"),
			"items": [
				{
					"type": "doctype",
					"name": "Salary Structure",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Salary Structure Assignment",
					"onboard": 1,
					"dependencies": ["Salary Structure", "Employee"],
				},
				{
					"type": "doctype",
					"name": "Payroll Entry",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Salary Slip",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Payroll Period",
				},
				{
					"type": "doctype",
					"name": "Salary Component",
				},
				{
					"type": "doctype",
					"name": "Additional Salary",
				},
				{
					"type": "doctype",
					"name": "Retention Bonus",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Incentive",
					"dependencies": ["Employee"]
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Salary Register",
					"doctype": "Salary Slip"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Salary Structure",
					"label": _("Salary Structure Report"),
					"doctype": "Salary Structure"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Main Salary Register",
					"label": _("Main Salary Register"),
					"doctype": "Salary Slip"
				},
                {
					"type": "report",
					"is_query_report": True,
					"name": "Bank Salary Register",
					"label": _("Bank Salary Register"),
					"doctype": "Salary Slip"
				}
			]
		},
		{
			"label": _("Employee Lifecycle"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Onboarding",
					"dependencies": ["Job Applicant"],
				},
				{
					"type": "doctype",
					"name": "Employee Skill Map",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Promotion",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Transfer",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Separation",
					"dependencies": ["Employee"],
				},
				{
					"type": "doctype",
					"name": "Employee Onboarding Template",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Separation Template",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "EOS Master",
					"label": _("EOS Master"),
					"description": _("EOS Master.")
				},
				{
					"type": "doctype",
					"name": "Benefit Type for EOS",
					"label": _("Benefit Type for EOS"),
					"description": _("Benefit Type for EOS.")
				},
				{
					"type": "doctype",
					"name": "Service Award Rule",
					"label": _("Service Award Rule"),
					"description": _("Service Award Rule.")
				},
				{
					"type": "doctype",
					"name": "Service Closing",
					"label": _("Service Closing"),
					"description": _("Service Closing.")
				}
			]
		},
		{
			"label": _("Recruitment"),
			"items": [
				{
					"type": "doctype",
					"name": "Job Opening",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Job Applicant",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Job Offer",
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Staffing Plan",
				},
			]
		},
		{
			"label": _("Training"),
			"items": [
				{
					"type": "doctype",
					"name": "Training Program"
				},
				{
					"type": "doctype",
					"name": "Training Event"
				},
				{
					"type": "doctype",
					"name": "Training Result"
				},
				{
					"type": "doctype",
					"name": "Training Feedback"
				},
			]
		},
		{
			"label": _("Performance"),
			"items": [
				{
					"type": "doctype",
					"name": "Appraisal",
				},
				{
					"type": "doctype",
					"name": "Appraisal Template",
				},
				{
					"type": "doctype",
					"name": "Energy Point Rule",
				},
				{
					"type": "doctype",
					"name": "Energy Point Log",
				},
				{
					"type": "link",
					"doctype": "Energy Point Log",
					"label": _("Energy Point Leaderboard"),
					"route": "#social/users"
				},
			]
		},
		{
			"label": _("Expense Claims"),
			"items": [
				{
					"type": "doctype",
					"name": "Expense Claim",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Employee Advance",
					"dependencies": ["Employee"]
				},
			]
		},
		{
			"label": _("Loans"),
			"items": [
				{
					"type": "doctype",
					"name": "Loan Application",
					"dependencies": ["Employee"]
				},
				{
					"type": "doctype",
					"name": "Loan"
				},
				{
					"type": "doctype",
					"name": "Loan Type",
				},
			]
		},
		{
			"label": _("Shift Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Shift Type",
				},
				{
					"type": "doctype",
					"name": "Shift Request",
				},
				{
					"type": "doctype",
					"name": "Shift Assignment",
				},
			]
		},
		{
			"label": _("Fleet Management"),
			"items": [
				{
					"type": "doctype",
					"name": "Vehicle"
				},
				{
					"type": "doctype",
					"name": "Vehicle Log"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Vehicle Expenses",
					"doctype": "Vehicle"
				},
			]
		},
		{
			"label": _("Settings"),
			"icon": "fa fa-cog",
			"items": [
				{
					"type": "doctype",
					"name": "HR Settings",
				},
				{
					"type": "doctype",
					"name": "Daily Work Summary Group"
				},
				{
					"type": "page",
					"name": "team-updates",
					"label": _("Team Updates")
				},
			]
		},
		{
			"label": _("Document"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Data Changes",
					"description": _("Employee Data Changes.")
				},
				{
					"type": "doctype",
					"name": "Employee Complaint Form",
					"description": _("Employee Complaint Form.")
				},
				{
					"type": "doctype",
					"name": "Warning Letter",
					"description": _("Warning Letter.")
				},
				{
					"type": "doctype",
					"name": "Insurance",
					"description": _("Insurance.")
				},
				{
					"type": "doctype",
					"name": "Insurance Class",
					"description": _("Insurance Class.")
				},
				{
					"type": "doctype",
					"name": "Master Request",
					"description": _("Master Request.")
				},
				{
					"type": "doctype",
					"name": "Modify Employee Reports To",
					"description": _("Modify Employee Reports To.")
				}
			]
		},
		{
			"label": _("Reports"),
			"icon": "fa fa-list",
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employee Birthday",
					"doctype": "Employee"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Employees working on a holiday",
					"doctype": "Employee"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Department Analytics",
					"doctype": "Employee"
				},
				{
					"type": "report",
					"name": "Attendance Log",
					"doctype": "Attendance Process",
					"is_query_report": True
				}
			]
		},
	]
