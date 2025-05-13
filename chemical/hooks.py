# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version
app_name = "chemical"
app_title = "Chemical"
app_publisher = "FinByz Tech Pvt. Ltd."
app_description = "Custom App for chemical Industry"
app_icon = "octicon octicon-beaker"
app_color = "Orange"
app_email = "info@finbyz.com"
app_license = "GPL 3.0"

from . import __version__ as app_version

app_include_js = [
	"chemical.bundle.js"
]

doctype_list_js = {"Item Price" : "public/js/list_js/item_price.js"}

doctype_js = {
	"Production Plan": "public/js/doctype_js/production_plan.js",
	"BOM": "public/js/doctype_js/bom.js",
	"BOM Update Tool": "public/js/doctype_js/bom_update_tool.js",
	"Stock Entry": "public/js/doctype_js/stock_entry.js",
	"Purchase Invoice": "public/js/doctype_js/purchase_invoice.js",
	"Purchase Order": "public/js/doctype_js/purchase_order.js",
	"Work Order": "public/js/doctype_js/work_order.js",
	"Sales Order": "public/js/doctype_js/sales_order.js",
	"Sales Invoice": "public/js/doctype_js/sales_invoice.js",
	"Delivery Note": "public/js/doctype_js/delivery_note.js",
	"Address": "public/js/doctype_js/address.js",
	"Customer": "public/js/doctype_js/customer.js",
	"Supplier": "public/js/doctype_js/supplier.js",
	"Purchase Receipt": "public/js/doctype_js/purchase_receipt.js",
	"Item": "public/js/doctype_js/item.js",
	# "Batch": "public/js/doctype_js/batch.js",
	"Quotation":"public/js/doctype_js/quotation.js",
	"Quality Inspection":"public/js/doctype_js/quality_inspection.js",
}

override_doctype_class = {
    "Stock Entry": "chemical.chemical.override.doctype.stock_entry.StockEntry",
    "Work Order": "chemical.chemical.override.doctype.work_order.WorkOrder",
    "Quality Inspection": "chemical.chemical.override.doctype.quality_inspection.QualityInspection",
    "Production Plan":"chemical.chemical.override.doctype.production_plan.ProductionPlan",
    "Purchase Receipt": "chemical.chemical.override.doctype.purchase_receipt.PurchaseReceipt",
    "Purchase Invoice": "chemical.chemical.override.doctype.purchase_invoice.PurchaseInvoice",
    "Stock Reconciliation": "chemical.chemical.override.doctype.stock_reconciliation.StockReconciliation",
    "Subcontracting Receipt": "chemical.chemical.override.doctype.subcontracting_receipt.SubcontractingReceipt",
}

override_whitelisted_methods = {
	"erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool.enqueue_update_cost": "chemical.chemical.doc_events.bom.enqueue_update_cost",
	"erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance_for": "chemical.chemical.doc_events.stock_reconciliation.get_stock_balance_for",
    "erpnext.controllers.stock_controller.make_quality_inspections":"chemical.chemical.overrides.whitelisted_methods.stock_controller.make_quality_inspections",
    "erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry": "chemical.chemical.override.doctype.work_order.make_stock_entry",
}

