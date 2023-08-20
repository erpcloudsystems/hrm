# -*- coding: utf-8 -*-
# Copyright (c) 2021, AVU and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, add_days, get_time, formatdate, getdate, get_first_day, get_last_day
# from erpnext.hr.doctype.employee_checkin.employee_checkin import time_diff_in_hours, calculate_working_hours
from datetime import timedelta

from hrm.custom_script.salary_slip.salary_slip import get_actual_structure, get_payroll_period
# from hrm.custom_script.attendance.attendance import get_ot
from hrm.hrm.doctype.ot_planner.ot_planner import applied_ot_rule
from hrm.custom_methods import get_comp_name
from hrm import *


class OTRequest(Document):
	def onload(self):
		if not self.is_new() and self.is_single_punch() == 1:
			self.get("__onload").sp_warning = _('OT Request Created with Single Punch')
	

	def validate(self):
		self.validate_duplicate()
		self.validate_date()
		self.validate_sp()
		self.ot_planner()
		self.attendance_ot(validate=1)
		#self.ot_worked()

		if (self.get('ot_hours') or 0) <= 0:
			frappe.throw(_('OT Request Hours Should be Greater then Zero'))


	def on_submit(self):
		if self.get('status') == "Open":
			frappe.throw(_("Only OT Request with status 'Approved' and 'Rejected' can be submitted"))
		
		if self.get('status') == 'Approved':
			self.update_attendance(self.get('ot_hours_minutes'))


	def on_cancel(self):
		self.validate_date()

		# if self.attendance_processed():
		# 	frappe.throw(_('OT Request Cannot be Cancelled Attendance already marked'))
		self.update_attendance()
		
		self.status = "Cancelled"
	

	def attendance_processed(self):
		attendance = """SELECT *
			FROM `tabAttendance`
			WHERE docstatus = 1
			AND employee = '{}'
			AND attendance_date ='{}'""".format(self.get('applicant'), self.get('ot_request_date'))
		attendance = frappe.db.sql(attendance, as_dict=True)
		
		return attendance [0]['name'] if attendance else None
	

	def validate_duplicate(self):
		pre_req = """select *
			from `tab{}`
			where name != '{}'
			and applicant = '{}'
			and ot_request_date = '{}'
			and docstatus < 2""".format(self.get('doctype'), self.get('name'), self.get('applicant'), self.get('ot_request_date'))
		pre_req = frappe.db.sql(pre_req, as_dict=True)

		if pre_req:
			frappe.throw(_('{} is already applied'.format(self.get('doctype'))))
	

	def validate_date(self):
		salary_slip = """SELECT `S`.*
			FROM `tabSalary Slip` AS `S`
			LEFT JOIN `tabPayroll Period` AS `PP`
				ON `PP`.`start_date` = `S`.`start_date`
				AND `PP`.`end_date` = `S`.`end_date`
				AND `PP`.`company` = `S`.`company`
			WHERE `S`.docstatus = 1
			AND `S`.`employee` = '{}'
			AND '{}' BETWEEN `PP`.`actual_start_date` and `PP`.`actual_end_date`""".format(self.get('applicant'), self.get('ot_request_date'))
		salary_slip = frappe.db.sql(salary_slip, as_dict=True)

		if salary_slip:
			salary_slip = salary_slip[0]
			frappe.throw(_("Salary Slip Already Processed for period {} and {}".format(formatdate(salary_slip.get('start_date')), formatdate(salary_slip.get('end_date')))))


	def ot_planner(self):
		duplicate = """SELECT *
			FROM `tabOT Planner`
			WHERE docstatus < 2
			AND employee = '{}'
			AND '{}' BETWEEN from_date AND to_date""".format(self.get('applicant'), self.get('ot_request_date'))
		duplicate = frappe.db.sql(duplicate, as_dict=True)

		if duplicate:
			duplicate = duplicate[0]
			frappe.throw(_("Employee has OT Planned between {} and {}".format(formatdate(duplicate.get('from_date')), formatdate(duplicate.get('to_date')))))
	

	def update_attendance(self, ot_min=0):
		from hrm.custom_script.attendance.attendance import process_attendance

		attendance = self.attendance_processed()
		if not attendance: return
		att_doc = frappe.get_doc('Attendance', attendance)
		process_attendance(doc=att_doc, ot_request=ot_min,overtime_without_punch = self.get('apply_overtime_without_any_attendance_punches') )
		# present = frappe.db.get_value('Employee', self.get('applicant'), 'default_present')

		# get_ot(doc=att_doc, ot_request=ot_min, present=present)
		# att_doc.ot_hours_time = float_2_time((att_doc.get('ot_hours_minutes') or 0.0) / 60)
		# att_doc.db_update()


	def ot_worked(self):
		ot_rule = applied_ot_rule(employee=self.get('applicant'), to_date=self.get('ot_request_date'))
		frappe.errprint(ot_rule)
		if not ot_rule: return

		start_date_time = '{} {}'.format(self.get('ot_request_date'), self.get('from_time'))

		end_date = self.get('ot_request_date')
		if get_time(self.get('from_time')) > get_time(self.get('to_time')):
			end_date = add_days(end_date, 1)
		end_date_time = '{} {}'.format(end_date, self.get('to_time'))
		start_date_time = ":".join(start_date_time.split(":")[:-1])
		end_date_time = ":".join(end_date_time.split(":")[:-1])
		# ot_working_hrs = time_diff_in_hours(get_datetime(start_date_time), get_datetime(end_date_time))
		ot_working_sec = (get_datetime(end_date_time) - get_datetime(start_date_time)).total_seconds() 
		ot_working_min = ot_working_sec / 60

		ot_rule_doc = frappe.get_doc('OT Rule', ot_rule)

		if ot_working_min < ot_rule_doc.get('minimum_ot_limit', 0):
			ot_working_min = 0

		ot_working_min = (abs(ot_working_min / (ot_rule_doc.get('ot_slab') or 1)) * (ot_rule_doc.get('ot_slab') or 1))

		self.ot_hours = flt(ot_working_min / 60, 2)
		self.ot_hours_minutes = flt(ot_working_min, 0)
		# self.ot_hours_time = float_2_time(self.get('ot_hours'))
		frappe.errprint([self.ot_hours_minutes ,"self.ot_hours_minutes "])
		self.ot_hours_time = timedelta(seconds=int(ot_working_min * 60))
		
		self.get_ot_amt(ot_rule_doc)

	def get_ot_amt(self, ot_rule):
		from hrm.custom_script.attendance.attendance import weekoff_holiday

		start_date = get_first_day(self.get('ot_request_date'))
		end_date = get_last_day(start_date)
		company = frappe.db.get_value('Employee', {'name': self.get('applicant')}, 'company')
		payroll_dict = get_payroll_period(company=company, start_date=start_date, end_date=end_date, actual_period=1)

		sal_obj = frappe.new_doc('Salary Slip')
		sal_obj.employee = self.get('applicant')
		struct_assig, earning_deduction = get_actual_structure(sal_obj, payroll_dict)

		weak_off, _shift = weekoff_holiday(self.get('applicant'), getdate(self.get('ot_request_date')))

		ot_rate = ot_rule.get('working_day_ot_rate') or 0
		if weak_off:
			ot_rate = ot_rule.get('non_working_day_ot_rate' if weak_off[0]['is_weekoff'] else 'holiday_ot_rate') or 0
		
		basic_amt = sum([(earning_deduction.get('earnings', {}).get(get_comp_name(abbr, 0), {}).get('default_amount') or 0) for abbr in ['B', 'BC', 'BCI', 'BSA']])
		from hrm.custom_script.employee_checkin.employee_checkin import get_employee_shift

		current_shift = get_employee_shift(employee=self.get('applicant'), for_date=getdate(self.get('ot_request_date')), consider_default_shift=True, next_shift_direction='forward')
		daily_working_hrs_minutes = (current_shift.end_datetime.replace(second=0)- current_shift.start_datetime.replace(second=0)).total_seconds()/60
		override_hrs = current_shift.shift_type.override_working_hours
		if override_hrs and override_hrs*60  > daily_working_hrs_minutes:
			daily_working_hrs_minutes = override_hrs*30
		else :
			### converted minutes too hours and divided by #0 working days i.e  30/60=1/2
			daily_working_hrs_minutes = daily_working_hrs_minutes/2
		# frappe.errprint("hii" + str(daily_working_hrs_minutes))
		frappe.errprint([basic_amt ,daily_working_hrs_minutes, ot_rate, (self.get('ot_hours') or 0)])
		self.ot_value = (basic_amt / daily_working_hrs_minutes) * ot_rate * (self.get('ot_hours') or 0)
	

	def is_single_punch(self):
		from hrm.custom_script.employee_checkin.employee_checkin import get_employee_shift

		current_shift = get_employee_shift(employee=self.get('applicant'), for_date=getdate(self.get('ot_request_date')), consider_default_shift=True, next_shift_direction='forward')

		if current_shift:
			logs = """SELECT *
				FROM `tabEmployee Checkin`
				WHERE skip_auto_attendance = 0
				AND employee = '{}'
				AND shift_start = '{}'
				AND shift_end = '{}'
				AND shift = '{}'
				ORDER BY employee, time""".format(self.get('applicant'), current_shift.start_datetime, current_shift.end_datetime, current_shift.shift_type.name)
			logs = frappe.db.sql(logs, as_dict=True)

			return len(logs)
		
		return 0

	def validate_sp(self):
		
		overtime_without_punch = self.get('apply_overtime_without_any_attendance_punches') or 0
	
		if self.is_single_punch()  < 2 and overtime_without_punch == 0:
			frappe.throw(_("OT Request for this date can be created only with 'Apply overtime without any attendance punches' as the system should have at least 2 punches"))
	
	def get_attedance(self):
			from hrm.custom_script.attendance.attendance import ot_worked
			attendance_list=frappe.db.sql("""select * from `tabAttendance` where docstatus=1 and employee="{0}" and attendance_date ='{1}'
			 and ot_hours>0""".format(self.get("applicant"),self.get("ot_request_date")), as_dict=True)
			if attendance_list:
					attendance_details = ot_worked(employee=self.get('applicant'), attendance_date=getdate(self.get('ot_request_date')), error=not bool(validate or 0))
					frappe.errprint([attendance_details,"attendance_details"])
					ot_start_time = attendance_details.get('ot_start_time') or get_datetime()
					ot_hours = attendance_details.get('ot_hours')
					self.from_time = get_time(ot_start_time).strftime("%H:%M:%S")
					self.to_time = get_time(ot_start_time + timedelta(seconds=ot_hours * 3600)).strftime("%H:%M:%S")
	def attendance_ot(self, validate=0):
		from hrm.custom_script.attendance.attendance import ot_worked
		attendance_list=frappe.db.sql("""select * from `tabAttendance` where docstatus=1 and employee="{0}" and attendance_date ='{1}'
			 and ot_hours>0""".format(self.get("applicant"),self.get("ot_request_date")), as_dict=True)
		att = attendance_list[0] if attendance_list else {}
		frappe.errprint([att.get('name'),"att.get('name')"])
		if not att.get('name'):
					frappe.throw(_('Attendance Not Proccessed'))
		if attendance_list:
				
				att_doc=frappe.get_doc("Attendance",attendance_list[0].name)
		
				attendance_details = ot_worked(employee=self.get('applicant'), attendance_date=getdate(self.get('ot_request_date')), error=not bool(validate or 0),doc=att_doc)
		
				ot_start_time = attendance_details.get('ot_start_time') or get_datetime()
		
		# self.from_time = get_time(ot_start_time).strftime("%H:%M:%S")
				ot_hours = att_doc.get('ot_hours')
				ot_hrs_min = ot_hours * 60				
				ot_rule_doc = frappe.get_doc('OT Rule', att_doc.ot_rule)
				if int(validate or 0) == 0:
					self.from_time = get_time(ot_start_time).strftime("%H:%M:%S")
					#self.to_time = get_time(ot_start_time + timedelta(seconds=ot_hours * 3600)).strftime("%H:%M:%S")
					self.to_time=att_doc.custom_out_time
					# frappe.errprint([self.to_time,get_time(self.to_time)])
					if attendance_details.get("out_time") and self.to_time and get_time(self.to_time) > get_time(attendance_details.get("out_time")) : 
						self.to_time = get_time(attendance_details.get("out_time")).strftime("%H:%M:%S")
				else:
					overtime_without_punch = 1
					#frappe.db.get_value('Employee', {'name': self.get('applicant')}, 'apply_overtime_without_any_attendance_punches')
					if not attendance_details.get("holiday_weekoff") and attendance_details.get("total_working_hours") :
						start_date = self.get('ot_request_date')
						start_date_time = '{} {}'.format(start_date, self.get('from_time'))
						if get_datetime(start_date_time) < ot_start_time:
							frappe.throw(_('OT Request from Time Should be greater then {}').format(ot_start_time))
					overtime_without_punch = self.get('apply_overtime_without_any_attendance_punches')
					if (overtime_without_punch or 0): return

					shift_end_time = get_time(ot_start_time).strftime("%H:%M:%S")
					otr_start_time = get_time(self.from_time).strftime("%H:%M:%S")
			
					if not otr_start_time == shift_end_time:
						frappe.throw(_('OT Request Start Time Should be {}').format(shift_end_time))

					end_date = self.get('ot_request_date')
					if get_time(self.get('from_time')) > get_time(self.get('to_time')):
						end_date = add_days(end_date, 1)
					end_date_time = '{} {}'.format(end_date, self.get('to_time'))
					otr_end_time = get_datetime(end_date_time)

					# shift_end_time = get_datetime(ot_start_time)

					last_punch = attendance_details.get('out_time')
					if not last_punch: return
					last_punch = get_datetime(last_punch)

					# if shift_end_time > otr_end_time:
					# 	frappe.throw(_('OT Request To Time Should be greater then {}').format(shift_end_time))
					if otr_end_time > last_punch:
						frappe.throw(_('OT Request To Time Should be less then {}').format(last_punch))
				import math
				self.ot_hours_minutes = flt(math.ceil(ot_hrs_min), 0)
				self.ot_hours = ot_hours
				self.ot_hours_time = timedelta(seconds=int(ot_hrs_min * 60))
				
				self.get_ot_amt(ot_rule_doc)