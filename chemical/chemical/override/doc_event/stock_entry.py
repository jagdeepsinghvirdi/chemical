import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.utils import get_latest_stock_qty


def before_validate(self, method):
	calculate_qty(self)

def validate(self, method):
	set_concentration_to_100_for_non_batch_item(self)
	check_based_on_item(self)
	calculate_additional_cost(self)
	calculate_rate_and_amount(self)
	cal_validate_additional_cost_qty(self)
	cal_target_yield_cons(self)


def before_save(self, method):
	get_stock_rate_for_repack_and_not_from_ball_mill(self)


def before_submit(self, method):
	validate_concentration(self)
	validate_quality_inspection(self)


def on_submit(self, method):
	add_extra_items_to_work_order_items(self)
	add_items_to_work_order_finish_items(self)
	set_work_order_details(self)
	set_batch_no_in_quality_inspection(self)


def on_cancel(self, method):
	remove_items_from_work_order_finish_items(self)
	set_work_order_details(self)
	set_batch_no_in_quality_inspection(self)


def calculate_qty(self):
	for row in self.items:
		if row.get("packing_size") and row.get("no_of_packages"):
			row.qty = cint(row.packing_size) * cint(row.no_of_packages)


def set_concentration_to_100_for_non_batch_item(self):
	for row in self.items:
		if row.item_code and not row.batch_no:
			row.concentration = 100


def check_based_on_item(self):
	if (
		self.purpose == "Manufacture"
		and frappe.db.get_value("BOM", self.bom_no, "based_on")
		and self.based_on
		and self.based_on not in [item.item_code for item in self.items]
	):
		frappe.throw(
			f"Based on Item {frappe.bold(self.based_on)} Required in Raw Materials"
		)


def calculate_additional_cost(self):
	for row in self.additional_costs or []:
		if row.uom == "FG QTY":
			row.qty = self.fg_completed_qty

		if row.qty and row.rate:
			row.amount = flt(row.qty) * flt(row.rate)
			row.base_amount = flt(row.qty) * flt(row.rate)


def get_stock_rate_for_repack_and_not_from_ball_mill(self):
	if self.purpose == "Repack" and not self.from_ball_mill:
		self.get_stock_and_rate()


def validate_concentration(self):
	if self.work_order and self.purpose == "Manufacture":
		production_item = frappe.db.get_value(
			"Work Order", self.work_order, "production_item"
		)
		for row in self.items:
			if (
				row.t_warehouse
				and row.item_code == production_item
				and not row.concentration
			):
				frappe.throw(
					_(f"Add concentration in row {row.idx} for item {row.item_code}")
				)


def validate_quality_inspection(self):
	if (
		self.purpose == "Manufacture"
		and self.bom_no
		and frappe.db.get_value("BOM", self.bom_no, "inspection_required")
	):
		for row in self.items:
			if row.t_warehouse and not row.quality_inspection:
				frappe.throw(
					_(
						f"Quality Inspection is mandatory in row {row.idx} for item {row.item_code}."
					)
				)


def add_extra_items_to_work_order_items(self):
	if self.purpose == "Manufacture" and self.work_order:
		work_order = frappe.get_doc("Work Order", self.work_order)
		for row in self.items:
			if (
				row.s_warehouse
				and not row.t_warehouse
				and row.item_code
				not in [d.item_code for d in work_order.required_items]
			):
				work_order.append(
					"required_items",
					{
						"item_code": row.item_code,
						"item_name": row.item_name,
						"description": row.description,
						"source_warehouse": row.s_warehouse,
						"required_qty": row.qty,
						"transferred_qty": row.qty,
						"valuation_rate": row.valuation_rate,
						"available_qty_at_source_warehouse": get_latest_stock_qty(
							row.item_code, row.s_warehouse
						),
					},
				)

		for row in work_order.required_items:
			work_order.db_update()


