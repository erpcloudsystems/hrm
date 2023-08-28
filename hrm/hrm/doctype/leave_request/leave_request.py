# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import (
    cint,
    date_diff,
    flt,
    formatdate,
    getdate,
    get_fullname,
    add_days,
    nowdate,
    month_diff,
    add_months,
    add_years,
)
from hrms.hr.utils import set_employee_name, get_leave_period
from hrms.hr.doctype.leave_block_list.leave_block_list import (
    get_applicable_block_dates,
)
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import (
    create_leave_ledger_entry,
)
import datetime
import json


class LeaveDayBlockedError(frappe.ValidationError):
    pass


class OverlapError(frappe.ValidationError):
    pass


class AttendanceAlreadyMarkedError(frappe.ValidationError):
    pass


class NotAnOptionalHoliday(frappe.ValidationError):
    pass


from frappe.model.document import Document


class LeaveRequest(Document):
    def get_feed(self):
        return _("{0}: From {0} of type {1}").format(
            self.employee_name, self.leave_type
        )

    def validate(self):
        if self.validate_ss_processed(
            self.employee, self.from_date
        ) or self.validate_ss_processed(self.employee, self.to_date):
            frappe.throw(
                "Can not create or edit leave request, Salary is already processed for this month"
            )
        set_employee_name(self)
        self.validate_dates()
        self.validate_balance_leaves()
        self.validate_leave_overlap()
        self.validate_max_days()
        self.show_block_day_warning()
        self.validate_block_days()
        self.validate_salary_processed_days()
        self.validate_attendance()
        self.set_half_day_date()
        if frappe.db.get_value("Leave Type", self.leave_type, "is_optional_leave"):
            self.validate_optional_leave()
        self.validate_applicable_after()

    def on_update(self):
        if self.status == "Open" and self.docstatus < 1:
            # notify leave approver about creation
            if (
                frappe.db.get_single_value("HR Settings", "send_leave_notification")
                and self.status == "Open"
                and self.docstatus < 1
            ):
                self.notify_leave_approver()

        # share_doc_with_approver(self, self.leave_approver)

    def before_save(self):
        workflow = []
        workflow_del = frappe.db.get_value(
            "HR Settings", None, "enable_workflow_delegation"
        )
        if int(workflow_del or 0) == 1:
            emp_doc = frappe.get_doc("Employee", self.employee)
            user_role = frappe.get_roles(emp_doc.user_id)
            if emp_doc.user_id:
                if user_role:
                    for i in user_role:
                        workflow_list = frappe.get_list(
                            "Workflow Document State",
                            filters={"allow_edit": i},
                            fields=["parent", "allow_edit"],
                        )
                        if workflow_list:
                            for j in workflow_list:
                                # frappe.msgprint(str(j.allow_edit))
                                workflow.append(j.parent)
                sql = (
                    "select * from `tabWorkflow Delegation` inner join `tabWorkflow Delegation Details` on `tabWorkflow Delegation`.name = `tabWorkflow Delegation Details`.parent and `tabWorkflow Delegation Details`.workflow_doctype='"
                    + self.doctype
                    + "' where `tabWorkflow Delegation`.from_date<='"
                    + (
                        self.from_date.strftime("%m/%d/%Y")
                        if isinstance(self.from_date, datetime.datetime)
                        or isinstance(self.from_date, datetime.date)
                        else self.from_date
                    )
                    + "' and `tabWorkflow Delegation`.to_date>='"
                    + (
                        self.to_date.strftime("%m/%d/%Y")
                        if isinstance(self.to_date, datetime.datetime)
                        or isinstance(self.to_date, datetime.date)
                        else self.to_date
                    )
                    + "' and `tabWorkflow Delegation`.employee='"
                    + self.employee
                    + "'"
                )
                work_sql = frappe.db.sql(sql, as_dict=1)
                if (
                    len(work_sql) == 0
                    and self.doctype == "Leave Request"
                    and self.ignore_workflow_delegation == 0
                    and self.workflow_delegation_id == None
                    and self.status == "Open"
                ):
                    self.flags.ignore_on_update = True
                    frappe.msgprint("Please Make <b>Workflow Delegation</b>")

    def before_cancel(self):
        if self.validate_ss_processed(
            self.employee, self.from_date
        ) or self.validate_ss_processed(self.employee, self.to_date):
            frappe.throw(
                "Can not cancel leave request, Salary is already processed for this month"
            )

        if self.workflow_delegation_id:
            wf_doc = frappe.get_doc("Workflow Delegation", self.workflow_delegation_id)
            wf_id = wf_doc.reference_id
            if wf_doc.docstatus == 1:
                wf_doc.reference_id = None
                wf_doc.cancel()
                # wf_doc.reference_id = wf_id
                frappe.db.sql(
                    "UPDATE `tabWorkflow Delegation` SET reference_id ='{0}' where name ='{1}' ".format(
                        wf_id, self.workflow_delegation_id
                    )
                )
            else:
                wf_doc.reference_id = ""
                wf_doc.db_update()
                wf_doc.delete()

    def validate_ss_processed(self, employee, date):
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

    def before_submit(self):
        workflow = []
        workflow_del = frappe.db.get_value(
            "HR Settings", None, "enable_workflow_delegation"
        )
        if int(workflow_del or 0) == 1:
            emp_doc = frappe.get_doc("Employee", self.employee)
            user_role = frappe.get_roles(emp_doc.user_id)
            if user_role:
                for i in user_role:
                    workflow_list = frappe.get_list(
                        "Workflow Document State",
                        filters={"allow_edit": i},
                        fields=["parent", "allow_edit"],
                    )
                    # frappe.errprint(str(workflow_list))
                    if workflow_list:
                        for j in workflow_list:
                            # frappe.msgprint(str(j.allow_edit))
                            workflow.append(j.parent)
            sql = (
                "select * from `tabWorkflow Delegation` inner join `tabWorkflow Delegation Details` on `tabWorkflow Delegation`.name = `tabWorkflow Delegation Details`.parent and `tabWorkflow Delegation Details`.workflow_doctype='"
                + self.doctype
                + "' where `tabWorkflow Delegation`.from_date<='"
                + (
                    self.from_date.strftime("%m/%d/%Y")
                    if isinstance(self.from_date, datetime.datetime)
                    or isinstance(self.from_date, datetime.date)
                    else self.from_date
                )
                + "' and `tabWorkflow Delegation`.to_date>='"
                + (
                    self.to_date.strftime("%m/%d/%Y")
                    if isinstance(self.to_date, datetime.datetime)
                    or isinstance(self.to_date, datetime.date)
                    else self.to_date
                )
                + "' and `tabWorkflow Delegation`.employee='"
                + self.employee
                + "' and `tabWorkflow Delegation`.docstatus=1"
            )
            work_sql = frappe.db.sql(sql, as_dict=1)
            if (
                len(work_sql) == 0
                and self.doctype == "Leave Request"
                and self.workflow_delegation_id == None
                and self.ignore_workflow_delegation == 0
                and self.status == "Approved"
            ):
                self.flags.ignore_validate = True
                self.flags.ignore_on_update = True
                frappe.throw("Please Make <b>Workflow Delegation</b>")
            else:
                self.run_method("on_update")

    def on_submit(self):
        if self.status == "Open":
            frappe.throw(
                _(
                    "Only Leave Request with status 'Approved' and 'Rejected' can be submitted"
                )
            )

        self.validate_back_dated_application()
        if self.status == "Approved":
            self.leave_allocation()
            self.insert_in_leav_appl()
        self.update_attendance()

        # notify leave applier about approval
        if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
            self.notify_employee()
        self.create_leave_ledger_entry()
        self.reload()

    def insert_in_leav_appl(self):
        doc = frappe.new_doc("Leave Application")
        doc.employee = self.employee
        doc.company = self.company
        doc.leave_type = self.leave_type
        doc.leave_request = self.name
        doc.posting_date = self.posting_date
        doc.status = self.status
        doc.description = self.description
        doc.from_date = self.from_date
        doc.to_date = self.to_date
        doc.half_day = self.half_day
        doc.half_day_date = self.half_day_date
        doc.total_leave_days = self.total_leave_days
        doc.leave_approver = self.leave_approver
        doc.ignore_workflow_delegation = 1

        # doc.insert(ignore_permissions=True)
        doc.flags.ignore_permissions = True
        doc.save()
        doc.submit()

        state = {"Approved": "Approve", "Rejected": "Reject"}
        leave_sql = frappe.db.sql(
            "select * from `tabWorkflow` where document_type='Leave Application' and is_active=1"
        )
        if leave_sql:
            while True:
                # frappe.errprint(state.get(self.status))
                apply_workflow(doc, state.get(self.status))
                if doc.docstatus == 1:
                    break

    def leave_allocation(self):
        if frappe.db.get_value("Leave Type", self.leave_type, "allow_negative"):
            return
        # leave for 1 day

        adjust_day = 1 if getdate(self.from_date) == getdate(self.to_date) else 0

        ledg = frappe.new_doc("Leave Allocation")

        ledg.employee = self.employee
        ledg.leave_type = self.leave_type
        ledg.from_date = self.from_date
        ledg.to_date = add_days(self.to_date, adjust_day)
        ledg.new_leaves_allocated = self.total_leave_days

        # ledg.insert()
        ledg.flags.ignore_permissions = True
        ledg.submit()

    def before_cancel(self):
        self.status = "Cancelled"

    def on_cancel(self):
        self.create_leave_ledger_entry(submit=False)
        # notify leave applier about cancellation
        if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
            self.notify_employee()
        self.cancel_attendance()
        self.remove_leave_application(status=1)
        self.remove_allocation(status=1)

    def on_trash(self):
        if self.validate_ss_processed(
            self.employee, self.from_date
        ) or self.validate_ss_processed(self.employee, self.to_date):
            frappe.throw(
                "Can not delete leave request, Salary is already processed for this month"
            )
        self.remove_leave_application(status=2)
        self.remove_allocation(status=2)
        self.delete_wf()

    def remove_allocation(self, status):
        # leave for 1 day
        adjust_day = 1 if getdate(self.from_date) == getdate(self.to_date) else 0

        remo_sql = """SELECT name, docstatus
			FROM `tabLeave Allocation`
			WHERE leave_type = '{0}'
			AND employee = '{1}'
			AND from_date = '{2}'
			AND to_date = '{3}'
			AND docstatus = {4}""".format(
            self.leave_type,
            self.employee,
            self.from_date,
            add_days(self.to_date, adjust_day),
            status,
        )
        data = frappe.db.sql(remo_sql, as_dict=True)

        for i in data:
            name = i["name"]
            d_status = i["docstatus"]
            doc = frappe.get_doc("Leave Allocation", name)
            if d_status == 1 and status == 1:
                doc.cancel()
            else:
                if d_status == 1:
                    doc.cancel()
                doc.delete()

    def remove_leave_application(self, status):
        sql = "select name, docstatus from `tabLeave Application` where leave_request = '{0}'".format(
            self.name
        )
        data = frappe.db.sql(sql, as_dict=True)

        for i in data:
            name = i["name"]
            d_status = i["docstatus"]
            doc = frappe.get_doc("Leave Application", name)
            doc.leave_request = None
            if d_status == 1 and status == 1:
                # doc.cancel()
                # doc.leave_request = self.name
                # doc.workflow_state = self.workflow_state
                # doc.db_update()
                state = {
                    "Approved": "Approve",
                    "Rejected": "Reject",
                    "Cancelled": "Cancel",
                }
                leave_sql = frappe.db.sql(
                    "select * from `tabWorkflow` where document_type='Leave Application'  and is_active=1"
                )
                if leave_sql:
                    while True:
                        apply_workflow(doc, state.get(self.status))
                        if doc.docstatus == 2:
                            break
                else:
                    doc.cancel()
                doc.leave_request = self.name
                # doc.workflow_state = self.workflow_state
                doc.db_update()
            else:
                doc.db_update()
                if d_status == 1:
                    doc.cancel()
                doc.delete()

    def delete_wf(self):
        # if doc.workflow_delegation_id:
        wd_list = "select name from `tabWorkflow Delegation` where reference_id='{0}' order by name desc".format(
            self.name
        )
        wd_list_data = frappe.db.sql(wd_list, as_dict=True)
        if wd_list_data:
            for w in wd_list_data:
                # frappe.msgprint(str(w.name))
                wf_doc = frappe.get_doc("Workflow Delegation", w.name)
                wf_id = wf_doc.reference_id
                wf_doc.reference_id = None
                if wf_doc.docstatus == 1:
                    wf_doc.cancel()
                    wf_doc.delete()
                else:
                    # frappe.throw(str(wf_doc.reference_id))
                    wf_doc.reference_id = ""
                    wf_doc.db_update()
                    wf_doc.delete()

    def validate_applicable_after(self):
        if self.leave_type:
            leave_type = frappe.get_doc("Leave Type", self.leave_type)
            if leave_type.applicable_after > 0:
                date_of_joining = frappe.db.get_value(
                    "Employee", self.employee, "date_of_joining"
                )
                leave_days = get_approved_leaves_for_period(
                    self.employee, False, date_of_joining, self.from_date
                )
                number_of_days = date_diff(getdate(self.from_date), date_of_joining)
                if number_of_days >= 0:
                    holidays = 0
                    if not frappe.db.get_value(
                        "Leave Type", self.leave_type, "include_holiday"
                    ):
                        holidays = get_holidays(
                            self.employee, date_of_joining, self.from_date
                        )
                    number_of_days = number_of_days - leave_days - holidays
                    if number_of_days < leave_type.applicable_after:
                        frappe.throw(
                            _("{0} applicable after {1} working days").format(
                                self.leave_type, leave_type.applicable_after
                            )
                        )

    def validate_dates(self):
        if frappe.db.get_single_value(
            "HR Settings", "restrict_backdated_leave_application"
        ):
            if self.from_date and self.from_date < frappe.utils.today():
                allowed_role = frappe.db.get_single_value(
                    "HR Settings", "role_allowed_to_create_backdated_leave_application"
                )
                if allowed_role not in frappe.get_roles():
                    frappe.throw(
                        _(
                            "Only users with the {0} role can create backdated leave request"
                        ).format(allowed_role)
                    )

        if (
            self.from_date
            and self.to_date
            and (getdate(self.to_date) < getdate(self.from_date))
        ):
            frappe.throw(_("To date cannot be before from date"))

        if (
            self.half_day
            and self.half_day_date
            and (
                getdate(self.half_day_date) < getdate(self.from_date)
                or getdate(self.half_day_date) > getdate(self.to_date)
            )
        ):
            frappe.throw(_("Half Day Date should be between From Date and To Date"))

        if not is_lwp(self.leave_type):
            self.validate_dates_across_allocation()
            self.validate_back_dated_application()

    def validate_dates_across_allocation(self):
        if frappe.db.get_value("Leave Type", self.leave_type, "allow_negative"):
            return

        def _get_leave_allocation_record(date):
            allocation = frappe.db.sql(
                """select name from `tabLeave Allocation`
				where employee=%s and leave_type=%s and docstatus=1
				and %s between from_date and to_date""",
                (self.employee, self.leave_type, date),
            )

            return allocation and allocation[0][0]

        allocation_based_on_from_date = _get_leave_allocation_record(self.from_date)
        allocation_based_on_to_date = _get_leave_allocation_record(self.to_date)

        if not (allocation_based_on_from_date or allocation_based_on_to_date):
            frappe.throw(
                _("Application period cannot be outside leave allocation period")
            )

        elif allocation_based_on_from_date != allocation_based_on_to_date:
            frappe.throw(
                _("Application period cannot be across two allocation records")
            )

    def validate_back_dated_application(self):
        future_allocation = frappe.db.sql(
            """select name, from_date from `tabLeave Allocation`
			where employee=%s and leave_type=%s and docstatus=1 and from_date > %s
			and carry_forward=1""",
            (self.employee, self.leave_type, self.to_date),
            as_dict=1,
        )

        if future_allocation:
            frappe.throw(
                _(
                    "Leave cannot be applied/cancelled before {0}, as leave balance has already been carry-forwarded in the future leave allocation record {1}"
                ).format(
                    formatdate(future_allocation[0].from_date),
                    future_allocation[0].name,
                )
            )

    def update_attendance(self):
        if self.status == "Approved":
            for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
                date = dt.strftime("%Y-%m-%d")
                status = (
                    "Half Day"
                    if self.half_day_date
                    and getdate(date) == getdate(self.half_day_date)
                    else "On Leave"
                )
                attendance_name = frappe.db.exists(
                    "Attendance",
                    dict(
                        employee=self.employee,
                        attendance_date=date,
                        docstatus=("!=", 2),
                    ),
                )

                if attendance_name:
                    # update existing attendance, change absent to on leave
                    doc = frappe.get_doc("Attendance", attendance_name)
                    if doc.status != status:
                        doc.db_set("status", status)
                        doc.db_set("leave_type", self.leave_type)
                        doc.db_set("leave_application", self.name)
                else:
                    # make new attendance and submit it

                    doc = frappe.new_doc("Attendance")
                    doc.employee = self.employee
                    doc.employee_name = self.employee_name
                    doc.attendance_date = date
                    doc.company = self.company
                    doc.leave_type = self.leave_type
                    doc.leave_application = self.name
                    doc.status = status
                    doc.flags.ignore_validate = True
                    doc.insert(ignore_permissions=True)
                    doc.submit()

    def cancel_attendance(self):
        if self.docstatus == 2:
            attendance = frappe.db.sql(
                """select name from `tabAttendance` where employee = %s\
				and (attendance_date between %s and %s) and docstatus < 2 and status in ('On Leave', 'Half Day')""",
                (self.employee, self.from_date, self.to_date),
                as_dict=1,
            )
            for name in attendance:
                frappe.db.set_value("Attendance", name, "docstatus", 2)

    def validate_salary_processed_days(self):
        if not frappe.db.get_value("Leave Type", self.leave_type, "is_lwp"):
            return

        last_processed_pay_slip = frappe.db.sql(
            """
			select start_date, end_date from `tabSalary Slip`
			where docstatus = 1 and employee = %s
			and ((%s between start_date and end_date) or (%s between start_date and end_date))
			order by modified desc limit 1
		""",
            (self.employee, self.to_date, self.from_date),
        )

        if last_processed_pay_slip:
            frappe.throw(
                _(
                    "Salary already processed for period between {0} and {1}, Leave request period cannot be between this date range."
                ).format(
                    formatdate(last_processed_pay_slip[0][0]),
                    formatdate(last_processed_pay_slip[0][1]),
                )
            )

    def show_block_day_warning(self):
        block_dates = get_applicable_block_dates(
            self.from_date, self.to_date, self.employee, self.company, all_lists=True
        )

        if block_dates:
            frappe.msgprint(
                _("Warning: Leave request contains following block dates") + ":"
            )
            for d in block_dates:
                frappe.msgprint(formatdate(d.block_date) + ": " + d.reason)

    def validate_block_days(self):
        block_dates = get_applicable_block_dates(
            self.from_date, self.to_date, self.employee, self.company
        )

        if block_dates and self.status == "Approved":
            frappe.throw(
                _("You are not authorized to approve leaves on Block Dates"),
                LeaveDayBlockedError,
            )

    def compenstation_percent(self, leave_rule, joining_date, leave_taken, reset=1):
        compansation = compenstation_percent(
            leave_rule=leave_rule,
            from_date=self.from_date,
            to_date=self.to_date,
            joining_date=joining_date,
            total_leave_days=self.total_leave_days,
            leave_taken=leave_taken,
        )

        idx_row = 1
        for row in self.get("salary_days_compensation"):
            comp = compansation.get(row.get("eligible_compensation"))
            if comp:
                row.idx = idx_row
                row.set("days", len(comp))
                row.set("from_date", comp[0])
                row.set("to_date", comp[-1])
                row.set("leave_rule", leave_rule.get("name"))
                idx_row += 1
                del compansation[row.get("eligible_compensation")]
            else:
                self.salary_days_compensation.remove(row)

        for key in compansation.keys():
            self.append(
                "salary_days_compensation",
                {
                    "days": len(compansation[key]),
                    "eligible_compensation": key,
                    "approved_compensation": key,
                    "from_date": compansation[key][0],
                    "to_date": compansation[key][-1],
                    "leave_rule": leave_rule.get("name"),
                },
            )

    def validate_balance_leaves(self):
        if self.from_date and self.to_date:
            self.total_leave_days = get_number_of_leave_days(
                self.employee,
                self.leave_type,
                self.from_date,
                self.to_date,
                self.half_day,
                self.half_day_date,
            )

            if self.total_leave_days <= 0:
                frappe.throw(
                    _(
                        "The day(s) on which you are applying for leave are holidays. You need not apply for leave."
                    )
                )

            self.leave_balance = 0
            self.get_leave_balance_on(attachment=1)
            if self.status != "Rejected" and (
                self.leave_balance < self.total_leave_days or not self.leave_balance
            ):
                # if not frappe.db.get_value("Leave Type", self.leave_type, "allow_negative"):
                if not frappe.db.get_value(
                    "Leave Type", self.leave_type, "unlimited_leaves_allowed"
                ):
                    frappe.throw(
                        _(
                            "There is not enough leave balance for Leave Type {0}"
                        ).format(self.leave_type)
                    )

    def validate_leave_overlap(self):
        if not self.name:
            # hack! if name is null, it could cause problems with !=
            self.name = "New Leave Application"

        for d in frappe.db.sql(
            """
			select
				name, leave_type, posting_date, from_date, to_date, total_leave_days, half_day_date
			from `tabLeave Application`
			where employee = %(employee)s and docstatus < 2 and status in ("Open", "Approved")
			and to_date >= %(from_date)s and from_date <= %(to_date)s
			and name != %(name)s""",
            {
                "employee": self.employee,
                "from_date": self.from_date,
                "to_date": self.to_date,
                "name": self.name,
            },
            as_dict=1,
        ):
            if (
                cint(self.half_day) == 1
                and getdate(self.half_day_date) == getdate(d.half_day_date)
                and (
                    flt(self.total_leave_days) == 0.5
                    or getdate(self.from_date) == getdate(d.to_date)
                    or getdate(self.to_date) == getdate(d.from_date)
                )
            ):
                total_leaves_on_half_day = self.get_total_leaves_on_half_day()
                if total_leaves_on_half_day >= 1:
                    self.throw_overlap_error(d)
            else:
                self.throw_overlap_error(d)

    def throw_overlap_error(self, d):
        msg = _(
            "Employee {0} has already applied for {1} between {2} and {3} : "
        ).format(
            self.employee,
            d["leave_type"],
            formatdate(d["from_date"]),
            formatdate(d["to_date"]),
        ) + """ <b><a href="/app/Form/Leave Application/{0}">{0}</a></b>""".format(
            d["name"]
        )
        frappe.throw(msg, OverlapError)

    def get_total_leaves_on_half_day(self):
        leave_count_on_half_day_date = frappe.db.sql(
            """select count(name) from `tabLeave Application`
			where employee = %(employee)s
			and docstatus < 2
			and status in ("Open", "Approved")
			and half_day = 1
			and half_day_date = %(half_day_date)s
			and name != %(name)s""",
            {
                "employee": self.employee,
                "half_day_date": self.half_day_date,
                "name": self.name,
            },
        )[0][0]

        return leave_count_on_half_day_date * 0.5

    def validate_max_days(self):
        max_days = frappe.db.get_value(
            "Leave Type", self.leave_type, "max_continuous_days_allowed"
        )
        if max_days and self.total_leave_days > cint(max_days):
            frappe.throw(
                _("Leave of type {0} cannot be longer than {1}").format(
                    self.leave_type, max_days
                )
            )

    def validate_attendance(self):
        attendance = frappe.db.sql(
            """select name from `tabAttendance` where employee = %s and (attendance_date between %s and %s)
					and status = "Present" and docstatus = 1""",
            (self.employee, self.from_date, self.to_date),
        )
        if attendance:
            frappe.throw(
                _("Attendance for employee {0} is already marked for this day").format(
                    self.employee
                ),
                AttendanceAlreadyMarkedError,
            )

    def validate_optional_leave(self):
        leave_period = get_leave_period(self.from_date, self.to_date, self.company)
        if not leave_period:
            frappe.throw(_("Cannot find active Leave Period"))
        optional_holiday_list = frappe.db.get_value(
            "Leave Period", leave_period[0]["name"], "optional_holiday_list"
        )
        if not optional_holiday_list:
            frappe.throw(
                _("Optional Holiday List not set for leave period {0}").format(
                    leave_period[0]["name"]
                )
            )
        day = getdate(self.from_date)
        while day <= getdate(self.to_date):
            if not frappe.db.exists(
                {
                    "doctype": "Holiday",
                    "parent": optional_holiday_list,
                    "holiday_date": day,
                }
            ):
                frappe.throw(
                    _("{0} is not in Optional Holiday List").format(formatdate(day)),
                    NotAnOptionalHoliday,
                )
            day = add_days(day, 1)

    def set_half_day_date(self):
        if self.from_date == self.to_date and self.half_day == 1:
            self.half_day_date = self.from_date

        if self.half_day == 0:
            self.half_day_date = None

    def notify_employee(self):
        employee = frappe.get_doc("Employee", self.employee)
        if not employee.user_id:
            return

        parent_doc = frappe.get_doc("Leave Request", self.name)
        args = parent_doc.as_dict()

        template = frappe.db.get_single_value(
            "HR Settings", "leave_status_notification_template"
        )
        if not template:
            frappe.msgprint(
                _(
                    "Please set default template for Leave Status Notification in HR Settings."
                )
            )
            return
        email_template = frappe.get_doc("Email Template", template)
        message = frappe.render_template(email_template.response, args)

        self.notify(
            {
                # for post in messages
                "message": message,
                "message_to": employee.user_id,
                # for email
                "subject": email_template.subject,
                "notify": "employee",
            }
        )

    def notify_leave_approver(self):
        if self.leave_approver:
            parent_doc = frappe.get_doc("Leave Request", self.name)
            args = parent_doc.as_dict()

            template = frappe.db.get_single_value(
                "HR Settings", "leave_approval_notification_template"
            )
            if not template:
                frappe.msgprint(
                    _(
                        "Please set default template for Leave Approval Notification in HR Settings."
                    )
                )
                return
            email_template = frappe.get_doc("Email Template", template)
            message = frappe.render_template(email_template.response, args)

            self.notify(
                {
                    # for post in messages
                    "message": message,
                    "message_to": self.leave_approver,
                    # for email
                    "subject": email_template.subject,
                }
            )

    def notify(self, args):
        args = frappe._dict(args)
        # args -> message, message_to, subject
        if cint(self.follow_via_email):
            contact = args.message_to
            if not isinstance(contact, list):
                if not args.notify == "employee":
                    contact = frappe.get_doc("User", contact).email or contact

            sender = dict()
            sender["email"] = frappe.get_doc("User", frappe.session.user).email
            sender["full_name"] = frappe.utils.get_fullname(sender["email"])

            try:
                frappe.sendmail(
                    recipients=contact,
                    sender=sender["email"],
                    subject=args.subject,
                    message=args.message,
                )
                frappe.msgprint(_("Email sent to {0}").format(contact))
            except frappe.OutgoingEmailError:
                pass

    def create_leave_ledger_entry(self, submit=True):
        if self.status != "Approved" and submit:
            return

        expiry_date = get_allocation_expiry(
            self.employee, self.leave_type, self.to_date, self.from_date
        )

        lwp = frappe.db.get_value("Leave Type", self.leave_type, "is_lwp")

        if expiry_date:
            self.create_ledger_entry_for_intermediate_allocation_expiry(
                expiry_date, submit, lwp
            )
        else:
            raise_exception = True
            if frappe.flags.in_patch:
                raise_exception = False

            args = dict(
                leaves=self.total_leave_days * -1,
                from_date=self.from_date,
                to_date=self.to_date,
                is_lwp=lwp,
                holiday_list=get_holiday_list_for_employee(
                    self.employee, raise_exception=raise_exception
                )
                or "",
            )
            create_leave_ledger_entry(self, args, submit)

    def create_ledger_entry_for_intermediate_allocation_expiry(
        self, expiry_date, submit, lwp
    ):
        """splits leave application into two ledger entries to consider expiry of allocation"""

        raise_exception = True
        if frappe.flags.in_patch:
            raise_exception = False

        args = dict(
            from_date=self.from_date,
            to_date=expiry_date,
            leaves=(date_diff(expiry_date, self.from_date) + 1) * -1,
            is_lwp=lwp,
            holiday_list=get_holiday_list_for_employee(
                self.employee, raise_exception=raise_exception
            )
            or "",
        )
        create_leave_ledger_entry(self, args, submit)

        if getdate(expiry_date) != getdate(self.to_date):
            start_date = add_days(expiry_date, 1)
            args.update(
                dict(
                    from_date=start_date,
                    to_date=self.to_date,
                    leaves=date_diff(self.to_date, expiry_date) * -1,
                )
            )
            create_leave_ledger_entry(self, args, submit)

    def validate_attachment(self):
        for row in self.get("attach_document"):
            if not row.get("attachment"):
                frappe.throw(_("{} Attachment Required".format(row.get("document"))))

    def find_attachment_required(self, leave_rule):
        attachment = (
            """SELECT document FROM `tabChecklist` WHERE parent = '{}'""".format(
                leave_rule.get("name")
            )
        )
        attachment = frappe.db.sql_list(attachment)

        idx_row = 1
        for row in self.get("attach_document"):
            row.idx = idx_row
            if row.get("document") in attachment:
                idx_row += 1
                attachment.remove(row.get("document"))
            else:
                self.attach_document.remove(row)

        for val in attachment:
            self.append("attach_document", {"document": val})

    def validate_pecentage(self):
        for row in self.get("salary_days_compensation"):
            if not 0 <= row.get("approved_compensation") <= 100:
                frappe.throw(
                    _(
                        "Percentage of Compensation should be between 0 to 100 at Row {}".format(
                            row.get("idx")
                        )
                    )
                )

    @frappe.whitelist()
    def get_leave_balance_on(self, attachment=0):
        # self = json.loads(self)

        # self.total_leave_days = date_diff(getdate(self.to_date), getdate(self.from_date)) + 1
        if self.employee and self.leave_type:
            applicant_gender, date_of_joining = frappe.db.get_value(
                "Employee", self.employee, ["gender", "date_of_joining"]
            )

            leave_rule = get_leave_rule(
                date=(self.from_date or nowdate()), leave_type=self.leave_type
            )
            if not leave_rule:
                return
            leave_rule = leave_rule[0]

            if (
                leave_rule.get("gender")
                and leave_rule.get("gender") != applicant_gender
            ):
                frappe.throw(
                    _(
                        "Applicant Gender Should be {} for Leave Type {}".format(
                            leave_rule.get("gender"), self.leave_type
                        )
                    )
                )

            if leave_rule.get("applicable_after_days", 0) > 0:
                applicable_date = add_days(
                    date_of_joining, leave_rule.get("applicable_after_days")
                )

                if applicable_date > getdate(self.from_date):
                    frappe.throw(
                        _(
                            "Employee {} cannot apply before {} for Leave Type {}".format(
                                self.employee,
                                formatdate(applicable_date),
                                self.leave_type,
                            )
                        )
                    )

            self.find_attachment_required(leave_rule)

            if attachment == 1:
                self.validate_attachment()

            leave_taken = get_leaves_for_period(
                self.employee, self.leave_type, self.from_date, leave_rule
            )
            pending_leave = leave_rule.get("max_leaves_allowed", 0) - leave_taken
            self.leave_balance = pending_leave if pending_leave > 0 else 0
            self.compenstation_percent(
                leave_rule=leave_rule,
                joining_date=date_of_joining,
                leave_taken=leave_taken,
                reset=0,
            )


