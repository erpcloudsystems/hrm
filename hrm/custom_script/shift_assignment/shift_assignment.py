# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from hrms.hr.doctype.shift_assignment.shift_assignment import ShiftAssignment


class CustomShiftAssignment(ShiftAssignment):
    def on_update_after_submit(self):
        from datetime import date
        from datetime import datetime

        today = date.today()
        if today >= datetime.strptime(str(self.start_date), "%Y-%m-%d").date():
            frappe.throw("Shift Assignment can not be changed for past days")
        sql = "update `tabEmployee Shift Schedule` set shift_type = '{}' where shift_assignment = '{}'".format(
            self.shift_type, self.name
        )
        frappe.db.sql(sql)
