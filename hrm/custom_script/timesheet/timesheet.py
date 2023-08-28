from __future__ import unicode_literals
import frappe
from frappe import _
# from hrms.hr.doctype.employee_checkin.employee_checkin import (
#     calculate_working_hours,
# )
from frappe.utils import flt, cint, get_datetime, add_days, getdate, formatdate

from datetime import timedelta

from hrm.hrm.doctype.ot_planner.ot_planner import applied_ot_rule
from hrm.doctype_triggers.hr.employee_checkin.employee_checkin import get_employee_shift
from hrm.custom_methods import get_leve_name
from hrm import *

import json
from frappe.model.document import Document


def validate(doc, method):
    sal_str = (
        "select * from `tabSalary Slip` where '"
        + str(doc.start_date)
        + "' >= actual_attendance_start_date and '"
        + str(doc.end_date)
        + "' <= actual_attendance_end_date and employee='"
        + doc.employee
        + "' and docstatus=1"
    )
    sal_sql = frappe.db.sql(sal_str, as_dict=True)
    if sal_sql:
        sal_doc = frappe.get_doc("Salary Slip", sal_sql[0].name)
        if sal_doc.name:
            frappe.throw("Salary has already been Processed " + sal_doc.name + "")

    att_str = (
        "select * from `tabLeave Request` where '"
        + str(doc.start_date)
        + "' >= from_date and '"
        + str(doc.end_date)
        + "' <= to_date and employee='"
        + doc.employee
        + "' and docstatus=1 and status='Approved'"
    )
    att_sql = frappe.db.sql(att_str, as_dict=True)
    if att_sql:
        att_doc = frappe.get_doc("Leave Request", att_sql[0].name)
        if att_doc.name:
            frappe.throw(
                "Cannot create Timesheet Leave applied from "
                + str(att_doc.from_date)
                + " - "
                + str(att_doc.to_date)
                + " Leave Request <a href='#Form/Leave Request/"
                + att_doc.name
                + "'>"
                + att_doc.name
                + "</a>"
            )

    app_str = (
        "select * from `tabLeave Application` where '"
        + str(doc.start_date)
        + "' >= from_date and '"
        + str(doc.end_date)
        + "' <= to_date and employee='"
        + doc.employee
        + "' and docstatus=1 and (workflow_state='Approved' or status='Approved')"
    )
    app_sql = frappe.db.sql(app_str, as_dict=True)
    if app_sql:
        app_doc = frappe.get_doc("Leave Application", app_sql[0].name)
        if app_doc.name:
            frappe.throw(
                "Cannot create Timesheet Leave applied from "
                + str(app_doc.from_date)
                + " - "
                + str(app_doc.to_date)
                + " Leave Application <a href='#Form/Leave Application/"
                + app_doc.name
                + "'>"
                + app_doc.name
                + "</a>"
            )

    vac_str = (
        "select * from `tabVacation Leave Application` where '"
        + str(doc.start_date)
        + "' >= from_date and '"
        + str(doc.end_date)
        + "' <= to_date and employee_id='"
        + doc.employee
        + "' and docstatus=1 and workflow_state='Approved'"
    )
    vac_sql = frappe.db.sql(vac_str, as_dict=True)
    if vac_sql:
        vac_doc = frappe.get_doc("Vacation Leave Application", vac_sql[0].name)
        if vac_doc.name:
            frappe.throw(
                "Cannot create Timesheet Leave applied from "
                + str(vac_doc.from_date)
                + " - "
                + str(vac_doc.to_date)
                + " Vacation Leave Application <a href='#Form/Vacation Leave Application/"
                + vac_doc.name
                + "'>"
                + vac_doc.name
                + "</a>"
            )


def on_submit(doc, method):
    if doc.workflow_state == "Approved":
        for det in doc.time_logs:
            if det.confirm_yes_no == "":
                frappe.throw("Validate Punches before Approving")
        for i in doc.time_logs:
            if i.confirm_yes_no == "Yes":
                sql = (
                    "select * from `tabEmployee Checkin` where employee='"
                    + doc.employee
                    + "' and `tabEmployee Checkin`.`time` between '"
                    + i.from_time
                    + "' and '"
                    + i.to_time
                    + "'"
                )
                str_sql = frappe.db.sql(sql, as_dict=True)
                if str_sql:
                    for empi in str_sql:
                        emp_doc = frappe.get_doc("Employee Checkin", empi.name)
                        emp_doc.delete()
                checkin_doc = frappe.new_doc("Employee Checkin")
                checkin_doc.time = i.from_time
                checkin_doc.employee = doc.employee
                checkin_doc.log_type = "IN"
                checkin_doc.timesheet_reference = doc.name
                checkin_doc.insert()
                frappe.db.commit()
                # frappe.msgprint(doc.time_logs[0].activity_type)
                checkin_doc = frappe.new_doc("Employee Checkin")
                checkin_doc.time = i.to_time
                checkin_doc.employee = doc.employee
                checkin_doc.log_type = "OUT"
                checkin_doc.timesheet_reference = doc.name
                checkin_doc.insert()
                frappe.db.commit()

        # frappe.msgprint("bye", doc.employee)
        att_str = (
            "select * from `tabAttendance` where cast(attendance_date as date) between cast('"
            + str(doc.start_date)
            + "' as date) and cast('"
            + str(doc.end_date)
            + "' as date) and employee='"
            + doc.employee
            + "' and docstatus=1"
        )
        att_sql = frappe.db.sql(att_str, as_dict=True)
        # frappe.throw(str(att_sql))
        if att_sql:
            for row in att_sql:
                att_doc = frappe.get_doc("Attendance", row.name)
                att_doc.cancel()


