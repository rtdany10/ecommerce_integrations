import json

import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.utils import cint, cstr, flt, getdate

from ecommerce_integrations.shopify.constants import (
	FULLFILLMENT_ID_FIELD,
	ORDER_ID_FIELD,
	ORDER_NUMBER_FIELD,
	SETTING_DOCTYPE,
)
from ecommerce_integrations.shopify.order import (
	get_sales_order,
	get_tax_account_description,
	get_tax_account_head,
)
from ecommerce_integrations.shopify.product import get_item_code
from ecommerce_integrations.shopify.utils import create_shopify_log


def prepare_delivery_note(payload, request_id=None):
	frappe.set_user("Administrator")
	setting = frappe.get_doc(SETTING_DOCTYPE)
	frappe.flags.request_id = request_id

	order = payload

	try:
		sales_order = get_sales_order(cstr(order["id"]))
		if sales_order:
			create_delivery_note(order, setting, sales_order)
			create_shopify_log(status="Success")
		else:
			create_shopify_log(status="Invalid", message="Sales Order not found for syncing delivery note.")
	except Exception as e:
		create_shopify_log(status="Error", exception=e, rollback=True)


def create_delivery_note(shopify_order, setting, so):
	if not cint(setting.sync_delivery_note):
		return

	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

	for fulfillment in shopify_order.get("fulfillments"):
		if (
			not frappe.db.get_value("Delivery Note", {FULLFILLMENT_ID_FIELD: fulfillment.get("id")}, "name")
			and so.docstatus == 1
		):

			dn = make_delivery_note(so.name)
			setattr(dn, ORDER_ID_FIELD, fulfillment.get("order_id"))
			setattr(dn, ORDER_NUMBER_FIELD, shopify_order.get("name"))
			setattr(dn, FULLFILLMENT_ID_FIELD, fulfillment.get("id"))
			dn.set_posting_time = 1
			dn.posting_date = getdate(fulfillment.get("created_at"))
			dn.naming_series = setting.delivery_note_series or "DN-Shopify-"
			dn.items = get_fulfillment_items(
				dn.items, fulfillment.get("line_items"), fulfillment.get("location_id")
			)
			dn.flags.ignore_mandatory = True
			dn.taxes = []
			for tax in get_dn_taxes(fulfillment, setting):
				dn.append("taxes", tax)
			dn.save().submit()

			if shopify_order.get("note"):
				dn.add_comment(text=f"Order Note: {shopify_order.get('note')}")

			if setting.sync_invoice_on_delivery:
				inv = make_sales_invoice(dn.name)
				if inv.items:
					setattr(inv, ORDER_ID_FIELD, fulfillment.get("order_id"))
					setattr(inv, ORDER_NUMBER_FIELD, shopify_order.get("name"))
					inv.submit()


def get_fulfillment_items(dn_items, fulfillment_items, location_id=None):
	setting = frappe.get_cached_doc(SETTING_DOCTYPE)
	wh_map = setting.get_integration_to_erpnext_wh_mapping()
	warehouse = wh_map.get(str(location_id)) or setting.warehouse

	return [
		dn_item.update({"qty": item.get("quantity"), "warehouse": warehouse})
		for item in fulfillment_items
		for dn_item in dn_items
		if get_item_code(item) == dn_item.item_code
	]


def update_fulfillment_status(payload, request_id=None):
	frappe.set_user("Administrator")
	frappe.flags.request_id = request_id
	fulfillment = payload

	delivery_note = frappe.db.get_value(
		"Delivery Note", {FULLFILLMENT_ID_FIELD: cstr(fulfillment["id"]), "docstatus": 1}, "name"
	)
	if not delivery_note:
		return

	try:
		if cstr(fulfillment["status"]) == "cancelled":
			frappe.get_doc("Delivery Note", delivery_note).cancel()
		create_shopify_log(status="Success")
	except Exception as e:
		create_shopify_log(status="Error", exception=e, rollback=True)
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "Delivery Note",
				"reference_name": delivery_note,
				"content": frappe._(
					"""
					This delivery note has been cancelled on Shopify.
					Could not cancel on ERPNext, check integration logs for more info.
					"""
				),
			}
		).insert(ignore_permissions=True)


def get_dn_taxes(fulfillment, setting):
	tax_account_wise_data = {}
	line_items = fulfillment.get("line_items")

	for line_item in line_items:
		item_code = get_item_code(line_item)
		for tax in line_item.get("tax_lines"):
			account_head = get_tax_account_head(tax)
			tax_account_wise_data.setdefault(
				account_head, {
					"charge_type": "Actual",
					"description": (
						f"{get_tax_account_description(tax) or tax.get('title')}"
					),
					"cost_center": setting.cost_center,
					"included_in_print_rate": 0,
					"dont_recompute_tax": 1,
					"tax_amount": 0,
					"item_wise_tax_detail": {}
				}
			)
			tax_amt = (
				flt(tax.get("rate", 0)) * flt(line_item.get("quantity", 0)) * flt(line_item.get("price", 0))
			)

			tax_account_wise_data[account_head]["tax_amount"] += flt(tax_amt)
			tax_account_wise_data[account_head]["item_wise_tax_detail"].update({
				item_code: [flt(tax.get("rate")) * 100, flt(tax_amt)]
			})

	taxes = []
	for account, tax_row in tax_account_wise_data.items():
		row = {"account_head": account, **tax_row}
		row["item_wise_tax_detail"] = json.dumps(row.get("item_wise_tax_detail", {}))
		taxes.append(row)

	return taxes