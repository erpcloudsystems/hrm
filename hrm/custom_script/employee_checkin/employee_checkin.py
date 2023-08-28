from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import timedelta
from frappe.utils import get_datetime, now_datetime, nowdate
from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_details


def validate(doc, method):
    holiday_fetch_shift(doc)
    # if not doc.shift or doc.shift == '':
    # 	sql = """select holiday_date from `tabHoliday` WHERE holiday_date = cast(now() as date)"""
    # 	holiday_data=frappe.db.sql(sql,as_dict=True)
    # 	if not holiday_data or len(holiday_data) == 0:
    # 		frappe.throw("No Shift assigned for today. Also there is no holiday")


def holiday_fetch_shift(doc):
    shift_actual_timings = get_actual_start_end_datetime_of_shift(
        doc.employee, get_datetime(doc.time), True
    )
    if shift_actual_timings[0] and shift_actual_timings[1]:
        if not doc.attendance:
            doc.shift = shift_actual_timings[2].shift_type.name
            doc.shift_actual_start = shift_actual_timings[0]
            doc.shift_actual_end = shift_actual_timings[1]
            doc.shift_start = shift_actual_timings[2].start_datetime
            doc.shift_end = shift_actual_timings[2].end_datetime


def get_actual_start_end_datetime_of_shift(
    employee, for_datetime, consider_default_shift=False
):
    """Takes a datetime and returns the 'actual' start datetime and end datetime of the shift in which the timestamp belongs.
    Here 'actual' means - taking in to account the "begin_check_in_before_shift_start_time" and "allow_check_out_after_shift_end_time".
    None is returned if the timestamp is outside any actual shift timings.
    Shift Details is also returned(current/upcoming i.e. if timestamp not in any actual shift then details of next shift returned)
    """
    actual_shift_start = actual_shift_end = shift_details = None
    shift_timings_as_per_timestamp = get_employee_shift_timings(
        employee, for_datetime, consider_default_shift
    )
    timestamp_list = []
    for shift in shift_timings_as_per_timestamp:
        if shift:
            timestamp_list.extend([shift.actual_start, shift.actual_end])
        else:
            timestamp_list.extend([None, None])
    timestamp_index = None
    for index, timestamp in enumerate(timestamp_list):
        if timestamp and for_datetime <= timestamp:
            timestamp_index = index
            break
    if timestamp_index and timestamp_index % 2 == 1:
        shift_details = shift_timings_as_per_timestamp[int((timestamp_index - 1) / 2)]
        actual_shift_start = shift_details.actual_start
        actual_shift_end = shift_details.actual_end
    elif timestamp_index:
        shift_details = shift_timings_as_per_timestamp[int(timestamp_index / 2)]

    return actual_shift_start, actual_shift_end, shift_details


def get_employee_shift_timings(
    employee, for_timestamp=now_datetime(), consider_default_shift=False
):
    """Returns previous shift, current/upcoming shift, next_shift for the given timestamp and employee"""
    # write and verify a test case for midnight shift.
    prev_shift = curr_shift = next_shift = None
    curr_shift = get_employee_shift(
        employee, for_timestamp.date(), consider_default_shift, "forward"
    )
    if curr_shift:
        next_shift = get_employee_shift(
            employee,
            curr_shift.start_datetime.date() + timedelta(days=1),
            consider_default_shift,
            "forward",
        )
    prev_shift = get_employee_shift(
        employee,
        for_timestamp.date() + timedelta(days=-1),
        consider_default_shift,
        "reverse",
    )

    if curr_shift:
        if prev_shift:
            curr_shift.actual_start = (
                prev_shift.end_datetime
                if curr_shift.actual_start < prev_shift.end_datetime
                else curr_shift.actual_start
            )
            prev_shift.actual_end = (
                curr_shift.actual_start
                if prev_shift.actual_end > curr_shift.actual_start
                else prev_shift.actual_end
            )
        if next_shift:
            next_shift.actual_start = (
                curr_shift.end_datetime
                if next_shift.actual_start < curr_shift.end_datetime
                else next_shift.actual_start
            )
            curr_shift.actual_end = (
                next_shift.actual_start
                if curr_shift.actual_end > next_shift.actual_start
                else curr_shift.actual_end
            )
    return prev_shift, curr_shift, next_shift


def get_employee_shift(
    employee,
    for_date=nowdate(),
    consider_default_shift=False,
    next_shift_direction=None,
):
    """Returns a Shift Type for the given employee on the given date. (excluding the holidays)

    :param employee: Employee for which shift is required.
    :param for_date: Date on which shift are required
    :param consider_default_shift: If set to true, default shift is taken when no shift assignment is found.
    :param next_shift_direction: One of: None, 'forward', 'reverse'. Direction to look for next shift if shift not found on given date.
    """
    shift_type_name = ""
    default_shift = frappe.db.get_value("Employee", employee, "default_shift")
    shift_type_query = "select shift_type from `tabShift Assignment` where docstatus=1 and employee='{0}' and '{1}' between start_date and end_date".format(
        employee, for_date
    )
    shift_type_data = frappe.db.sql(shift_type_query, as_dict=True)
    if shift_type_data:
        shift_type_name = shift_type_data[0]["shift_type"]
    # frappe.errprint(['name',shift_type_name])
    # shift_type_name = frappe.db.get_value('Shift Assignment', {'employee':employee, 'date': for_date, 'docstatus': '1'}, 'shift_type')
    if not shift_type_name and consider_default_shift:
        shift_type_name = default_shift

    if not shift_type_name and next_shift_direction:
        MAX_DAYS = 366
        if consider_default_shift and default_shift:
            direction = -1 if next_shift_direction == "reverse" else +1
            for i in range(MAX_DAYS):
                date = for_date + timedelta(days=direction * (i + 1))
                shift_details = get_employee_shift(
                    employee, date, consider_default_shift, None
                )
                if shift_details:
                    shift_type_name = shift_details.shift_type.name
                    for_date = date
                    break
        else:
            direction = "<" if next_shift_direction == "reverse" else ">"
            sort_order = "desc" if next_shift_direction == "reverse" else "asc"

            # dates = frappe.db.get_all('Shift Assignment',
            # 	'date',
            # 	{'employee':employee, 'date':(direction, for_date), 'docstatus': '1'},
            # 	as_list=True,
            # 	limit=MAX_DAYS, order_by="date "+sort_order)
            dates_query = "select start_date from `tabShift Assignment` where docstatus=1 and employee='{0}' and  start_date {4} '{1}' order by start_date {2} limit {3}".format(
                employee, for_date, sort_order, MAX_DAYS, direction
            )
            dates = frappe.db.sql(dates_query, as_dict=True)
            for date in dates:
                # frappe.errprint(date)
                shift_details = get_employee_shift(
                    employee, date["start_date"], consider_default_shift, None
                )
                if shift_details:
                    shift_type_name = shift_details.shift_type.name
                    for_date = date["start_date"]
                    break

    return get_shift_details(shift_type_name, for_date)
