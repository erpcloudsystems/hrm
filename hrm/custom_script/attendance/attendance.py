# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

# from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours
from frappe.utils import flt, cint, get_datetime, add_days, getdate, formatdate

from datetime import timedelta

from hrm.hrm.doctype.ot_planner.ot_planner import applied_ot_rule
from hrm.custom_script.employee_checkin.employee_checkin import get_employee_shift
from hrm.custom_methods import get_leve_name
from hrm import *
from hrm.custom_script.common_code import raise_link_exists_exception


def validate(doc, method):
    if validate_ss_processed(doc.employee, doc.attendance_date):
        frappe.throw(
            "Can not create or edit attendance, salary is already processed for this month"
        )
    if not doc.is_new():
        process_attendance(doc)
        # frappe.errprint(doc.ot_hours)
        # frappe.throw("AAAAAAAAAAA")


def on_trash(doc, method):
    if validate_ss_processed(doc.employee, doc.attendance_date):
        frappe.throw(
            "Can not delete attendance, salary is already processed for this month"
        )
    validate_leave_applications(doc, "Delete")


def validate_ss_processed(employee, date):
    ss_list = frappe.db.sql(
        """
			select t1.name, t1.salary_structure from `tabSalary Slip` t1
			where t1.docstatus = 1 and t1.actual_attendance_start_date <= %s and t1.actual_attendance_end_date >= %s and t1.employee = %s
		"""
        % ("%s", "%s", "%s"),
        (date, date, employee),
        as_dict=True,
    )
    # frappe.errprint(["ss",ss_list])
    if len(ss_list):
        return True
    return False


def after_insert(doc, method):
    process_attendance(doc)


def process_attendance(doc, ot_request=0, overtime_without_punch=0):
    present = frappe.db.get_value("Employee", doc.get("employee"), "default_present")
    frappe.errprint([doc.in_time, doc.in_time, "in_time"])
    weak_off(doc)
    get_ot(
        doc=doc,
        ot_request=ot_request,
        present=present,
        overtime_without_punch=overtime_without_punch,
    )
    short_time(doc)

    # reset the othours in case of absent and onleave exclude weekoff and holiday
    # frappe.errprint('{} {} or {}'.format(doc.ot_hours_minutes, (doc.get('status') == 'Absent' and not present), doc.get('leave_type') not in exclude_leave()))
    # if (doc.get('status') == 'Absent' and not present) or doc.get('leave_type') not in exclude_leave():
    # 	doc.ot_hours_minutes = 0
    # 	doc.ot_hours = 0
    # 	doc.ot_rule = None

    make_present(doc, present)
    # if doc.working_hours_time:
    # 	frappe.errprint(doc.working_hours_time<float_2_time(doc.get('working_hours') or 0.0))
    # 	if doc.get('working_hours') and doc.working_hours_time<float_2_time(doc.get('working_hours')) :
    # 		doc.working_hours_time = float_2_time(doc.get('working_hours') or 0.0)
    # else:
    # 	doc.working_hours_time = float_2_time(doc.get('working_hours') or 0.0)
    doc.working_hours_time = float2time(doc.get("working_hours") or 0.0)

    doc.ot_hours_time = float2time((doc.get("ot_hours_minutes") or 0.0) / 60)

    doc.db_update()
    doc.load_from_db()


def float2time(time):
    """Convert a float to a string containig a time"""
    time2 = int(time)
    hour = time2
    minute = round((time - time2) * 60)
    return "%02d:%02d" % (hour, minute)


