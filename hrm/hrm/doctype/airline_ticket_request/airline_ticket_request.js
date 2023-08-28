// Copyright (c) 2018, Digitalprizm and contributors
// For license information, please see license.txt

frappe.ui.form.on('Airline Ticket Request', {
	setup: function(frm) {
		frm.add_fetch("employee", "employee_name", "employee_name");
		frm.add_fetch("airline_agent", "name1", "agent_name");
	},

	refresh: function(frm) {
		if(frm.is_new()) {
			frm.trigger('valid_head_count');
			frm.trigger('number_of_eligible_tickets');
		}
	},

	employee: function(frm) {
		if (!frm.doc.employee) {
			frm.set_value('employee_name', undefined);
		}

		frm.trigger('valid_head_count');
	},

	airline_agent: function(frm) {
		if (!frm.doc.airline_agent) {
			frm.set_value('agent_name', undefined);
		}
	},

	to_date: function(frm) {
		frm.trigger('from_date');
	},

	from_date: function(frm) {
		frm.trigger('date_validate');
		frm.trigger('reason');
	},
	
	reason: function(frm) {
		frm.trigger('valid_head_count');
		frm.trigger('set_passenger');
	},

	date_validate: function(frm) {
		if(frm.doc.from_date && frm.doc.to_date && (frm.doc.from_date >= frm.doc.to_date)) {
			frappe.throw({ title: "Mandatory",
				message: "To Date Should not be less than or equal to From Date"
			});
		}
	},
		
	number_of_eligible_tickets: function(frm) {
		if (frm.doc.reason == "Vacation" && ((frm.doc.number_of_eligible_tickets || 0) > (frm.doc.available_tickets || 0))) {
			frappe.throw({ title: "Mandatory",
				message:"Eligible tickets should not be greater than Available tickets"
			});
		}

		frm.trigger('set_passenger');
	},

	set_passenger: function(frm) {
		frm.set_value("passenger_names", "");
		if(frm.doc.employee && (frm.doc.number_of_eligible_tickets || 0) > 0) {
			frappe.call({
				method: "family_members",
				args: {	},
				doc: frm.doc,
				async:false,
				callback: function(r) {
					frm.refresh_field('passenger_names');
				}
			});
		}
	},

	valid_head_count: function(frm) {
		['origin_airport', 'destination_airport', 'class', 'available_tickets'].forEach(field => {
			frm.set_value(field, undefined);
		});

		if(frm.doc.employee && frm.doc.reason && frm.doc.from_date) {
			frappe.call({
				method: "head_count",
				args: { },
				doc: frm.doc,
				async: false,
				callback: function(r) {
					frm.refresh_fields();
				}
			});
		}
	}
});