def get_allocation_expiry(employee, leave_type, to_date, from_date):
    """Returns expiry of carry forward allocation in leave ledger entry"""
    expiry = frappe.get_all(
        "Leave Ledger Entry",
        filters={
            "employee": employee,
            "leave_type": leave_type,
            "is_carry_forward": 1,
            "transaction_type": "Leave Allocation",
            "to_date": ["between", (from_date, to_date)],
        },
        fields=["to_date"],
    )
    return expiry[0]["to_date"] if expiry else None


@frappe.whitelist()
def get_number_of_leave_days(
    employee,
    leave_type,
    from_date,
    to_date,
    half_day=None,
    half_day_date=None,
    holiday_list=None,
):
    number_of_days = 0
    if cint(half_day) == 1:
        if from_date == to_date:
            number_of_days = 0.5
        elif half_day_date and half_day_date <= to_date:
            number_of_days = date_diff(to_date, from_date) + 0.5
        else:
            number_of_days = date_diff(to_date, from_date) + 1

    else:
        number_of_days = date_diff(to_date, from_date) + 1

    if not frappe.db.get_value("Leave Type", leave_type, "include_holiday"):
        number_of_days = flt(number_of_days) - flt(
            get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
        )
    return number_of_days


@frappe.whitelist()
def get_leave_details(employee, date):
    allocation_records = get_leave_allocation_records(employee, date)
    leave_allocation = {}
    for d in allocation_records:
        allocation = allocation_records.get(d, frappe._dict())

        total_allocated_leaves = (
            frappe.db.get_value(
                "Leave Allocation",
                {
                    "from_date": ("<=", date),
                    "to_date": (">=", date),
                    "employee": employee,
                    "leave_type": allocation.leave_type,
                },
                "SUM(total_leaves_allocated)",
            )
            or 0
        )

        remaining_leaves = get_leave_balance_on(
            employee,
            d,
            date,
            to_date=allocation.to_date,
            consider_all_leaves_in_the_allocation_period=True,
        )

        end_date = allocation.to_date
        leaves_taken = (
            get_leaves_for_period(employee, d, allocation.from_date, end_date) * -1
        )
        leaves_pending = get_pending_leaves_for_period(
            employee, d, allocation.from_date, end_date
        )

        leave_allocation[d] = {
            "total_leaves": total_allocated_leaves,
            "expired_leaves": total_allocated_leaves
            - (remaining_leaves + leaves_taken),
            "leaves_taken": leaves_taken,
            "pending_leaves": leaves_pending,
            "remaining_leaves": remaining_leaves,
        }

    # is used in set query
    lwps = frappe.get_list("Leave Type", filters={"is_lwp": 1})

    lwps = [lwp.name for lwp in lwps]

    ret = {
        "leave_allocation": leave_allocation,
        "leave_approver": get_leave_approver(employee),
        "lwps": lwps,
    }

    return ret