def on_cancel(doc, method):
    if validate_ss_processed(doc.employee, doc.attendance_date):
        frappe.throw(
            "Can not cancel attendance, salary is already processed for this month"
        )
    validate_leave_applications(doc, "Cancel")
    if doc.get("_cancel_flag", 1) and doc.get("amended_request"):
        amend_doc = frappe.get_doc("Attendance Amendment", doc.get("amended_request"))
        if amend_doc.name:
            frappe.db.sql(
                """update `tabAttendance Amendment` set `attendance`= NULL where name='{0}'""".format(
                    amend_doc.name
                )
            )
            frappe.db.commit()
            frappe.db.sql(
                """update `tabAttendance` set `amended_request`= NULL where name='{0}'""".format(
                    doc.name
                )
            )
            frappe.db.commit()
            amend_doc.cancel()
            if amend_doc.docstatus == 2:
                amend_doc.delete()

        # frappe.throw(_("Attendance Cannot be Cancelled"))
    emp_checkin_data = frappe.db.get_list(
        "Employee Checkin", filters={"attendance": doc.name}, fields=["name"]
    )
    if emp_checkin_data:
        for d in emp_checkin_data:
            frappe.db.set_value("Employee Checkin", d.name, {"attendance": None})


def validate_leave_applications(doc, method):
    if doc.get("leave_application"):
        leave_application = frappe.get_doc(
            "Leave Application", doc.get("leave_application")
        )
        if leave_application:
            if method:
                document = "Leave Application"
                doc_name = leave_application.name
                if leave_application.leave_request:
                    document = "Leave Request"
                    doc_name = leave_application.leave_request
                elif leave_application.vacation_leave_application:
                    document = "Vacation Leave Application"
                    doc_name = leave_application.vacation_leave_application
                raise_link_exists_exception(doc, document, doc_name)


