// Copyright (c) 2018, Digitalprizm and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exit ReEntry Visa', {
	setup: function(frm) {
		frm.add_fetch("employee", "employee_name", "employee_name");
		frm.add_fetch("airline_agent", "name1", "agent_name");
	},
	
	refresh: function(frm) {
		frm.trigger('email_pop');
		if(frm.is_new())
			frm.trigger('set_passenger');
	},

	employee: function(frm) {
		if (!frm.doc.employee) {
			frm.set_value('employee_name', undefined);
		}

		frm.trigger('set_passenger');
	},

	airline_agent: function(frm) {
		if (!frm.doc.airline_agent) {
			frm.set_value('agent_name', undefined);
		}
	},
	
	number_of_reentries_required: function(frm) {
		frm.trigger('set_passenger');

		if (frm.doc.number_of_reentries_required && frm.doc.number_of_reentries_required <= 0) {
			frappe.throw({ title: "Mandatory",
				message: "Number Re-Entry Cannot Be Zero."
			});
		}
	},

	set_passenger: function(frm) {
		frm.set_value("passenger_names", "");
		if(frm.doc.employee && (frm.doc.number_of_reentries_required || 0) > 0) {
			frappe.call({
				method: "family_members",
				args: {	},
				doc: frm.doc,
				async: false,
				callback: function(r) {
					frm.refresh_field('passenger_names');
				}
			});
		}
	},

	reentry_charges: function(frm) {
		if (frm.doc.reentry_charges && frm.doc.reentry_charges < 0) {
			frappe.throw({ title: "Mandatory",
				message: "Re-Entry charges Cannot Be Negative."
			});
		}
	},

	from_date: function(frm) {
		frm.trigger('date_validate');
	},

	to_date: function(frm) {
		frm.trigger('date_validate');
	},

	date_validate: function(frm) {
		if(frm.doc.from_date && frm.doc.to_date && (frm.doc.from_date >= frm.doc.to_date)) {
			frappe.throw({ title:"Mandatory",
				message: "To Date Should not be less than or equal to From Date"
			});
		}
	},

	email_pop: function(frm){
		if(frm.doc.__last_sync_on &&  frm.doc.docstatus != 2) {
			frm.add_custom_button(('Email'), function(frm) {
				// var user=frappe.session.user_email;
				new frappe.views.CommunicationComposer(
				//     sender:user,
				//     subject: "Exit ReEntry Visa: "+frm.doc.name+"Employee Name: "+frm.doc.employee_name,
				//     recipients:"jagdishr@avu.net.in",
				// message:"The above employee has been allocated respective amount as traving expance"
				);
			});
		}
	}
});
