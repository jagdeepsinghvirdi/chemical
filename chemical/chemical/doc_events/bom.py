import frappe
from frappe import _
from frappe.utils import flt
from erpnext.stock.get_item_details import get_price_list_rate
from erpnext.manufacturing.doctype.bom.bom import get_valuation_rate

def bom_validate(self, method):
	item_list = [item.item_code for item in self.items]
	if self.based_on:
		if self.based_on not in item_list:
			frappe.throw("Based on Item {} Required in Raw Materials".format(frappe.bold(self.based_on)))
	price_overrides(self)
	cost_calculation(self)
	set_fg_qty_in_additional_cost(self)
	_update_bom_cost(self)
	amount=0
	for row in self.items:
		amount += row.amount
	self.raw_material_cost = amount

def bom_before_save(self, method):
	multiple_finish_item(self)
	validate_cost_ratio_and_quantity_ratio(self)
	cost_calculation(self)
	yield_cal(self)

def on_submit(self, method):
	cost_calculation(self)
	
def set_fg_qty_in_additional_cost(self):
	for row in self.additional_cost:
		row.amount = flt(flt(row.qty) * flt(row.rate))
		if row.uom == "FG QTY":
			row.qty = self.total_quantity

def price_overrides(self):
	for row in self.items:
		if row.from_price_list:
			#row.db_set('bom_no','')
			row.bom_no = ''

def cost_calculation(self):
	etp_amount = 0
	additional_amount = 0	
	valuation_amount = 0
	last_purchase_amount = 0
	docitems_type = frappe.get_doc({"doctype":"BOM Item"})

	self.volume_amount = flt(self.volume_quantity) * flt(self.volume_rate)
	
	if hasattr(self, 'etp_qty'):
		etp_amount = flt(self.etp_qty)*flt(self.etp_rate)
		self.etp_amount = flt(self.etp_qty)*flt(self.etp_rate)
		self.db_set('per_unit_etp_cost',(flt(etp_amount/self.quantity)))

	for row in self.items:
		row.per_unit_rate = flt(row.amount)/flt(self.quantity)
		if hasattr(docitems_type, 'valuation_amount'):
			row.valuation_amount = flt(row.valuation_rate) * flt(row.qty)
			row.last_purchase_amount = flt(row.last_purchase_rate) * flt(row.qty)
			valuation_amount += flt(row.valuation_rate) * flt(row.qty)
			last_purchase_amount += flt(row.last_purchase_rate) * flt(row.qty)

	for row in self.scrap_items:
		row.per_unit_rate = flt(row.amount)/self.quantity
	
	if self.is_multiple_item:
		for item in self.multiple_finish_item:
			if self.item == item.item_code:
				self.db_set('per_unit_rmc',flt(flt(self.raw_material_cost * item.qty_ratio / 100)/self.quantity))
	else:
		self.db_set('per_unit_rmc',flt(flt(self.raw_material_cost)/self.quantity))

	additional_amount = sum(flt(d.amount) for d in self.additional_cost)

	self.db_set('per_unit_rmc',flt(flt(self.raw_material_cost)/flt(self.quantity)))
	if hasattr(self, 'rmc_valuation_amount'):
		self.db_set('rmc_valuation_amount',flt(valuation_amount))
		rmc_valuation_amount = flt(valuation_amount)
		self.db_set('rmc_last_purchase_amount',flt(last_purchase_amount))
		rmc_last_purchase_amount = flt(last_purchase_amount)
		self.db_set('per_unit_rmc_valuation',flt(flt(rmc_valuation_amount)/flt(self.quantity)))
		self.db_set('per_unit_rmc_last_purchase',flt(flt(rmc_last_purchase_amount)/flt(self.quantity)))
	
	self.additional_amount = additional_amount
	self.db_set('additional_amount',additional_amount)
	self.db_set('total_operational_cost',flt(self.additional_amount) + flt(self.volume_amount) + etp_amount)
	total_operational_cost = flt(self.additional_amount) + flt(self.volume_amount) + etp_amount
	self.db_set('total_scrap_cost', flt(self.scrap_material_cost))
	total_scrap_cost = flt(self.scrap_material_cost)
	self.db_set('total_cost',self.raw_material_cost + total_operational_cost - flt(self.scrap_material_cost))
	total_cost = self.raw_material_cost + total_operational_cost - flt(self.scrap_material_cost)

	if hasattr(self, 'total_valuation_cost'):
		self.db_set('total_valuation_cost',rmc_valuation_amount + total_operational_cost - flt(self.scrap_material_cost))
		total_valuation_cost = rmc_valuation_amount + total_operational_cost - flt(self.scrap_material_cost)
		self.db_set('total_last_purchase_cost',rmc_last_purchase_amount + total_operational_cost - flt(self.scrap_material_cost))
		total_last_purchase_cost = rmc_last_purchase_amount + total_operational_cost - flt(self.scrap_material_cost)
	
	self.db_set('per_unit_volume_cost',flt(self.volume_amount/self.quantity))	
	self.db_set('per_unit_additional_cost',flt(flt(self.additional_amount)/self.quantity))
	self.db_set('per_unit_operational_cost',flt(flt(total_operational_cost)/self.quantity))
	self.db_set('per_unit_scrap_cost',flt(flt(total_scrap_cost)/self.quantity))

	per_unit_price = flt(total_cost) / flt(self.quantity)
	# if self.per_unit_price != per_unit_price:
	self.db_set('per_unit_price', per_unit_price)
	if hasattr(self, 'per_unit_valuation_price'):
		self.db_set('per_unit_valuation_price', flt(total_valuation_cost) / flt(self.quantity))
		self.db_set('per_unit_last_purchase_price', flt(total_last_purchase_cost) / flt(self.quantity))
		
	#frappe.db.commit()

