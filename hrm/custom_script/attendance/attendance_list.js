// Copyright (c) 2020, avu and contributors
// For license information, please see license.txt

frappe.listview_settings['Attendance'] = {
	// add_fields: ["status", "attendance_date", "leave_type"],
	filters: [["docstatus","!=", "2"]],
	onload: function(doc) {
		doc.columns.push({
			type: "Field",
			df: doc.meta.fields.filter((df) => {
				if (df.fieldname === "status") {
					return true;
				}
			})[0]
		});

		doc.$result.find('.list-row-head').remove();

		doc.columns = this.reorder_listview_fields(doc);
		doc.render_header();

		// doc.filter_area.set([{
		// 	fieldtype: 'Select',
		// 	label: __('Document Status'),
		// 	fieldname: 'docstatus',
		// 	option: ['Draft', 'Sumbitted', 'Cancelled']
		// }]);
	},

	reorder_listview_fields: function(doc) {
		let fields_order = [];
		let fields = ['status', 'leave_type', 'attendance_date','custom_in_time','custom_out_time'];
		//title and tags field is fixed
		fields_order.push(doc.columns[0]);
		fields_order.push(doc.columns[1]);
		doc.columns.splice(0, 2);
        
		for (let fld in fields) {
			for (let col in doc.columns) {
				let field = fields[fld];
				let column = doc.columns[col];

				if (column.type == "Field" && field == column.df.fieldname) {
					fields_order.push(column);
					break;
				}
			}
		}
		
		return fields_order;
	},


	// get_indicator: function(doc) {
	// 	if (doc.leave_type) {
	// 		return [__(doc.leave_type), doc.status=="Present" ? "green" : "darkgrey", "leave_type,=," + doc.leave_type];
	// 	}
	// 	return [__(doc.status), doc.status=="Present" ? "green" : "darkgrey", "status,=," + doc.status];
	// }
};