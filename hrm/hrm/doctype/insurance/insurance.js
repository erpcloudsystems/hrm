// Copyright (c) 2018, Digitalprizm and contributors
// For license information, please see license.txt

frappe.ui.form.on('Insurance', {
	refresh: function (frm) {
		frm.fields_dict['insurance_details'].grid.get_field("employee").get_query = function (doc, cdt, cdn) {
			return {
				filters: [
					['Employee', 'status', '=', 'Active']
				]
			}
		}
	},
	validate: function (frm) {
		// frappe.msgprint("welcome")
		var insurance_type = cur_frm.doc.insurance_type
		var insurance_details = cur_frm.doc.insurance_details.length
		if (insurance_type == "Individual" && insurance_details > 1) {
			frappe.throw("Cannot Assign More Than One Detail for Insurance Type \"Individual\"")
		}
		cur_frm.set_value("count", insurance_details)
		// inactive(frm)




	},
	insurance_start_date: function (frm) {
		data_validation(frm);
	},
	insurance_end_date: function (frm) {
		data_validation(frm);
	},



});

function data_validation(frm) {

	var from_date = moment(cur_frm.doc.insurance_start_date);
	var to_date = moment(cur_frm.doc.insurance_end_date);
	var today = moment();
	if (cur_frm.doc.insurance_start_date && cur_frm.doc.insurance_end_date) {

		if (from_date > to_date) {
			frappe.msgprint
				({
					title: __("You can not select Future Date"),
					message: __("Insurance Start Date  should be less than Insuarance End Date"),
					indicator: "red"
				})
		}
	}
}







frappe.ui.form.on('Insurance Details', {

	employee: function (frm) {
		var find_val, pr_val;
		var len_val = cur_frm.doc.insurance_details.length;


		if (len_val > 1) {
			//console.log(len_val);

			pr_val = cur_frm.doc.insurance_details[len_val - 1].employee;
			//console.log(pr_val)

			for (var i = 0; i < len_val - 1; i++) {
				//console.log(i);
				find_val = cur_frm.doc.insurance_details[i].employee;
				if (pr_val == find_val) {
					cur_frm.doc.insurance_details[len_val - 1].employee = "";
					cur_frm.doc.insurance_details[len_val - 1].employee_name = "";
					cur_frm.doc.insurance_details[len_val - 1].employee_contribute = "";
					cur_frm.doc.insurance_details[len_val - 1].eligible_class = "";
					cur_frm.doc.insurance_details[len_val - 1].inactive = "";
					cur_frm.doc.insurance_details[len_val - 1].remark = "";

					cur_frm.refresh_field("insurance_details")
					frappe.throw({ title: "Duplicate Data", message: "" + find_val + " Record Already Exit" });
				}
			}
		}
		//console.log(find_val+' pv '+pr_val);
	}
})



frappe.ui.form.on("Insurance", "refresh", function (frm) {
	frm.set_df_property("insurance_no", "read_only", frm.doc.__islocal ? 0 : 1);
	frm.set_df_property("insurance_start_date", "read_only", frm.doc.__islocal ? 0 : 1);
	frm.set_df_property("insurance_amount", "read_only", frm.doc.__islocal ? 0 : 1);
	frm.set_df_property("insurance_end_date", "read_only", frm.doc.__islocal ? 0 : 1);
	frm.set_df_property("insurance_type", "read_only", frm.doc.__islocal ? 0 : 1);
	frm.set_df_property("insurance_details", "read_only", frm.doc.__islocal ? 0 : 1);
	frm.set_df_property("insurance_start_date", "read_only", frm.doc.__islocal ? 0 : 1);
	frm.set_df_property("comments", "read_only", frm.doc.__islocal ? 0 : 1);
	frm.set_df_property("class", "read_only", frm.doc.__islocal ? 0 : 1);
})




		// frappe.ui.form.on("Insurance", 
		// {
		// 	validate: function(frm) 
		// {
		// 	// insurance_table_length = cur_frm.doc.insurance_details.length
		// 	if(cur_frm.doc.insurance_details.length<1)
		// 	{
		// 		frappe.msgprint("Please Insert Some Data In Insurance Details For Insurance")
		// 	}

		// }
		// })