def get_ot(doc, ot_request=0, present=0, overtime_without_punch=0):
    doc.ot_hours_minutes = 0
    doc.ot_hours = 0
    doc.ot_rule = None

    ot_planner = """SELECT approved_maximum_ot_allowed_per_day, 0 AS default_ot,0 AS apply_overtime_without_any_attendance_punches
		FROM `tabOT Planner`
		WHERE docstatus = 1
		AND status = 'Approved'
		AND employee = '{0}'
		AND '{1}' BETWEEN from_date AND to_date
		
		UNION ALL
		
		SELECT ot_hours_minutes AS approved_maximum_ot_allowed_per_day, 1 AS default_ot,apply_overtime_without_any_attendance_punches
		FROM `tabOT Request`
		WHERE docstatus = 1
		AND status = 'Approved'
		AND applicant = '{0}'
		AND ot_request_date = '{1}'""".format(
        doc.get("employee"), doc.get("attendance_date")
    )
    ot_planner = frappe.db.sql(ot_planner, as_dict=True)

    if ot_request:
        ot_planner.append(
            {
                "approved_maximum_ot_allowed_per_day": ot_request,
                "default_ot": 1,
                "apply_overtime_without_any_attendance_punches": overtime_without_punch,
            }
        )

    default_ot = 0
    if ot_planner and (
        present
        or overtime_without_punch
        or (
            ot_planner[-1]
            and ot_planner[-1]["apply_overtime_without_any_attendance_punches"]
        )
        or 0
    ):
        ot_dict = ot_planner[-1]
        if ot_dict.get("default_ot"):
            default_ot = ot_dict["approved_maximum_ot_allowed_per_day"]

    attendance_details = ot_worked(
        employee=doc.get("employee"),
        attendance_date=getdate(doc.get("attendance_date")),
        doc=doc,
    )

    ot_hours = attendance_details.get("ot_hours") or default_ot
    if overtime_without_punch or (
        ot_planner and ot_planner[-1]["apply_overtime_without_any_attendance_punches"]
    ):
        ot_hours = default_ot
    ot_rule = applied_ot_rule(
        employee=doc.get("employee"), to_date=getdate(doc.get("attendance_date"))
    )
    if not ot_rule:
        return

    # if doc.get('status') != 'Present' or not ot_rule: return
    ot_hrs_min = ot_hours * 60
    ot_rule_doc = frappe.get_doc("OT Rule", ot_rule)

    if ot_hrs_min < (ot_rule_doc.get("minimum_ot_limit") or 0):
        ot_hrs_min = 0
    ot_hrs_min = abs(ot_hrs_min / (ot_rule_doc.get("ot_slab") or 1)) * (
        ot_rule_doc.get("ot_slab") or 1
    )

    if ot_hrs_min > 0:
        if not ot_planner:
            if ot_hrs_min > (ot_rule_doc.get("default_ot_allowed_in_a_day") or 0):
                if ot_rule_doc.get("violation_action") == "Violation approval required":
                    # create violation
                    return
                else:
                    ot_hrs_min = ot_rule_doc.get("default_ot_allowed_in_a_day") or 0
        else:
            ot_planner = ot_planner[-1]
            if ot_hrs_min > (
                ot_planner.get("approved_maximum_ot_allowed_per_day") or 0
            ):
                if ot_planner.get("violation_action") == "Violation approval required":
                    # create violation
                    return
                else:
                    if (
                        ot_planner.get("approved_maximum_ot_allowed_per_day") or 0
                    ) != 0:
                        ot_hrs_min = (
                            ot_planner.get("approved_maximum_ot_allowed_per_day") or 0
                        )
        import math

        doc.ot_hours_minutes = flt(math.ceil(ot_hrs_min), 0)
        doc.ot_hours = flt(round(ot_hrs_min) / 60, 2)
        doc.ot_rule = ot_rule

        if (
            doc.get("status") in ("Absent", "On Leave")
            and (doc.get("ot_hours_minutes") or 0)
            and (
                attendance_details.get("in_time") and attendance_details.get("out_time")
            )
        ):
            doc.attendance_in_punch = get_datetime(attendance_details.get("in_time"))
            doc.attendance_out_punch = get_datetime(attendance_details.get("out_time"))
            doc.custom_in_time = get_datetime(doc.attendance_in_punch).time()
            doc.custom_out_time = get_datetime(doc.attendance_out_punch).time()
        # frappe.errprint(attendance_details)
        # frappe.errprint([doc.get('working_hours') , attendance_details.get("total_working_hours")])
        if doc.get("working_hours") and doc.get("working_hours") < round(
            attendance_details.get("total_working_hours"), 2
        ):
            doc.working_hours = round(attendance_details.get("total_working_hours"), 2)
        if (
            not attendance_details.get("holiday_weekoff")
            and attendance_details.get("total_working_hours")
            and doc.status == "Present"
            and (
                overtime_without_punch
                or (
                    ot_planner
                    and ot_planner["apply_overtime_without_any_attendance_punches"]
                    and attendance_details.get("total_working_hours")
                    >= doc.working_hours
                )
            )
        ):
            add_ot_in_earlygoing_hrs(doc)
    else:
        doc.working_hours = round(attendance_details.get("total_working_hours"), 2)
    # To get Working hours as OT in case of Weakly Off
    # if doc.get('leave_type'):
    # 	doc.ot_hours = doc.get('working_hours')
    # 	doc.ot_rule = ot_rule


