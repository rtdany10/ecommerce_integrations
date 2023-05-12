# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class ShopifyWarehouse(Document):
	def validate(self):
		for row in self.priority:
			if frappe.db.get_value("Warehouse", row.warehouse, "is_group"):
				frappe.throw(_("Row #{0}: {1} is a group warehouse and cannot be selected."))
	
	def get_wh(self, item_code, qty):
		rem_qty = qty
		wh = [row.warehouse for row in self.priority]
		if not wh:
			return

		stock_qty = frappe.db.get_all(
			"Bin",
			fields=["actual_qty", "warehouse"],
			filters={"warehouse": ["IN", wh], "item_code": item_code},
		)

		wh_map = {}
		for wh_stock in stock_qty:
			if wh_stock["actual_qty"] <= 0:
				continue

			wh_map[wh_stock["warehouse"]] = min(wh_stock["actual_qty"], rem_qty)
			rem_qty -= wh_map[wh_stock["warehouse"]]
			if rem_qty <= 0:
				break

		if rem_qty:
			return

		return wh_map
