// Copyright (c) 2020, avu and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Portal', {
	refresh: function(frm) {
		frm.disable_save();

		$(frm.fields_dict.dashboard.wrapper).empty();
		frm.dashboard_wrapper_holder = $('<div>')
			.appendTo(frm.fields_dict.dashboard.wrapper);
		frm.dashboard_wrapper = new erpnext.EmployeePortal(frm, frm.dashboard_wrapper_holder);
		
		frm.trigger('get_employee');
	},

	get_employee: function(frm) {
		frappe.db.get_value('Employee', {
			'user_id': frappe.session.user
		}, 'name',
		(r) => {
			frm.set_value('employee', (r && r.name));
			frm.trigger('employee');

			if (!r) unhide_field('filter_section_section');
		});
	},

	employee: function(frm) {
		frm.trigger('call_data');
	},

	call_data: function(frm) {
		frappe.call({
			method: 'employee_detail_json',
			doc: frm.doc,
			async: false,
			freeze: true,
			freeze_message: __('Loading Dashboard...'),
			callback: function(r) {
				frm.dashboard_wrapper.set_data(r.message);
			}
		});
	}
});


erpnext.EmployeePortal = Class.extend({
	init: function(frm, wrapper) {
		this.frm = frm;
		this.wrapper = wrapper;
		this.employee_data = {};
		this.make();
	},

	make: function() {
		var me = this;
		$(this.wrapper).empty();
		this.wrapper.html(frappe.render_template('employee_portal'));
	},

	set_data: function(data) {
		this.employee_data = JSON.parse(data);
		
		this.set_profile_img();
		this.create_tab();
	},

	set_profile_img: function() {
		var profile_img = $(this.wrapper).find('.profile-img');
		var user_name = $(this.wrapper).find('.user-name');
		profile_img.empty();
		user_name.empty();

		var profile_detail = this.employee_data['profile_detail'];
		if (profile_detail['profile_img']) {
			profile_img.append(repl(`<img class="image-holder" src="%(profile_img)s">`, {
				profile_img: profile_detail['profile_img']
			}));
		}
		else {
			profile_img.append(repl(`<span class="placeholder-text">%(profile_img)s</span>`, {
				profile_img: frappe.get_abbr(profile_detail['profile_name'] || frappe.user.name)
			}));
		}

		user_name.append(repl(`<span>%(name)s</span>`, {name : profile_detail['profile_name'] || frappe.user.name}));
		this.employee_detail(profile_detail['profile_tab']);
	},

	employee_detail: function(employee) {
		var me = this;
		var employee_details = $(this.wrapper).find('.employee-details');
		employee_details.empty();

		var data = employee.data;

		$(repl(`
		<div>
			<label class="label">Employee Requests</label>
			<div class="link-container value"></div>
		</div>
		<br/>
        <div>
			<label class="label">Approval List</label>
			<div class="link-container-list value"></div>
		</div>
		<div class="element-holder">
				<label class="label">Date of Joining</label>
				<div class="value">%(date_of_joining)s</div>
			</div>
			<br/>
			<div>
				<label class="label">Status</label>
				<div class="value">%(status)s</div>
			</div>
			<div>
				<label class="label">Employment Type</label>
				<div class="value">%(employment_type)s</div>
			</div>
			<div>
				<label class="label">Nationality</label>
				<div class="value">%(nationality)s</div>
			</div>
			<div>
				<label class="label">ID Number</label>
				<div class="value">%(id_number)s</div>
			</div>
			<br/>
			<div>
				<label class="label">Emergency Phone No.</label>
				<div class="value">%(emergency_phone_no)s</div>
			</div>
			<div>
				<label class="label">Personal Email ID</label>
				<div class="value">%(personal_email_id)s</div>
			</div>
			<div>
				<label class="label">Cell Number</label>
				<div class="value">%(cell_number)s</div>
			</div>
			
			`, {
				'date_of_joining': data['Date of Joining'],
				'status': data['Status'],
				'employment_type': data['Employment Type'],
				'nationality': data['Nationality'],
				'id_number': data['ID Number'],
				'emergency_phone_no': data['Emergency Phone No.'],
				'personal_email_id': data['Personal Email ID'],
				'cell_number': data['Cell Number']
			})).appendTo(employee_details);
		

		if (employee.link) {
			(employee.link).forEach(link => {
                if(link.label!='Pending Approval List'){
				employee_details.find('.link-container').append(repl(`<div class="link-holder">
					<a _action="%(action)s" method="%(method)s"><span>
					<!--<i class="fa fa-link"></i>-->%(label)s</span></a>
				</div>`, {
                    
						'label': link.label,
						'action': link.action,
						'method': link.method
					})
				)
            }
			});
            (employee.link).forEach(link => {
                if(link.label=='Pending Approval List'){
				employee_details.find('.link-container-list').append(repl(`<div class="link-holder">
					<a _action="%(action)s" method="%(method)s"><span>
					<!--<i class="fa fa-link"></i>-->%(label)s</span></a>
				</div>`, {
                    
						'label': link.label,
						'action': link.action,
						'method': link.method
					})
				)
            }
			});
			employee_details.find('a').on('click', function() {
				me[$(this).attr('_action')]($(this).attr('method'));
			});
		}
	},

	create_tab: function() {
		var me = this;
		var tab_list = $(this.wrapper).find('.tab ul');
		tab_list.empty();
		var view_holder = $(this.wrapper).find('.view-holder');
		view_holder.empty();

		Object.entries(this.employee_data['employee_detail'] || {}).forEach(([tab, data]) => {
			var idx = tab.toLowerCase().replace(/ /g, '-');
			tab_list.append(repl(`<li tab-idx="%(idx)s"><span>%(tab)s</span></li>`, {
				idx: idx,
				tab: tab
			}));

			view_holder.append(repl(`<div class="tabcontent" tabview-idx="%(idx)s">
				<div class="row filter"></div>
				<div class="row card-holder"></div>
			</div>`, {
				idx: idx
			}));

			if (data.method)
				this[data.method](tab, data.data);
		});

		tab_list.find('li:first').addClass('active');
		view_holder.find('div.tabcontent:first').addClass('active');

		this.tablistener();
	},

	form_route: function(method) {
		frappe.call({
			method: method,
			doc: this.frm.doc,
			args: { },
			freeze: true,
			freeze_message: __('Loading Dashboard...'),
			callback: function(r) {
                console.log(r,'r')
				var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("Form", doc.doctype, doc.name);
			}
		});
	},
    form_list: function(method) {
		frappe.call({
			method: method,
			doc: this.frm.doc,
			args: { },
			freeze: true,
			freeze_message: __('Loading Dashboard...'),
			callback: function(r) {
				var doc = frappe.model.sync(r.message)[0];
				frappe.set_route("List", doc.doctype);
			}
		});
	},

	tablistener: function() {
		var me = this;
		this.wrapper.find('.tab ul li').on('click', function() {
			$('.tab ul li').removeClass('active');
			$(this).addClass('active');

			$('.view-holder .tabcontent').removeClass('active');
			$('.view-holder .tabcontent[tabview-idx="'+$(this).attr('tab-idx')+'"]').addClass('active');

			if (me.leave_chart_wrapper) me.leave_chart_wrapper.resize();
			if (me.attendance_chart_wrapper) me.attendance_chart_wrapper.resize();
		});
	},

	general_tab: function(tab_name, data) {
		var me = this;
		var tab_idx = tab_name.toLowerCase().replace(/ /g, '-');
		var tabframe = $(this.wrapper).find('.view-holder .tabcontent[tabview-idx="'+tab_idx+'"]');
		var tabholder =  tabframe.find('.card-holder');
		tabholder.empty();
		
		data = data.profile_tab.data;

		$(repl(`<div class="col-sm-6 card">
			<div>
				<div class="box">
					<div class="box-head text-center">
						<i class="fa fa-3x fa-info-circle"></i>
						<div class="title"><h4>Basic Information</h4></div>
					</div>
					<div class="box-body form-group">
						<div class="row">
							<div class="col-sm-4 row-label">Date of Birth</div>
							<div class="col-sm-8 row-value">%(date_of_birth)s</div>
						</div>
						<div class="row">
							<div class="col-sm-4 row-label">Company</div>
							<div class="col-sm-8 row-value">%(company)s</div>
						</div>
						<div class="row">
							<div class="col-sm-4 row-label">User ID</div>
							<div class="col-sm-8 row-value">%(user_id)s</div>
						</div>
						<div class="row">
							<div class="col-sm-4 row-label">Gender</div>
							<div class="col-sm-8 row-value">%(gender)s</div>
						</div>
						<div class="row">
							<div class="col-sm-4 row-label">Shift Type</div>
							<div class="col-sm-8 row-value">%(shift_type)s</div>
						</div>
						<div class="row">
							<div class="col-sm-4 row-label">Shift Time</div>
							<div class="col-sm-8 row-value">%(shift_time)s</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="col-sm-6 card">
			<div>
				<div class="box">
					<div class="box-head text-center">
						<i class="fa fa-3x fa-user-circle"></i>
						<div class="title"><h4>Employment Details</h4></div>
					</div>
					<div class="box-body form-group">
						<div class="row">
							<div class="col-sm-4 row-label">Enroll Number</div>
							<div class="col-sm-8 row-value">%(enroll_number)s</div>
						</div>

						<div class="row">
							<div class="col-sm-4 row-label">Branch</div>
							<div class="col-sm-8 row-value">%(branch)s</div>
						</div>
						<div class="row">
							<div class="col-sm-4 row-label">Department</div>
							<div class="col-sm-8 row-value">%(department)s</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="col-sm-6 card">
			<div>
				<div class="box">
					<div class="box-head text-center">
						<i class="fa fa-3x fa-address-card"></i>
						<div class="title"><h4>Identification</h4></div>
					</div>
					<div class="box-body form-group">
						<div class="row">
							<div class="col-sm-4 row-label">Country</div>
							<div class="col-sm-8 row-value">%(country)s</div>
						</div>

						<div class="row">
							<div class="col-sm-4 row-label">Driving License No</div>
							<div class="col-sm-8 row-value">%(driving_license_no)s</div>
						</div>
						<div class="row">
							<div class="col-sm-4 row-label">License Issue Date</div>
							<div class="col-sm-8 row-value">%(driving_license_issue_date)s</div>
						</div>
						<div class="row">
							<div class="col-sm-4 row-label">License Expiry Date</div>
							<div class="col-sm-8 row-value">%(driving_license_expiry_date)s</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="col-sm-6 card">
			<div>
				<div class="box">
					<div class="box-head text-center">
						<i class="fa fa-3x fa-phone-square"></i>
						<div class="title"><h4>Contact Details</h4></div>
					</div>
					<div class="box-body form-group">
						<div class="row">
							<div class="col-sm-4 row-label">Current Address</div>
							<div class="col-sm-8 row-value">%(current_address)s</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="col-sm-12 progress">
			<div class="progress-bar progress-bar-striped active" style="width: %(progress)s%"><span>%(progress)s% Master Data Updated..</span></div>
		</div>`, {
			'date_of_birth': ': ' +data['Date of Birth'],
			'company': ': ' +data['Company'],
			'user_id': ': ' +data['User ID'],
			'gender': ': ' +data['Gender'],
			'shift_type': ': ' +data['Shift Type'],
			'shift_time': ': ' +data['Shift Name'],
			'enroll_number': ': ' +data['Enroll Number'],
			'branch': ': ' +data['Branch'],
			'department': ': ' +data['Department'],
			'job_title': ': ' +data['Job Title'],
			'country': ': ' +data['Country'],
			'driving_license_no': ': ' +data['Driving License No'],
			'driving_license_issue_date': ': ' +data['Driving License Issue Date'],
			'driving_license_expiry_date': ': ' +data['Driving License Expiry Date'],
			'current_address': ': ' +data['Current Address'],
			'progress': me.progress(data)
		})).appendTo(tabholder);

	},

	progress: function(data) {
		var max_val = Object.entries(data || {}).length;

		var has_val = 0;
		Object.entries(data || {}).forEach(([label, value]) => {
			if (String(value || '').length > 0)
				has_val += 1;
		});

		return roundNumber((has_val / max_val) * 100, 2);
	},

	cardview_tab: function(tab_name, data) {
		var me = this;
		var tab_idx = tab_name.toLowerCase().replace(/ /g, '-');
		var tabframe = $(this.wrapper).find('.view-holder .tabcontent[tabview-idx="'+tab_idx+'"]');
		var tabholder =  tabframe.find('.card-holder');
		tabholder.empty();
		var filter = tabframe.find('.filter');
		filter.empty();

		filter.append(`<div class="payroll-period col-sm-2"></div></div>`);
		
		this.payroll_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Link',
				label: 'Payroll Period',
				fieldname: 'payroll_period',
				options: 'Payroll Period',
				reqd: 1,
				onchange: () => {
					me.payroll_period = me.payroll_field.get_value();
					frappe.call({
						method: 'salary_detail',
						doc: this.frm.doc,
						args: {
							payroll_period: me.payroll_field.get_value()
						},
						freeze: true,
						freeze_message: __('Loading Dashboard...'),
						callback: function(r) {
							me.employee_data.employee_detail[tab_name] = r.message;
							me.create_card(tabholder, r.message);
						}
					});
				}
			},
			parent: filter.find('.payroll-period'),
			render_input: true
		});

		this.payroll_field.set_value(this.payroll_period || data.payroll_period);
		this.create_card(tabholder, data);
	},

	create_card: function(tabholder, data) {
		tabholder.empty();

		$(`<div class="col-sm-6 card attendance-card">
				<div>
					<div class="box">
						<div class="box-head text-center">
							<i class="fa fa-3x fa-pencil-square-o"></i>
							<div class="title"><h4>Attendance</h4></div>
						</div>
						<div class="box-body form-group">
							<div class="row">
								<div class="empty-holder">No Employee Selected</div>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-sm-6 card">
				<div>
					<div id="attendance-chart">
					</div>
				</div>
			</div>
			<div class="col-sm-6 card salary-slip-card">
				<div>
					<div class="box">
						<div class="box-head text-center">
							<i class="fa fa-3x fa-envelope-open"></i>
							<div class="title"><h4>Salary Slip</h4></div>
						</div>
						<div class="box-body form-group">
							<div class="row">
								<div class="empty-holder">No Employee Selected</div>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-sm-6 card earning-deducation-table">
				<div>
				<div class="table-responsive custom_container">
					<table class="table">
						<thead>
							<tr>
								<th>Salary Component</th>
								<th class="int-val">Earning Amount</th>
								<th class="int-val">Deduction Amount</th>
							</tr>
						</thead>
						<tbody>
						</tbody>
					</table>
				</div>
			</div>
		`).appendTo(tabholder);

		Object.entries(data.data || {}).forEach(([idx, detail]) => {
			this.set_body_content(tabholder.find('.'+idx), detail.data);
			this.create_link(tabholder.find('.'+idx), detail.link);
			tabholder.find('.'+idx+' .box-head .title').append(repl(`<span class="period">%(period)s</span>`, {period: detail.period}));

			if(detail['table_data']) {
				this.table_entry(tabholder.find('.earning-deducation-table'), detail['table_data']);
			}
		});

		this.attendance_chart_wrapper = echarts.init(document.getElementById('attendance-chart'));
		this.attendance_chart();
	},

	table_entry: function(holder, data) {
		var tbody = holder.find('tbody');

		(data || []).forEach(row => {
			$(repl(`<tr>
				<td>%(salary_component)s</td>
				<td class="int-val">%(earning)s</td>
				<td class="int-val">%(deduction)s</td>
			</tr>`, {
				'salary_component': row.salary_component,
				'earning': row.earning,
				'deduction': row.deduction
			})).appendTo(tbody);
		});

	},

	custom_print_format: function(args) {
		if (!args.name) return;

		frappe.run_serially([
			() => frappe.set_route('Form', args.doctype, args.name),
			// () => frappe.timeout(1),
			() => cur_frm.print_doc(),
		]);

		
		// var w = window.open(frappe.urllib.get_full_url("/printview?"
		// + "doctype=" + encodeURIComponent(args.doctype)
		// + "&name=" + encodeURIComponent(args.name)
		// + "&trigger_print=1"
		// + "&format=" + encodeURIComponent("Standard")
		// + "&no_letterhead=1"
		// + "&_lang=en"), "employee-portal-print", 'location=no,locationbar=no,menubar=no,toolbar=no,status=no,scrollbars=no,fullscreen=yes');
		// if (!w) {
		//	frappe.msgprint(__("Please enable pop-ups")); return;
		// }
	},

	custom_report: function(args) {
		if (!args.name) return;
		
		var filters = Object.assign({}, args);
		delete filters['name'];
		frappe.route_options = filters;
		frappe.set_route("query-report", args.name);
	},
    custom_doctype: function(args) {
		if (!args.name) return;
		var filters = Object.assign({}, args);
        // filters.append('attendance_date':['Between', filters['start_date']+'to'+])
		delete filters['name'];
        var start_date=filters['start_date']
        var end_date=filters['end_date']
        delete filters['start_date'];
        delete filters['end_date'];
        var new_filters={'company':filters['company'],'employee':filters['employee'],'attendance_date':["between", [start_date, end_date]]}
		frappe.route_options = new_filters;
		frappe.set_route("List", args.name);
	},

	set_body_content: function(card_view, data) {
		var me = this;
		card_view.find('.row').not(':first').remove();
		Object.entries(data || {}).forEach(([label, value]) => {
			card_view.find('.box-body.form-group .row .empty-holder').hide();
			
			card_view.find('.box-body.form-group').append(repl(`<div class="row">
				<div class="col-sm-4 row-label">%(label)s</div>
				<div class="col-sm-8 row-value">%(value)s</div>
			</div>`, {
				label: label,
				value: ": " + value
			}));
		});

		card_view.find('a').on('click', function() {
			me[$(this).attr('_action')]($(this).attr('method'));
		});
	},

	create_link: function(holder, link_opt) {
		var me = this;
		if (link_opt) {
			holder.find('.box-body.form-group').append(repl(`<div class="row link-holder">
				<a _action="%(action)s"><span>
				<!--<i class="fa fa-link"></i>--> %(label)s</span></a>
			</div>`, {
					'label': link_opt.label,
					'action': link_opt.action
				})
			)

			holder.find('a').on('click', function() {
				if($(this).attr('method')) return;
				me[$(this).attr('_action')](link_opt.option);
			});
		}
	},

	leave_tab: function(tab_name, data) {
		var tab_idx = tab_name.toLowerCase().replace(/ /g, '-');
		var tabholder = $(this.wrapper).find('.view-holder .tabcontent[tabview-idx="'+tab_idx+'"] .card-holder');
		tabholder.empty();
		
		var leave_table = $(`<div class="col-sm-12"><div>
			<table class="table leave-table">
				<thead>
					<tr>
						<th>Leave Type</th>
						<th>Leave Balance</th>
						<th>As On</th>
					</tr>
				</thead>
				<tbody>
				</tbody>
			</table>
		</div></div>
		<div class="col-sm-12"><div><div id="leave-chart" class="chart"></div></div></div>`).appendTo(tabholder);

		if (!Object.entries(data).length) return;

		this.leave_chart_wrapper = echarts.init(document.getElementById('leave-chart'));

		Object.entries(data || {}).forEach(([leave_type, detail]) => {
			leave_table.find('tbody').append(repl(`<tr leave-idx="%(leave_type)s">
				<td>%(leave_type)s</td>
				<td>%(leave_bal)s</td>
				<td>%(as_on_date)s</td>
				</tr>`, {leave_type: leave_type,
					leave_bal: detail.remaining_leaves,
					as_on_date: moment().format("DD-MM-YYYY")}));
		});
		
		leave_table.find('tbody tr:first').addClass('active');

		var key = Object.keys(data)[0];
		this.pie_chart_setter(key);

		this.table_listener();
	},

	table_listener: function() {
		var me = this;
		this.wrapper.find('.leave-table tbody tr').on('click', function() {
			$('.leave-table tbody tr').removeClass('active');
			$(this).addClass('active');
			me.pie_chart_setter($(this).attr('leave-idx'));
		});
	},

	pie_chart_setter: function(leave_type) {
		var {label, data} = this.pie_chart_data(leave_type);
		
		var pie_setting = {
			title: {
				text: leave_type,
				// textStyle: {
				// 	color: 'white'
				// }
			},
			legend: {
				orient: 'vertical',
				right: 10,
				top: 20,
				bottom: 20,
				// textStyle: {
				// 	color: 'white'
				// }
			},
			tooltip: {
				trigger: 'item',
				formatter: function (params, ticket, callback) {
					return repl("%(name)s : %(value)s (%(percent)s%)", {
						name: params.value['name'],
						value: params.value['value'],
						percent: params.percent
					});
				}
			},
			dataset: {
				dimensions: label,
				source: data
			},
			series: [{
				name: leave_type,
				type: 'pie',
				radius: '55%',
				center: ['40%', '50%'],
				label: {
					show: true,
					formatter: function (params, ticket, callback) {
						return repl("%(name)s : %(value)s", {
							name: params.value['name'],
							value: params.value['value']
						});
					}
				}
			}]
		}
		
		this.leave_chart_wrapper.clear();
		this.leave_chart_wrapper.setOption(pie_setting);
	},

	attendance_chart: function() {
		var {label, data} = this.attendance_chart_data();
		
		var attendance_setting = {
			title: {
				text: 'Attendance'
			},
			legend: {
				show: false,
				orient: 'vertical',
				right: 10,
				top: 20,
				bottom: 20
			},
			tooltip: {
				trigger: 'item',
				formatter: function (params, ticket, callback) {
					return repl("%(name)s : %(value)s (%(percent)s%)", {
						name: params.value['name'],
						value: params.value['value'],
						percent: params.percent
					});
				}
			},
			dataset: {
				dimensions: label,
				source: data
			},
			series: [{
				name: 'Attendance',
				type: 'pie',
				radius: '55%',
				center: ['50%', '50%'],
				label: {
					show: true,
					formatter: function (params, ticket, callback) {
						return repl("%(name)s : %(value)s", {
							name: params.value['name'],
							value: params.value['value']
						});
					}
				}
			}]
		}
		
		this.attendance_chart_wrapper.clear();
		this.attendance_chart_wrapper.setOption(attendance_setting);
	},

	attendance_chart_data: function() {
		var label = ['name', 'value'];
		var data = [];

		var _data = this.employee_data.employee_detail["Salary Details"].data;
		
		if (_data) {
			_data = _data['attendance-card'];
			if (_data) {
				Object.entries(_data.data || {}).forEach(([name, value]) => {
					if (value > 0)
						data.push({'name': name, 'value': value});
				});
			}
			
		}
		
		return {'label': label, 'data': data}
	},

	pie_chart_data: function(leave_type) {
		var label = ['name', 'value'];
		var data = [];
		
		var _data = this.employee_data.employee_detail["Leave Details"].data[leave_type];
		
		Object.entries(_data).forEach(([name, value]) => {
			data.push({'name': name.replace(/_/g, ' ').replace(/^.| ./g, str => str.toUpperCase()), 'value': value});
		});

		return {'label': label, 'data': data}
	},

	leave_history_tab: function(tab_name, data) {
		var tab_idx = tab_name.toLowerCase().replace(/ /g, '-');
		var tabholder = $(this.wrapper).find('.view-holder .tabcontent[tabview-idx="'+tab_idx+'"] .card-holder');
		tabholder.empty();

		if (!Object.entries(data).length) return;

		var leave_table = $(`<div class="col-sm-12"><div>
			<table class="table">
				<thead>
					<tr>
						<th>Leave Type</th>
						<th>Application No</th>
						<th>Start Date</th>
						<th>End Date</th>
						<th>Total Days</th>
						<th>Status</th>
					</tr>
				</thead>
				<tbody>
				</tbody>
			</table>
		</div></div>`).appendTo(tabholder);

		(data || {}).forEach(row => {
			leave_table.find('tbody').append(repl(`<tr>
					<td>%(leave_type)s</td>
					<td>%(name)s</td>
					<td>%(from_date)s</td>
					<td>%(to_date)s</td>
					<td>%(total_days)s</td>
					<td>%(status)s</td>
				</tr>`, {leave_type: row.leave_type,
					name: row.name,
					from_date: row.from_date,
					to_date: row.to_date,
					total_days: row.total_leave_days,
					status: row.status
				}));
		});
	}
});
