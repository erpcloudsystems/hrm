# Copyright (c) 2013, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from hrm.hrm.doctype.vacation_leave_application.vacation_leave_application import calculate_vacation
from frappe.utils import flt, nowdate, formatdate

def execute(filters=None):
	if not filters: filters = {}

	leave_ledg = calculate_vacation(employee=filters.get('employee'), from_date=filters.get('system_date') or nowdate(), ignore_rejoining=1, ignore_msg=1)
	leave_ledg = leave_ledg.get('slab', [])
	# frappe.errprint(str(leave_ledg))
	
	columns = [{
			'label': _('Employee'),
			'fieldname': 'employee',
			'fieldtype': 'Link',
			'options': 'Employee',
			'width': 150
		},
		{
			'label': _('Applied Rule'),
			'fieldname': 'applied_rule',
			'fieldtype': 'Link',
			'options': 'Vacation Leave Rule',
			'width': 120
		},
		{
			'label': _('From Date'),
			'fieldname': 'from_date',
			'fieldtype': 'Date',
			'width': 100
		},
		{
			'label': _('To Date'),
			'fieldname': 'to_date',
			'fieldtype': 'Date',
			'width': 100
		},
		{
			'label': _('Working Days'),
			'fieldname': 'working_days',
			'fieldtype': 'Float',
			'precision': 3,
			'width': 120
		},
		{
			'label': _('Opening Balance'),
			'fieldname': 'opening_balance',
			'fieldtype': 'Float',
			'precision': 3,
			'width': 120
		},
		{
			'label': _('Credit'),
			'fieldname': 'credit',
			'fieldtype': 'Float',
			'precision': 3,
			'width': 120
		},
		{
			'label': _('Debit'),
			'fieldname': 'debit',
			'fieldtype': 'Float',
			'precision': 3,
			'width': 120
		},
		{
			'label': _('Balance'),
			'fieldname': 'balance',
			'fieldtype': 'Data',
			'width': 120
		},
		{
			'label': _('Comment'),
			'fieldname': 'comment',
			'fieldtype': 'Text',
			'width': 200
		}
	]

	data = []
	for slab in leave_ledg:
		prev_row = data and data[-1]

		balance = slab.get('opening_balance', 0) + slab.get('credit', 0) - slab.get('debit', 0)
		if prev_row:
			balance += flt(prev_row.get('balance', 0))
		
		row_data = {
			'employee': slab.get('employee'),
			'applied_rule': slab.get('applied_rule'),
			'from_date': slab.get('start_date'),
			'to_date': slab.get('to_date'),
			'working_days': slab.get('working_days', 0),
			'opening_balance': slab.get('opening_balance', 0),
			'credit': slab.get('credit'),
			'debit': slab.get('debit'),
			'balance': str(flt(balance, 3)),
			'comment': comment_data(slab)
		}
		
		data.append(row_data)

	return columns, data

def comment_data(slab):
	comment_list = []
	if slab.get('carryforward_flag'):
		carryforward_dict = slab.get('carryforward') or {}
		if carryforward_dict and carryforward_dict.get('exclude_carryforward') > 0:
			comment_list.append("Expired unutilised Leaves {} days - Max Carryforward Limit {} days".format(flt(carryforward_dict.get('exclude_carryforward'), 3), carryforward_dict.get('carryforward_day')))
	
	if slab.get('expired_carryforward_on') and slab.get('expired_carryforward') > 0:
		comment_list.append("Carryforward {} days Expired on {}".format(flt(slab.get('expired_carryforward'), 3), formatdate(slab.get('expired_carryforward_on'))))
	
	comment_list += ['<b><a href="#Form/Vacation Leave Application/{0}">{0}</a></b> ({1} - {2}) - {3}'.format(row.get('name'), formatdate(row.get('from_date')), formatdate(row.get('to_date')), formatdate(row.get('vacation_rejoining_date'))) for row in slab.get('vacation', [])]
	comment_list += ['<b><a href="#Form/Vacation Leave Encashment/{name}">{name}</a></b> ({pay_days:.3f})'.format_map(row) for row in slab.get('encashed_leav', [])]
	return ', '.join(comment_list)