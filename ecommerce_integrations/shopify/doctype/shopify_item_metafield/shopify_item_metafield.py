# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from shopify.resources import Product, Variant
from ecommerce_integrations.shopify.connection import temp_shopify_session
from ecommerce_integrations.shopify.constants import (
	MODULE_NAME,
)


class ShopifyItemMetafield(Document):
	def validate(self):
		self.fetch_meta_fields()

	def fetch_meta_fields(self):
		self.shopify_product_id = frappe.db.get_value(
			"Ecommerce Item",
			{"erpnext_item_code": self.item_code, "integration": MODULE_NAME},
			"integration_item_code",
		)
		meta_fields = get_product_meta_fields(self.shopify_product_id)
		frappe.msgprint(meta_fields[0])



def get_product_meta_fields(product_id):
	return _get_product_meta_fields(product_id)


@temp_shopify_session
def _get_product_meta_fields(product_id):
	shopify_product = Product.find(product_id).metafields()
	metafields = []
	for d in shopify_product:
		metafields.append(d.to_dict())
	return metafields
