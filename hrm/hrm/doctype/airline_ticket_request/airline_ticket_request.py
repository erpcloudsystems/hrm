# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, add_days, getdate, add_months, add_years

class AirlineTicketRequest(Document):

	def validate(self):
		self.validate_entry()
		self.validate_date()

	def validate_entry(self):
		if self.from_date and self.to_date and (getdate(str(self.from_date)) >= getdate(str(self.to_date))):
			frappe.throw("To Date Should not be less than or equal to From Date")

		if (self.number_of_eligible_tickets or 0) <= 0:
			frappe.throw("Eligible tickets should not be zero")
		
		if self.reason == "Vacation":
			if (self.available_tickets or 0) <= 0:
				frappe.throw("Sorry Employee <a href='#Form/Employee/{0}'>{0}</a> has no more Privilege to take more Tickets".format(self.employee))
			
			if self.number_of_eligible_tickets > self.available_tickets:
				frappe.throw("Eligible tickets should not be greater than Available tickets")

	def validate_date(self):
		data_val_sql = """SELECT *
			FROM `tabAirline Ticket Request`
			WHERE docstatus = 1
			AND (from_date BETWEEN '{0}' AND '{1}'
				OR to_date BETWEEN '{0}' AND '{1}')
			AND employee = '{2}'""".format(self.from_date, self.to_date, self.employee) 
		data_val_sql_res = frappe.db.sql(data_val_sql, as_dict=True)
		if data_val_sql_res:
			frappe.throw("There is a trip already allocated between this period")

	def family_members(self):
		passanger_detail = "Name     Gender     Date of Birth\n"

		family_sql = """
		(SELECT employee_name AS name, gender, DATE_FORMAT(date_of_birth, "%d-%m-%Y") AS date_of_birth
		FROM `tabEmployee`
		WHERE name = '{0}'
		LIMIT 1)
		
		UNION ALL
		
		(SELECT member_name AS name, gender, DATE_FORMAT(date_of_birth, "%d-%m-%Y") AS date_of_birth
		FROM `tabFamily Details`
		WHERE parent = '{0}'
		{1} LIMIT 0
		)""".format(self.employee, '--' if (self.number_of_eligible_tickets or 0) > 1 else '')
		family_sql_res = frappe.db.sql(family_sql, as_dict=0)

		if family_sql_res: self.passenger_names = passanger_detail + '\n'.join('     '.join(map(str, row)) for row in family_sql_res)
		
		
	def head_count(self):
		emp_sql = """SELECT number_of_trips, eligible_head_count_including_self, year, date_of_joining, origin_airport, destination_airport, class, gender, date_of_birth ,number_of_trips * eligible_head_count_including_self AS eligible
			FROM `tabEmployee`
			WHERE name = '{0}'""".format(self.employee)
		emp_result = frappe.db.sql(emp_sql, as_dict=1)

		if emp_result:
			emp_result = emp_result[0]
			self.origin_airport = emp_result['origin_airport']
			self.destination_airport = emp_result['destination_airport']
			self.set('class', emp_result['class'])

			if self.from_date and self.reason and self.reason == "Vacation" and (emp_result['year'] or 0):
				day_diff = 0
				
				day_diff = date_diff(self.from_date, emp_result['date_of_joining'])
				day_diff = day_diff % (365 * emp_result['year'])
				
				from_date = add_days(self.from_date, -1 * day_diff)
				to_date = add_days(add_years(self.from_date, emp_result['year']), -1)

				self.req_head_count(from_date, to_date, emp_result['eligible'] or 0)
	
	def req_head_count(self, from_date, to_date, eligible):
		head_count_sql = """SELECT COUNT(from_date) year_count, SUM(number_of_eligible_tickets) ticket_count
			FROM `tabAirline Ticket Request`
			WHERE employee = '{2}'
			AND reason = 'Vacation'
			AND from_date BETWEEN '{0}' AND '{1}'""".format(from_date, to_date, self.employee)
		head_count_result = frappe.db.sql(head_count_sql, as_dict=1)

		if head_count_result:
			head_count_result = head_count_result[0]
			self.available_tickets = eligible - int(head_count_result['ticket_count'] or 0)
			if (self.number_of_eligible_tickets or 0) > self.available_tickets: self.number_of_eligible_tickets = 0