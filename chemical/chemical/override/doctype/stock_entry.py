import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.stock.doctype.stock_entry.stock_entry import FinishedGoodError, StockEntry as _StockEntry
from frappe.utils import cstr


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
		
		additional_cost_dict["expense_account"] = 'Expenses Included In Valuation - {}'.format(abbr)
		additional_cost_dict["description"] = additional_cost.description
		additional_cost_dict["qty"] = qty
		additional_cost_dict["rate"] = additional_cost.rate
		additional_cost_dict["amount"] = qty * flt(additional_cost.rate)
		additional_cost_dict["base_amount"] = qty * flt(additional_cost.rate)
		
		doc.append("additional_costs", additional_cost_dict)

def validate_bom_no(item, bom_no):
	"""Validate BOM No of sub-contracted items"""
	bom = frappe.get_doc("BOM", bom_no)
	if not bom.is_active:
		frappe.throw(_("BOM {0} must be active").format(bom_no))
	if bom.docstatus != 1:
		if not getattr(frappe.flags, "in_test", False):
			frappe.throw(_("BOM {0} must be submitted").format(bom_no))
	if item:
		rm_item_exists = False
		for d in bom.items:
			if d.item_code.lower() == item.lower():
				rm_item_exists = True
		for d in bom.scrap_items:
			if d.item_code.lower() == item.lower():
				rm_item_exists = True
		if (
			bom.item.lower() == item.lower()
			or bom.item.lower() == cstr(frappe.db.get_value("Item", item, "variant_of")).lower()
		):
			rm_item_exists = True
		
		if (
			item.lower() in [d.item_code.lower() for d in bom.multiple_finish_item]
		):
			rm_item_exists = True

		if not rm_item_exists:
			frappe.throw(_("BOM {0} does not belong to Item {1}").format(bom_no, item))

class StockEntry(_StockEntry):
	def validate_bom(self):
		for d in self.get("items"):
			if d.bom_no and d.is_finished_item:
				item_code = d.original_item or d.item_code
				validate_bom_no(item_code, d.bom_no)

	def validate_finished_goods(self):
		"""
		1. Check if FG exists (mfg, repack)
		2. Check if Multiple FG Items are present (mfg)
		3. Check FG Item and Qty against WO if present (mfg)
		"""
		production_item, wo_qty, finished_items = None, 0, []

		wo_details = frappe.db.get_value("Work Order", self.work_order, ["production_item", "qty"])
		if wo_details:
			production_item, wo_qty = wo_details
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

				if d.item_code not in production_item:
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

		if self.purpose == "Manufacture":
			allowance_percentage = flt(
				frappe.db.get_single_value(
					"Manufacturing Settings", "overproduction_percentage_for_work_order"
				)
			)
			allowed_qty = wo_qty + ((allowance_percentage / 100) * wo_qty)

			# No work order could mean independent Manufacture entry, if so skip validation
			if self.work_order and flt(self.fg_completed_qty) > allowed_qty:
				frappe.throw(
					_("For quantity {0} should not be greater than allowed quantity {1}").format(
						flt(self.fg_completed_qty), allowed_qty
					)
				)
	def validate_fg_completed_qty(self):
		item_wise_qty = {}
		if self.purpose == "Manufacture" and self.work_order:
			for d in self.items:
				if d.is_finished_item:
					if self.process_loss_qty:
						d.qty = self.fg_completed_qty - self.process_loss_qty

					item_wise_qty.setdefault(d.item_code, []).append(d.qty)

		precision = frappe.get_precision("Stock Entry Detail", "qty")
		total = 0
		for item_code, qty_list in item_wise_qty.items():
			total += flt(sum(qty_list), precision)

			if (flt(self.fg_completed_qty) - total) > 0 and not self.process_loss_qty:
				self.process_loss_qty = flt(self.fg_completed_qty - total, precision)
				self.process_loss_percentage = flt(self.process_loss_qty * 100 / self.fg_completed_qty)

			if self.process_loss_qty:
				total += flt(self.process_loss_qty, precision)

		if self.fg_completed_qty != total:
			frappe.throw(
				_(
					"The finished product quantity {0} and For Quantity {1} cannot be different"
				).format(frappe.bold(total), frappe.bold(self.fg_completed_qty))
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
				add_additional_cost(self, work_order)

			# add finished goods item
			if self.purpose in ("Manufacture", "Repack"):
				self.set_process_loss_qty()
				self.load_items_from_bom()

		self.set_scrap_items()
		self.set_actual_qty()
		self.validate_customer_provided_item()
		self.calculate_rate_and_amount(raise_error_if_no_rate=False)

def calculate_rate_and_amount(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
	# if self.purpose in ["Material Transfer for Manufacture"]:
	# 	set_incoming_rate(self)
	if self.purpose in ['Manufacture','Repack']:
		multi_item_list = []
		
		for d in self.items:
			if d.t_warehouse and d.qty != 0 and d.is_finished_item:
				multi_item_list.append(d.item_code)
		
		if len(multi_item_list) == 1:
			return

		