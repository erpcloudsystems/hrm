# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from hrm.hrm.doctype.vacation_rejoining.vacation_rejoining import vacation_rejoining_edit
from frappe.utils import getdate
from datetime import datetime, timedelta

@frappe.whitelist()
def validate(doc, method):
	if not doc.rejoining_date: doc.vacation_opening_balance = 0

	validate_rejoining_date(doc)
	validate_airline(doc)
	validate_onupdate(doc)

@frappe.whitelist()
def onload(doc, method):
	validate_future_vacation(doc)

def validate_onupdate(doc):
	if doc.is_new() == None and doc.get("__onload"):
		validate_future_vacation(doc)
		date_change = find_date_change(doc)
		if doc.get("__onload")["read_only"] == 1 and date_change == 1:
			frappe.throw("Joining Date OR Rejoining Date Cannot be Updated")

def validate_future_vacation(doc):
	if doc.is_new() == None:
		result_parm = vacation_rejoining_edit(doc.employee)
		modif_parm = validate_rule_modification(doc)

		doc.get("__onload")["read_only"] = modif_parm if result_parm == 1 else 1

def validate_rule_modification(doc):
	modif_select = """SELECT *
	FROM `tabVacation Rule Modification`
	WHERE docstatus < 2
	AND employee = '{0}'
	""".format(doc.employee)
	modif_result = frappe.db.sql(modif_select,as_list = True)

	return 1 if modif_result else 0

def find_date_change(doc):
	modif_select = """SELECT *
	FROM `tabEmployee`
	WHERE name = '{0}'
	AND( date_of_joining != '{1}'
	OR rejoining_date != '{2}'
	OR vacation_opening_balance != '{3}')
	""".format(doc.employee, doc.date_of_joining, doc.rejoining_date, doc.vacation_opening_balance)
	modif_select = frappe.db.sql(modif_select, as_list = True)

	return 1 if modif_select else 0

def validate_airline(doc):
	if doc.eligible_for_airline_ticket == 1:
		if (doc.number_of_trips or 0) <= 0:
			frappe.throw("Number Of Trips Should not be Zero")

		if (doc.year or 0) <= 0:
			frappe.throw("Per Year Should not be Zero")

		if (doc.eligible_head_count_including_self or 0) <= 0:
			frappe.throw("Eligible head count including self Should not be Zero")

		if doc.mode_of_reimbursement == "Cash" and (doc.eligible_cash or 0) <= 0:
			frappe.throw("Eligible cash Should not be Zero")

def validate_rejoining_date(doc):
	if doc.rejoining_date and getdate(str(doc.rejoining_date)) < getdate(str(doc.date_of_joining)):
		frappe.throw("Vacation Rejoining Date Cannot be Less then Date of Joining")


@frappe.whitelist()
def fetch_child(templete, date_of_joining):
	list_data = []
	date_jo = datetime.strptime(date_of_joining, '%Y-%m-%d')
	sql = """select days, document, responsible_persons
		from `tabDocument List`
		where parent = '{}'""".format(templete)
	data = frappe.db.sql(sql, as_dict=True)

	for i in data:
		days = i['days']
		future = date_jo + timedelta(days=int(days))
		dat = datetime.strftime(future, '%Y-%m-%d')
		document = i['document']
		list_data.append({"document": document,
			"date": dat})
	
	return list_data