def ot_worked(employee, attendance_date, error=False, doc=None):
    current_shift = get_employee_shift(
        employee=employee,
        for_date=attendance_date,
        consider_default_shift=True,
        next_shift_direction="forward",
    )
    ot_rule = applied_ot_rule(employee=employee, to_date=attendance_date)

    holiday_weekoff, _shift = weekoff_holiday(employee, attendance_date)

    ot_rule_doc = frappe._dict()
    if ot_rule:
        ot_rule_doc = frappe.get_doc("OT Rule", ot_rule)

    total_working_hours, total_ot, in_time, out_time = 0, 0, None, None
    ot_start_time = get_datetime("{} {}".format(attendance_date, "00:00:00"))

    if current_shift:
        ot_start_time = current_shift.end_datetime
        frappe.errprint([ot_start_time, "ot_start_time"])
        logs = """SELECT *
			FROM `tabEmployee Checkin`
			WHERE skip_auto_attendance = 0
			AND employee = '{}'
			AND shift_start = '{}'
			AND shift_end = '{}'
			AND shift = '{}'
			ORDER BY employee, time""".format(
            employee,
            current_shift.start_datetime,
            current_shift.end_datetime,
            current_shift.shift_type.name,
        )

        logs = frappe.db.sql(logs, as_dict=True)

        if logs or (doc and doc.amended_request):
            if doc and doc.get("amended_request"):
                amend_req = """SELECT *
							FROM `tabAttendance Amendment`
							WHERE name = '{}'""".format(
                    doc.get("amended_request")
                )
                amend_req = frappe.db.sql(amend_req, as_dict=True)

                if amend_req:
                    amend_req = amend_req[0]
                    first_in_punch = get_datetime(
                        "{} {}".format(
                            doc.get("attendance_date"), amend_req.get("amended_in_time")
                        )
                    )
                    last_out_punch = get_datetime(
                        "{} {}".format(
                            doc.get("attendance_date"),
                            amend_req.get("amended_out_time"),
                        )
                    )

                    total_working_hours = time_diff_in_hours(
                        first_in_punch.replace(second=0, microsecond=0),
                        last_out_punch.replace(second=0, microsecond=0),
                    )
                    in_time = first_in_punch
                    out_time = last_out_punch
            else:
                total_working_hours, in_time, out_time = custom_calculate_working_hours(
                    logs,
                    current_shift.shift_type.determine_check_in_and_check_out,
                    current_shift.shift_type.working_hours_calculation_based_on,
                )
            # total_working_hours = (get_datetime(out_time or current_shift.end_datetime) - get_datetime(in_time or current_shift.start_datetime)).total_seconds() / 3600
            # frappe.errprint("OT DETAILS")
            # frappe.errprint(total_working_hours)
            # frappe.errprint(in_time)
            # frappe.errprint(out_time)

            if not holiday_weekoff:
                attendance = """SELECT *
					FROM `tabAttendance`
					WHERE docstatus = 1
					AND employee = '{}'
					AND attendance_date ='{}'""".format(
                    employee, attendance_date
                )
                attendance = frappe.db.sql(attendance, as_dict=True)
                if attendance and attendance[0]["name"]:
                    att_doc = frappe.get_doc("Attendance", attendance[0]["name"])
                    if att_doc.leave_type:
                        holiday_weekoff = True

            if holiday_weekoff:
                if in_time and out_time:
                    total_working_hours = (
                        out_time.replace(second=0, microsecond=0)
                        - in_time.replace(second=0, microsecond=0)
                    ).total_seconds() / 3600
                total_ot = total_working_hours

                ot_start_time = get_datetime(in_time)
            else:
                att_intime = get_datetime(
                    in_time or current_shift.start_datetime
                ).replace(second=0, microsecond=0)
                shift_intime = get_datetime(current_shift.start_datetime).replace(
                    second=0, microsecond=0
                )
                early_coming_ot = (shift_intime - att_intime).total_seconds()
                early_coming = (
                    ot_rule_doc.get("include_early_coming_ot")
                    if not ot_rule_doc.get("include_early_coming_ot") is None
                    else 1
                )
                early_coming_ot = early_coming_ot if early_coming else 0

                att_outtime = get_datetime(
                    out_time or current_shift.end_datetime
                ).replace(second=0, microsecond=0)
                shift_outime = get_datetime(current_shift.end_datetime).replace(
                    second=0, microsecond=0
                )
                late_going_ot = (att_outtime - shift_outime).total_seconds()
                late_going_ot = late_going_ot if True else 0

                total_ot = (early_coming_ot + late_going_ot) / 3600
                # frappe.errprint(_("early_coming_ot>{0} late_going_ot>{1} total_ot>{2}".format(early_coming_ot,late_going_ot,total_ot)))
                total_ot = total_ot if total_ot > 0 else 0

        elif error:
            frappe.msgprint(
                _(
                    "Employee Checkin Not Found for Employee {} within Shift {} Between {} and {}".format(
                        employee,
                        current_shift.shift_type.name,
                        current_shift.start_datetime,
                        current_shift.end_datetime,
                    )
                )
            )
    elif error:
        frappe.msgprint(
            _(
                "Shift Not Found for Employee {} in Date {}".format(
                    employee, formatdate(attendance_date)
                )
            )
        )

    return {
        "shift": current_shift,
        "ot_hours": total_ot,
        "total_working_hours": total_working_hours,
        "in_time": in_time,
        "out_time": out_time,
        "ot_start_time": ot_start_time,
        "holiday_weekoff": holiday_weekoff,
    }