def _update_bom_cost(self,update_parent=False, from_child_bom=False, save=False):
	docitems_type = frappe.get_doc({"doctype":"BOM Item"})
	if self.docstatus == 2:
			return

	existing_bom_cost = self.total_cost

	for d in self.get("items"):
		rate, valuation_rate, last_purchase_rate = get_rm_rate(self,{
			"item_code": d.item_code,
			"bom_no": d.bom_no,
			"qty": d.qty,
			"uom": d.uom,
			"stock_uom": d.stock_uom,
			"conversion_factor": d.conversion_factor,
			"company": self.company
		})

		if rate:
			d.rate = rate
		d.amount = flt(d.rate) * flt(d.qty)
		d.base_rate = flt(d.rate) * flt(self.conversion_rate)
		d.base_amount = flt(d.amount) * flt(self.conversion_rate)
		if valuation_rate and hasattr(docitems_type, 'valuation_amount'):
			d.valuation_rate = valuation_rate
			d.valuation_amount = flt(d.valuation_rate) * flt(d.qty)
		if last_purchase_rate and hasattr(docitems_type, 'last_purchase_amount'):
			d.last_purchase_rate= last_purchase_rate
			d.last_purchase_amount = flt(d.last_purchase_rate) * flt(d.qty)

		if save:
			d.db_update()

	if self.docstatus == 1:
		self.flags.ignore_validate_update_after_submit = True
		self.calculate_cost()
	if save:
		self.db_update()
	# self.update_exploded_items()

	# update parent BOMs
	if self.total_cost != existing_bom_cost and update_parent:
		parent_boms = frappe.db.sql_list("""select distinct parent from `tabBOM Item`
			where bom_no = %s and docstatus=1 and parenttype='BOM'""", self.name)

		for bom in parent_boms:
			frappe.get_doc("BOM", bom).update_cost(from_child_bom=True)

	# if not from_child_bom:
	# 	frappe.msgprint(_("Cost Updated"))


