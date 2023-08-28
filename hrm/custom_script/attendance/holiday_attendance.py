# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

# from hrms.hr.doctype.attendance.attendance import mark_absent
from frappe.utils import nowdate, add_days, getdate, date_diff

from hrm.doctype_triggers.hr.employee_checkin.employee_checkin import get_employee_shift
from hrm.doctype_triggers.hr.attendance.attendance import weekoff_holiday


# @frappe.whitelist()
# def holiday_attendance(shift, process=0):
# 	employee = """SELECT `E`.`name`, `H`.`holiday_date`, `E`.`date_of_joining`, `E`.`relieving_date`, IFNULL(CAST(`ST`.`last_sync_of_checkin` AS DATE), `H`.`holiday_date`) AS process_date, `ST`.`enable_auto_attendance`
# 		FROM `tabEmployee` AS `E`
# 		LEFT JOIN `tabShift Type` AS ST
# 			ON `E`.`default_shift` = `ST`.`name`
# 		LEFT JOIN `tabCompany` AS C
# 			ON `E`.`company` = `C`.`name`
# 		INNER JOIN `tabHoliday` AS H
# 			ON IF(CHAR_LENGTH(`E`.`holiday_list`) > 0
# 				, `E`.`holiday_list`
# 				, IF(CHAR_LENGTH(`ST`.`holiday_list`) > 0
# 					, `ST`.`holiday_list`
# 					, `C`.`default_holiday_list`)) = `H`.`parent`
# 			AND `H`.`holiday_date` BETWEEN IFNULL(`ST`.`process_attendance_after`, `H`.`holiday_date`)
# 				AND IFNULL(CAST(`ST`.`last_sync_of_checkin` AS DATE), `H`.`holiday_date`)
# 		WHERE `H`.`holiday_date` NOT IN (SELECT `attendance_date`
# 			FROM `tabAttendance`
# 			WHERE `employee` = `E`.`name`
# 			AND `docstatus` = 1)"""
# 	employee = frappe.db.sql(employee, as_dict=True)

# 	for emp in employee:
# 		if process == 0 and (emp.get('enable_auto_attendance') or 0) == 0: continue

# 		if add_days(emp.get('process_date'), 1) <= getdate(nowdate())\
# 			and getdate(emp.get('date_of_joining')) <= getdate(emp.get('holiday_date')) <= getdate((emp.get('relieving_date') or emp.get('holiday_date'))):
# 			try:
# 				mark_absent(emp.get('name'), emp.get('holiday_date'))
# 				frappe.db.commit()
# 			except Exception as e:
# 				print(e)


@frappe.whitelist()
def holiday_attendance(shift=None, process=0):
    shifts = frappe.db.sql(
        """SELECT *
		FROM `tabShift Type`
		{} """.format(
            "WHERE name = '{}'".format(shift) if shift else ""
        ),
        as_dict=True,
    )

    system_date = nowdate()

    for shift in shifts:
        if (process == 0 and shift.get("enable_auto_attendance") == 0) or not shift.get(
            "process_attendance_after"
        ):
            continue

        if shift.get("last_sync_of_checkin") and add_days(
            getdate(shift.get("last_sync_of_checkin")), -1
        ) >= getdate(system_date):
            continue

        process_to = getdate(shift.get("last_sync_of_checkin") or system_date)
        process_from = getdate(shift.get("process_attendance_after"))
        days = date_diff(process_to, process_from)

        for inc in range(0, days):
            att_date = add_days(process_from, inc)

            employees = """SELECT *
				FROM `tabEmployee`
				WHERE name not in (SELECT employee
					FROM `tabAttendance`
					WHERE docstatus = 1
					AND attendance_date = '{0}')
				AND date_of_joining <= '{0}'
				AND (CHAR_LENGTH(relieving_date) = 0
					OR relieving_date IS NULL
					OR relieving_date >= '{0}')""".format(
                att_date
            )
            employees = frappe.db.sql(employees, as_dict=True)

            for emp in employees:
                weekoff, _shift = weekoff_holiday(emp.get("name"), att_date)

                if not weekoff or shift.get("name") != _shift or not _shift:
                    continue

                if add_days(att_date, 1) >= getdate(system_date):
                    continue

                try:
                    mark_absent(emp.get("name"), att_date)
                    frappe.db.commit()
                    filters = {
                        "status": "Approved",
                        "docstatus": 1,
                        "applicant": emp.get("name"),
                        "ot_request_date": att_date,
                    }
                    doc_list = frappe.get_list(
                        "OT Request", filters=filters, order_by="name"
                    )
                    for k in doc_list:
                        doc_name = k["name"]
                        ot_req = frappe.get_doc("OT Request", doc_name)
                        ot_req.update_attendance(ot_req.get("ot_hours_minutes"))
                except Exception as e:
                    print(e)


def mark_absent(employee, attendance_date, shift=None):
    employee_doc = frappe.get_doc("Employee", employee)
    if not frappe.db.exists(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": attendance_date,
            "docstatus": ("!=", "2"),
        },
    ):
        doc_dict = {
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": attendance_date,
            "status": "Absent",
            "company": employee_doc.company,
            "shift": shift,
        }
        attendance = frappe.get_doc(doc_dict).insert()
        attendance.submit()
        return attendance.name
