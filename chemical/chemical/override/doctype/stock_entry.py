from collections import defaultdict

import frappe
from frappe.utils import flt, cstr, cint
from erpnext.stock.doctype.stock_entry.stock_entry import (
	StockEntry as _StockEntry,
	FinishedGoodError,
)
from chemical.chemical.override.utils import make_batches
from frappe import _
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.get_item_details import get_default_cost_center
from erpnext.stock.doctype.item.item import get_item_defaults


# TODO: need to check with default function
def add_additional_cost(doc, self, qty=None):
	maintain_as_is_new = frappe.db.get_value("Company",self.company,'maintain_as_is_new')
	qty = flt(qty)
	abbr = frappe.db.get_value("Company",self.company,'abbr')
	bom = frappe.get_doc("BOM",self.bom_no)

	for additional_cost in bom.additional_cost:
		additional_cost_dict = {}
		if additional_cost.uom == "FG QTY":
			qty = flt(doc.fg_completed_qty if maintain_as_is_new else doc.fg_completed_quantity)
			additional_cost_dict['uom'] = "FG QTY"
		else:
			qty = (qty *flt(additional_cost.qty)) / flt(bom.quantity) if maintain_as_is_new else (qty *flt(additional_cost.qty)) / flt(bom.quantity)
		# fetch expense_account from bom if not then fetch defaut account 
		additional_cost_dict["expense_account"] = additional_cost.account or 'Expenses Included In Valuation - {}'.format(abbr)
		additional_cost_dict["description"] = additional_cost.description
		additional_cost_dict["qty"] = qty
		additional_cost_dict["rate"] = additional_cost.rate
		additional_cost_dict["amount"] = qty * flt(additional_cost.rate)
		additional_cost_dict["base_amount"] = qty * flt(additional_cost.rate)
		doc.append("additional_costs", additional_cost_dict)

def get_available_materials(company, work_order) -> dict:
	maintain_as_is_new, data = get_stock_entry_data(company, work_order)

	available_materials = {}
	for row in data:
		key = (row.item_code, row.warehouse)
		if row.purpose != "Material Transfer for Manufacture":
			key = (row.item_code, row.s_warehouse)

		if key not in available_materials:
			data = {"item_details": row, "batch_details": defaultdict(float), "qty": 0, "serial_nos": []}
			
			if not maintain_as_is_new:
				data['quantity'] = 0
				data['batch_details_quantity'] = defaultdict(float)
			
			available_materials.setdefault(
				key,
				frappe._dict(data),
			)

		item_data = available_materials[key]

		if row.purpose == "Material Transfer for Manufacture":
			item_data.qty += row.qty
			if row.batch_no:
				item_data.batch_details[row.batch_no] += row.qty
			
			if not maintain_as_is_new:
				item_data.quantity += row.quantity

				if row.batch_no:
					item_data.batch_details_quantity[row.batch_no] += row.quantity

			if row.serial_no:
				item_data.serial_nos.extend(get_serial_nos(row.serial_no))
				item_data.serial_nos.sort()
		else:
			# Consume raw material qty in case of 'Manufacture' or 'Material Consumption for Manufacture'

			item_data.qty -= row.qty
			if row.batch_no:
				item_data.batch_details[row.batch_no] -= row.qty
			
			if not maintain_as_is_new:
				item_data.quantity -= row.quantity

				if row.batch_no:
					item_data.batch_details_quantity[row.batch_no] -= row.quantity

			if row.serial_no:
				for serial_no in get_serial_nos(row.serial_no):
					item_data.serial_nos.remove(serial_no)

	return maintain_as_is_new, available_materials


