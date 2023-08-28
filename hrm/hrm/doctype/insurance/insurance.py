# -*- coding: utf-8 -*-
# Copyright (c) 2018, Digitalprizm and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json 
from frappe import _


class Insurance(Document):
    def validate(self):
        # frappe.throw("hieee")
        error_list=[]
        insurance_start_date = self.insurance_start_date
        insurance_end_date = self.insurance_end_date
        docname=self.name
        # employee_details = self.insurance_details
            
   
        for q in range(0,len(self.insurance_details)):
            employee = self.insurance_details[q].employee
            # in_active = self.insurance_details[q].inactive
            # frappe.throw(str(in_active))

            sql = "SELECT * from `Insurance_View` where ('{0}' between insurance_start_date and insurance_end_date or '{1}' between insurance_start_date and insurance_end_date ) and employee = '{2}'and Istatus=0 and parent!='{3}'".format(insurance_start_date,insurance_end_date,employee,docname)
            # frappe.msgprint(str(sql))
            data = frappe.db.sql(sql,as_dict=1)
            # frappe.msgprint(str(data))
            if data:
                # frappe.msgprint(str(data))
                error_list.append("Insurance for '"+docname+"' Already Exits for Employee '"+employee+"'")
                # frappe.validate=False
		

		# for t in range(0,len(error_list)):
        if error_list:
            for n in error_list:
                frappe.msgprint(_(n))

            frappe.throw("")
		
# @frappe.whitelist()
# def dulpicate_employee(insurance_detail):
#     child_insurance_details = json.loads(insurance_detail)
#     for e in child_insurance_details:
#         # employee_id = e["employee"]
#         emp=frappe.db.sql("select employee,employee_name from `tabInsurance Details` ",as_dict=True)


#         return emp