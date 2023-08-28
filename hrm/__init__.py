# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe.utils import getdate

__version__ = '0.0.1'


def float_2_time(time):
	seconds = float(time) * 3600
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)

	# print "%02d:%02d:%02d"%(hours, minutes, seconds)
	return "%02d:%02d"%(hours, minutes)


def month_30days(month_start, month_end, actual_days):
	start_date = getdate(month_start)
	end_date = getdate(month_end)

	working_days = (end_date - start_date).days + 1
	if working_days == actual_days:
		return 30
	else:
		diff_days = (working_days - 30)
		if (working_days - abs(diff_days)) > actual_days:
			diff_days = 0
		
		return actual_days - diff_days