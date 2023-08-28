# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate, getdate


class LateComingRequest(Document):
    def onload(self):
        if self.get("docstatus") == 0:
            self.att_application(validate=0)

    def validate(self):
        if self.is_new():
            if float(self.actual_number_of_minutes_late or 0) != 0:
                self.approved_number_of_minutes_late = (
                    self.actual_number_of_minutes_late
                )
            else:
                self.approved_number_of_minutes_late = self.number_of_minutes_late
        self.validate_duplicate()
        self.validate_date()
        self.validate_zero_value()
        self.att_application(validate=1)

        # if self.get('approved_number_of_minutes_late') > self.get('actual_number_of_minutes_late'):
        # 	frappe.throw(_("Approved Number of Minutes Late cannot be Greater then Actual Number of Minutes Late"))

    def on_submit(self):
        if self.get("approved_number_of_minutes_late") > self.get(
            "actual_number_of_minutes_late"
        ):
            frappe.throw(
                _(
                    "Approved Number of Minutes Late cannot be Greater then Actual Number of Minutes Late"
                )
            )

        if self.get("status") == "Open":
            frappe.throw(
                _(
                    "Only Late Coming Request with status 'Approved' and 'Rejected' can be submitted"
                )
            )

        short_time = self.get("actual_number_of_minutes_late")
        if self.get("status") == "Approved":
            short_time -= self.get("approved_number_of_minutes_late")
        self.update_attendance(short_time)

    def on_cancel(self):
        self.validate_date()
        self.status = "Cancelled"
        self.update_attendance(self.get("actual_number_of_minutes_late"))

    def validate_date(self):
        salary_slip = """SELECT `S`.*
			FROM `tabSalary Slip` AS `S`
			LEFT JOIN `tabPayroll Period` AS `PP`
				ON `PP`.`start_date` = `S`.`start_date`
				AND `PP`.`end_date` = `S`.`end_date`
				AND `PP`.`company` = `S`.`company`
			WHERE `S`.`docstatus` < 2
			AND `S`.`employee` = '{}'
			AND '{}' BETWEEN `PP`.`actual_start_date` and `PP`.`actual_end_date`""".format(
            self.get("employee"), self.get("attendance_date")
        )
        salary_slip = frappe.db.sql(salary_slip, as_dict=True)

        if salary_slip:
            salary_slip = salary_slip[0]
            frappe.throw(
                _(
                    "Salary Slip Already Processed for period {} and {}".format(
                        formatdate(salary_slip.get("start_date")),
                        formatdate(salary_slip.get("end_date")),
                    )
                )
            )

    def validate_duplicate(self):
        duplicate = """SELECT *
			FROM `tabLate Coming Request`
			WHERE docstatus < 2
			AND employee = '{}'
			AND attendance_date = '{}'
			AND name != '{}'""".format(
            self.get("employee"), self.get("attendance_date"), self.get("name")
        )
        duplicate = frappe.db.sql(duplicate, as_dict=True)

        if duplicate:
            frappe.throw(
                _(
                    "Employee has Already Applied for Late Coming Request for this date {}".format(
                        formatdate(self.get("attendance_date"))
                    )
                )
            )

    def validate_zero_value(self):
        meta = frappe.get_meta(self.doctype)

        for field in ["number_of_minutes_late", "approved_number_of_minutes_late"]:
            fieldname = meta.get_field(field).get("label", "")
            if self.get(field, 0) < 0:
                frappe.throw(_("{} Cannot be Less then Zero".format(fieldname)))

            if field in ["number_of_minutes_late"] and self.get(field, 0) == 0:
                frappe.throw(_("{} Should be Greater then Zero".format(fieldname)))

    def update_attendance(self, short_time):
        att_doc = frappe.get_doc("Attendance", self.get("attendance"))
        att_doc.late_coming_minutes = short_time
        att_doc.db_update()

    def att_application(self, validate):
        self.actual_number_of_minutes_late = 0
        # if self.is_new(): return

        attendance = """SELECT *
			FROM `tabAttendance`
			WHERE docstatus = 1
			AND employee = '{}'
			AND attendance_date = '{}'""".format(
            self.get("employee"), self.get("attendance_date")
        )
        attendance = frappe.db.sql(attendance, as_dict=True)
        attendance = attendance[0] if attendance else {}
        self.attendance = attendance.get("name")

        if not attendance.get("name"):
            self.employee_checkin()

            if validate and not self.is_new():
                frappe.throw(_("Attendance Not Process For this date"))
            else:
                return
        else:
            if attendance.get("status") != "Present":
                if self.get("status") == "Approved" and validate:
                    frappe.throw(_("Employee is not Present"))

                self.reason_for_late_coming = (
                    self.reason_for_late_coming or ""
                ) + " Employee is not Present"
                return

            if not attendance.get("attendance_in_punch"):
                if validate:
                    frappe.throw(_("Employee Punch Not Found"))
                else:
                    return

            self.actual_number_of_minutes_late = attendance.get("late_coming_minutes")

    def employee_checkin(self):
        from hrm.custom_script.employee_checkin.employee_checkin import (
            get_employee_shift,
        )
        from hrm.custom_script.attendance.attendance import late_coming

        current_shift = get_employee_shift(
            employee=self.get("employee"),
            for_date=getdate(self.get("attendance_date")),
            consider_default_shift=True,
            next_shift_direction="forward",
        )
        if not current_shift:
            return

        logs = """SELECT *
			FROM `tabEmployee Checkin`
			WHERE skip_auto_attendance = 0
			AND employee = '{}'
			AND shift_start = '{}'
			AND shift_end = '{}'
			AND shift = '{}'
			ORDER BY employee, time""".format(
            self.get("employee"),
            current_shift.start_datetime,
            current_shift.end_datetime,
            current_shift.shift_type.name,
        )
        logs = frappe.db.sql(logs, as_dict=True)

        if not logs:
            return

        first_punch = logs[0] if logs else {}
        first_in_punch = first_punch.get("time")
        shift = frappe._dict(
            {
                "enable_entry_grace_period": current_shift.shift_type.enable_entry_grace_period,
                "late_entry_grace_period": current_shift.shift_type.late_entry_grace_period,
                "start_datetime": current_shift.start_datetime,
            }
        )

        self.actual_number_of_minutes_late = late_coming(shift, first_in_punch)
