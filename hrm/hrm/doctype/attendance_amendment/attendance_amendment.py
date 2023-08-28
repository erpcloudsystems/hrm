# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, add_days
from hrms.hr.doctype.employee_checkin.employee_checkin import time_diff_in_hours


class AttendanceAmendment(Document):
    def validate(self):
        self.processed_attendance(reset=0)

    def on_submit(self):
        self.ammend_attendance()

    # def on_cancel(self):
    # 	if self.attendance:
    # 		frappe.throw(_('Application Cannot be Cancelled'))

    def processed_attendance(self, reset=1):
        att = """SELECT *
			FROM `tabAttendance`
			WHERE docstatus = 1
			AND employee = '{}'
			AND attendance_date = '{}'""".format(
            self.get("employee"), self.get("attendance_date")
        )
        att = frappe.db.sql(att, as_dict=True)
        att = att[0] if att else {}

        self.attendance = att.get("name")
        self.status = att.get("status")
        self.shift = att.get("shift")

        self.in_time, self.out_time = "00:00:00", "00:00:00"
        if att.get("name"):
            punch = """SELECT *
				FROM `tabEmployee Checkin`
				WHERE attendance = '{}'
				ORDER BY time""".format(
                att.get("name")
            )
            punch = frappe.db.sql(punch, as_dict=True)
            if punch:
                self.in_time = get_datetime(punch[0]["time"]).strftime("%H:%M:%S")
                self.out_time = get_datetime(punch[-1]["time"]).strftime("%H:%M:%S")

        if att.get("amended_request"):
            amended_att = """SELECT *
				FROM `tabAttendance Amendment`
				WHERE docstatus = 1
				AND name = '{}'""".format(
                att.get("amended_request")
            )
            amended_att = frappe.db.sql(amended_att, as_dict=True)
            if amended_att:
                self.in_time = amended_att[0]["amended_in_time"]
                self.out_time = amended_att[0]["amended_out_time"]

        if reset == 1:
            self.amended_status = self.status
            self.amended_in_time = self.in_time
            self.amended_out_time = self.out_time
            self.amended_shift = self.shift

        if not self.get("attendance"):
            frappe.throw(_("Attendance Not Proccessed"))
        else:
            if self.get("status") == "On Leave":
                frappe.throw(_("Attendance with Leave Applicaton Cannot be Amended"))

    def ammend_attendance(self):
        att_doc = frappe.get_doc("Attendance", self.get("attendance"))
        ammend_att = frappe.new_doc("Attendance")
        ammend_att.in_time = att_doc.in_time
        ammend_att.out_time = att_doc.out_time
        att_doc._cancel_flag = 0
        att_doc.cancel()

        ammend_att.employee = self.employee
        ammend_att.employee_name = self.employee_name
        ammend_att.attendance_date = self.attendance_date
        ammend_att.status = self.amended_status
        ammend_att.working_hours = self.cal_working_hrs()
        ammend_att.shift = self.amended_shift
        ammend_att.amended_request = self.name
        ammend_att.amended_from = self.get("attendance")
        ammend_att.save()
        ammend_att.submit()

    def cal_working_hrs(self):
        start_date_time = "{} {}".format(
            self.get("attendance_date"), self.get("amended_in_time")
        )

        end_date = self.get("attendance_date")
        if self.get("amended_in_time") >= self.get("amended_out_time"):
            end_date = add_days(end_date, 1)
        end_date_time = "{} {}".format(end_date, self.get("amended_out_time"))

        working_hrs = time_diff_in_hours(
            get_datetime(start_date_time), get_datetime(end_date_time)
        )

        return working_hrs if self.get("amended_status") == "Present" else 0
