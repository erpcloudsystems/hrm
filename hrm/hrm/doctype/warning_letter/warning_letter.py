# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime

class WarningLetter(Document):
	pass
@frappe.whitelist()
def previous_warning(employee):
	sql1=("select * from `tabWarning Letter` where employee_id='"+employee+"' ")
	sql2=frappe.db.sql(sql1,as_dict = True)
	if sql2:
		date_list = []
		data = ("select warning_no as count,date from `tabWarning Letter` where employee_id='"+employee+"' order by warning_no desc limit 1 " )
		sql = frappe.db.sql(data,as_dict = True)
		p = frappe.session.user
		date_list.append(p)
		if sql:
			count=sql[0]['count']
			date1=sql[0]['date']
			
		
			t=frappe.utils.data.getdate(date1)
			date_strings = t
			
      

			warning_no =int(count)+1
			date_list.append(warning_no)
		
		date_list.append(date_strings)
		
		return date_list
	else:
		date_list = []
		data = ("select count(employee_id) as count from `tabWarning Letter` where employee_id='"+employee+"' ")
		sql = frappe.db.sql(data,as_dict = True)
		p = frappe.session.user
		
		date_list.append(p)
		if sql:
			count=sql[0]['count']
		
			
			t=""
			
			

			warning_no =int(count)+1
			date_list.append(warning_no)
		
		date_list.append(t)
		
		return date_list


  

	
  
  
	
  
  