def add_items_to_work_order_finish_items(self):
	if self.purpose == "Manufacture" and self.work_order:
		work_order = frappe.get_doc("Work Order", self.work_order)
		bom = frappe.get_doc("BOM", work_order.bom_no)
		if bom.multiple_finish_item:
			items = {
				row.item_code: (row.cost_ratio, row.qty_ratio, row.batch_yield)
				for row in bom.multiple_finish_item
			}
		else:
			items = {work_order.production_item: (100, 100, bom.batch_yield)}
		total_valuation = 0
		for row in self.items:
			if row.t_warehouse and row.item_code in items:
				data = items[row.item_code]
				total_valuation += flt(row.valuation_rate)
				work_order.append(
					"finish_item",
					{
						"item_code": row.item_code,
						"actual_qty": row.qty,
						"actual_valuation": row.valuation_rate,
						"lot_no": row.lot_no,
						"purity": row.concentration,
						"packing_size": row.packing_size,
						"no_of_packages": row.no_of_packages,
						"batch_yield": row.batch_yield,
						"batch_no": row.batch_no,
						"bom_cost_ratio": data[0],
						"bom_qty_ratio": data[1],
						"bom_qty": work_order.qty * data[1] / 100,
						"bom_yield": data[2],
						"stock_entry": self.name,
						"se_detail": row.name,
					},
				)
		work_order.flags.ignore_permissions = True
		work_order.flags.ignore_validate_update_after_submit = True
		work_order.save()
		work_order.db_set("valuation_rate", total_valuation)
		work_order.db_set("valuation_price", total_valuation)

def set_batch_no_in_quality_inspection(self):
	for row in self.items:
		if row.quality_inspection:
			qi_doc = frappe.get_doc("Quality Inspection", row.quality_inspection)
			qi_doc.db_set("batch_no", row.batch_no, update_modified=False)


def remove_items_from_work_order_finish_items(self):
	if self.purpose == "Manufacture" and self.work_order:
		work_order = frappe.get_doc("Work Order", self.work_order)

		data = []

		for row in work_order.finish_item:
			if row.stock_entry != self.name:
				data.append(
					{
						"item_code": row.item_code,
						"actual_qty": row.actual_qty,
						"actual_valuation": row.actual_valuation,
						"lot_no": row.lot_no,
						"purity": row.purity,
						"packing_size": row.packing_size,
						"no_of_packages": row.no_of_packages,
						"batch_yield": row.batch_yield,
						"batch_no": row.batch_no,
						"bom_cost_ratio": row.bom_cost_ratio,
						"bom_qty_ratio": row.bom_qty_ratio,
						"bom_qty": row.bom_qty,
						"bom_yield": row.bom_yield,
						"stock_entry": row.stock_entry,
						"se_detail": row.se_detail,
					}
				)

		work_order.finish_item = []
		for row in data:
			work_order.append("finish_item", row)

		work_order.flags.ignore_permissions = True
		work_order.flags.ignore_validate_update_after_submit = True
		work_order.save()


def set_work_order_details(self):
	if self.purpose == "Manufacture" and self.work_order:
		work_order = frappe.get_doc("Work Order", self.work_order)

		count = len(work_order.finish_item)
		batch_yield = 0
		concentration = 0
		lot_nos = []

		for row in work_order.finish_item:
			batch_yield += flt(row.batch_yield)
			concentration += flt(row.purity)
			if row.lot_no:
				lot_nos.append(row.lot_no)

		work_order.db_set("batch_yield", flt(batch_yield))
		work_order.db_set("concentration", flt(concentration))
		work_order.db_set("lot_no", ", ".join(lot_nos))


def calculate_rate_and_amount(self):
	if self.purpose in ["Manufacture", "Repack"]:
		multi_item_list = []

		for d in self.items:
			if d.t_warehouse and d.qty != 0 and d.is_finished_item:
				multi_item_list.append(d.item_code)

		if len(multi_item_list) <= 1:
			return

		self.set_basic_rate(reset_outgoing_rate=False, raise_error_if_no_rate=True)

		if self.bom_no:
			bom_doc = frappe.get_doc("BOM", self.bom_no)

			if bom_doc.equal_cost_ratio:
				calculate_multiple_repack_valuation(self)
			else:
				cal_rate_for_finished_item(self)
		else:
			calculate_multiple_repack_valuation(self)

		self.update_valuation_rate()
		self.set_total_incoming_outgoing_value()
		self.set_total_amount()


def calculate_multiple_repack_valuation(self):
	self.total_additional_costs = sum(
		[flt(t.amount) for t in self.get("additional_costs")]
	)
	scrap_total = 0

	qty = 0.0
	total_outgoing_value = 0.0

	for row in self.items:
		if row.s_warehouse:
			total_outgoing_value += flt(row.basic_amount)
		if row.t_warehouse:
			qty += row.qty
		if row.is_scrap_item:
			scrap_total += flt(row.basic_amount)

	total_outgoing_value = flt(total_outgoing_value) - flt(scrap_total)

	for row in self.items:
		if row.t_warehouse:
			row.basic_amount = flt(total_outgoing_value) * flt(row.qty) / qty
			row.additional_cost = flt(self.total_additional_costs) * flt(row.qty) / qty
			row.basic_rate = flt(row.basic_amount / row.qty)