def get_stock_entry_data(company, work_order):
	maintain_as_is_new = frappe.db.get_value("Company", company, "maintain_as_is_new")
	stock_entry = frappe.qb.DocType("Stock Entry")
	stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")

	fields = [
		stock_entry_detail.item_name,
		stock_entry_detail.original_item,
		stock_entry_detail.item_code,
		stock_entry_detail.qty,
		(stock_entry_detail.t_warehouse).as_("warehouse"),
		(stock_entry_detail.s_warehouse).as_("s_warehouse"),
		stock_entry_detail.description,
		stock_entry_detail.stock_uom,
		stock_entry_detail.expense_account,
		stock_entry_detail.cost_center,
		stock_entry_detail.batch_no,
		stock_entry_detail.serial_no,
		stock_entry.purpose,
	]

	if not maintain_as_is_new:
		fields.append(stock_entry_detail.quantity)

	return maintain_as_is_new, (
		frappe.qb.from_(stock_entry)
		.from_(stock_entry_detail)
		.select(
			*fields
		)
		.where(
			(stock_entry.name == stock_entry_detail.parent)
			& (stock_entry.work_order == work_order)
			& (stock_entry.docstatus == 1)
			& (stock_entry_detail.s_warehouse.isnotnull())
			& (
				stock_entry.purpose.isin(
					["Manufacture", "Material Consumption for Manufacture", "Material Transfer for Manufacture"]
				)
			)
		)
		.orderby(stock_entry.creation, stock_entry_detail.item_code, stock_entry_detail.idx)
	).run(as_dict=1)