@frappe.whitelist()
def get_workflow_delegation(employee, from_date, to_date, doctype):
    sql = (
        "select * from `tabWorkflow Delegation` inner join `tabWorkflow Delegation Details` on `tabWorkflow Delegation`.name = `tabWorkflow Delegation Details`.parent and `tabWorkflow Delegation Details`.workflow_doctype='"
        + doctype
        + "' where `tabWorkflow Delegation`.from_date<='"
        + from_date
        + "' and `tabWorkflow Delegation`.to_date>='"
        + to_date
        + "' and `tabWorkflow Delegation`.employee='"
        + employee
        + "' and `tabWorkflow Delegation`.docstatus=1"
    )
    work_sql = frappe.db.sql(sql, as_dict=1)
    # frappe.errprint(str(len(work_sql)))
    str_point = 0
    if len(work_sql) == 0:
        str_point = 1
    return str_point


def get_leave_rule(leave_type, date):
    leave_rule = """SELECT `LR`.`name`, `LR`.`gender`, `LR`.`max_leaves_allowed`, `LT`.`applicable_after_days`, `LR`.`frequency_based_on`, `LT`.`leave_credit_frequency`
		FROM `tabLeave Rule` AS `LR`
		LEFT JOIN `tabLeave Type` AS `LT`
			ON `leave_type` = `LT`.`name`
		WHERE `LR`.`docstatus` = 1
		AND `LR`.`leave_type` = '{}'
		AND `LR`.`effective_from` <= '{}'
		ORDER BY `LR`.`effective_from` DESC
		LIMIT 1""".format(
        leave_type, date
    )
    return frappe.db.sql(leave_rule, as_dict=True)


