// Copyright (c) 2018, Digitalprizm and contributors
// For license information, please see license.txt


frappe.ui.form.on('Salary Allowance Process', {
	setup: function(frm) {
		frm.add_fetch('payroll_period', 'start_date', 'from_date');
		frm.add_fetch('payroll_period', 'end_date', 'to_date');

		frm.set_query('department', function() {
			return {
				filters: {
					company: frm.doc.company
				}
			}
		});

		frm.set_query('payroll_period', function() {
			return {
				filters: {
					'company': frm.doc.company
				}
			}
		});
	},

	refresh: function(frm) {
		frm.disable_save();
		hide_field('section_break_18');
		hide_field('section_break_3');
		// frm.set_value('allowance_type', 'Daily');
		frm.trigger('allowance_type');
		$(frm.fields_dict.company.$wrapper).closest('.col-sm-2').addClass('col-sm-4').removeClass('col-sm-2');
		frm.set_value('company', frappe.defaults.get_user_default("Company"));
		frm.fields_dict.get_template.$input.addClass('btn btn-primary');
	},

	allowance_type: function(frm) {
		frm.set_value('payroll_period', undefined);
		if(frm.doc.allowance_type == 'Daily') {
			frm.set_df_property('from_date', 'reqd', 1);
			frm.set_df_property('payroll_period', 'reqd', 0);
			frm.set_df_property('from_date', 'read_only', 0);
			frm.fields_dict["from_date"].label_area.textContent = 'Date';
			$(frm.fields_dict.payroll_period.$wrapper).closest('.form-column').hide();
		}
		else {
			frm.set_df_property('from_date', 'reqd', 0);
			frm.set_df_property('payroll_period', 'reqd', 1);
			frm.set_df_property('from_date', 'read_only', 1);
			frm.fields_dict["from_date"].label_area.textContent = 'From Date';
			$(frm.fields_dict.payroll_period.$wrapper).closest('.form-column').show();
		}
	},

	company: function(frm){
		frm.set_value('department', undefined);
		frm.trigger('alter_template');
	},

	from_date: function(frm) {
		frm.trigger('alter_template');
	},

	department: function(frm) {
		frm.trigger('alter_template');
	},

	designation: function(frm) {
		frm.trigger('alter_template');
	},

	branch: function(frm) {
		frm.trigger('alter_template');
	},
	
	alter_template: function(frm) {
		frm.trigger('excel_upload');
		if(frm.doc.from_date && frm.doc.company) {
			unhide_field('section_break_18');
			unhide_field('section_break_3');
			frm.trigger('rend_html');
		}
		else {
			hide_field('section_break_18');
			hide_field('section_break_3');
		}
	},

	get_template: function(frm) {
		window.location.href = repl(frappe.request.url +
			'?cmd=%(cmd)s&company=%(company)s&from_date=%(from_date)s&to_date=%(to_date)s', {
				cmd: "hrm.hrm.doctype.salary_allowance_process.salary_allowance_process.get_template",
				company: encodeURIComponent(frm.doc.company),
				from_date: encodeURIComponent(frm.doc.from_date),
				to_date: encodeURIComponent(frm.doc.to_date)
			});
	},

	excel_upload: function(frm) {
		var $wrapper = $(frm.fields_dict.upload_salary_allowance_process.wrapper).empty();
		new frappe.ui.FileUploader({
			wrapper: $wrapper,
			method: 'hrm.hrm.doctype.salary_allowance_process.salary_allowance_process.excel_upload',
			// allow_multiple: 0,
			on_success: function(attachment, r) {
				$.fn.set_employee_comp(r.message, 'change');
			}
		});
	},

	rend_html: function(frm) {
		if (!frm.doc.__islocal) {
			frappe.call({
				method:"get_data",
				doc:frm.doc,
				args: { },
				freeze: true,
				freeze_message: __("Data is Loading, it might take some time"),
				callback: function(r) {
					$(frm.fields_dict['adjustment'].wrapper)
						.html(frappe.render_template("salary_allowance_process", r.message[0]));
					$.fn.script_sal_allow_process(frm);

					$("#Update_data").on('click', function() {
						$.fn.process(frm);
					});

					$.fn.decimal_validate();
					$.fn.previous_record(frm);
				}
			})
		}
	},

	payroll_period: function(frm) {
		if(!frm.doc.payroll_period) {
			frm.set_value('from_date', undefined);
			frm.set_value('to_date', undefined);
			$(frm.fields_dict.adjustment.wrapper).empty();
		}
	}
});