def custom_calculate_working_hours(logs, check_in_out_type, working_hours_calc_type):
    """Given a set of logs in chronological order calculates the total working hours based on the parameters.
    Zero is returned for all invalid cases.

    :param logs: The List of 'Employee Checkin'.
    :param check_in_out_type: One of: 'Alternating entries as IN and OUT during the same shift', 'Strictly based on Log Type in Employee Checkin'
    :param working_hours_calc_type: One of: 'First Check-in and Last Check-out', 'Every Valid Check-in and Check-out'
    """
    total_hours = 0
    in_time = out_time = None
    if check_in_out_type == "Alternating entries as IN and OUT during the same shift":
        in_time = logs[0].time
        if len(logs) >= 2:
            out_time = logs[-1].time
        if working_hours_calc_type == "First Check-in and Last Check-out":
            # assumption in this case: First log always taken as IN, Last log always taken as OUT

            total_hours = time_diff_in_hours(
                in_time.replace(second=0, microsecond=0),
                logs[-1].time.replace(second=0, microsecond=0),
            )
        elif working_hours_calc_type == "Every Valid Check-in and Check-out":
            logs = logs[:]
            while len(logs) >= 2:
                total_hours += time_diff_in_hours(
                    logs[0].time.replace(second=0, microsecond=0),
                    logs[1].time.replace(second=0, microsecond=0),
                )
                del logs[:2]

    elif check_in_out_type == "Strictly based on Log Type in Employee Checkin":
        if working_hours_calc_type == "First Check-in and Last Check-out":
            first_in_log_index = find_index_in_dict(logs, "log_type", "IN")
            first_in_log = (
                logs[first_in_log_index]
                if first_in_log_index or first_in_log_index == 0
                else None
            )
            last_out_log_index = find_index_in_dict(reversed(logs), "log_type", "OUT")
            last_out_log = (
                logs[len(logs) - 1 - last_out_log_index]
                if last_out_log_index or last_out_log_index == 0
                else None
            )
            if first_in_log and last_out_log:
                in_time, out_time = first_in_log.time, last_out_log.time
                total_hours = time_diff_in_hours(
                    in_time.replace(second=0, microsecond=0),
                    out_time.replace(second=0, microsecond=0),
                )
        elif working_hours_calc_type == "Every Valid Check-in and Check-out":
            in_log = out_log = None
            for log in logs:
                if in_log and out_log:
                    if not in_time:
                        in_time = in_log.time
                    out_time = out_log.time
                    total_hours += time_diff_in_hours(
                        in_log.time.replace(second=0, microsecond=0),
                        out_log.time.replace(second=0, microsecond=0),
                    )
                    in_log = out_log = None
                if not in_log:
                    in_log = log if log.log_type == "IN" else None
                elif not out_log:
                    out_log = log if log.log_type == "OUT" else None
            if in_log and out_log:
                out_time = out_log.time
                total_hours += time_diff_in_hours(
                    in_log.time.replace(second=0, microsecond=0),
                    out_log.time.replace(second=0, microsecond=0),
                )
    return total_hours, in_time, out_time


def time_diff_in_hours(start, end):
    return (end - start).total_seconds() / 3600


def find_index_in_dict(dict_list, key, value):
    return next((index for (index, d) in enumerate(dict_list) if d[key] == value), None)


