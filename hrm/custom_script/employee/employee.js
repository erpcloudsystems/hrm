frappe.ui.form.on("Employee", {
	setup: function(frm) {
		frm.trigger('filter_vacation_rule');

		frm.set_query('ot_rule', function(doc) {
			return {
				filters: {
					docstatus: 1
				}
			}
		});
	},

	refresh: function(frm) {
		frm.trigger('set_read_only');
	},

	eligible_for_airline_ticket: function(frm) {
		var eligible = frm.doc.eligible_for_airline_ticket;

		frm.set_df_property('class', 'reqd', eligible == 1 ? 1 : 0);
		frm.set_df_property('mode_of_reimbursement', 'reqd', eligible == 1 ? 1 : 0);
		frm.set_df_property('origin_airport', 'reqd',  eligible == 1 ? 1 : 0);
		frm.set_df_property('destination_airport', 'reqd', eligible == 1 ? 1 : 0);
		frm.set_df_property('number_of_trips', 'reqd', eligible == 1 ? 1 : 0);
		frm.set_df_property('year', 'reqd', eligible == 1 ? 1 : 0);
		frm.set_df_property('eligible_head_count_including_self', 'reqd', eligible == 1 ? 1 : 0);
		frm.set_value("number_of_trips", eligible == 1 ? 1 : 0);
		frm.set_value("year", eligible == 1 ? 1 : 0);

		if(frm.doc.eligible_for_airline_ticket == 0) {
			frm.set_value("class", undefined);
			frm.set_value("mode_of_reimbursement", undefined);
			frm.set_value("origin_airport", undefined);
			frm.set_value("destination_airport", undefined);
		}
	},

	mode_of_reimbursement: function(frm) {
		frm.set_df_property('eligible_cash', 'reqd', frm.doc.mode_of_reimbursement == "Cash" ? 1 : 0);
		if(!frm.doc.mode_of_reimbursement == "Cash") {
			frm.set_value("eligible_cash", 0);
		}
	},

	filter_vacation_rule: function(frm) {
		frm.fields_dict['vacation_rule'].get_query = function(doc) {
			return {
				filters: {
					docstatus: 1
				}
			}
		}
	},

	rejoining_date: function(frm) {
		if(frm.doc.rejoining_date && frm.doc.rejoining_date < frm.doc.date_of_joining) {
			frappe.throw("Vacation Rejoining Date Cannot be Less then Date of Joining");
		}
	},

	set_read_only: function(frm) {
		// set rejoining and vacation rule readonly if there is any vaction for future
		var result = frm.doc.__onload ? frm.doc.__onload.read_only : 0;
		frm.set_df_property('rejoining_date', 'read_only', result);
		frm.set_df_property('vacation_rule', 'read_only', result);
		frm.set_df_property('date_of_joining', 'read_only', result);
		frm.set_df_property('vacation_opening_balance', 'read_only', result);
	},

	first_name: function(frm) {
		if(frm.doc.firstname == undefined) {
			frm.set_value('employee_name', undefined);
		}
	},

	template: function(frm) {
		if (!frm.doc.template || !frm.doc.date_of_joining) {
			frm.set_value('documents', []);
			frm.refresh_field('documents');
			return
		}
		
		frappe.call({
			method: "hrm.doctype_triggers.hr.employee.employee.fetch_child",
			args:
			{
				"templete": frm.doc.template,
				"date_of_joining": frm.doc.date_of_joining,
			},
			callback: function (r) {
				frm.set_value('documents', r.message);
				frm.refresh_field('documents');
			}
		});
	}
});