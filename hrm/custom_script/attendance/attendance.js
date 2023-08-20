frappe.ui.form.on('Attendance', {
	refresh: function(frm) {
		if (frm.is_new())
			frm.set_value('amended_request', undefined);
	}
});


cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(doc.__islocal && !doc.amended_from) cur_frm.set_value("attendance_date", frappe.datetime.get_today());
}