def get_leave_rule(leave_type, date):
    leave_rule = """SELECT `LR`.`name`, `LR`.`gender`, `LR`.`max_leaves_allowed`, `LT`.`applicable_after_days`, `LR`.`frequency_based_on`, `LT`.`leave_credit_frequency`
		FROM `tabLeave Rule` AS `LR`
		LEFT JOIN `tabLeave Type` AS `LT`
			ON `leave_type` = `LT`.`name`
		WHERE `LR`.`docstatus` = 1
		AND `LR`.`leave_type` = '{}'
		AND `LR`.`effective_from` <= '{}'
		ORDER BY `LR`.`effective_from` DESC
		LIMIT 1""".format(
        leave_type, date
    )
    return frappe.db.sql(leave_rule, as_dict=True)


def compenstation_percent(
    leave_rule, from_date, to_date, joining_date, total_leave_days, leave_taken
):
    based_on = {
        "Number of Days availed": {
            "from_range": "(leave_taken or 0)",
            "to_range": "(leave_taken or 0) + (leave_days or 0)",
        },
        "Number of Months worked": {
            "from_range": "month_diff(from_date, joining_date)",
            "to_range": "month_diff(to_date, joining_date)",
        },
        "Number of Years worked": {
            "from_range": "month_diff(from_date, joining_date) / 12",
            "to_range": "month_diff(to_date, joining_date) / 12",
        },
    }

    eval_dict = {
        "joining_date": joining_date,
        "to_date": to_date,
        "from_date": from_date,
        "leave_taken": leave_taken,
        "month_diff": month_diff,
        "leave_days": total_leave_days,
    }

    if not leave_rule.get("frequency_based_on"):
        return {}

    from_range = eval(
        based_on[leave_rule.get("frequency_based_on")]["from_range"], eval_dict
    )
    to_range = eval(
        based_on[leave_rule.get("frequency_based_on")]["to_range"], eval_dict
    )

    percent = """SELECT starting_unit, ending_unit, percentage_of_compensation
		FROM `tabCompensation Rule Slab`
		WHERE parent = '{0}'
		AND ending_unit >= {1} and starting_unit <= {2}
		ORDER BY starting_unit"""
    percent = percent.format(leave_rule.get("name"), from_range, to_range)
    percent = frappe.db.sql(percent, as_dict=True)

    compansation = {}
    leave_days = flt(total_leave_days, 0)
    leave_date = getdate(from_date)
    if leave_rule.get("frequency_based_on") == "Number of Days availed":
        for row in percent:
            slab_percentage = row.get("percentage_of_compensation")
            for day in range(0, leave_days):
                leave_taken += 1
                if row.get("starting_unit") <= leave_taken <= row.get("ending_unit"):
                    compansation[slab_percentage] = compansation.get(
                        slab_percentage, []
                    ) + [leave_date]

                    leave_days -= 1
                    leave_date = add_days(getdate(leave_date), 1)
                else:
                    leave_taken -= 1
                    break
    elif leave_rule.get("frequency_based_on") == "Number of Months worked":
        for row in percent:
            slab_percentage = row.get("percentage_of_compensation")
            for day in range(0, leave_days):
                if (
                    add_months(joining_date, row.get("starting_unit"))
                    <= leave_date
                    <= add_days(add_months(joining_date, row.get("ending_unit")), -1)
                ):
                    compansation[slab_percentage] = compansation.get(
                        slab_percentage, []
                    ) + [leave_date]

                    leave_days -= 1
                    leave_date = add_days(getdate(leave_date), 1)
                else:
                    break
    else:
        for row in percent:
            slab_percentage = row.get("percentage_of_compensation")
            for day in range(0, leave_days):
                if (
                    add_years(joining_date, row.get("starting_unit"))
                    <= leave_date
                    <= add_days(add_years(joining_date, row.get("ending_unit")), -1)
                ):
                    compansation[slab_percentage] = compansation.get(
                        slab_percentage, []
                    ) + [leave_date]

                    leave_days -= 1
                    leave_date = add_days(getdate(leave_date), 1)
                else:
                    break

    return compansation


