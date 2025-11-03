// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shopify Item Metafield", {
	refresh(frm) {
        frm.add_custom_button(__('Sync Metafields from Shopify'), async function() {
            frm.dirty();
            await frm.call("fetch_meta_fields", {force: true});
            frappe.ui.toolbar.clear_cache();
        });
	},
});