class StockEntry(_StockEntry):
	def make_batches(self, warehouse_field):
		return make_batches(self, warehouse_field)
	
	def get_unconsumed_raw_materials(self):
		maintain_as_is_new = frappe.db.get_value("Company", self.company, "maintain_as_is_new")
		wo = frappe.get_doc("Work Order", self.work_order)
		wo_items = frappe.get_all(
			"Work Order Item",
			filters={"parent": self.work_order},
			fields=["item_code", "source_warehouse", "required_qty", "consumed_qty", "transferred_qty"],
		)

		work_order_qty = wo.material_transferred_for_manufacturing or wo.qty
		for item in wo_items:
			item_account_details = get_item_defaults(item.item_code, self.company)
			# Take into account consumption if there are any.

			wo_item_qty = item.transferred_qty or item.required_qty

			wo_qty_consumed = flt(wo_item_qty) - flt(item.consumed_qty)
			wo_qty_to_produce = flt(work_order_qty) - flt(wo.produced_qty)

			req_qty_each = (wo_qty_consumed) / (wo_qty_to_produce or 1)

			if maintain_as_is_new:
				qty = req_qty_each * flt(self.fg_completed_quantity)
			else:
				qty = req_qty_each * flt(self.fg_completed_qty)

			if qty > 0:
				row = {
					"from_warehouse": wo.wip_warehouse or item.source_warehouse,
					"to_warehouse": "",
					"item_name": item.item_name,
					"description": item.description,
					"stock_uom": item_account_details.stock_uom,
					"expense_account": item_account_details.get("expense_account"),
					"cost_center": item_account_details.get("buying_cost_center"),
				}
				if maintain_as_is_new:
					row["qty"] = qty
				else:
					row["quantity"] = qty
				
				self.add_to_stock_entry_detail(
					{
						item.item_code: row
					}
				)
	
	def add_transfered_raw_materials_in_items(self) -> None:
		maintain_as_is_new, available_materials = get_available_materials(self.company, self.work_order)

		wo_data = frappe.db.get_value(
			"Work Order",
			self.work_order,
			["qty", "produced_qty", "material_transferred_for_manufacturing as trans_qty"],
			as_dict=1,
		)

		for key, row in available_materials.items():
			remaining_qty_to_produce = flt(wo_data.trans_qty) - flt(wo_data.produced_qty)
			if remaining_qty_to_produce <= 0 and not self.is_return:
				continue

			qty = flt(row.qty)
			if not self.is_return:
				qty = (flt(row.qty) * flt(self.fg_completed_qty)) / remaining_qty_to_produce
			
			if not maintain_as_is_new:
				quantity = flt(row.quantity)
				if not self.is_return:
					quantity = (flt(row.quantity) * flt(self.fg_completed_qty)) / remaining_qty_to_produce

			item = row.item_details
			if cint(frappe.get_cached_value("UOM", item.stock_uom, "must_be_whole_number")):
				qty = frappe.utils.ceil(qty)
			
			if not maintain_as_is_new:
				if cint(frappe.get_cached_value("UOM", item.stock_uom, "must_be_whole_number")):
					quantity = frappe.utils.ceil(quantity)

			if not maintain_as_is_new:
				if row.batch_details_quantity:
					batches_quantity = sorted(row.batch_details_quantity.items(), key=lambda x: x[0])


					for batch_no, batch_quantity in batches_quantity:
						if quantity <= 0 or batch_quantity <= 0:
							continue

						if batch_quantity > quantity:
							batch_quantity = quantity

						item.batch_no = batch_no
						# frappe.throw(str(item)+"4")
						self.update_item_in_stock_entry_detail(row, item, quantity=batch_quantity)

						row.batch_details[batch_no] -= batch_quantity
						quantity -= batch_quantity
				else:
					# frappe.throw(str(item)+"3")
					self.update_item_in_stock_entry_detail(row, item, quantity=quantity)

			else:
				if row.batch_details:
					batches = sorted(row.batch_details.items(), key=lambda x: x[0])

					for batch_no, batch_qty in batches:
						if qty <= 0 or batch_qty <= 0:
							continue

						if batch_qty > qty:
							batch_qty = qty

						item.batch_no = batch_no
						# frappe.throw(str(item)+"2")
						self.update_item_in_stock_entry_detail(row, item, qty=batch_qty)

						row.batch_details[batch_no] -= batch_qty
						qty -= batch_qty
				else:
					# frappe.throw(str(item)+"1")
					self.update_item_in_stock_entry_detail(row, item, qty=qty)
	
	def update_item_in_stock_entry_detail(self, row, item, qty=None, quantity=None) -> None:
		if not (qty or quantity):
			return
		ste_item_details = {
			"from_warehouse": item.warehouse,
			"to_warehouse": "",
			"item_name": item.item_name,
			"batch_no": item.batch_no,
			"description": item.description,
			"stock_uom": item.stock_uom,
			"expense_account": item.expense_account,
			"cost_center": item.cost_center,
			"original_item": item.original_item,
		}

		if qty is not None:
			ste_item_details["qty"] = qty
		if quantity is not None:
			ste_item_details["quantity"] = quantity
		
		if self.is_return:
			ste_item_details["to_warehouse"] = item.s_warehouse

		if row.serial_nos:
			serial_nos = row.serial_nos
			if item.batch_no:
				serial_nos = self.get_serial_nos_based_on_transferred_batch(item.batch_no, row.serial_nos)

			serial_nos = serial_nos[0 : cint(qty)]
			ste_item_details["serial_no"] = "\n".join(serial_nos)

			# remove consumed serial nos from list
			for sn in serial_nos:
				row.serial_nos.remove(sn)

		self.add_to_stock_entry_detail({item.item_code: ste_item_details})
	
	def add_to_stock_entry_detail(self, item_dict, bom_no=None):
		maintain_as_is_new = frappe.db.get_value("Company", self.company, "maintain_as_is_new")
		# frappe.throw(str(item_dict))
		for d in item_dict:
			item_row = item_dict[d]
			# frappe.throw(str(item_row))
			stock_uom = item_row.get("stock_uom") or frappe.db.get_value("Item", d, "stock_uom")

			se_child = self.append("items")
			se_child.s_warehouse = item_row.get("from_warehouse")
			se_child.t_warehouse = item_row.get("to_warehouse")
			se_child.item_code = item_row.get("item_code") or cstr(d)
			se_child.uom = item_row["uom"] if item_row.get("uom") else stock_uom
			se_child.stock_uom = stock_uom
			if not maintain_as_is_new:
				se_child.quantity = flt(item_row.get("quantity"), se_child.precision("quantity"))
				se_child.qty = flt(item_row.get("quantity"), se_child.precision("quantity"))
			else:
				se_child.qty = flt(item_row["qty"], se_child.precision("qty"))
			se_child.allow_alternative_item = item_row.get("allow_alternative_item", 0)
			se_child.subcontracted_item = item_row.get("main_item_code")
			se_child.cost_center = item_row.get("cost_center") or get_default_cost_center(
				item_row, company=self.company
			)
			se_child.is_finished_item = item_row.get("is_finished_item", 0)
			se_child.is_scrap_item = item_row.get("is_scrap_item", 0)
			se_child.po_detail = item_row.get("po_detail")
			se_child.sco_rm_detail = item_row.get("sco_rm_detail")

			for field in [
				self.subcontract_data.rm_detail_field,
				"original_item",
				"expense_account",
				"description",
				"item_name",
				"serial_no",
				"batch_no",
				"allow_zero_valuation_rate",
			]:
				if item_row.get(field):
					se_child.set(field, item_row.get(field))

			if se_child.s_warehouse is None:
				se_child.s_warehouse = self.from_warehouse
			if se_child.t_warehouse is None:
				se_child.t_warehouse = self.to_warehouse

			# in stock uom
			se_child.conversion_factor = flt(item_row.get("conversion_factor")) or 1
			if not maintain_as_is_new:
				se_child.transfer_qty = flt(
					item_row["quantity"] * se_child.conversion_factor, se_child.precision("quantity")
				)
			else:
				se_child.transfer_qty = flt(
					item_row["qty"] * se_child.conversion_factor, se_child.precision("qty")
				)

			se_child.bom_no = bom_no  # to be assigned for finished item
			se_child.job_card_item = item_row.get("job_card_item") if self.get("job_card") else None
	
	def load_items_from_bom(self):
		maintain_as_is_new = frappe.db.get_value("Company", self.company, "maintain_as_is_new")

		if self.work_order:
			item_code = self.pro_doc.production_item
			to_warehouse = self.pro_doc.fg_warehouse
		else:
			item_code = frappe.db.get_value("BOM", self.bom_no, "item")
			to_warehouse = self.to_warehouse

		item = get_item_defaults(item_code, self.company)
		# frappe.throw(str(item))

		if not self.work_order and not to_warehouse:
			# in case of BOM
			to_warehouse = item.get("default_warehouse")

		args = {
			"to_warehouse": to_warehouse,
			"from_warehouse": "",
			"item_name": item.item_name,
			"description": item.description,
			"stock_uom": item.stock_uom,
			"expense_account": item.get("expense_account"),
			"cost_center": item.get("buying_cost_center") or item.get("selling_cost_center"),
			"is_finished_item": 1,
		}

		if not maintain_as_is_new:
			args["quantity"] = flt(self.fg_completed_qty) - flt(self.process_loss_qty)
		else:
			args["qty"] = flt(self.fg_completed_qty) - flt(self.process_loss_qty)

		if (
			self.work_order
			and self.pro_doc.has_batch_no
			and cint(
				frappe.db.get_single_value(
					"Manufacturing Settings", "make_serial_no_batch_from_work_order", cache=True
				)
			)
		):
			self.set_batchwise_finished_goods(args, item)
		else:
			self.add_finished_goods(args, item)
	
	def get_finished_item_row(self):
		finished_item_row = []
		if self.purpose in ("Manufacture", "Repack"):
			for d in self.get("items"):
				if d.is_finished_item:
					finished_item_row.append(d)

		return finished_item_row

	def get_sle_for_source_warehouse(self, sl_entries, finished_item_row):
		finish_dict = {'name' : [], 'item_code' : [], 'warehouse' : []}
		if finished_item_row:
			for row in finished_item_row:
				finish_dict['name'].append(row.name)
				finish_dict['item_code'].append(row.item_code)
				finish_dict['warehouse'].append(row.t_warehouse)
		for d in self.get("items"):
			if cstr(d.s_warehouse):
				sle = self.get_sl_entries(
					d, {"warehouse": cstr(d.s_warehouse), "actual_qty": -flt(d.transfer_qty), "incoming_rate": 0}
				)
				if cstr(d.t_warehouse):
					sle.dependant_sle_voucher_detail_no = d.name
				elif finish_dict and (
					d.item_code not in finish_dict['item_code'] or d.s_warehouse not in finish_dict['warehouse']
				):
					sle.dependant_sle_voucher_detail_no = ','.join(list(set(finish_dict['name'])))

				sl_entries.append(sle)

	def get_sle_for_target_warehouse(self, sl_entries, finished_item_row):
		finish_dict = {'name' : []}
		if finished_item_row:
			for row in finished_item_row:
				finish_dict['name'].append(row.name)
		for d in self.get("items"):
			if cstr(d.t_warehouse):
				sle = self.get_sl_entries(
					d,
					{
						"warehouse": cstr(d.t_warehouse),
						"actual_qty": flt(d.transfer_qty),
						"incoming_rate": flt(d.valuation_rate),
					},
				)
				if cstr(d.s_warehouse) or (finish_dict and d.name in finish_dict['name']):
					sle.recalculate_rate = 1

				sl_entries.append(sle)
	
	def get_pending_raw_materials(self, backflush_based_on=None):
		"""
		issue (item quantity) that is pending to issue or desire to transfer,
		whichever is less
		"""
		maintain_as_is_new = frappe.db.get_value("Company", self.company, "maintain_as_is_new")
		item_dict = self.get_pro_order_required_items(backflush_based_on)

		max_qty = flt(self.pro_doc.qty)

		allow_overproduction = False
		overproduction_percentage = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)

		to_transfer_qty = flt(self.pro_doc.material_transferred_for_manufacturing) + flt(
			self.fg_completed_qty
		)
		transfer_limit_qty = max_qty + ((max_qty * overproduction_percentage) / 100)

		if transfer_limit_qty >= to_transfer_qty:
			allow_overproduction = True

		for item, item_details in item_dict.items():
			pending_to_issue = flt(item_details.required_qty) - flt(item_details.transferred_qty)
			desire_to_transfer = flt(self.fg_completed_qty) * flt(item_details.required_qty) / max_qty

			if (
				desire_to_transfer <= pending_to_issue
				or (desire_to_transfer > 0 and backflush_based_on == "Material Transferred for Manufacture")
				or allow_overproduction
			):
				# "No need for transfer but qty still pending to transfer" case can occur
				# when transferring multiple RM in different Stock Entries
				item_dict[item]["qty"] = desire_to_transfer if (desire_to_transfer > 0) else pending_to_issue
			elif pending_to_issue > 0:
				item_dict[item]["qty"] = pending_to_issue
			else:
				item_dict[item]["qty"] = 0
			
			if not maintain_as_is_new:
				item_dict[item]["quantity"] = item_dict[item]["qty"]

		# delete items with 0 qty
		list_of_items = list(item_dict.keys())
		for item in list_of_items:
			if not item_dict[item]["qty"]:
				del item_dict[item]

		# show some message
		if not len(item_dict):
			frappe.msgprint(_("""All items have already been transferred for this Work Order."""))

		return item_dict
	
	def validate_fg_completed_qty(self):
		maintain_as_is_new = frappe.db.get_value("Company", self.company, "maintain_as_is_new")
		if self.purpose != "Manufacture":
			return

		fg_qty = defaultdict(float)
		if maintain_as_is_new:
			for d in self.items:
				if d.is_finished_item:
					fg_qty[d.item_code] += flt(d.qty)
		else:
			for d in self.items:
				if d.is_finished_item:
					fg_qty[d.item_code] += flt(d.quantity)

		if not fg_qty:
			return

		precision = frappe.get_precision("Stock Entry Detail", "qty")
		fg_item = next(iter(fg_qty.keys()))
		fg_item_qty = flt(fg_qty[fg_item], precision)
		if maintain_as_is_new:
			fg_completed_qty = flt(self.fg_completed_qty, precision)
		else:
			fg_completed_qty = flt(self.fg_completed_quantity, precision)

		for d in self.items:
			if not fg_qty.get(d.item_code):
				continue

			if (fg_completed_qty - fg_item_qty) > 0:
				self.process_loss_qty = fg_completed_qty - fg_item_qty

			if not self.process_loss_qty:
				continue

			if fg_completed_qty != (flt(fg_item_qty) + flt(self.process_loss_qty, precision)):
				frappe.throw(
					_(
						"Since there is a process loss of {0} units for the finished good {1}, you should reduce the quantity by {0} units for the finished good {1} in the Items Table."
					).format(frappe.bold(self.process_loss_qty), frappe.bold(d.item_code))
				)
	
	def validate_finished_goods(self):
		"""
		1. Check if FG exists (mfg, repack)
		2. Check if Multiple FG Items are present (mfg)
		3. Check FG Item and Qty against WO if present (mfg)
		"""
		production_item, wo_qty, finished_items = None, 0, []

		wo_details = frappe.db.get_value("Work Order", self.work_order, ["production_item", "qty","is_multiple_item"])
		
		if wo_details:
			production_item, wo_qty , is_multiple_item = wo_details

			# Finbyz Changes for bom multi doc
			bom_multi_doc = frappe.get_doc("BOM", frappe.db.get_value("Work Order" , self.work_order , "bom_no"))
			production_item = [d.item_code for d in bom_multi_doc.multiple_finish_item]
			if not production_item:
				production_item.append(frappe.db.get_value("Work Order",self.work_order , "production_item"))

		for d in self.get("items"):
			if d.is_finished_item:
				if not self.work_order:
					# Independent MFG Entry/ Repack Entry, no WO to match against
					finished_items.append(d.item_code)
					continue

				if d.item_code not in production_item: # Finbyz Changes
					frappe.throw(
						_("Finished Item {0} does not match with Work Order {1}").format(
							d.item_code, self.work_order
						)
					)
				elif flt(d.transfer_qty) > flt(self.fg_completed_qty):
					frappe.throw(
						_("Quantity in row {0} ({1}) must be same as manufactured quantity {2}").format(
							d.idx, d.transfer_qty, self.fg_completed_qty
						)
					)

				finished_items.append(d.item_code)

		if not finished_items:
			frappe.throw(
				msg=_("There must be atleast 1 Finished Good in this Stock Entry").format(self.name),
				title=_("Missing Finished Good"),
				exc=FinishedGoodError,
			)

		if self.purpose == "Manufacture" and not is_multiple_item:
			if len(set(finished_items)) > 1:
				frappe.throw(
					msg=_("Multiple items cannot be marked as finished item"),
					title=_("Note"),
					exc=FinishedGoodError,
				)

			allowance_percentage = flt(
				frappe.db.get_single_value(
					"Manufacturing Settings", "overproduction_percentage_for_work_order"
				)
			)
			allowed_qty = wo_qty + ((allowance_percentage / 100) * wo_qty)

			# No work order could mean independent Manufacture entry, if so skip validation
			if self.work_order and float(self.fg_completed_qty) > allowed_qty:
				frappe.throw(
					_("For quantity {0} should not be greater than allowed quantity {1}").format(
						flt(self.fg_completed_qty), allowed_qty
					)
				)

	@frappe.whitelist()
	def get_items(self):
		self.set("items", [])
		self.validate_work_order()

		if not self.posting_date or not self.posting_time:
			frappe.throw(_("Posting date and posting time is mandatory"))

		self.set_work_order_details()
		self.flags.backflush_based_on = frappe.db.get_single_value(
			"Manufacturing Settings", "backflush_raw_materials_based_on"
		)

		if self.bom_no:
			backflush_based_on = frappe.db.get_single_value(
				"Manufacturing Settings", "backflush_raw_materials_based_on"
			)

			if self.purpose in [
				"Material Issue",
				"Material Transfer",
				"Manufacture",
				"Repack",
				"Send to Subcontractor",
				"Material Transfer for Manufacture",
				"Material Consumption for Manufacture",
			]:
				if self.work_order and self.purpose == "Material Transfer for Manufacture":
					item_dict = self.get_pending_raw_materials(backflush_based_on)
					if self.to_warehouse and self.pro_doc:
						for item in item_dict.values():
							item["to_warehouse"] = self.pro_doc.wip_warehouse
					self.add_to_stock_entry_detail(item_dict)

				elif (
					self.work_order
					and (
						self.purpose == "Manufacture"
						or self.purpose == "Material Consumption for Manufacture"
					)
					and not self.pro_doc.skip_transfer
					and self.flags.backflush_based_on == "Material Transferred for Manufacture"
				):
					self.add_transfered_raw_materials_in_items()

				elif (
					self.work_order
					and (
						self.purpose == "Manufacture"
						or self.purpose == "Material Consumption for Manufacture"
					)
					and self.flags.backflush_based_on == "BOM"
					and frappe.db.get_single_value("Manufacturing Settings", "material_consumption") == 1
				):
					self.get_unconsumed_raw_materials()

				else:
					if not self.fg_completed_qty:
						frappe.throw(_("Manufacturing Quantity is mandatory"))

					item_dict = self.get_bom_raw_materials(self.fg_completed_qty)

					# Get Subcontract Order Supplied Items Details
					if (
						self.get(self.subcontract_data.order_field)
						and self.purpose == "Send to Subcontractor"
					):
						# Get Subcontract Order Supplied Items Details
						parent = frappe.qb.DocType(self.subcontract_data.order_doctype)
						child = frappe.qb.DocType(self.subcontract_data.order_supplied_items_field)

						item_wh = (
							frappe.qb.from_(parent)
							.inner_join(child)
							.on(parent.name == child.parent)
							.select(child.rm_item_code, child.reserve_warehouse)
							.where(parent.name == self.get(self.subcontract_data.order_field))
						).run(as_list=True)

						item_wh = frappe._dict(item_wh)

					for item in item_dict.values():
						if self.pro_doc and cint(self.pro_doc.from_wip_warehouse):
							item["from_warehouse"] = self.pro_doc.wip_warehouse
						# Get Reserve Warehouse from Subcontract Order
						if (
							self.get(self.subcontract_data.order_field)
							and self.purpose == "Send to Subcontractor"
						):
							item["from_warehouse"] = item_wh.get(item.item_code)
						item["to_warehouse"] = (
							self.to_warehouse if self.purpose == "Send to Subcontractor" else ""
						)

					self.add_to_stock_entry_detail(item_dict)

			# fetch the serial_no of the first stock entry for the second stock entry
			if self.work_order and self.purpose == "Manufacture":
				work_order = frappe.get_doc("Work Order", self.work_order)
				add_additional_cost(self, work_order, self.fg_completed_qty) # Finbyz Changes

			# add finished goods item
			if self.purpose in ("Manufacture", "Repack"):
				self.set_process_loss_qty()
				self.load_items_from_bom()

		self.set_scrap_items()
		self.set_actual_qty()
		self.validate_customer_provided_item()
		self.calculate_rate_and_amount(raise_error_if_no_rate=False)