def get_leave_allocation_records(employee, date, leave_type=None):
    """returns the total allocated leaves and carry forwarded leaves based on ledger entries"""

    conditions = ("and leave_type='%s'" % leave_type) if leave_type else ""
    allocation_details = frappe.db.sql(
        """
		SELECT
			SUM(CASE WHEN is_carry_forward = 1 THEN leaves ELSE 0 END) as cf_leaves,
			SUM(CASE WHEN is_carry_forward = 0 THEN leaves ELSE 0 END) as new_leaves,
			MIN(from_date) as from_date,
			MAX(to_date) as to_date,
			leave_type
		FROM `tabLeave Ledger Entry`
		WHERE
			from_date <= %(date)s
			AND to_date >= %(date)s
			AND docstatus=1
			AND transaction_type="Leave Allocation"
			AND employee=%(employee)s
			AND is_expired=0
			AND is_lwp=0
			{0}
		GROUP BY employee, leave_type
	""".format(
            conditions
        ),
        dict(date=date, employee=employee),
        as_dict=1,
    )  # nosec

    allocated_leaves = frappe._dict()
    for d in allocation_details:
        allocated_leaves.setdefault(
            d.leave_type,
            frappe._dict(
                {
                    "from_date": d.from_date,
                    "to_date": d.to_date,
                    "total_leaves_allocated": flt(d.cf_leaves) + flt(d.new_leaves),
                    "unused_leaves": d.cf_leaves,
                    "new_leaves_allocated": d.new_leaves,
                    "leave_type": d.leave_type,
                }
            ),
        )
    return allocated_leaves


