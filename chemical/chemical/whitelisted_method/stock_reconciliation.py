import frappe
from erpnext.stock.utils import get_stock_balance, get_incoming_rate
from erpnext.stock.doctype.batch.batch import get_batch_qty
from frappe.utils import flt

@frappe.whitelist()
def get_stock_balance_for(item_code, warehouse,
	posting_date, posting_time, batch_no=None, with_valuation_rate= True):
	frappe.has_permission("Stock Reconciliation", "write", throw = True)
	item_dict = frappe.db.get_value("Item", item_code,
		["has_serial_no", "has_batch_no"], as_dict=1)

	if not item_dict:
		# In cases of data upload to Items table
		msg = _("Item {} does not exist.").format(item_code)
		frappe.throw(msg, title=_("Missing"))

	serial_nos = ""
	with_serial_no = True if item_dict.get("has_serial_no") else False
	data = get_stock_balance(item_code, warehouse, posting_date, posting_time,
		with_valuation_rate=with_valuation_rate, with_serial_no=with_serial_no)

	if with_serial_no:
		qty, rate, serial_nos = data
	else:
		qty, rate = data

	if item_dict.get("has_batch_no"):
		qty = get_batch_qty(batch_no, warehouse, posting_date=posting_date, posting_time=posting_time) or 0
		rate = get_incoming_rate({
				"item_code": item_code,
				"warehouse": warehouse,
				"qty": flt(qty) * -1,
				"posting_date": posting_date,
				"posting_time": posting_time,
				"batch_no": batch_no
			}, raise_error_if_no_rate=True)

	return {
		'qty': qty,
		'rate': rate,
		'serial_nos': serial_nos
	}