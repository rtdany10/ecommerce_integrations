# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from shopify.resources import Product
from ecommerce_integrations.shopify.connection import temp_shopify_session
from ecommerce_integrations.shopify.constants import (
	MODULE_NAME,
)
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


class ShopifyItemMetafield(Document):
	def validate(self):
		self.fetch_meta_fields()
		self.update_shopify_metafields()

	def update_shopify_metafields(self):
		if not self.shopify_product_id:
			return

		metafields = Product.find(self.shopify_product_id).metafields()
		for metafield in metafields:
			key = frappe.scrub(metafield.key)
			if value := self.get(key):
				if value != metafield.value:
					metafield.value = value
					metafield.save()

		frappe.msgprint("Shopify Metafields updated successfully.")

	@frappe.whitelist()
	def fetch_meta_fields(self, force=False):
		if not force and not self.is_new():
			return

		self.shopify_product_id = frappe.db.get_value(
			"Ecommerce Item",
			{"erpnext_item_code": self.item_code, "integration": MODULE_NAME},
			"integration_item_code",
		)
		if not self.shopify_product_id:
			frappe.throw(
				f"Shopify Product ID not found for Item Code: {self.item_code} and Integration: {MODULE_NAME}"
			)

		meta_fields = get_product_meta_fields(self.shopify_product_id)
		self.create_fields(meta_fields)
		if force:
			self.save()

	def create_fields(self, meta_fields):
		fields = []
		last_field = self.meta.fields[-1].fieldname
		field_values = {}
		for field in meta_fields:
			key = frappe.scrub(field.get("key"))
			field_values[key] = field.get("value")
			if self.meta.has_field(key):
				continue

			fields.append({
				"fieldname": key,
				"label": frappe.unscrub(key),
				"fieldtype": "Small Text",
				"translatable": 0,
				"reqd": 0,
				"insert_after": last_field,
			})
			last_field = field.get("key")

		create_custom_fields({self.doctype: fields})
		for k, v in field_values.items():
			self.set(k, v)


def get_product_meta_fields(product_id):
	return _get_product_meta_fields(product_id)


@temp_shopify_session
def _get_product_meta_fields(product_id):
	shopify_product = Product.find(product_id).metafields()
	metafields = []
	for d in shopify_product:
		metafields.append(d.to_dict())
	return metafields