def get_pending_leaves_for_period(employee, leave_type, from_date, to_date):
    """Returns leaves that are pending approval"""
    leaves = frappe.get_all(
        "Leave Application",
        filters={"employee": employee, "leave_type": leave_type, "status": "Open"},
        or_filters={
            "from_date": ["between", (from_date, to_date)],
            "to_date": ["between", (from_date, to_date)],
        },
        fields=["SUM(total_leave_days) as leaves"],
    )[0]
    return leaves["leaves"] if leaves["leaves"] else 0.0


def get_remaining_leaves(allocation, leaves_taken, date, expiry):
    """Returns minimum leaves remaining after comparing with remaining days for allocation expiry"""

    def _get_remaining_leaves(remaining_leaves, end_date):
        if remaining_leaves > 0:
            remaining_days = date_diff(end_date, date) + 1
            remaining_leaves = min(remaining_days, remaining_leaves)

        return remaining_leaves

    total_leaves = flt(allocation.total_leaves_allocated) + flt(leaves_taken)

    if expiry and allocation.unused_leaves:
        remaining_leaves = flt(allocation.unused_leaves) + flt(leaves_taken)
        remaining_leaves = _get_remaining_leaves(remaining_leaves, expiry)

        total_leaves = flt(allocation.new_leaves_allocated) + flt(remaining_leaves)

    return _get_remaining_leaves(total_leaves, allocation.to_date)


