# Copyright (c) 2013, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def get_columns(data, has_key=1):
	column = []
	if len(data) != 0:
		for _key in sorted(data[0].keys()):
			_charidx = _key.find('#') + 1 if _key.find('#') > 0 else 0
			if _key.find('#') >= 0 or has_key: column.append(_key[_charidx:])
	return column


def get_values_list(data, has_key=1):
	rows = []
	if len(data) != 0:
		for idx in range(0, len(data)):
			val = []
			for _key in sorted(data[0].keys()):
				if _key.find('#') >= 0 or has_key: val.append(data[idx][_key])
			rows.append(val)
	return rows