# def weekoff_holiday(employee, date):
# 	weak_off = """SELECT `H`.`is_weekoff`
# 		FROM `tabEmployee` AS `E`
# 		LEFT JOIN `tabShift Type` AS ST
# 			ON `E`.`default_shift` = `ST`.`name`
# 		LEFT JOIN `tabCompany` AS C
# 			ON `E`.`company` = `C`.`name`
# 		INNER JOIN `tabHoliday` AS `H`
# 			ON IF(CHAR_LENGTH(`E`.`holiday_list`) > 0
# 				, `E`.`holiday_list`
# 				, IF(CHAR_LENGTH(`ST`.`holiday_list`) > 0
# 					, `ST`.`holiday_list`
# 					, `C`.`default_holiday_list`)) = `H`.`parent`
# 		WHERE `E`.`name` = '{}'
# 		AND `H`.`holiday_date` = '{}'""".format(employee, date)

# 	return frappe.db.sql(weak_off, as_dict=True)


def weekoff_holiday(employee, date):
    current_shift = get_employee_shift(
        employee=employee,
        for_date=getdate(date),
        consider_default_shift=True,
        next_shift_direction="forward",
    )

    if current_shift:
        weak_off = """SELECT `H`.`is_weekoff`
			FROM `tabEmployee` AS `E`
			LEFT JOIN `tabShift Type` AS ST
				ON `ST`.`name` = '{2}'
			LEFT JOIN `tabCompany` AS C
				ON `E`.`company` = `C`.`name`
			INNER JOIN `tabHoliday` AS `H`
				ON IF(CHAR_LENGTH(`E`.`holiday_list`) > 0
					, `E`.`holiday_list`
					, IF(CHAR_LENGTH(`ST`.`holiday_list`) > 0
						, `ST`.`holiday_list`
						, `C`.`default_holiday_list`)) = `H`.`parent`
			WHERE `E`.`name` = '{0}'
			AND `H`.`holiday_date` = '{1}'
			union select `STE`.`is_weekoff` from `tabShift Type` AS STE   where `STE`.`name` = '{2}' and `STE`.`is_weekoff` 
			""".format(
            employee, date, current_shift.shift_type.get("name")
        )
        return frappe.db.sql(weak_off, as_dict=True), current_shift.shift_type.get(
            "name"
        )
    else:
        return [], None


def weak_off(doc):
    if doc.get("status") == "On Leave":
        return
    is_weekoff_shift = frappe.db.get_value("Shift Type", doc.get("shift"), "is_weekoff")
    weak_off, _shift = weekoff_holiday(
        doc.get("employee"), getdate(doc.get("attendance_date"))
    )
    doc.leave_type = (
        (
            get_leve_name("WO")
            if is_weekoff_shift or (weak_off[0] and weak_off[0]["is_weekoff"])
            else get_leve_name("H")
        )
        if weak_off or is_weekoff_shift
        else None
    )


