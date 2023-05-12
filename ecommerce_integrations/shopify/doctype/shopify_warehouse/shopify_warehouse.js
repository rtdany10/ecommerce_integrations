// Copyright (c) 2023, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shopify Warehouse', {
	setup: function(frm) {
		frm.set_query('warehouse', 'priority', function () {
			return {
				filters: {
					is_group: 0,
				},
			};
		});
	}
});
