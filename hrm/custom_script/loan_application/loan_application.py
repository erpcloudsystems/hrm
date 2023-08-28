# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from dateutil.relativedelta import relativedelta
from frappe.utils import getdate, get_first_day, get_last_day, formatdate
from hrm.custom_script.salary_slip.salary_slip import (
    get_actual_structure,
    get_payroll_period,
)


def validate(doc, method):
    validate_employee(doc.get("applicant"), doc.get("required_by_date"))
    doc.existing_loan_amount = get_balance_loan(doc.get("applicant"))
    doc.eos_amount = eos_amount(
        doc.get("applicant"), doc.get("required_by_date"), doc.get("company")
    )


@frappe.whitelist()
def get_balance_loan(applicant):
    loan = """select sum(rps.total_payment) as 'total_loan'
			, if(rps.is_accrued = 1, rps.total_payment, 0) as 'paid_amount'
			, sum(rps.total_payment) - if(rps.is_accrued = 1, rps.total_payment, 0) as 'pending_amount'
		from `tabRepayment Schedule` as rps, `tabLoan` as l
		where l.name = rps.parent
		-- and l.repay_from_salary = 1
		and l.docstatus = 1
		and l.applicant = '{}'
		group by l.applicant""".format(
        applicant
    )

    loan = frappe.db.sql(loan, as_dict=True)

    loan = loan[0] if loan else {}
    return loan.get("pending_amount") or 0


@frappe.whitelist()
def eos_amount(applicant, required_date, company):
    working_days = total_working(applicant, required_date)
    net_pay = default_net_pay(applicant, required_date, company)

    year = working_days.years
    first_slab = 5 if year > 5 else year
    second_slab = year - first_slab
    months = working_days.months if second_slab > 0 else 0

    return (first_slab * (net_pay / 2)) + (
        (second_slab * net_pay) + ((net_pay / 12) * months)
    )


def total_working(applicant, required_date):
    joining_date = frappe.db.get_value("Employee", applicant, "date_of_joining")

    return relativedelta(getdate(required_date), getdate(joining_date))


def default_net_pay(applicant, required_date, company):
    # earnings, deductions = 0
    earnings = 0
    deductions = 0
    start_date = get_first_day(required_date)
    end_date = get_last_day(start_date)
    payroll_dict = get_payroll_period(
        company=company, start_date=start_date, end_date=end_date, actual_period=1
    )

    sal_obj = frappe.new_doc("Salary Slip")
    sal_obj.employee = applicant
    struct_assig, earning_deduction = get_actual_structure(sal_obj, payroll_dict)
    # frappe.errprint(str(earning_deduction))

    # change function due to None fetching in get by Suresh N
    # earnings = sum([row.get('default_amount', 0) for comp, row in earning_deduction.get('earnings').items()])
    # deductions = sum([row.get('default_amount', 0) frappe.errprint(row.get('default_amount')) for comp, row in earning_deduction.get('deductions').items()])

    # frappe.errprint(str(earning_deduction.get('earnings').items()))
    if earning_deduction.get("earnings"):
        for comp, row in earning_deduction.get("earnings").items():
            # frappe.errprint("hi"+str(row.get('default_amount',0)))
            if row.get("default_amount"):
                earnings += row.get("default_amount")

    if earning_deduction.get("deductions"):
        for comp, row in earning_deduction.get("deductions").items():
            # frappe.errprint("hi"+str(row.get('default_amount',0)))
            if row.get("default_amount"):
                deductions += row.get("default_amount")
        # change function due to None fetching in get by Suresh N

    return earnings - deductions


def validate_employee(applicant, required_date):
    if not applicant or not required_date:
        return

    joining_date, relieving_date = frappe.get_cached_value(
        "Employee", applicant, ["date_of_joining", "relieving_date"]
    )

    if getdate(required_date) < getdate(joining_date):
        frappe.throw(
            _("Loan Application can only be applied after {}").format(
                formatdate(joining_date)
            )
        )

    if relieving_date and getdate(required_date) > getdate(relieving_date):
        frappe.throw(
            _("Loan Application cannot be applied after {}").format(
                formatdate(relieving_date)
            )
        )