$.all_pages;
$.fn.script_sal_allow_process = function(frm) {
	var $tabObject = $("#emp_table").DataTable({
		'columnDefs': [{
			'bSortable': false,
	 		'aTargets': 'no-sort'
		}],
		"scrollX": true,
		"scrollY": 450,
		"scrollCollapse": true,
		'retrieve': true,
		"paging": false,
		'bSort': true,
		"searching": true,
		"bLengthChange": true,
		"stateSave": true,	
	});
	$tabObject.order( [[0, 'asc' ]] )
		.search('')
		.draw();
	
	$.all_pages = $tabObject.cells( ).nodes( );
	$.fn.body_trigger(frm);
}

$.fn.list_emp = function(id) {
	return {
		'sort_val': id,
		'emp_name': $('#'+$.fn.jq(id)).closest('tr').attr('id'),
		"comp_name": $("#"+$.fn.jq(id)).closest('table').find('th').eq($("#"+$.fn.jq(id)).closest('td').index()).text(),
		"comp_val": $("#"+$.fn.jq(id)).val() || 0
	}
}

$.get_list = [];
$.fn.create_list = function(id) {
	$.get_list = $.grep($.get_list, function(item) {
		return item.sort_val != id;
	} ,false);

	$.get_list.push($.fn.list_emp(id));
}

//to ignore special character
$.fn.jq = function( myid ) {
	return "" + myid.replace( /([ #;&,.+*~\':"!^$[\]()=>|\/@])/g, "\\$1" );
}

$.fn.date_val = function(frm, id=null) {
	if(!frm.doc.from_date) {
		if(id) {
			$("#"+$.fn.jq(id)).val($("#"+$.fn.jq(id)).defaultValue);
		}
		frappe.throw({ title: "Mandatory",
			message: "Please Select Date Before Process"
		});
	}
	else {
		return 1
	}
}

$.fn.body_trigger = function(frm) {
	$("#emp_table_body").on("change", function(e) {
		var $id = e.target.id;
		var $def_val = e.target.defaultValue || 0;
		var $new_val = e.target.value || 0;
		// console.log($def_val, $new_val)
		if ($def_val != $new_val && $.fn.date_val(frm, $id)) {
			$.fn.create_list($id);
			$("#"+$.fn.jq($id)).attr('value', $new_val);
		}
	});
}

$.fn.process = function(frm) {
	$.fn.date_val(frm);

	if(frm.doc.from_date && $.get_list) {
		frappe.call({
			method: "update_sal_adj",
			doc: frm.doc,
			args: {
				"sal_comp_val": $.get_list
			},
			freeze: true,
			freeze_message: __("Data is Uploading, it might take some time"),
			callback: function(r) {
				frappe.msgprint(r.message);
				$.get_list = [];
			}
		});
	}
}

$.fn.previous_record = function(frm) {
	$.fn.date_val(frm);

	if(frm.doc.from_date) {
		frappe.call({
			method: "get_prev_data",
			doc: frm.doc,
			args: {	},
			freeze: true,
			freeze_message: __("Data is Loading, it might take some time"),
			callback: function(r) {
				$.fn.set_employee_comp(r.message);
				$.fn.disable_field_salary_slip(frm);
			}
		});
	}
}

$.fn.set_employee_comp = function(employee, trigger=undefined) {
	$(employee || []).each((idx, emp_row) => {
		var $row = $("#"+$.fn.jq(emp_row["employee"])).index();
		// console.log($row)
		var $col = $('th:contains('+emp_row["salary_component"]+')').index() - 4;
		// console.log($col)
		if (!$("#comp_val_"+$row+"_"+$col).prop('readonly')) {
			$("#comp_val_"+$row+"_"+$col).val(emp_row["value"]);
			
			if (trigger) {
				$("#comp_val_"+$row+"_"+$col).trigger(trigger);
			}
			else {
				$("#comp_val_"+$row+"_"+$col).attr('value', emp_row["value"]);
			}
		}
	});
}

$.fn.disable_field_salary_slip = function(frm) {
	frappe.call({
		method: "salary_slip_val",
		doc: frm.doc,
		args: {	},
		freeze: true,
		freeze_message: __("Data is Loading, it might take some time"),
		callback: function(r) {
			if(r.message) {
				for(var k = 0; k < r.message.length; k++) {
					var $row = $("#"+$.fn.jq(r.message[k]["employee"])).index();
					for(var j = 0; j < $("thead th").length - 4; j++) {
						$("#comp_val_"+$row+"_"+j).attr("readonly", "readonly").css("background-color", "#d9dddd");
						$("#"+$.fn.jq(r.message[k]["employee"])).css("background-color", "#d9dddd");

					}	
				}
			}
		}
	});
}

$.fn.decimal_validate = function() {
	$(".validate_number").on("keypress keyup blur",function (event) {
 		$(this).val($(this).val().replace(/[^0-9\.]/g,''));
		if ((event.which != 46 || $(this).val().indexOf('.') != -1) && (event.which < 48 || event.which > 57)) {
			$(".error").html(event.which);
			event.preventDefault();
		}
	});
}