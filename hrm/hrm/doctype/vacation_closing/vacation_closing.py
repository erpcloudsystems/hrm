# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, rounded, add_months, nowdate
from datetime import date
from frappe.utils.data import get_first_day, add_days, date_diff, get_last_day, getdate
from frappe.utils import cint, cstr, flt
from hrm.doctype_triggers.hr.salary_slip.salary_slip import (
    get_actual_structure,
    get_payroll_period,
)
from hrm.hrm.doctype.vacation_leave_encashment.vacation_leave_encashment import (
    vacation_encash_amount,
)


class VacationClosing(Document):
    def validate(self):
        self.validate_salary_slip_date()
        self.validate_grand_total()

    def before_submit(self):
        if self.ignore_account_effect != 1:
            self.mandatory_fild()
            self.vacation_leave_save()

    def on_submit(self):
        if self.ignore_account_effect != 1:
            self.vacation_leave_submit()

    def on_cancel(self):
        jv_to_cancel = self.get_jv()
        if str(jv_to_cancel) != "0":
            jv_canceller = frappe.get_doc("Journal Entry", str(jv_to_cancel))
            if jv_canceller.docstatus == 1:
                jv_canceller.cancel()
        if self.employee_loan_reference:
            canceller = frappe.get_doc("Loan", self.employee_loan_reference)
            if canceller.docstatus == 1:
                canceller.cancel()
        vacation_doc = frappe.get_doc(
            "Vacation Leave Application", self.leave_application_reference
        )
        vacation_doc.vacation_closing_reference = None
        vacation_doc.db_update()

    def on_trash(self):
        jv_to_delete = self.get_jv()
        if str(jv_to_delete) != "0":
            jv_deleter = frappe.get_doc("Journal Entry", str(jv_to_delete))
            jv_deleter.delete()

        if self.employee_loan_reference:
            try:
                sql = (
                    " UPDATE `tabVacation Closing` SET employee_loan_reference = null "
                )
                check = frappe.db.sql(sql, as_dict=1)
                deleter = frappe.get_doc("Loan", self.employee_loan_reference)
                deleter.delete()
                # check.save()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(str(e))

    def validate_grand_total(self):
        self.grand_total = (
            flt(self.present_day_salary)
            + flt(self.salary_processed_amount)
            + flt(self.advance_amount)
            - flt(self.different_ticket)
        )

        if (flt(self.grand_total) or 0) <= 0:
            frappe.throw("Grand Total Cannot be Less Than or Equal to Zero")

    def mandatory_fild(self):
        if (
            not self.mode_of_payment
            or not self.payment_account
            or not self.employee_loan_account
            or not self.interest_income_account
        ):
            frappe.throw(
                "Please fill the mandatory field ['Mode of Payment','Payment Account','Employee Loan Account','Interest Income Account']"
            )

    def validate_salary_slip_date(self):
        if (
            self.salary_start_date
            and self.leave_from
            and getdate(self.salary_start_date) != get_first_day(self.leave_from)
        ):
            frappe.throw("Salary Start Date Cannot be Less than Month First Date")

        if (
            self.salary_end_date
            and self.leave_from
            and getdate(self.salary_end_date) >= getdate(self.leave_from)
        ):
            frappe.throw(
                "Salary End Date Cannot be Greater than or Equal to Leave From Date"
            )

        if (
            self.salary_start_date
            and self.salary_end_date
            and getdate(self.salary_end_date) < getdate(self.salary_start_date)
        ):
            frappe.throw("Salary Start Date Cannot be Greater than Salary End Date")

    def get_sal_and_attendance(self):
        self.last_vacation()
        self.validate_salary_slip_date()

        month_start_date = get_first_day(self.salary_start_date or self.leave_from)
        pay_end_date = self.salary_end_date or add_days(self.leave_from, -1)

        self.attendance_days = 0
        self.present_day_salary = 0.0
        self.set("earnings", [])
        self.set("deductions", [])

        try:
            doc = frappe.new_doc("Salary Slip")
            doc.employee = self.employee
            doc.posting_date = month_start_date
            doc.start_date = month_start_date
            doc.end_date = get_last_day(month_start_date)
            doc.pay_end_date = pay_end_date
            doc.save()

            if (
                not float(doc.payment_days) < 0
                and self.enable_salary_date == 1
                and self.salary_end_date != None
            ):
                self.set_val_inchild("earnings", doc.earnings)
                self.set_val_inchild("deductions", doc.deductions)
                self.attendance_days += doc.payment_days
                self.present_day_salary += doc.gross_pay - doc.total_deduction

            self.vacation_salary()
            frappe.db.rollback()
        except Exception as e:
            frappe.db.rollback()
            frappe.as_unicode(frappe.get_traceback())
            frappe.throw(str(e))

        self.grand_total = (
            flt(self.present_day_salary)
            + flt(self.salary_processed_amount)
            + flt(self.advance_amount)
            - flt(self.different_ticket)
        )

    def set_val_inchild(self, target_field, source_child, vacation=False):
        for row in source_child:
            flag = False
            for i in self.get(target_field):
                if i.salary_component == str(row.get("salary_component")):
                    flag = True
                    i.default_amount = row.get("default_amount")
                    if vacation:
                        i.vacation_amount = row.get("vacation_amount")
                    else:
                        i.amount = row.get("amount")
            if flag:
                pass
            elif (
                row.get("vacation_amount" if vacation else "amount") >= 0
                or row.get("default_amount") > 0
            ):
                child_row = self.append(target_field)
                child_row.salary_component = row.get("salary_component")
                child_row.default_amount = row.get("default_amount")
                if vacation:
                    child_row.vacation_amount = row.get("vacation_amount")
                else:
                    child_row.amount = row.get("amount")

    def vacation_salary(self):
        start_date = get_first_day(self.get("leave_from"))
        end_date = get_last_day(start_date)

        vacation_day = date_diff(self.leave_to, self.leave_from) + 1

        payroll_dict = get_payroll_period(
            company=self.get("company"),
            start_date=start_date,
            end_date=end_date,
            actual_period=1,
        )
        struct_assig, earning_deduction = get_actual_structure(self, payroll_dict)

        if not struct_assig:
            frappe.throw(_("There is no Salary Structure for the selected Employee"))

        earnings = earning_deduction.get("earnings", {})
        gross_ear = vacation_encash_amount(earnings, vacation_day)
        self.set_val_inchild("earnings", earnings.values(), True)

        deductions = earning_deduction.get("deductions", {})
        gross_ded = vacation_encash_amount(deductions, vacation_day)
        self.set_val_inchild("deductions", deductions.values(), True)

        self.salary_processed_amount = gross_ear - gross_ded

    def make_jv_entry(self):
        if self.employee_loan_reference:
            self.check_permission("write")
            journal_entry = frappe.new_doc("Journal Entry")
            default_cost_center = self.get_default_cost_center()
            journal_entry.voucher_type = "Bank Entry"
            journal_entry.user_remark = "Made from " + self.name
            journal_entry.doctype_reference = self.doctype
            journal_entry.doctype_id = self.name
            journal_entry.company = self.company
            journal_entry.posting_date = nowdate()
            journal_entry.company_series = self.company_abbreviation

            account_amt_list = []

            account_amt_list.append(
                {
                    "account": self.employee_loan_account,
                    "party_type": "Employee",
                    "party": self.employee,
                    "debit_in_account_currency": self.grand_total,
                    "reference_type": "Loan",
                    "reference_name": self.employee_loan_reference,
                    "cost_center": default_cost_center,
                }
            )
            account_amt_list.append(
                {
                    "account": self.payment_account,
                    "credit_in_account_currency": self.grand_total,
                    "reference_type": "Loan",
                    "reference_name": self.employee_loan_reference,
                    "cost_center": default_cost_center,
                }
            )
            journal_entry.set("accounts", account_amt_list)
            return journal_entry.as_dict()
        else:
            frappe.throw("Loan Reference Missing")

    def get_default_cost_center(self):
        cost_center = frappe.db.get_value(
            "Company", {"company_name": self.company}, "cost_center"
        )

        if not cost_center:
            frappe.throw(
                "Please set Default Cost Center in Company {0}".format(self.company)
            )

        return cost_center

    def get_salary(self):
        query = (
            "select base from `tabSalary Structure Employee` where employee ='"
            + self.employee
            + "'"
        )
        data = frappe.db.sql(query, as_dict=True)
        if data:
            return data

    def get_jv(self):
        query = (
            "select name from `tabJournal Entry` where doctype_id='" + self.name + "';"
        )
        data = frappe.db.sql(query, as_dict=True)
        if data:
            return data[0]["name"]
        else:
            return int(0)

    def get_attendance(self):
        month_start_date = get_first_day(self.leave_from)
        month_end_date = add_days(self.leave_from, -1)
        query = (
            "select count(*) 'attendance' from `tabAttendance` where employee = '"
            + self.employee
            + "' and status = 'Present' and attendance_date >= '"
            + str(month_start_date)
            + "' and attendance_date <='"
            + str(month_end_date)
            + "'"
        )
        data = frappe.db.sql(query, as_dict=True)
        if data:
            return data

    def vacation_leave_save(self):
        vacay = frappe.new_doc("Loan")
        vacay.company = self.company
        vacay.applicant = self.employee
        vacay.posting_date = self.entry_date
        vacay.loan_type = "Vacation Payout"
        vacay.status = "Fully Disbursed"
        vacay.loan_amount = float(self.grand_total)
        vacay.mode_of_payment = self.mode_of_payment
        vacay.loan_account = self.employee_loan_account
        vacay.disbursement_date = self.repayment_date
        vacay.repayment_start_date = self.repayment_date
        vacay.repayment_method = "Repay Fixed Amount per Period"
        vacay.monthly_repayment_amount = float(self.grand_total)
        vacay.interest_income_account = self.interest_income_account
        vacay.payment_account = self.payment_account
        vacay.loan_adjustment = True
        vacay.repay_from_salary = True
        vacay.reference_doctype = self.doctype
        vacay.reference_name = self.name

        if self.amended_from:
            vacay.amended_from = self.temp_reference

        vacay.save()

        self.employee_loan_reference = vacay.name
        self.temp_reference = vacay.name

        vacay_app = frappe.get_doc(
            "Vacation Leave Application", self.leave_application_reference
        )
        vacay_app.vacation_closing_reference = self.name
        vacay_app.save()

    def vacation_leave_submit(self):
        saver = frappe.get_doc("Loan", self.employee_loan_reference)
        saver.submit()

    def has_jv_entries(self):
        response = {}

        journal_entries = frappe.db.sql(
            """SELECT J.name
			FROM `tabJournal Entry` J
			WHERE J.docstatus < 2
			AND J.doctype_reference = '{0}'
			AND J.doctype_id = '{1}'""".format(
                self.doctype, self.name
            ),
            as_dict=1,
        )

        response["submitted"] = journal_entries[0]["name"] if journal_entries else 0

        return response

    def last_vacation(self):
        last_vec = """SELECT vacation_rejoining_date
			FROM `tabVacation Rejoining`
			WHERE docstatus = 1
			AND employee_id = '{0}' 
			ORDER BY vacation_rejoining_date DESC
			LIMIT 1""".format(
            self.employee
        )

        last_vec_res = frappe.db.sql(last_vec, as_dict=True)

        self.last_rejoining_date = (
            last_vec_res[0]["vacation_rejoining_date"]
            if last_vec_res
            else self.joining_date
        )


def add_component_val(comp_dict, comp_list):
    amount = 0
    for row in comp_dict:
        if row.get("salary_component") in comp_list:
            amount += row.get("amount")

    return amount


@frappe.whitelist()
def get_leave_application(doctype, txt, searchfield, start, page_len, filters):
    emp_sql = """SELECT `VLA`.`name`, `VLA`.`employee_id`, `VLA`.`employee_name`
		FROM `tabVacation Leave Application` AS `VLA`
		WHERE `VLA`.`docstatus` = 1
		AND `VLA`.`status` = 'Approved'
		AND `VLA`.`company` = '{0}'
		AND `VLA`.`name` NOT IN (SELECT `VC`.`leave_application_reference`
			FROM `tabVacation Closing` AS `VC`
			WHERE `VC`.`docstatus` IN (0,1)
			AND `VC`.`name` != '{1}')
		AND (`VLA`.`name` LIKE %(txt)s
		OR `VLA`.`employee_id` LIKE %(txt)s
		OR `VLA`.`employee_name` LIKE %(txt)s)""".format(
        filters.get("company"), filters.get("name")
    )

    return frappe.db.sql(emp_sql, {"txt": "%%%s%%" % txt})
