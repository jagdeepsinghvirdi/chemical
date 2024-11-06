# -*- coding: utf-8 -*-
# Copyright (c) 2018, FinByz Tech Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, db
from frappe.model.document import Document
from chemical.api import get_party_details
from frappe.model.mapper import get_mapped_doc
from frappe.desk.reportview import get_match_cond, get_filters_cond
from erpnext.utilities.product import get_price
from frappe.utils import nowdate, flt

# from finbyzerp.finbyzerp.doc_events.naming_series import before_naming as naming_series
from chemical.comments_api import (
    creation_comment,
    status_change_comment,
    cancellation_comment,
    delete_comment,
)


class OutwardSample(Document):
    def before_save(self):
        party_detail = get_party_details(party=self.party, party_type=self.link_to)
        self.party_name = party_detail.party_name
        self.update_outward_sample()
        self.get_master_sample()
        self.get_latest_ball_mill()
        self.get_latest_sample()

    @frappe.whitelist()
    def update_outward_sample(self):
        total_qty = 0
        total_amount = 0

        for row in self.details:

            if row.item_code:
                concentration = row.concentration or 100
                row.bom_no = frappe.db.get_value("Item", row.item_code, "default_bom") or None
                price = self.get_price_list(
                    item_code=row.item_code,
                    price_list=self.price_list or "Standard Buying",
                    company=self.company,
                )
                if price.price_list_rate:
                    rate = flt(price.price_list_rate) * flt(concentration) / 100
                    row.db_set("rate", rate)
                    row.db_set("price_list_rate", price.price_list_rate)

            row.db_set("amount", flt(row.quantity) * flt(row.rate))

            total_qty += row.quantity
            total_amount += flt(row.amount)

        self.db_set("total_qty", total_qty)
        self.db_set("total_amount", total_amount)
        if total_qty == 0:
            self.db_set("per_unit_price", 0)
        else:
            self.db_set("per_unit_price", (total_amount / total_qty))
        self.db_set("price_updated_on", nowdate())

        return "Price Updated"

    def on_submit(self):
        creation_comment(self)

    def before_update_after_submit(self):
        status_change_comment(self)

    def on_trash(self):
        delete_comment(self)

    def on_cancel(self):
        self.db_set("against", "")
        cancellation_comment(self)

    @frappe.whitelist()
    def get_ball_mill(self):
        if not self.ball_mill_ref:
            frappe.throw(_("Please select Ball Mill Data Sheet!"))

        bm = frappe.get_doc("Ball Mill Data Sheet", self.ball_mill_ref)
        self.product_name = bm.product_name
        self.link_to = "Customer"
        self.party = bm.customer_name
        # self.batch_yield = bm.total_yield

        customer_name, destination = db.get_value(
            "Customer", bm.customer_name, ["customer_name", "territory"]
        )
        self.party_name = customer_name
        self.destination_1 = self.destination = destination

        self.set("details", [])

        total_amount = 0.0
        for row in bm.items:
            price = self.get_price_list(
                row.item_name, "Standard Buying"
            ).price_list_rate

            if row.batch_yield:
                bomyield = frappe.db.get_value(
                    "BOM", {"item": row.item_name}, "batch_yield"
                )
                if bomyield != 0:
                    rate = (price * flt(bomyield)) / row.batch_yield
                else:
                    rate = (price * 2.2) / row.batch_yield
            else:
                rate = price

            amount = rate * row.quantity
            total_amount += amount

            self.append(
                "details",
                {
                    "item_name": row.item_name,
                    "batch_yield": row.batch_yield,
                    "quantity": row.quantity,
                    "rate": rate,
                    "price_list_rate": price,
                    "amount": amount,
                },
            )

        self.total_amount = total_amount
        self.total_qty = bm.total_qty
        self.per_unit_price = total_amount / bm.total_qty

    def get_master_sample(self):
        if hasattr(self, "master_sample"):
            master_sample = db.sql(
                "select name from `tabOutward Sample` \
					where docstatus = 1 and product_name = %s and party = %s and is_master_sample = 1",
                (self.product_name, self.party),
            )

        if master_sample:
            self.master_sample = master_sample[0][0]

    def get_latest_ball_mill(self):
        ball_mill = db.sql(
            "select name, date from `tabBall Mill Data Sheet` \
				where docstatus = 1 and product_name = %s and customer_name = %s ORDER BY date DESC",
            (self.product_name, self.party),
        )
        if ball_mill:
            self.last_purchase_reference = ball_mill[0][0]

    def get_latest_sample(self):
        last_sample = db.sql(
            "select name,date from `tabOutward Sample` \
				where docstatus = 1 and product_name = %s and party = %s ORDER BY date DESC",
            (self.product_name, self.party),
        )
        if last_sample:
            self.last_sample = last_sample[0][0]

    # def before_naming(self):
    #     naming_series(self, "save")

    @frappe.whitelist()
    def get_price_list(
        self, item_code, price_list, customer_group="All Customer Groups", company=None
    ):
        price = get_price(item_code, price_list, customer_group, company)

        if not price:
            price = frappe._dict({"price_list_rate": 0.0})

        return price


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
    def set_missing_values(source, target):
        conversion_rate = target.conversion_rate if target.conversion_rate else 1
        description = frappe.db.get_value("Item", source.product_name, "description")
        uom = frappe.db.get_value("Item", source.product_name, "stock_uom")
        target.append(
            "items",
            {
                "item_code": source.product_name,
                "item_name": source.product_name,
                "outward_sample": source.name,
                "uom": uom,
                "description": description,
                "sample_ref_no": source.ref_no,
                "base_cost": source.per_unit_price,
                "cost": source.per_unit_price / conversion_rate,
            },
        )

    doclist = get_mapped_doc(
        "Outward Sample",
        source_name,
        {
            "Outward Sample": {
                "doctype": "Quotation",
                "field_map": {
                    "link_to": "quotation_to",
                    "party": "customer",
                    "date": "transaction_date",
                },
            }
        },
        target_doc,
        set_missing_values,
    )

    return doclist


@frappe.whitelist()
def make_quality_inspection(source_name, target_doc=None):
    doclist = get_mapped_doc(
        "Outward Sample",
        source_name,
        {
            "Outward Sample": {
                "doctype": "Quality Inspection",
                "field_map": {
                    "product_name": "item_code",
                    "doctype": "reference_type",
                    "name": "reference_name",
                },
            }
        },
        target_doc,
    )
    doclist.inspection_type = "Outgoing"
    item_doc = frappe.db.get_value("Item", doclist.item_code, "quality_inspection_template", as_dict=1)
    doclist.quality_inspection_template = item_doc.quality_inspection_template if item_doc else None
    doclist.set("inspected_by", frappe.session.user)
    return doclist


# def get_outward_sample(doctype, txt, searchfield, start, page_len, filters, as_dict):
# 	return frappe.db.sql("""
# 		SELECT
# 			`tabOutward Sample`.name, `tabOutward Sample`.date as transaction_date
# 		FROM
# 			`tabOutward Sample`
# 		WHERE
# 			`tabOutward Sample`.docstatus = 1
# 			%(fcond)s
# 			%(mcond)s
# 		""" % {
# 			"fcond": get_filters_cond(doctype, filters, []),
# 			"mcond": get_match_cond(doctype),
# 			"txt": "%(txt)s"
# 		}, {"txt": ("%%%s%%" % txt)}, as_dict=as_dict)
