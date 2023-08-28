# -*- coding: utf-8 -*-
# Copyright (c) 2020, avu and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
import json


@frappe.whitelist()
def update_weekoff(doc):
	doc = json.loads(doc)
	holiday_list = frappe.get_doc(doc)
	get_weekly_off_dates(holiday_list)

	return holiday_list


def get_weekly_off_dates(doc):
	doc.validate_values()
	date_list = doc.get_weekly_off_date_list(doc.from_date, doc.to_date)
	last_idx = max([cint(d.idx) for d in doc.get("holidays")] or [0,])
	for i, d in enumerate(date_list):
		ch = doc.append('holidays', {})
		ch.description = doc.weekly_off
		ch.holiday_date = d
		ch.idx = last_idx + i + 1
		ch.is_weekoff = 1