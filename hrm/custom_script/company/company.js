frappe.ui.form.on("Company", {
    configure_hrm: function(frm) {
        if (frm.is_new()) return;
        // frappe.throw("abs")
        frappe.confirm('By Accepting this all HRM Setting will be Reset. Are you sure you want to proceed?',
        () => {
            frappe.call({
                method: "hrm.install.add_data",
                args: {
                    company: frm.doc.name
                },
                freeze: true,
                freeze_message: "Configuring..."
                // callback:{()};
            });
            // frappe.show_progress('Loading..', 70, 100, 'Please wait');
        }, 
        () => {});
    }
});