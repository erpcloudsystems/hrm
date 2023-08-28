# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def on_change(doc, method=None):
	doc_before_save = doc.get_doc_before_save()

	if doc_before_save and doc_before_save.get('is_default'):
		frappe.throw(_('Leave Type with is defualt checked cannot be changed'))


def on_trash(doc, method=None):
	if doc.get('is_default'):
		frappe.throw(_('Is Defualt checked Leave Type cannot be Deleted'))