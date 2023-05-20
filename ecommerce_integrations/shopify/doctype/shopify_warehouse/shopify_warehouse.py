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
		warehouses = [row.warehouse for row in self.priority]
		if not warehouses:
			return

		stock_qty = frappe.db.get_all(
			"Bin",
			fields=["actual_qty", "warehouse"],
			filters={"warehouse": ["IN", warehouses], "item_code": item_code},
		)

		wh_qty_map = {d["warehouse"]: d["actual_qty"] for d in stock_qty}

		row_wh_map = {}
		for wh in warehouses:
			if wh_qty_map.get(wh, 0) <= 0:
				continue

			row_wh_map[wh] = min(wh_qty_map[wh], rem_qty)
			rem_qty -= row_wh_map[wh]
			if rem_qty <= 0:
				break

		if rem_qty:
			return

		return row_wh_map