doc_events = {
    # Finbyz Check Start
    "Batch": {
        "before_naming": "chemical.chemical.override.doc_events.batch.before_naming",
	},
    "Work Order":{
		"validate":"chemical.chemical.override.doc_events.work_order.validate",
		"before_submit": "chemical.chemical.override.doc_events.work_order.before_submit",
	},
    "Stock Entry": {
		"before_validate": "chemical.chemical.override.doc_events.stock_entry.before_validate",
		"validate": "chemical.chemical.override.doc_events.stock_entry.validate",
		"before_save": "chemical.chemical.override.doc_events.stock_entry.before_save",
		"before_submit": "chemical.chemical.override.doc_events.stock_entry.before_submit",
		"on_submit": "chemical.chemical.override.doc_events.stock_entry.on_submit",
		"before_cancel": "chemical.chemical.override.doc_events.stock_entry.before_cancel",
		"on_cancel": "chemical.chemical.override.doc_events.stock_entry.on_cancel",
	},
	"Item Price": {
		"before_save": "chemical.chemical.override.doc_events.item_price.before_save",
	},
	# Finbyz Check End
	"BOM": {
		"before_save": "chemical.chemical.doc_events.bom.bom_before_save",
		"validate": "chemical.chemical.doc_events.bom.bom_validate",
		"on_submit":"chemical.chemical.doc_events.bom.on_submit"
	},
	"Item": {
		"validate": "chemical.chemical.doc_events.item.item_validate",
	},
	"Purchase Receipt": {
		"onload":"chemical.chemical.doc_events.purchase_receipt.onload",
		"before_validate": "chemical.chemical.doc_events.purchase_receipt.before_validate",
		"validate": [
			# "chemical.api.pr_validate",
			"chemical.batch_valuation.pr_validate",
			"chemical.chemical.doc_events.purchase_receipt.t_validate",
		],
		"on_cancel": "chemical.batch_valuation.pr_on_cancel",
		"before_submit": "chemical.chemical.doc_events.purchase_receipt.before_submit",
		"before_cancel": "chemical.chemical.doc_events.purchase_receipt.before_cancel",
	},
	"Purchase Invoice": {
		"onload":"chemical.chemical.doc_events.purchase_invoice.onload",
		"before_validate": "chemical.chemical.doc_events.purchase_invoice.before_validate",
		"validate": [
			"chemical.batch_valuation.pi_validate",
		],
		"on_cancel": "chemical.batch_valuation.pi_on_cancel",
		"before_submit": "chemical.chemical.doc_events.purchase_invoice.before_submit",
		"before_cancel": "chemical.chemical.doc_events.purchase_invoice.before_cancel",
		"on_trash":"chemical.chemical.doc_events.purchase_invoice.on_trash",

	},
	"Purchase Order": {
		"onload":"chemical.chemical.doc_events.purchase_order.onload",
		"validate": "chemical.chemical.doc_events.purchase_order.validate"
	},
	
	"Landed Cost Voucher": {
		"validate": [
			"chemical.batch_valuation.lcv_validate",
			# "chemical.api.lcv_validate",
		],
		"on_submit": "chemical.batch_valuation.lcv_on_submit",
		"on_cancel": [
			"chemical.batch_valuation.lcv_on_cancel",
		],
	},
	"Delivery Note": {
		"onload":"chemical.chemical.doc_events.delivery_note.onload",
		"on_submit": "chemical.chemical.doc_events.delivery_note.dn_on_submit",
		"before_cancel": "chemical.chemical.doc_events.delivery_note.before_cancel",
		"before_submit": "chemical.chemical.doc_events.delivery_note.before_submit",

		"before_validate": "chemical.chemical.doc_events.delivery_note.validate",
	},
	"Sales Invoice": {
		"onload":"chemical.chemical.doc_events.sales_invoice.onload",
		"before_submit": [
			"chemical.chemical.doc_events.sales_invoice.si_before_submit",
			"chemical.chemical.doc_events.sales_invoice.before_submit",
		],
		"before_validate": "chemical.chemical.doc_events.sales_invoice.before_validate",
		"validate": "chemical.chemical.doc_events.sales_invoice.validate",
		"before_cancel": "chemical.chemical.doc_events.sales_invoice.before_cancel",
		"on_trash":"chemical.chemical.doc_events.sales_invoice.on_trash",

	},
	"Stock Ledger Entry": {
		"before_submit": "chemical.chemical.doc_events.stock_ledger_entry.sl_before_submit"
	},
	"Stock Reconciliation":{
		"on_submit":"chemical.chemical.doc_events.stock_reconciliation.on_submit",
		"on_cancel":"chemical.chemical.doc_events.stock_reconciliation.on_cancel"
	},
	"Sales Order": {
		"onload":"chemical.chemical.doc_events.sales_order.onload",
		"on_cancel": "chemical.api.so_on_cancel",
		"before_validate": "chemical.chemical.doc_events.sales_order.validate"
	},
    "Quality Inspection": {
       "on_submit": "chemical.chemical.doc_events.quality_inspection.validate",
       "on_cancel": "chemical.chemical.doc_events.quality_inspection.on_cancel",
       "validate": "chemical.chemical.doc_events.quality_inspection.validate_qc"
	},
	("Outward Sample","Ball Mill Data Sheet","Outward Tracking"):{
		"on_submit":"chemical.chemical.doc_events.outward_sample.on_submit",
		"before_update_after_submit":"chemical.chemical.doc_events.outward_sample.before_update_after_submit",
		"before_cancel":"chemical.chemical.doc_events.outward_sample.on_cancel",
		"on_trash":"chemical.chemical.doc_events.outward_sample.on_trash"
	},
}

scheduler_events = {
	"daily":[
		"chemical.chemical.doc_events.bom.update_item_price_daily"
	]
}

override_doctype_dashboards = {
	"Stock Entry": "chemical.chemical.dashboard.stock_entry.get_data",
	"Customer": "chemical.chemical.dashboard.customer.get_data",
	"Quotation": "chemical.chemical.dashboard.quotation.get_data",
	"Lead": "chemical.chemical.dashboard.lead.get_data"
}

from erpnext.stock.stock_ledger import update_entries_after
from chemical.chemical.doc_events.stock_ledger import build
update_entries_after.build = build
