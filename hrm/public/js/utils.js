$(function() {
	if (window.location.hash == '#modules/HR') {
		frappe.route_history.pop(-1);
		window.location.hash = '#modules/HRM';
		window.location.reload();
	}
});

$(window).on('hashchange', function() {
	if (window.location.hash == '#modules/HR') {
		frappe.route_history.pop(-1);
		window.location.hash = '#modules/HRM';
		window.location.reload();
		// frappe.route();
		// frappe.route.trigger('change');
	}
});

// window.addEventListener('popstate', (e) => {
	
// });