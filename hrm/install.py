import frappe
from frappe import _
import json
import os
# from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
# from hrm.custom_script.leave_type.default_leave_type import DEFAULT_LEAVE_TYPE

def after_install():
	add_data()
	frappe.db.commit()
	

@frappe.whitelist()
def add_data(company):
	# path_to_json = "/home/debian/frappe-bench/apps/hrm/hrm/setup_wizard/"
	# json_files = [file_name for file_name in os.listdir(path_to_json) if file_name.endswith('.json')]
	master_data = json.loads(open(frappe.get_app_path("hrm", "setup_wizard", "default_data.json")).read())
	# frappe.errprint(str(master_data))
	try:
		if master_data:
			# frappe.errprint(master_data)
			for data in master_data:
				# frappe.errprint(data["doctype"])
				# settings = frappe.get_doc(data["doctype"])
				is_single_doc = frappe.db.get_value("DocType", data["doctype"], "issingle")
				# frappe.errprint(is_single_doc)
				if is_single_doc != 1:
					old_data = frappe.db.get_all(data["doctype"])
					if old_data:
						for d in old_data:
							del_doc = frappe.get_doc(data["doctype"], d["name"])
							if del_doc.get('company') and del_doc.get('company') != company: continue 
							# frappe.errprint(del_doc.docstatus)
							if del_doc.docstatus == 1 and data["doctype"] != "Benefit Type for EOS":
								del_doc.cancel()
							# frappe.delete()
							if data["doctype"] != "Benefit Type for EOS":
								frappe.delete_doc(data["doctype"], d["name"], force=1)

				#     frappe.db.sql("DELETE FROM `tab{0}`".format(data["doctype"]))
				#     frappe.db.commit()
				
				doc = {}
				doc = {**doc, **{'doctype': data["doctype"]}}
				for d in range(0,len(data["data"])):
					# frappe.errprint(data["data"][d])
					doc1 = {}
					doc1 = {**doc, **data["data"][d]}
					doc1['company'] = company
					if data["doctype"] == "Benefit Type for EOS" :
						if frappe.db.exists({'doctype': data["doctype"],"name":doc1["name"]}) : continue 
					# frappe.errprint(doc1)
					entry = frappe.get_doc(doc1)
					# frappe.errprint(entry.name)
					entry.insert(ignore_permissions=True,ignore_mandatory=True)
					# frappe.msgprint("In Json file Page {} at row {}".format(data["doctype"], d.idx))
					if "docstatus" in doc:
						if doc["docstatus"] == 1 :
							entry.run_method("submit")
		frappe.msgprint("Configure HRM Successfully!")

	except frappe.ValidationError:
		frappe.throw("In Json file DocType {} at Row {}".format(data["doctype"], d+1))
		pass
		# frappe.throw(frappe.ValidationError)
	except:
		frappe.throw("In Json file DocType {} at Row {}".format(data["doctype"], d+1))
		pass
		# frappe.errprint(data[0].data)
		# with open(path_to_json + file_name) as json_file:
		# data = json.load(json_file)
			# if data:
			#     for d in data:
					# frappe.errprint(d)
					# frappe.get_doc(d).insert(ignore_permissions=True)
		