def get_leaves_for_period(employee, leave_type, from_date, leave_rule):
    condition = ""
    if from_date and leave_rule.get("leave_credit_frequency") == "Yearly":
        year_start = getdate(from_date).replace(month=1, day=1)
        year_end = getdate(from_date).replace(month=12, day=31)
        condition = " and from_date between '{}' and '{}'".format(year_start, year_end)

    leave_applications = frappe.db.sql(
        """
		select ifnull(sum(total_leave_days), 0) as total_leave_days
		from `tabLeave Application`
		where employee=%(employee)s and leave_type=%(leave_type)s
			and status = 'Approved' and docstatus != 2 {}""".format(
            condition
        ),
        {"employee": employee, "leave_type": leave_type},
        as_dict=1,
    )

    leave_days = leave_applications[0]["total_leave_days"] if leave_applications else 0

    return leave_days


def skip_expiry_leaves(leave_entry, date):
    """Checks whether the expired leaves coincide with the to_date of leave balance check.
    This allows backdated leave entry creation for non carry forwarded allocation"""
    end_date = frappe.db.get_value(
        "Leave Allocation", {"name": leave_entry.transaction_name}, ["to_date"]
    )
    return True if end_date == date and not leave_entry.is_carry_forward else False


# def get_leave_entries(employee, leave_type, from_date, to_date):
# 	''' Returns leave entries between from_date and to_date. '''
# 	return frappe.db.sql("""
# 		SELECT
# 			employee, leave_type, from_date, to_date, leaves, transaction_name, transaction_type, holiday_list,
# 			is_carry_forward, is_expired
# 		FROM `tabLeave Ledger Entry`
# 		WHERE employee=%(employee)s AND leave_type=%(leave_type)s
# 			AND docstatus=1
# 			AND (leaves<0
# 				OR is_expired=1)
# 			AND (from_date between %(from_date)s AND %(to_date)s
# 				OR to_date between %(from_date)s AND %(to_date)s
# 				OR (from_date < %(from_date)s AND to_date > %(to_date)s))
# 	""", {
# 		"from_date": from_date,
# 		"to_date": to_date,
# 		"employee": employee,
# 		"leave_type": leave_type
# 	}, as_dict=1)


