# -*- coding: utf-8 -*-
# Copyright (c) 2020, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def validate(doc, method):
	check_default(doc)


def check_default(doc):
	has_default = """SELECT *
		FROM `tab{}`
		WHERE `name` != '{}'
		AND `default` = 1
		AND `disabled` = 0""".format(doc.get('doctype'), doc.get('name'))
	has_default = frappe.db.sql(has_default, as_dict=True)
	if (doc.get('default') or 0) == 1 and has_default:
		has_default = has_default[0]
		frappe.throw(_('Loan type <a href="#Form/Loan Type/{0}">{0}</a> is already set as default'.format(has_default.get('name'))))