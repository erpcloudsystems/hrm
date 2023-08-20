# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"module_name": "HRM",
			"category": "Modules",
			"label": _("HRM"),
			"color": "grey",
			"icon": "octicon octicon-organization",
			"type": "module",
			"onboard_present": 1
		},
		{
			"module_name": "Portal",
			"color": "grey",
			"icon": "octicon octicon-file-directory",
			"type": "module",
			"label": _("Portal")
		},
	]
