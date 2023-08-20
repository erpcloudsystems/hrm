# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def raise_link_exists_exception(doc, reference_doctype, reference_docname, row=''):
	doc_link = '<a href="#Form/{0}/{1}">{1}</a>'.format(doc.doctype, doc.name)
	reference_link = '<a href="#Form/{0}/{1}">{1}</a>'.format(reference_doctype, reference_docname)

	#hack to display Single doctype only once in message
	if reference_doctype == reference_docname:
		reference_doctype = ''

	frappe.throw(_('Cannot delete or cancel because {0} {1} is linked with {2} {3} {4}')
		.format(_(doc.doctype), doc_link, _(reference_doctype), reference_link, row), frappe.LinkExistsError)