def cal_rate_for_finished_item(self):
	self.total_additional_costs = sum(
		[flt(t.amount) for t in self.get("additional_costs")]
	)

	work_order_doc = frappe.get_doc("Work Order", self.work_order)
	bom_doc = frappe.get_doc("BOM", work_order_doc.bom_no)

	scrap_total = 0
	for d in self.items:
		if d.is_scrap_item:
			scrap_total += flt(d.basic_amount)

	if self.total_outgoing_value:
		self.total_outgoing_value = max(
			flt(self.total_outgoing_value) - flt(scrap_total), 0
		)

	item_arr = list()
	item_map = dict()
	finished_list = []
	result = {}

	for row in self.items:
		if row.t_warehouse and not d.is_scrap_item:
			finished_list.append(
				{row.item_code: row.qty}
			)  # create a list of dict of finished item

	for d in finished_list:
		for k in d.keys():
			result[k] = result.get(k, 0) + d[k]  # create a dict of unique item

	for d in self.items:
		if d.item_code not in item_arr:
			item_map.setdefault(d.item_code, {"qty": 0, "yield_weights": 0})

		item_map[d.item_code]["qty"] += flt(d.qty)

		bom_cost_list = []
		if bom_doc.is_multiple_item:
			for bom_fi in bom_doc.multiple_finish_item:
				bom_cost_list.append(
					{"item_code": bom_fi.item_code, "cost_ratio": bom_fi.cost_ratio}
				)
		else:
			bom_cost_list.append({"item_code": bom_doc.item, "cost_ratio": 100})

		if d.t_warehouse:
			for bom_cost_dict in bom_cost_list:
				if d.item_code == bom_cost_dict["item_code"]:
					d.basic_amount = flt(
						flt(
							flt(self.total_outgoing_value)
							* flt(bom_cost_dict["cost_ratio"])
							* flt(d.qty)
						)
						/ flt(100 * flt(result[d.item_code]))
					)
					d.additional_cost = flt(
						flt(
							flt(self.total_additional_costs)
							* flt(bom_cost_dict["cost_ratio"])
							* flt(d.qty)
						)
						/ flt(100 * flt(result[d.item_code]))
					)
					d.amount = flt(d.basic_amount + d.additional_cost)
					d.basic_rate = flt(d.basic_amount / d.qty)
					d.valuation_rate = flt(d.amount / d.qty)


def cal_validate_additional_cost_qty(self):
	if self.additional_costs:
		for addi_cost in self.additional_costs:
			if addi_cost.qty and addi_cost.rate:
				addi_cost.amount = flt(addi_cost.qty) * flt(addi_cost.rate)
				addi_cost.base_amount = flt(addi_cost.qty) * flt(addi_cost.rate)
			if addi_cost.uom == "FG QTY":
				addi_cost.qty = self.fg_completed_qty
				addi_cost.amount = flt(self.fg_completed_qty) * flt(addi_cost.rate)
				addi_cost.base_amount = flt(self.fg_completed_qty) * flt(addi_cost.rate)

def cal_target_yield_cons(self):
	item_arr = list()
	item_map = dict()
	flag = 0
	if self.purpose == "Manufacture" and self.based_on:
		for d in self.items:
			if d.t_warehouse:
				flag+=1		
			
			if d.item_code not in item_arr:
					item_map.setdefault(d.item_code, {'qty':0, 'yield_weights':0})
				
			# item_map[d.item_code]['quantity'] += flt(d.quantity)
			item_map[d.item_code]['qty'] += flt(d.qty)

		# List of item_code from items table
		items_list = [row.item_code for row in self.items]

		# Check if items list has frm.doc.based_on value
		finished_qty = 0
		if self.based_on in items_list: 
			for row in self.items:
				if row.t_warehouse and row.is_finished_item:
					finished_qty += row.qty
					row.batch_yield = flt(row.qty / item_map[self.based_on]['qty'])

		self.db_set('batch_yield', flt(finished_qty / item_map[self.based_on]['qty']))