@frappe.whitelist()
def get_holidays(employee, from_date, to_date, holiday_list=None):
    """get holidays between two dates for the given employee"""
    if not holiday_list:
        holiday_list = get_holiday_list_for_employee(employee)

    holidays = frappe.db.sql(
        """select count(distinct holiday_date) from `tabHoliday` h1, `tabHoliday List` h2
		where h1.parent = h2.name and h1.holiday_date between %s and %s
		and h2.name = %s""",
        (from_date, to_date, holiday_list),
    )[0][0]

    return holidays


def is_lwp(leave_type):
    lwp = frappe.db.sql(
        "select is_lwp from `tabLeave Type` where name = %s", leave_type
    )
    return lwp and cint(lwp[0][0]) or 0


@frappe.whitelist()
def get_events(start, end, filters=None):
    events = []

    employee = frappe.db.get_value(
        "Employee", {"user_id": frappe.session.user}, ["name", "company"], as_dict=True
    )
    if employee:
        employee, company = employee.name, employee.company
    else:
        employee = ""
        company = frappe.db.get_value("Global Defaults", None, "default_company")

    from frappe.desk.reportview import get_filters_cond

    conditions = get_filters_cond("Leave Application", filters, [])
    # show department leaves for employee
    if "Employee" in frappe.get_roles():
        add_department_leaves(events, start, end, employee, company)

    add_leaves(events, start, end, conditions)

    add_block_dates(events, start, end, employee, company)
    add_holidays(events, start, end, employee, company)
    return events


def add_department_leaves(events, start, end, employee, company):
    department = frappe.db.get_value("Employee", employee, "department")

    if not department:
        return

    # department leaves
    department_employees = frappe.db.sql_list(
        """select name from tabEmployee where department=%s
		and company=%s""",
        (department, company),
    )

    filter_conditions = ' and employee in ("%s")' % '", "'.join(department_employees)
    add_leaves(events, start, end, filter_conditions=filter_conditions)


def add_leaves(events, start, end, filter_conditions=None):
    conditions = []

    if not cint(
        frappe.db.get_value(
            "HR Settings", None, "show_leaves_of_all_department_members_in_calendar"
        )
    ):
        from frappe.desk.reportview import build_match_conditions

        match_conditions = build_match_conditions("Leave Application")

        if match_conditions:
            conditions.append(match_conditions)

    query = """select name, from_date, to_date, employee_name, half_day,
		status, employee, docstatus
		from `tabLeave Application` where
		from_date <= %(end)s and to_date >= %(start)s <= to_date
		and docstatus < 2
		and status!='Rejected' """

    if conditions:
        query += " and " + " and ".join(conditions)

    if filter_conditions:
        query += filter_conditions

    for d in frappe.db.sql(query, {"start": start, "end": end}, as_dict=True):
        e = {
            "name": d.name,
            "doctype": "Leave Application",
            "from_date": d.from_date,
            "to_date": d.to_date,
            "docstatus": d.docstatus,
            "color": d.color,
            "title": cstr(d.employee_name)
            + (" " + _("(Half Day)") if d.half_day else ""),
        }
        if e not in events:
            events.append(e)


def add_block_dates(events, start, end, employee, company):
    # block days
    from hrms.hr.doctype.leave_block_list.leave_block_list import (
        get_applicable_block_dates,
    )

    cnt = 0
    block_dates = get_applicable_block_dates(
        start, end, employee, company, all_lists=True
    )

    for block_date in block_dates:
        events.append(
            {
                "doctype": "Leave Block List Date",
                "from_date": block_date.block_date,
                "to_date": block_date.block_date,
                "title": _("Leave Blocked") + ": " + block_date.reason,
                "name": "_" + str(cnt),
            }
        )
        cnt += 1


def add_holidays(events, start, end, employee, company):
    applicable_holiday_list = get_holiday_list_for_employee(employee, company)
    if not applicable_holiday_list:
        return

    for holiday in frappe.db.sql(
        """select name, holiday_date, description
		from `tabHoliday` where parent=%s and holiday_date between %s and %s""",
        (applicable_holiday_list, start, end),
        as_dict=True,
    ):
        events.append(
            {
                "doctype": "Holiday",
                "from_date": holiday.holiday_date,
                "to_date": holiday.holiday_date,
                "title": _("Holiday") + ": " + cstr(holiday.description),
                "name": holiday.name,
            }
        )


@frappe.whitelist()
def get_mandatory_approval(doctype):
    mandatory = ""
    if doctype == "Leave Application":
        mandatory = frappe.db.get_single_value(
            "HR Settings", "leave_approver_mandatory_in_leave_application"
        )
    else:
        mandatory = frappe.db.get_single_value(
            "HR Settings", "expense_approver_mandatory_in_expense_claim"
        )

    return mandatory


def get_approved_leaves_for_period(employee, leave_type, from_date, to_date):
    query = """
		select employee, leave_type, from_date, to_date, total_leave_days
		from `tabLeave Application`
		where employee=%(employee)s
			and docstatus=1
			and (from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (from_date < %(from_date)s and to_date > %(to_date)s))
	"""
    if leave_type:
        query += "and leave_type=%(leave_type)s"

    leave_applications = frappe.db.sql(
        query,
        {
            "from_date": from_date,
            "to_date": to_date,
            "employee": employee,
            "leave_type": leave_type,
        },
        as_dict=1,
    )

    leave_days = 0
    for leave_app in leave_applications:
        if leave_app.from_date >= getdate(from_date) and leave_app.to_date <= getdate(
            to_date
        ):
            leave_days += leave_app.total_leave_days
        else:
            if leave_app.from_date < getdate(from_date):
                leave_app.from_date = from_date
            if leave_app.to_date > getdate(to_date):
                leave_app.to_date = to_date

            leave_days += get_number_of_leave_days(
                employee, leave_type, leave_app.from_date, leave_app.to_date
            )

    return leave_days


@frappe.whitelist()
def get_leave_approver(employee):
    leave_approver, department = frappe.db.get_value(
        "Employee", employee, ["leave_approver", "department"]
    )

    if not leave_approver and department:
        leave_approver = frappe.db.get_value(
            "Department Approver",
            {"parent": department, "parentfield": "leave_approvers", "idx": 1},
            "approver",
        )

    return leave_approver


@frappe.whitelist()
def make_workflow_delegation(name, employee, employee_name, from_date, to_date):
    workflow_delegation = frappe.new_doc("Workflow Delegation")
    workflow_delegation.employee = employee
    workflow_delegation.employee_name = employee_name
    workflow_delegation.reference_page = "Leave Request"
    workflow_delegation.reference_id = name
    workflow_delegation.from_date = from_date
    workflow_delegation.to_date = to_date
    return workflow_delegation.as_dict()