def multiple_finish_item(self):
	if (self.is_multiple_item):
		if(not self.multiple_finish_item and self.item):
			self.append("multiple_finish_item",{
				"item_code": self.item,
				"qty": self.quantity,
				"cost_ratio": 100,
				"qty_ratio": 100,
				"batch_yield": 0
			})

		if not any(item.item_code == self.item for item in self.multiple_finish_item or []):
			frappe.throw(f"At least one Finish Item in Multiple Finish Items must be <b>{self.item}<b>")

	else:
		self.multiple_finish_item = []
		self.total_quantity = self.quantity
	
	for row in self.multiple_finish_item:
		row.qty = self.total_quantity * row.qty_ratio / 100
	
def validate_cost_ratio_and_quantity_ratio(self):
	cost_ratio = 0
	qty_ratio = 0
	if(self.is_multiple_item == 1):
		for row in self.multiple_finish_item:
			cost_ratio += row.cost_ratio
			qty_ratio += row.qty_ratio
		if (cost_ratio != 100):
			frappe.throw("Cost Ratio Should be 100 for Multiple Finish Item")
		if (qty_ratio != 100):
			frappe.throw("Qty Ratio Should be 100 for Multiple Finish Item")

def yield_cal(self):
	cal_yield = 0
	for d in self.items:
		if self.based_on and self.based_on == d.item_code:
			cal_yield = flt(self.quantity) / flt(d.qty)	
			for row in self.multiple_finish_item:
				row.batch_yield = flt(row.qty) / d.qty
	self.batch_yield = cal_yield
	total_yield = 0
	if self.is_multiple_item:
		for row in self.multiple_finish_item:
			total_yield += row.batch_yield
		self.batch_yield = total_yield


def get_rm_rate(self, arg):
	"""	Get raw material rate as per selected method, if bom exists takes bom cost """
	rate = 0
	valuation_rate = 0
	last_purchase_rate = 0

	if arg.get('scrap_items'):
		valuation_rate = get_valuation_rate(arg)
	elif arg:
		#Customer Provided parts will have zero rate
		if not frappe.db.get_value('Item', arg["item_code"], 'is_customer_provided_item'):
			if arg.get('bom_no') and self.set_rate_of_sub_assembly_item_based_on_bom:
				rate = flt(self.get_bom_unitcost(arg['bom_no'])) * (arg.get("conversion_factor") or 1)
			else:
				valuation_rate = get_valuation_rate(arg) * (arg.get("conversion_factor") or 1)
				
				last_purchase_rate = flt(arg.get('last_purchase_rate') \
					or frappe.db.get_value("Item", arg['item_code'], "last_purchase_rate")) \
						* (arg.get("conversion_factor") or 1)

				if not self.buying_price_list:
					frappe.throw(_("Please select Price List"))
				args = frappe._dict({
					"doctype": "BOM",
					"price_list": self.buying_price_list,
					"qty": arg.get("qty") or 1,
					"uom": arg.get("uom") or arg.get("stock_uom"),
					"stock_uom": arg.get("stock_uom"),
					"transaction_type": "buying",
					"company": self.company,
					"currency": self.currency,
					"conversion_rate": 1, # Passed conversion rate as 1 purposefully, as conversion rate is applied at the end of the function
					"conversion_factor": arg.get("conversion_factor") or 1,
					"plc_conversion_rate": 1,
					"ignore_party": True
				})
				item_doc = frappe.get_doc("Item", arg.get("item_code"))
				out = frappe._dict()
				get_price_list_rate(args, item_doc, out)
				rate = out.price_list_rate

				if not rate:
					frappe.msgprint(_("Price not found for item {0} in price list {1}")
						.format(arg["item_code"], self.buying_price_list), alert=True)
				if not valuation_rate:
					frappe.msgprint(_("Valuation rate not found for item {0}")
						.format(arg["item_code"]), alert=True)
				if not last_purchase_rate:
					frappe.msgprint(_("Last purchase rate not found for item {0}")
						.format(arg["item_code"]), alert=True)

	return flt(rate) * flt(self.plc_conversion_rate or 1) / (self.conversion_rate or 1),flt(valuation_rate) * flt(self.plc_conversion_rate or 1) / (self.conversion_rate or 1),flt(last_purchase_rate) * flt(self.plc_conversion_rate or 1) / (self.conversion_rate or 1)
	