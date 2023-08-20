frappe.ui.form.on('Shift Type', {
	refresh: function(frm) {
		frm.trigger('weekoff');
	},

	weekoff: function(frm) {
		frm.add_custom_button(__('Mark Holiday Attendance'), () => {
			frappe.call({
				method: 'hrm.custom_script.attendance.holiday_attendance.holiday_attendance',
				args: {
					process: 1,
					shift: frm.doc.name
				},
				freeze: true,
				freeze_message: __('Marking Holiday Attendance'),
				callback: function() {
					frappe.msgprint(__("Attendance has been marked as per holiday list"));
				}
			})
		});
	}
});