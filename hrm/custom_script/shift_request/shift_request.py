
from __future__ import unicode_literals
import frappe,json
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate, getdate

@frappe.whitelist()
def oncancel(shift_allocation):
    new_val=0
    if shift_allocation:
        new_doc=frappe.get_doc("Shift Allocation",shift_allocation)
        if new_doc:
            new_val=1
            # frappe.throw("Shift Request cannot be cancelled as it is linked with Shift Allocation <b><a href='#Form/Shift Allocation/"+shift_allocation+"'>"+shift_allocation+"</a></b>")
    return new_val        
            

