// Copyright (c) 2020, AVU and contributors
// For license information, please see license.txt

frappe.ui.form.on('Attendance Amendment', {
	setup: function(frm) {
		frm.set_query("employee", erpnext.queries.employee);
	},

	refresh: function(frm) {
		frm.trigger('toggle_field');
	},

	employee: function(frm) {
		frm.trigger('processed_attendance');
	},

	attendance_date: function(frm) {
		frm.trigger('processed_attendance');
	},
    on_cancel: function(frm) {
        console.log(frm.doc.attendance ,"frm.doc.attendance ")
        if (frm.doc.attendance  ){
            frappe.validated=false
            frappe.throw("Application Cannot be Cancelled")
        }
        else{
            frappe.validated=true
        }
    },
	processed_attendance: function(frm) {
		if (!frm.doc.employee || !frm.doc.attendance_date) return

		frappe.call({
			method: 'processed_attendance',
			doc: frm.doc,
			args: { },
			callback: function(r) {
				frm.refresh_fields();
				frm.trigger('toggle_field');
			}
		})
	},

	amended_status: function(frm) {
		frm.set_value('amended_in_time', frm.doc.amended_status == 'Present' ? frm.doc.in_time: '00:00:00');
		frm.set_value('amended_out_time', frm.doc.amended_status == 'Present' ? frm.doc.out_time: '00:00:00');
		frm.set_value('amended_shift', frm.doc.amended_status == 'Present' ? frm.doc.shift: undefined);
		frm.trigger('toggle_field');
	},

	toggle_field: function(frm) {
		frm.toggle_enable('amended_in_time', frm.doc.amended_status == 'Present' ? 1: 0);
		frm.toggle_enable('amended_out_time', frm.doc.amended_status == 'Present' ? 1: 0);
		frm.toggle_enable('amended_shift', frm.doc.amended_status == 'Present' ? 1: 0);
		frm.toggle_reqd('amended_shift', frm.doc.amended_status == 'Present' ? 1: 0);
	}
});