def on_cancel(doc, method):
    sal_str = (
        "select * from `tabSalary Slip` where '"
        + str(doc.start_date)
        + "' >= actual_attendance_start_date and '"
        + str(doc.end_date)
        + "' <= actual_attendance_end_date and employee='"
        + doc.employee
        + "' and docstatus=1"
    )
    sal_sql = frappe.db.sql(sal_str, as_dict=True)
    if sal_sql:
        sal_doc = frappe.get_doc("Salary Slip", sal_sql[0].name)
        if sal_doc.name:
            frappe.throw("Salary Slip has already been Processed " + sal_doc.name + "")

    att_str = (
        "select * from `tabAttendance` where cast(attendance_date as date) between cast('"
        + str(doc.start_date)
        + "' as date) and cast('"
        + str(doc.end_date)
        + "' as date) and employee='"
        + doc.employee
        + "' and docstatus=1"
    )
    att_sql = frappe.db.sql(att_str, as_dict=True)
    # frappe.throw(str(att_sql))
    if att_sql:
        att_doc = frappe.get_doc("Attendance", att_sql[0].name)
        att_doc.cancel()

    emp_check = (
        "select * from `tabEmployee Checkin` where timesheet_reference='"
        + doc.name
        + "'"
    )
    sql_emp = frappe.db.sql(emp_check, as_dict=True)
    if sql_emp:
        for i in sql_emp:
            emp = frappe.get_doc("Employee Checkin", i.name)
            emp.delete()


# @frappe.whitelist()
# def get_checkin(employee,start_time,end_time):
# 	sql="select * from `tabEmployee Checkin` where employee='"+employee+"' and `tabEmployee Checkin`.`time` between '"+start_time+"' and '"+end_time+"'"
# 	str_sql=frappe.db.sql(sql,as_dict=True)
# 	return str_sql


def before_save(doc, method):
    # frappe.errprint("beforesave")
    frappe.errprint(str(Document))
    get_chekin_list(doc)


@frappe.whitelist()
def get_chekin_list(doc):
    for i in doc.time_logs:
        sql = (
            "select * from `tabEmployee Checkin` where employee='"
            + doc.employee
            + "' and `tabEmployee Checkin`.`time` between '"
            + i.from_time
            + "' and '"
            + i.to_time
            + "'"
        )
        str_sql = frappe.db.sql(sql, as_dict=True)
        html_str = "<center><table style='border: 1px solid black;width:100%'><tr ><th style='border: 1px solid black;padding: 5px;text-align:center;'>Log Type</th><th style='border: 1px solid black;padding: 5px;text-align:center;'>Time</th><tr>"
        if str_sql:
            htl_str1 = ""
            for empi in str_sql:
                if htl_str1 == "":
                    htl_str1 = (
                        html_str
                        + "<tr><td style='border: 1px solid black;padding: 5px;text-align:center;'>"
                        + str(empi.log_type)
                        + "</td><td style='border: 1px solid black;padding: 5px;text-align:center;'>"
                        + str(empi.time)
                        + "</td></tr>"
                    )
                else:
                    htl_str1 = (
                        htl_str1
                        + "<tr><td style='border: 1px solid black;padding: 5px;text-align:center;'>"
                        + str(empi.log_type)
                        + "</td><td style='border: 1px solid black;padding: 5px;text-align:center;'>"
                        + str(empi.time)
                        + "</td></tr>"
                    )
            i.list_of_checkin = htl_str1 + "<table></center>"
            i.employee_check = 1
        else:
            i.employee_check = 0


@frappe.whitelist()
def set_check(employee, from_time, to_time):
    # frappe.errprint(str(doc_name)+"  "+str(doctype)+" "+str(name))
    list_of_checkin = ""
    employee_check = 0

    sql = (
        "select * from `tabEmployee Checkin` where employee='"
        + employee
        + "' and `tabEmployee Checkin`.`time` between '"
        + from_time
        + "' and '"
        + to_time
        + "'"
    )
    str_sql = frappe.db.sql(sql, as_dict=True)
    html_str = "<center><table style='border: 1px solid black;width:100%'><tr ><th style='border: 1px solid black;padding: 5px;text-align:center;'>Log Type</th><th style='border: 1px solid black;padding: 5px;text-align:center;'>Time</th><tr>"
    if str_sql:
        htl_str1 = ""
        for empi in str_sql:
            if htl_str1 == "":
                htl_str1 = (
                    html_str
                    + "<tr><td style='border: 1px solid black;padding: 5px;text-align:center;'>"
                    + str(empi.log_type)
                    + "</td><td style='border: 1px solid black;padding: 5px;text-align:center;'>"
                    + str(empi.time)
                    + "</td></tr>"
                )
            else:
                htl_str1 = (
                    htl_str1
                    + "<tr><td style='border: 1px solid black;padding: 5px;text-align:center;'>"
                    + str(empi.log_type)
                    + "</td><td style='border: 1px solid black;padding: 5px;text-align:center;'>"
                    + str(empi.time)
                    + "</td></tr>"
                )
        list_of_checkin = htl_str1 + "<table></center>"
        employee_check = 1
    else:
        employee_check = 0
    frappe.errprint(str(list_of_checkin))
    return employee_check, list_of_checkin