def short_time(doc):
    doc.early_going_minutes = 0
    doc.late_coming_minutes = 0

    doc.actual_early_going_minutes = 0
    doc.actual_late_coming_minutes = 0

    doc.custom_in_time = "00:00:00"
    doc.custom_out_time = "00:00:00"

    if doc.get("status") != "Present" or not doc.get("shift"):
        return

    shift = """SELECT *
		FROM `tabShift Type`
		WHERE name = '{}'""".format(
        doc.get("shift")
    )
    shift = frappe.db.sql(shift, as_dict=True)
    shift = shift[0] if shift else {}

    shift_start_time = get_datetime(
        "{} {}".format(
            doc.get("attendance_date"), (shift.get("start_time") or "00:00:00")
        )
    )

    end_date = doc.get("attendance_date")
    if shift.get("start_time") >= shift.get("end_time"):
        end_date = add_days(end_date, 1)

    shift_end_time = get_datetime(
        "{} {}".format(end_date, (shift.get("end_time") or "00:00:00"))
    )

    first_in_punch = get_datetime(doc.get("attendance_in_punch"))
    if not doc.get("attendance_in_punch"):
        first_in_punch = get_datetime(
            "{} {}".format(doc.get("attendance_date"), "00:00:00")
        )

    last_out_punch = get_datetime(doc.get("attendance_out_punch"))
    if not doc.get("attendance_out_punch"):
        last_out_punch = get_datetime(
            "{} {}".format(doc.get("attendance_date"), "00:00:00")
        )

    if doc.get("amended_request"):
        amend_req = """SELECT *
			FROM `tabAttendance Amendment`
			WHERE name = '{}'""".format(
            doc.get("amended_request")
        )
        amend_req = frappe.db.sql(amend_req, as_dict=True)

        if amend_req:
            amend_req = amend_req[0]
            first_in_punch = get_datetime(
                "{} {}".format(
                    doc.get("attendance_date"), amend_req.get("amended_in_time")
                )
            )
            last_out_punch = get_datetime(
                "{} {}".format(
                    doc.get("attendance_date"), amend_req.get("amended_out_time")
                )
            )
    else:
        att_punch = """SELECT *
			FROM `tabEmployee Checkin` AS `EC`
			INNER JOIN `tabShift Type` AS `ST`
				ON `EC`.`shift` = `ST`.`name`
			WHERE `EC`.`employee` = '{0}'
			AND `EC`.`shift` = '{1}'
			AND `EC`.`shift_start` = '{2}'
			and `EC`.`shift_end` = '{3}'
			ORDER BY `EC`.`time` ASC""".format(
            doc.get("employee"), doc.get("shift"), shift_start_time, shift_end_time
        )
        att_punch = frappe.db.sql(att_punch, as_dict=True)

        if att_punch:
            first_punch = att_punch[0]
            first_in_punch = first_punch.get("time")
            last_punch = att_punch[-1]
            last_out_punch = last_punch.get("time")

    doc.attendance_in_punch = first_in_punch
    doc.attendance_out_punch = last_out_punch

    doc.custom_in_time = get_datetime(first_in_punch).time()
    doc.custom_out_time = get_datetime(last_out_punch).time()

    # Ignore Short Time in case of Weakly Off
    if doc.get("status") == "Present" and doc.get("leave_type"):
        return

    shift["start_datetime"] = shift_start_time
    shift["end_datetime"] = shift_end_time

    skip_late_comming = frappe.db.get_value(
        "Employee", doc.get("employee"), "not_to_account_late_coming"
    )

    doc.late_coming_minutes = (
        0 if skip_late_comming else late_coming(shift, first_in_punch)
    )
    doc.early_going_minutes = (
        0 if skip_late_comming else early_going(shift, last_out_punch)
    )
    doc.actual_early_going_minutes = doc.get("early_going_minutes")
    doc.actual_late_coming_minutes = doc.get("late_coming_minutes")


def add_ot_in_earlygoing_hrs(doc):
    current_shift = get_employee_shift(
        employee=doc.get("employee"),
        for_date=getdate(doc.get("attendance_date")),
        consider_default_shift=True,
        next_shift_direction="forward",
    )
    shift_outime = get_datetime(current_shift.end_datetime).replace(
        second=0, microsecond=0
    )
    if get_datetime(doc.attendance_out_punch) > shift_outime:
        doc.working_hours = (
            shift_outime - get_datetime(doc.attendance_in_punch)
        ).total_seconds() / 3600

    doc.working_hours = (doc.working_hours or 0) + (
        int(doc.get("ot_hours_minutes")) or 0
    ) / 60


def late_coming(shift, time):
    if not time or not shift:
        return 0

    time = time.replace(second=0, microsecond=0)
    shift_starttime = shift.get("start_datetime").replace(second=0, microsecond=0)
    grace_starttime = shift.get("start_datetime")
    if cint(shift.get("enable_entry_grace_period")):
        grace_starttime += timedelta(minutes=cint(shift.get("late_entry_grace_period")))

    if time > grace_starttime:
        return round((time - shift_starttime).total_seconds() / 60, 0)
    else:
        return 0


