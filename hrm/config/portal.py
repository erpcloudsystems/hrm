from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Portal"),
			"items": [
				{
					"type": "doctype",
					"name": "Employee Portal",
					"onboard": 1,
					"label": _("Employee Portal")
				}
			]
		}
	]