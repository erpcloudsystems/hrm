# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, formatdate, date_diff

def validate(doc, method):
	validate_dates(doc)
	validate_overlap(doc)
	doc.advance_days = abs(date_diff(doc.end_date, doc.actual_end_date))


def validate_dates(doc):
	if getdate(doc.actual_start_date) > getdate(doc.actual_end_date):
		frappe.throw(_("Actual Attendance End Date can not be less than Actual Attendance Start Date"))


def validate_overlap(doc):
	query = """
		select name
		from `tab{0}`
		where name != %(name)s
		and company = %(company)s and (actual_start_date between %(start_date)s and %(end_date)s \
			or actual_end_date between %(start_date)s and %(end_date)s \
			or (actual_start_date < %(start_date)s and actual_end_date > %(end_date)s))
		"""
	if not doc.name:
		# hack! if name is null, it could cause problems with !=
		doc.name = "New "+doc.doctype

	overlap_doc = frappe.db.sql(query.format(doc.doctype), {
			"start_date": doc.actual_start_date,
			"end_date": doc.actual_end_date,
			"name": doc.name,
			"company": doc.company
		}, as_dict = 1)

	if overlap_doc:
		msg = _("A {0} exists between {1} and {2} (").format(doc.doctype,
			formatdate(doc.actual_start_date), formatdate(doc.actual_end_date)) \
			+ """ <b><a href="#Form/{0}/{1}">{1}</a></b>""".format(doc.doctype, overlap_doc[0].name) \
			+ _(") for {0}").format(doc.company)
		frappe.throw(msg)