from __future__ import unicode_literals
import frappe
from frappe import _,msgprint
from frappe.utils import flt, cint, nowdate, cstr, now_datetime
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from chemical.api import purchase_cal_rate_qty, quantity_price_to_qty_rate


def onload(self,method):
    quantity_price_to_qty_rate(self)

def before_validate(self,method):
    pass
	# purchase_cal_rate_qty(self)

def before_submit(self, method):
	update_item_price_history(self)
	override_pi_status_updater_args()

def before_cancel(self, method):
	delete_item_price_history(self)
	override_pi_status_updater_args()

def on_trash(self, method):
	delete_item_price_history(self)

def override_pi_status_updater_args():
	PurchaseInvoice.update_status_updater_args = pi_update_status_updater_args

def pi_update_status_updater_args(self):
	if not frappe.db.get_value("Company", self.company, "maintain_as_is_new"):
		if cint(self.update_stock):
			self.status_updater.append({
				'source_dt': 'Purchase Invoice Item',
				'target_dt': 'Purchase Order Item',
				'join_field': 'po_detail',
				'target_field': 'received_qty',
				'target_parent_dt': 'Purchase Order',
				'target_parent_field': 'per_received',
				'target_ref_field': 'quantity',
				'source_field': 'quantity',
				'second_source_dt': 'Purchase Receipt Item',
				'second_source_field': 'quantity',
				'second_join_field': 'purchase_order_item',
				'percent_join_field':'purchase_order',
				'overflow_type': 'receipt',
				'extra_cond': """ and exists(select name from `tabPurchase Invoice`
					where name=`tabPurchase Invoice Item`.parent and update_stock = 1)"""
			})
			if cint(self.is_return):
				self.status_updater.append({
					'source_dt': 'Purchase Invoice Item',
					'target_dt': 'Purchase Order Item',
					'join_field': 'po_detail',
					'target_field': 'returned_qty',
					'source_field': '-1 * quantity',
					'second_source_dt': 'Purchase Receipt Item',
					'second_source_field': '-1 * quantity',
					'second_join_field': 'purchase_order_item',
					'overflow_type': 'receipt',
					'extra_cond': """ and exists (select name from `tabPurchase Invoice`
						where name=`tabPurchase Invoice Item`.parent and update_stock=1 and is_return=1)"""
				})
	else:
		if cint(self.update_stock):
			self.status_updater.append({
				'source_dt': 'Purchase Invoice Item',
				'target_dt': 'Purchase Order Item',
				'join_field': 'po_detail',
				'target_field': 'received_qty',
				'target_parent_dt': 'Purchase Order',
				'target_parent_field': 'per_received',
				'target_ref_field': 'qty',
				'source_field': 'qty',
				'second_source_dt': 'Purchase Receipt Item',
				'second_source_field': 'qty',
				'second_join_field': 'purchase_order_item',
				'percent_join_field':'purchase_order',
				'overflow_type': 'receipt',
				'extra_cond': """ and exists(select name from `tabPurchase Invoice`
					where name=`tabPurchase Invoice Item`.parent and update_stock = 1)"""
			})
			if cint(self.is_return):
				self.status_updater.append({
					'source_dt': 'Purchase Invoice Item',
					'target_dt': 'Purchase Order Item',
					'join_field': 'po_detail',
					'target_field': 'returned_qty',
					'source_field': '-1 * qty',
					'second_source_dt': 'Purchase Receipt Item',
					'second_source_field': '-1 * qty',
					'second_join_field': 'purchase_order_item',
					'overflow_type': 'receipt',
					'extra_cond': """ and exists (select name from `tabPurchase Invoice`
						where name=`tabPurchase Invoice Item`.parent and update_stock=1 and is_return=1)"""
				})

def update_item_price_history(self):
	if not frappe.db.get_value("Company", self.company, "maintain_as_is_new"):
		if self.items:
			for item in self.items:
				if item.item_code:
					doc = frappe.new_doc("Item Price History")
					doc.date = self.posting_date
					doc.item_code = item.item_code
					doc.price = item.price
					doc.supplier = self.supplier
					doc.buying = 1
					doc.update_from = self.doctype
					doc.docname = self.name
					doc.save(ignore_permissions=True)
	else:
		if self.items:
			for item in self.items:
				if item.item_code:
					doc = frappe.new_doc("Item Price History")
					doc.date = self.posting_date
					doc.item_code = item.item_code
					doc.price = item.rate
					doc.supplier = self.supplier
					doc.buying = 1
					doc.update_from = self.doctype
					doc.docname = self.name
					doc.save(ignore_permissions=True)

def delete_item_price_history(self):
	while frappe.db.exists("Item Price History",{"update_from":self.doctype,"docname":self.name}):
		doc = frappe.get_doc("Item Price History",{"update_from":self.doctype,"docname":self.name})
		doc.db_set('docname','')
		doc.delete()