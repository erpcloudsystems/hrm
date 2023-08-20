// Copyright (c) 2020, avu and contributors
// For license information, please see license.txt

frappe.provide('erpnext.hrm');

frappe.pages['hr-dashboard'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'HR Dashboard',
		single_column: true
	});


	wrapper.hr_dashboard = new erpnext.hrm.HRDashoard(wrapper);
}


erpnext.hrm.HRDashoard = class HRDashoard {
	constructor(wrapper) {
		this.wrapper = $(wrapper).find('.layout-main-section');
		this.page = wrapper.page;

		this.company = frappe.user_defaults.company;
		this.date = [frappe.datetime.get_today(), frappe.datetime.get_today()];
		this.catogery_wise = 'Designation';
		this.amount_category_wise = 'Gross Salary'
		this.defualt_payroll();

		this.make();
	}

	defualt_payroll() {
		var me = this;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.get_payroll_period",
			args: {
				company: me.company
			},
			async: false,
			callback: function(r) {
				me.payroll_from = r.message;
				me.payroll_to = r.message;
				me.payroll_period = r.message;
			}
		});
	}

	make() {
		return frappe.run_serially([
			() => frappe.dom.freeze(),
			() => {
				this.prepare_dom();
				this.make_filters();
				this.make_tab();
			},
			() => {
				frappe.dom.unfreeze();
			}
		]);
	}

	prepare_dom() {
		this.wrapper.append(`
			<div class="hr-dashboard-holder container">
				<div class="row">
					<div class="col-sm-4 tab parent-tab">
						<ul class="nav nav-pills nav-stacked">
						</ul>
					</div>
					<div colo-sm-8>
						<div class="row filter-tab"></div>
					</div>
				</div>
				<div class="row view-holder parent-view-holder">
				</div>
			</div>
		`);
	}

	make_tab() {
		var tab_holder = this.wrapper.find('.tab ul');
		tab_holder.empty();

		tab_holder.append(`
		<li tab-idx="employee-tab"><span>Headcount Info</span></li>
		<li tab-idx="payroll-tab"><span>Payroll Period Info</span></li>
		<li tab-idx="payroll-completion"><span>Payroll Readiness</span></li>`);

		var tab_view_holder = this.wrapper.find('.parent-view-holder');
		tab_view_holder.empty();

		tab_view_holder.append(`
		<div class="tabcontent parent-tabcontent" tabview-idx="employee-tab">
			<div class="row card-holder">
			</div>
		</div>
		<div class="tabcontent parent-tabcontent" tabview-idx="payroll-tab">
			<div class="row card-holder"></div>
		</div>
		<div class="tabcontent parent-tabcontent" tabview-idx="payroll-completion">
			<div class="row card-holder"></div>
		</div>`);

		tab_holder.find('li:first').addClass('active');
		tab_view_holder.find('div.tabcontent:first').addClass('active');

		this.tablistener();
		this.employee_tab(tab_view_holder.find('[tabview-idx="employee-tab"]'));
		this.payroll_tab(tab_view_holder.find('[tabview-idx="payroll-tab"]'));
		this.payroll_completion_tab(tab_view_holder.find('[tabview-idx="payroll-completion"]'))
	}

	make_filters() {
		var filter = this.wrapper.find('.filter-tab');
		filter.empty();

		filter.append(`
			<div class="filter company-field col-sm-2 active"></div>
			<div class="filter system-date-field col-sm-2 active"></div>
			<div class="filter payroll-from-field col-sm-2"></div>
			<div class="filter payroll-to-field col-sm-2"></div>
			<div class="filter category-wise-field col-sm-2"></div>
			<div class="filter payroll-period-field col-sm-2"></div>
		`);

		this.make_company_field(filter);
		this.make_date_field(filter);
		this.make_catogery_wise_field(filter);
		this.make_payroll_field('payroll_from', 'Payroll Period From', filter.find('.payroll-from-field'));
		this.make_payroll_field('payroll_to', 'Payroll Period To', filter.find('.payroll-to-field'));
		this.make_payroll_field('payroll_period', 'Payroll Period', filter.find('.payroll-period-field'));
	}

	tablistener() {
		var me = this;
		this.wrapper.find('.parent-tab ul li').on('click', function() {
			$('.parent-tab ul li').removeClass('active');
			$(this).addClass('active');

			$('.parent-view-holder .parent-tabcontent').removeClass('active');
			$('.parent-view-holder .parent-tabcontent[tabview-idx="'+$(this).attr('tab-idx')+'"]').addClass('active');

			var filters = me.wrapper.find('.filter-tab');
			if ($(this).attr('tab-idx') == 'payroll-tab') {
				filters.find('.filter').removeClass('active');

				['payroll-from-field', 'payroll-to-field', 'category-wise-field', 'company-field'].forEach(field => {
					var _field = filters.find('.'+field);
					if (!_field.hasClass('active'))
						_field.addClass('active');
				});
			}
			else if ($(this).attr('tab-idx') == 'employee-tab') {
				filters.find('.filter').removeClass('active');
				
				['system-date-field', 'company-field'].forEach(field => {
					var _field = filters.find('.'+field);
					if (!_field.hasClass('active'))
						_field.addClass('active');
				});
			}
			else {
				filters.find('.filter').removeClass('active');

				['payroll-period-field', 'company-field'].forEach(field => {
					var _field = filters.find('.'+field);
					if (!_field.hasClass('active'))
						_field.addClass('active');
				});

			}

			if (me.pie_chart_wrapper) me.pie_chart_wrapper.resize();
			if (me.designation_bar_chart_wrapper) me.designation_bar_chart_wrapper.resize();
			if (me.salary_category_wise_wrapper) me.salary_category_wise_wrapper.resize();
			if (me.joining_category_wise_wrapper) me.joining_category_wise_wrapper.resize();
			if (me.overtime_category_wise_wrapper) me.overtime_category_wise_wrapper.resize();
			if (me.relieving_category_wise_wrapper) me.relieving_category_wise_wrapper.resize();
			if (me.payroll_completion_chart_wrapper) me.payroll_completion_chart_wrapper.resize();
		});
	}

	employee_tab(holder) {
		var card_holder = holder.find('.card-holder');
		card_holder.empty();

		card_holder.append(`
			<div class="col-sm-12 card">
				<div class="row chart" id="tree-view"></div>
			</div>
			<div class="col-sm-12 card">
				<div class="row">
					<div class="col-sm-2 card">
						<div class="box">
							<div class="row employee-count">
								<span>Employee By Gender</span>
								<div class="row">
									<div class="col-sm-6">
										<span>Male</span>
										<div class="image-holder">
											<img class="profile-img" src="/image/Male image.png">
										</div>
										<div class="male-count">
										</div>
									</div>
									<div class="col-sm-6">
										<span>Female</span>
										<div class="image-holder">
											<img class="profile-img" src="/image/female image.png">
										</div>
										<div class="female-count"></div>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="col-sm-5 card">
						<div class="box">
							<div class="row chart" id="pie-view"></div>
						</div>
					</div>
					<div class="col-sm-5 card">
						<div class="box">
							<div class="row chart" id="designation-bar-view"></div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-sm-12 card">
				<div class="box">
					<div class ="row tab data-tab">
						<ul class="nav nav-pills nav-stacked">
							<li tab-idx="late-coming-details-tab"><span>Late Coming Details</span></li>
							<li tab-idx="early-going-details-tab"><span>Early Going Details</span></li>
							<li tab-idx="absent-details-tab"><span>Absent Details</span></li>
							<li tab-idx="joining-detail-tab"><span>Joining Details</span></li>
							<li tab-idx="relieving-details-tab"><span>Releving details</span></li>
						</ul>
					</div>

					<div class="row view-holder child-view-holder">
						<div class="tabcontent child-tabcontent" tabview-idx="late-coming-details-tab">
							<div class="row card-holder">
								<div class="col-sm-12 late-coming-details table-responsive custom_container"></div>
							</div>
						</div>
						<div class="tabcontent child-tabcontent" tabview-idx="early-going-details-tab">
							<div class="row card-holder">
								<div class="col-sm-12 early-going-details table-responsive custom_container"></div>
							</div>
						</div>
						<div class="tabcontent child-tabcontent" tabview-idx="absent-details-tab">
							<div class="row card-holder">
								<div class="col-sm-12 absent-details table-responsive custom_container"></div>
							</div>
						</div>
						<div class="tabcontent child-tabcontent" tabview-idx="joining-detail-tab">
							<div class="row card-holder">
								<div class="col-sm-12 joining-details table-responsive custom_container"></div>
							</div>
						</div>
						<div class="tabcontent child-tabcontent" tabview-idx="relieving-details-tab">
							<div class="row card-holder">
								<div class="col-sm-12 relieving-details table-responsive custom_container"></div>
							</div>
						</div>
					</div>
				</div>
			</div>`);
		
		card_holder.find('li:first').addClass('active');
		card_holder.find('div.tabcontent:first').addClass('active');

		card_holder.find('.data-tab ul li').on('click', function() {
			card_holder.find('.data-tab ul li').removeClass('active');
			$(this).addClass('active');

			card_holder.find('.child-view-holder .child-tabcontent').removeClass('active');
			$('.child-view-holder .child-tabcontent[tabview-idx="'+$(this).attr('tab-idx')+'"]').addClass('active');
		});

		this.tree_chart_wrapper = echarts.init(document.getElementById('tree-view'));
		this.pie_chart_wrapper = echarts.init(document.getElementById('pie-view'));
		this.designation_bar_chart_wrapper = echarts.init(document.getElementById('designation-bar-view'));
		this.tree_chart_event();
		this.set_data();

	}

	set_data() {
		if (!this.date || !this.company) return;

		frappe.run_serially([
			() => this.set_tree_chart(),
			() => this.absent_detail(),
			() => this.short_time_detail(),
			() => this.employee_status(),
			() => this.employee_count(),
			() => this.set_bar_chart(),
			// () => this.set_pie_chart(),
		]);
	}

	make_company_field(filter) {
		this.company_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Link',
				label: 'Company',
				fieldname: 'company',
				options: 'Company',
				reqd: 1,
				onchange: () => {
					this.company = this.company_field.get_value();
					this.set_data();
					this.set_salarytab_data();
				}
			},
			parent: filter.find('.company-field'),
			render_input: true
		});

		this.company_field.set_value(this.company);
	}

	make_date_field(filter) {
		this.system_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'DateRange',
				label: 'Date Range',
				fieldname: 'date',
				reqd: 1,
				onchange: () => {
					this.date = this.system_field.get_value();
					this.set_data();
				}
			},
			parent: filter.find('.system-date-field'),
			render_input: true
		});

		this.system_field.set_value(this.date);
	}

	make_payroll_field(field, label, target_field) {
		this[field+"_field"] = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Link',
				label: label,
				fieldname: field,
				options: 'Payroll Period',
				reqd: 1,
				onchange: () => {
					this[field] = this[field+"_field"].get_value();
					
					if (field == 'payroll_period') {
						this.set_completion_date();
					}
					else {
						this.set_salarytab_data();
					}
				}
			},
			parent: target_field,
			render_input: true
		});

		this[field+"_field"].set_value(this[field]);
	}

	make_catogery_wise_field(filter) {
		this.catogery_wise_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Select',
				label: 'Catogery Wise',
				fieldname: 'catogery_wise',
				options: ['Designation', 'Department'],
				reqd: 1,
				onchange: () => {
					this.catogery_wise = this.catogery_wise_field.get_value();
					this.set_salarytab_data();
				}
			},
			parent: filter.find('.category-wise-field'),
			render_input: true
		});

		this.catogery_wise_field.set_value(this.catogery_wise);
	}

	set_tree_chart() {
		var me = this;
		this.tree_chart_wrapper.clear();
		this.tree_chart_wrapper.showLoading();
		
		var tree_setting = (data) => {
			return {
					tooltip: {
						trigger: 'item',
						triggerOn: 'mousemove'
					},
					series: [
						{
							type: 'tree',
							data: data,
							left: '2%',
							right: '2%',
							// top: '8%',
							bottom: '50%',
			
							symbol: 'emptyCircle',
			
							orient: 'vertical',
			
							expandAndCollapse: true,
			
							label: {
								position: 'top',
								// rotate: -90,
								verticalAlign: 'middle',
								align: 'center',
								fontSize: 9
							},
			
							leaves: {
								label: {
									position: 'bottom',
									rotate: -90,
									verticalAlign: 'middle',
									align: 'left'
								}
							},
			
							animationDurationUpdate: 750
						}
					]
				}
			};

		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.chart_data",
			args: {
				company: me.company
			},
			callback: function(r) {
				me.tree_chart_wrapper.hideLoading();
				me.tree_chart_wrapper.setOption(tree_setting(r ? r.message : {}));
			}
		});
	}

	set_pie_chart() {
		this.pie_chart_wrapper.clear();
		this.pie_chart_wrapper.showLoading();

		var pie_setting = {
			title: {
				text: '',
				subtext: '',
			},
			legend: {
				show: false
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
				dimensions: ['name', 'value'],
				source: [
					{
						'name': 'Absent',
						'value': this.absent_count
					},
					{
						'name': 'Late Coming',
						'value': this.late_coming_count
					},
					{
						'name': 'Early Going',
						'value': this.early_going_count
					},
					{
						'name': 'New Joining',
						'value': this.joining_count
					},
					{
						'name': 'Relieving',
						'value': this.relieving_count
					}
				]
			},
			series: [{
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
				},
			}]
		}
		
		this.pie_chart_wrapper.hideLoading();
		this.pie_chart_wrapper.setOption(pie_setting);
	}

	set_bar_chart(department=undefined) {
		this.designation_bar_chart_wrapper.clear();
		this.designation_bar_chart_wrapper.showLoading();

		var me = this;

		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.desigination_data",
			args: {
				company: me.company,
				from_date: me.date[0],
				to_date: me.date[1],
				department: department

			},
			async: false,
			callback: function(r) {
				var bar_setting = {
					title: {
						text: __('Designation')
					},
					tooltip: {
						trigger: 'axis'
					},
					xAxis: {
						show: false,
						type: 'category',
						data: r.message['label'],
						axisLabel: {
							fontSize: 9
						}
					},
					yAxis: {
						name: 'Count',
						type: 'value',
						axisLabel: {
							formatter: function (value, index) {
								return numeral(value).format('0[.]0a');
							}
						}
					},
					series: [{
						data: r.message['value'],
						type: 'bar',
						showBackground: true,
						// label: {
						// 	show: false,
						// 	position: 'inside',
						// 	verticalAlign: 'middle',
						// 	rotate: 90,
						// 	formatter: '{c} {b}',
						// }
					}]
				};
			
				me.designation_bar_chart_wrapper.hideLoading();
				me.designation_bar_chart_wrapper.setOption(bar_setting);
			}
		});
	}

	employee_count(department=undefined) {
		var me = this;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.employee_count",
			args: {
				company: me.company,
				from_date: me.date[0],
				to_date: me.date[1],
				department: department

			},
			async: false,
			callback: function(r) {
				me.wrapper.find('.male-count').empty();
				me.wrapper.find('.male-count').append(repl(`<span>%(count)s</span>`, {count: r.message['Male']}));
				me.wrapper.find('.female-count').empty();
				me.wrapper.find('.female-count').append(repl(`<span>%(count)s</span>`, {count: r.message['Female']}));
			}
		});
	}

	tree_chart_event() {
		var me = this;
		var chart = this.tree_chart_wrapper;
		chart.on('click', function (params) {
			var department = params.data.catogery == 'Department' ? params.data.name : undefined;
			me.set_detail(me.wrapper.find('.absent-details'), 'absent_count', me.absent_details, department);
			me.set_detail(me.wrapper.find('.late-coming-details'), 'late_coming_count', me.late_coming_details, department);
			me.set_detail(me.wrapper.find('.early-going-details'), 'early_going_count', me.early_going_details, department);
			me.set_detail(me.wrapper.find('.joining-details'), 'joining_count', me.joining_details, department);
			me.set_detail(me.wrapper.find('.relieving-details'), 'relieving_count', me.relieving_details, department);

			me.set_bar_chart(department);
			me.employee_count(department);
			// me.set_pie_chart();
		});
	}

	absent_detail() {
		var me = this;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.absent_details",
			args: {
				company: me.company,
				from_date: me.date[0],
				to_date: me.date[1]
			},
			callback: function(r) {
				me.absent_details = (r.message || []);
				me.set_detail(me.wrapper.find('.absent-details'), 'absent_count', me.absent_details);
			}
		});
	}

	short_time_detail() {
		var me = this;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.short_time_details",
			args: {
				company: me.company,
				from_date: me.date[0],
				to_date: me.date[1]
			},
			callback: function(r) {
				me.late_coming_details = (r.message['late_coming'] || []);
				me.early_going_details = (r.message['early_going'] || []);
				me.set_detail(me.wrapper.find('.late-coming-details'), 'late_coming_count', me.late_coming_details);
				me.set_detail(me.wrapper.find('.early-going-details'), 'early_going_count', me.early_going_details);
			}
		});
	}

	employee_status() {
		var me = this;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.employee_status",
			args: {
				company: me.company,
				from_date: me.date[0],
				to_date: me.date[1]
			},
			callback: function(r) {
				me.joining_details = (r.message['joined'] || []);
				me.relieving_details = (r.message['relived'] || []);
				me.set_detail(me.wrapper.find('.joining-details'), 'joining_count', me.joining_details);
				me.set_detail(me.wrapper.find('.relieving-details'), 'relieving_count', me.relieving_details);
			}
		});
	}

	set_detail(holder, chart_data_obj, data, department=undefined) {
		holder.empty();
		
		var detail_holder = $(`<table class="table">
			<thead>
				<tr>
				</tr>
			</thead>
			<tbody>
			</tbody>
		</table>`).appendTo(holder);

		var break_data = 0;
		var header = Object.keys(data[0]);
		header.forEach((label, idx) => {
			$(repl(`<th>%(label)s</th>`, {label: label})).appendTo(detail_holder.find('thead tr'));

			if (header.length == (idx + 1) && !data[0][header[0]]) {
				break_data = 1;
			}
		});
		
		var data_count = 0;
		if (break_data == 0) {
			Object.entries(data).forEach(([idx, row]) => {
				if (department && row['Department'] != department) return;
				
				data_count += 1;
				var _row = $(`<tr></tr>`).appendTo(detail_holder.find('tbody'));
				Object.values(row).forEach(value => {
					$(repl(`<td>%(value)s</td>`, {value: value})).appendTo(_row)
				});
			});
		}
		
		this[chart_data_obj] = data_count;

		
		if(chart_data_obj == 'relieving_count') {
			this.set_pie_chart();
		}
	}

	payroll_tab(holder) {
		var card_holder = holder.find('.card-holder');
		card_holder.empty();

		card_holder.append(`<div class="col-sm-6 card">
			<div class="box">
				<div class="row filter-tab">
					<div class="col-sm-5 amount-category-field"></div>
				</div>
				<div class="row equal_chart" id="salary-category-wise"></div>
			</div>
		</div>
		<div class="col-sm-6 card">
			<div class="box">
				<div class="row chart" id="joining-category-wise"></div>
				<div class="row payroll-joining-details table-responsive custom_container"></div>
			</div>
		</div>
		<div class="col-sm-6 card">
			<div class="box">
				<div class="row chart" id="relieving-category-wise"></div>
				<div class="row payroll-relieving-details table-responsive custom_container"></div>
			</div>
		</div>
		<div class="col-sm-6 card">
			<div class="box">
				<div class="row equal_chart" id="overtime-category-wise"></div>
			</div>
		</div>`);

		var filters = card_holder.find('.filter-tab');
		this.make_amt_catogery_wise_field(filters);

		this.salary_category_wise_wrapper = echarts.init(document.getElementById('salary-category-wise'));
		this.joining_category_wise_wrapper = echarts.init(document.getElementById('joining-category-wise'));
		this.overtime_category_wise_wrapper = echarts.init(document.getElementById('overtime-category-wise'));
		this.relieving_category_wise_wrapper = echarts.init(document.getElementById('relieving-category-wise'));
		this.set_salarytab_data()
	}

	make_amt_catogery_wise_field(filter) {
		this.amount_category_wise_field = frappe.ui.form.make_control({
			df: {
				fieldtype: 'Select',
				// label: 'Amount Catogery',
				fieldname: 'amount_category_wise',
				options: ['Gross Salary', 'Net Salary'],
				reqd: 1,
				onchange: () => {
					this.amount_category_wise = this.amount_category_wise_field.get_value();
					this.salary_detail();
				}
			},
			parent: filter.find('.amount-category-field'),
			render_input: true
		});

		this.amount_category_wise_field.set_value(this.amount_category_wise);
	}

	set_salarytab_data() {
		this.salary_detail();
		this.joining_category_detail();
		this.overtime_category_detail();
		this.relieving_category_detail();
	}

	salary_detail() {
		var me = this;
		this.salary_category_wise_wrapper.clear();
		this.salary_category_wise_wrapper.showLoading();

		if (!me.company || !me.payroll_from || !me.payroll_to || !me.amount_category_wise || !me.catogery_wise) return;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.get_salary_amount",
			args: {
				company: me.company,
				payroll_from: me.payroll_from,
				payroll_to: me.payroll_to,
				amount_category: me.amount_category_wise,
				group_category: me.catogery_wise
			},
			callback: function(r) {
				var pie_setting = {
					title: {
						text: 'Salary Detail',
						subtext: '',
					},
					legend: {
						show: false
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
						dimensions: ['name', 'value'],
						source: r.message
					},
					series: [{
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
						},
					}]
				}

				me.salary_category_wise_wrapper.hideLoading();
				me.salary_category_wise_wrapper.setOption(pie_setting);
			}
		});
	}

	joining_category_detail() {
		var me = this;
		this.joining_category_wise_wrapper.clear();
		this.joining_category_wise_wrapper.showLoading();

		if (!me.company || !me.payroll_from || !me.payroll_to || !me.catogery_wise) return;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.new_joining_employee",
			args: {
				company: me.company,
				payroll_from: me.payroll_from,
				payroll_to: me.payroll_to,
				group_category: me.catogery_wise
			},
			callback: function(r) {
				var bar_setting = {
					title: {
						text: __('Joining Detail')
					},
					tooltip: {
						trigger: 'axis'
					},
					xAxis: {
						show: false,
						type: 'category',
						data: r.message['label'],
						axisLabel: {
							fontSize: 9
						}
					},
					yAxis: {
						name: 'Count',
						type: 'value',
						axisLabel: {
							formatter: function (value, index) {
								return numeral(value).format('0[.]0a');
							}
						}
					},
					series: [{
						data: r.message['value'],
						type: 'bar',
						showBackground: true
					}]
				};

				me.set_detail(me.wrapper.find('.payroll-joining-details'), 'payroll_joining_count', r.message['joined_dict']);

				me.joining_category_wise_wrapper.hideLoading();
				me.joining_category_wise_wrapper.setOption(bar_setting);
			}
		});
	}

	overtime_category_detail() {
		var me = this;
		this.overtime_category_wise_wrapper.clear();
		this.overtime_category_wise_wrapper.showLoading();

		if (!me.company || !me.payroll_from || !me.payroll_to || !me.catogery_wise) return;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.get_overtime_amount",
			args: {
				company: me.company,
				payroll_from: me.payroll_from,
				payroll_to: me.payroll_to,
				group_category: me.catogery_wise
			},
			callback: function(r) {
				var pie_setting = {
					title: {
						text: 'Overtime Detail',
						subtext: '',
					},
					legend: {
						show: false
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
						dimensions: ['name', 'value'],
						source: r.message
					},
					series: [{
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
						},
					}]
				}

				me.overtime_category_wise_wrapper.hideLoading();
				me.overtime_category_wise_wrapper.setOption(pie_setting);
			}
		});
	}

	relieving_category_detail() {
		var me = this;
		this.relieving_category_wise_wrapper.clear();
		this.relieving_category_wise_wrapper.showLoading();

		if (!me.company || !me.payroll_from || !me.payroll_to || !me.catogery_wise) return;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.relieving_employee",
			args: {
				company: me.company,
				payroll_from: me.payroll_from,
				payroll_to: me.payroll_to,
				group_category: me.catogery_wise
			},
			callback: function(r) {
				var bar_setting = {
					title: {
						text: __('Relieving Detail')
					},
					tooltip: {
						trigger: 'axis'
					},
					xAxis: {
						show: false,
						type: 'category',
						data: r.message['label'],
						axisLabel: {
							fontSize: 9
						}
					},
					yAxis: {
						name: 'Count',
						type: 'value',
						axisLabel: {
							formatter: function (value, index) {
								return numeral(value).format('0[.]0a');
							}
						}
					},
					series: [{
						data: r.message['value'],
						type: 'bar',
						showBackground: true
					}]
				};

				me.set_detail(me.wrapper.find('.payroll-relieving-details'), 'payroll_relieving_count', r.message['relieved_dict']);

				me.relieving_category_wise_wrapper.hideLoading();
				me.relieving_category_wise_wrapper.setOption(bar_setting);
			}
		});
	}

	payroll_completion_tab(holder) {
		var me = this;
		var card_holder = holder.find('.card-holder');
		card_holder.empty();

		card_holder.append(`<div class="col-sm-12 card">
			<div class="box">
				<div class="row chart" id="payroll-completion-chart"></div>
			</div>
		</div>
		<div class="col-sm-12 card">
			<div class="box">
				<div class="row pending-process-detail table-responsive custom_container"></div>
			</div>
		</div>
		`);

		this.payroll_completion_chart_wrapper = echarts.init(document.getElementById('payroll-completion-chart'));
		this.set_completion_date();

		this.payroll_completion_chart_wrapper.on('click', function (params) {
			if (params.name == 'Absent') {
				me.set_detail(me.wrapper.find('.pending-process-detail'), '_pending_count', me.pending_process_detail['attendance']);
			}
			else if (params.name == 'Pending Leave Approval') {
				me.set_detail(me.wrapper.find('.pending-process-detail'), '_pending_count', me.pending_process_detail['leave']);
			}
			else if (params.name == 'Pending Late Coming') {
				me.set_detail(me.wrapper.find('.pending-process-detail'), '_pending_count', me.pending_process_detail['late_coming']);
			}
			else {
				me.set_detail(me.wrapper.find('.pending-process-detail'), '_pending_count', me.pending_process_detail['early_going']);
			}
		});
	}

	set_completion_date() {
		this.pending_process();
	}

	pending_process() {
		var me = this;
		this.payroll_completion_chart_wrapper.clear();
		this.payroll_completion_chart_wrapper.showLoading();

		if (!me.company || !me.payroll_period) return;
		frappe.call({
			method: "hrm.hrm.page.hr_dashboard.hr_dashboard.payroll_completion_detail",
			args: {
				company: me.company,
				payroll_period: me.payroll_period,
			},
			callback: function(r) {
				me.pending_process_detail = r.message;

				var bar_setting = {
					title: {
						text: __('Readiness of Payroll Process')
					},
					tooltip: {
						trigger: 'axis'
					},
					xAxis: {
						show: false,
						type: 'category',
						data: ['Absent', 'Pending Leave Approval', 'Pending Late Coming', 'Pending Early Going'],
						axisLabel: {
							fontSize: 9
						}
					},
					yAxis: {
						type: 'value',
						axisLabel: {
							formatter: function (value, index) {
								return numeral(value).format('0[.]0a');
							}
						}
					},
					series: [{
						data: [r.message['attendance_count'], r.message['leave_count'], r.message['late_coming_count'], r.message['early_going_count']],
						type: 'bar',
						showBackground: true
					}]
				};

				me.payroll_completion_chart_wrapper.hideLoading();
				me.payroll_completion_chart_wrapper.setOption(bar_setting);

				me.set_detail(me.wrapper.find('.pending-process-detail'), '_pending_count', r.message['attendance']);
			}
		});
	}
}