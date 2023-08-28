// Copyright (c) 2021, AVU and contributors
// For license information, please see license.txt

frappe.ui.form.on('OT Request', {
	refresh: function(frm) {
		frappe.db.get_value('Employee', {
			'user_id': frappe.session.user
		}, 'name',
		(r) => {
			frm.toggle_enable('applicant', !(r && r.name));
		});

		if (!frm.is_new()) {
			if (frm.doc.__onload && frm.doc.__onload.sp_warning && frm.doc.docstatus < 2) {
				var msg = repl(`<span style="color: red; font-weight: bold;">%(msg)s</span>`, {msg : frm.doc.__onload.sp_warning});
				frm.dashboard.set_headline(msg);
			}
		}
		else {
            frm.set_value("apply_overtime_without_any_attendance_punches",1)
			frm.trigger('applicant');
		}

	},

	applicant: function(frm) {
		//frm.trigger('attendance_log');
	},

	ot_request_date: function(frm) {
	
       frm.trigger('attendance_log');
	},

	from_time: function(frm) {
		frm.trigger('get_ot');
	},

	to_time: function(frm) {
		frm.trigger('get_ot');
	},

	get_ot: function(frm) {
		frm.set_value('ot_hours', 0.0);
		frm.set_value('ot_hours_minutes', 0);
		frm.set_value('ot_hours_time', '00:00');
		frm.set_value('ot_value', 0);

		if (!frm.doc.applicant || !frm.doc.ot_request_date || !frm.doc.from_time || !frm.doc.to_time) return;
		frappe.call({
			method: 'attendance_ot',
			doc: frm.doc,
			args: {
				validate: 0
			},
			callback: function(r) {
				refresh_many(['ot_hours', 'ot_hours_minutes', 'ot_value', 'ot_hours_time']);
			}
		});
	},
	apply_overtime_without_any_attendance_punches : function(frm) {
		if(frm.doc.apply_overtime_without_any_attendance_punches){frm.set_value('ot_hours', 0.0);
		frm.set_value('ot_hours_minutes', 0);
		frm.set_value('ot_hours_time', '00:00');
		frm.set_value('ot_value', 0);
		frm.set_value('from_time', "");
		frm.set_value('to_time', "");
		refresh_many(['ot_hours', 'ot_hours_minutes', 'ot_value', 'ot_hours_time','from_time','to_time']);}
		else 
		frm.trigger('attendance_log');
	},
	attendance_log: function(frm) {
		if (!frm.doc.applicant || !frm.doc.ot_request_date) return;

		frappe.call({
			method: 'attendance_ot',
			doc: frm.doc,
			args: {
				validate: 0
			},
			callback: function(r) {
				refresh_many(['from_time', 'to_time']);
				frm.trigger('get_ot');
			}
		});
	}
});