def early_going(shift, time):
    if not time or not shift:
        return 0

    time = time.replace(second=0, microsecond=0)
    shift_endtime = shift.get("end_datetime").replace(second=0, microsecond=0)
    grace_endtime = shift.get("end_datetime")
    if cint(shift.get("enable_exit_grace_period")):
        grace_endtime -= timedelta(minutes=cint(shift.get("early_exit_grace_period")))

    if time < grace_endtime:
        return round((shift_endtime - time).total_seconds() / 60, 0)
    else:
        return 0


def exclude_leave():
    return [get_leve_name(l) for l in ("WO", "H")]


def make_present(doc, present=0):
    # frappe.errprint('{} {}'.format(doc.get('leave_type') not in exclude_leave(), doc.get('status') == 'Present'))
    # frappe.errprint('{} {}'.format(doc.get('leave_type'), (doc.get('ot_hours_minutes') or 0)))
    # ignore in case of leave other then weekoff and holiday
    # if doc.get('leave_type') not in exclude_leave(): return
    # ignore in case of weekoff and holiday with no ot
    # if doc.get('leave_type') and not (doc.get('ot_hours_minutes') or 0):
    # 	# make absent weekoff if not ot
    # 	make_absent(doc)
    # 	return
    # ignore in case of present
    if doc.get("status") == "Present":
        return

    shift_up = False
    if present and doc.get("status") == "Absent" and not doc.get("leave_type"):
        shift_up = True
        doc.status = "Present"

    current_shift = get_employee_shift(
        employee=doc.get("employee"),
        for_date=getdate(doc.get("attendance_date")),
        consider_default_shift=True,
        next_shift_direction="forward",
    )
    is_weekoff_shift = False
    if current_shift and current_shift.shift_type:
        is_weekoff_shift = frappe.db.get_value(
            "Shift Type", current_shift.shift_type.get("name"), "is_weekoff"
        )
    if is_weekoff_shift:
        doc.shift = current_shift.shift_type.get("name")
        weak_off(doc)
    if current_shift and (
        shift_up
        or (
            doc.get("status") in ("Absent", "On Leave")
            and (doc.get("ot_hours_minutes") or 0)
        )
    ):
        doc.shift = current_shift.shift_type.get("name")
        if current_shift and shift_up:
            doc.attendance_in_punch = get_datetime(current_shift.start_datetime)
            doc.attendance_out_punch = get_datetime(
                current_shift.end_datetime
            ) + timedelta(minutes=int(doc.get("ot_hours_minutes") or 0))

            doc.working_hours = (
                get_datetime(doc.attendance_out_punch)
                - get_datetime(doc.attendance_in_punch)
            ).total_seconds() / 3600
            doc.custom_in_time = get_datetime(doc.attendance_in_punch).time()
            doc.custom_out_time = get_datetime(doc.attendance_out_punch).time()
            # frappe.errprint([doc.attendance_in_punch,doc.attendance_out_punch,doc.working_hours])
        else:
            doc.working_hours = doc.get("ot_hours")
    else:
        doc.shift = None
        doc.attendance_in_punch = get_datetime(
            "{} {}".format(doc.get("attendance_date"), "00:00:00")
        )
        doc.attendance_out_punch = get_datetime(
            "{} {}".format(doc.get("attendance_date"), "00:00:00")
        )
        doc.working_hours = 0
        doc.custom_in_time = "00:00:00"
        doc.custom_out_time = "00:00:00"


def make_absent(doc):
    current_shift = get_employee_shift(
        employee=doc.get("employee"),
        for_date=getdate(doc.get("attendance_date")),
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
        doc.get("employee"),
        current_shift.start_datetime,
        current_shift.end_datetime,
        current_shift.shift_type.name,
    )
    logs = frappe.db.sql(logs, as_dict=True)

    if logs:
        return

    doc.status = "Absent"
    doc.shift = None
    doc.attendance_in_punch = get_datetime(
        "{} {}".format(doc.get("attendance_date"), "00:00:00")
    )
    doc.attendance_out_punch = get_datetime(
        "{} {}".format(doc.get("attendance_date"), "00:00:00")
    )
    doc.working_hours = 0
    doc.custom_in_time = "00:00:00"
    doc.custom_out_time = "00:00:00"
