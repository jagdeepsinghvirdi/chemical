// this.frm.add_fetch('batch_no', 'packaging_material', 'packaging_material');
// this.frm.add_fetch('batch_no', 'packing_size', 'packing_size');
// this.frm.add_fetch('batch_no', 'lot_no', 'lot_no');
// this.frm.add_fetch('batch_no', 'batch_yield', 'batch_yield');
// this.frm.add_fetch('batch_no', 'concentration', 'concentration');

erpnext.stock.DeliveryNoteController = class DeliveryNoteController extends erpnext.stock.DeliveryNoteController{
	show_stock_ledger () {
        var me = this;
        if (this.frm.doc.docstatus === 1) {
            cur_frm.add_custom_button(__("Stock Ledger"), function () {
                frappe.route_options = {
                    voucher_no: me.frm.doc.name,
                    from_date: me.frm.doc.posting_date,
                    to_date: me.frm.doc.posting_date,
                    company: me.frm.doc.company
                };
                frappe.set_route("query-report", "Stock Ledger");
            }, __("View"));
        }

    }
};

cur_frm.fields_dict.taxes_and_charges.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
		}
	}
};

// extend_cscript(cur_frm.cscript, new erpnext.stock.DeliveryNoteController({ frm: cur_frm }));

// Add searchfield to Item query

this.frm.cscript.onload = function (frm) {
    this.frm.set_query("item_code", "items", function () {
        return {
            query: "chemical.query.new_item_query1",
            filters: {
                'is_sales_item': 1
            }
        }
    });

    this.frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
        let d = locals[cdt][cdn];
        if (!d.item_code) {
            frappe.throw(__("Please enter Item Code to get batch no"));
        }
        else {
            return {
                query: "chemical.batch_valuation.get_batch_no",
                filters: {
                    'item_code': d.item_code,
                    'warehouse': d.warehouse,
                }
            }
        }
    });
}

frappe.ui.form.on("Delivery Note", {
    refresh: function(frm) {
		if(frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(__("Stock Ledger Chemical"), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					company: frm.doc.company,
					show_cancelled_entries: frm.doc.docstatus === 2,
					ignore_prepared_report: true
				};
				frappe.set_route("query-report", "Stock Ledger Chemical");
			}, __("View"));
		}
	},
	onload_post_render: function(frm) {
		frm.page.remove_inner_button("Stock Ledger", "View")
	},
    onload : function (frm) {
        if (frm.doc.items && frm.doc.__islocal){
            frm.doc.items.forEach(function (d) {
                d.quantity =  d.qty;
            });
            frm.refresh_field('items');
        }
        frm.posting_date = frm.doc.posting_date
        frm.posting_time = frm.doc.posting_time
    },
    posting_date: function(frm){
        frm.posting_date = frm.doc.posting_date
    },
    posting_time: function(frm){
        frm.posting_time = frm.doc.posting_time
    },
    before_save: function (frm) {

        frm.doc.items.forEach(function (d) {
            if (!d.item_code) {
                frappe.throw("Please Select the item")
            }
            frappe.call({
                method: 'chemical.api.get_customer_ref_code',
                args: {
                    'item_code': d.item_code,
                    'customer': frm.doc.customer,
                },
                callback: function (r) {
                    if (r.message) {
                        frappe.model.set_value(d.doctype, d.name, 'item_name', r.message);
                    }
                }
            })
        });
        frm.refresh_field('items');
       
    },
    
    before_validate: function(frm) {
        frappe.db.get_value("Company", frm.doc.company, 'maintain_as_is_new', function (c) {
            if(!c.maintain_as_is_new) {
                frm.doc.items.forEach(function (d) {
                    frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function (r) {
                        if (r.maintain_as_is_stock){
                            if(!d.concentration){
                                frappe.throw("Please add concentration for Item " + d.item_code)
                            }
                        }
                        if (d.packing_size && d.no_of_packages) {
                            if (frm.doc.is_return && d.packing_size > 0 && d.no_of_packages > 0){
                                frappe.model.set_value(d.doctype, d.name, 'qty', flt(-1 * d.packing_size * d.no_of_packages));
                            } else {
                                frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size * d.no_of_packages));
                            }
                            if (r.maintain_as_is_stock) {
                                frappe.model.set_value(d.doctype, d.name, 'quantity',flt(d.qty * d.concentration / 100));
                                if (d.price) {
                                    frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity * d.price) / flt(d.qty));
                                }
                            }
                            else {
                                frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
                                if (d.price) {
                                    frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.price));
                                }
                            }
                        }
                        else {
                            if (r.maintain_as_is_stock) {
                                if(d.quantity){
                                    frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.quantity * 100 / d.concentration));
                                }
                                if (!d.quantity && d.qty){
                                    frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty * d.concentration / 100));
                                }
                                if (d.price) {
                                    frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity * d.price) / flt(d.qty));
                                }
                            }
                            else {
                                if(d.quantity){
                                    frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.quantity));
                                }
                                if(!d.quantity && d.qty){
                                    frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
                                }
                                if (d.price) {
                                    frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.price));
                                }
                            }
                        }
                    })
                });
            } else {
                frm.doc.items.forEach(function (d) {
                    if(!d.ignore_calculation) {
                        if (d.packing_size && d.no_of_packages) {
                            if (frm.doc.is_return && d.packing_size > 0 && d.no_of_packages > 0){
                                frappe.model.set_value(d.doctype, d.name, 'qty', flt(-1 * d.packing_size * d.no_of_packages));
                            } else {
                                if(!d.calculate_qty_manually){
                                    frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size * d.no_of_packages));
                                }
                            }
                        } 
                        else {
                            frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function (r) {
                                if (r.maintain_as_is_stock && d.packing_size && d.no_of_packages && d.concentration && !d.calculate_qty_manually) {
                                    frappe.model.set_value(d.doctype, d.name, 'qty', (d.packing_size * d.no_of_packages * d.concentration) / 100.0);
                                }
                                else {
                                    frappe.model.set_value(d.doctype, d.name, 'qty', d.packing_size * d.no_of_packages);
                                }
                            })
                        }
                    } else {
                        if(d.ignore_calculation){
                            if (d.packing_size && d.no_of_packages) {
                                frappe.model.set_value(d.doctype, d.name, 'qty', d.packing_size * d.no_of_packages);
                            }
                        }
                    }
                })
            }
        });
        // frm.trigger("cal_total_quantity");
    },
    cal_rate_qty: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        frappe.db.get_value("Company", frm.doc.company, 'maintain_as_is_new', function (c) {
            if(!c.maintain_as_is_new) {
                frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function (r) {
                    if (d.packing_size && d.no_of_packages) {
                        frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size * d.no_of_packages));
                        if (r.maintain_as_is_stock) {
                            frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty * d.concentration / 100));
                            if (d.price) {
                                frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity * d.price) / flt(d.qty));
                            }
                        }
                        else {
                            frappe.model.set_value(d.doctype, d.name, 'quantity',flt( d.qty));
                            if (d.price) {
                                frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.price));
                            }
                        }
                    }
                    else {
                        if (r.maintain_as_is_stock) {
                            if(d.quantity){
                                frappe.model.set_value(d.doctype, d.name, 'qty',flt(d.quantity * 100 / d.concentration));
                            }
                            if (!d.quantity && d.qty){
                                frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty * d.concentration )/ 100);
                            }
                            if (d.price) {
                                frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity * d.price) / flt(d.qty));
                            }
                        }
                        else {
                            if(d.quantity){
                                frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.quantity));
                            }
                            if(!d.quantity && d.qty){
                                frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
                            }
                            if (d.price) {
                                frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.price));
                            }
                        }
                    }
                })
            } else {
                frm.doc.items.forEach(function (d) {
                    if(!d.ignore_calculation) {
                        if (d.packing_size && d.no_of_packages) {
                            if (frm.doc.is_return && d.packing_size > 0 && d.no_of_packages > 0){
                                frappe.model.set_value(d.doctype, d.name, 'qty', flt(-1 * d.packing_size * d.no_of_packages));
                            } else {
                                frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size * d.no_of_packages));
                            }
                        } 
                        else {
                            frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function (r) {
                                if (r.maintain_as_is_stock) {
                                    frappe.model.set_value(d.doctype, d.name, 'qty', (d.packing_size * d.no_of_packages * d.concentration) / 100.0);
                                }
                                else {
                                    frappe.model.set_value(d.doctype, d.name, 'qty', d.packing_size * d.no_of_packages);
                                }
                            })
                        }
                    } else {
                        if(d.ignore_calculation){
                            if (d.packing_size && d.no_of_packages) {
                                frappe.model.set_value(d.doctype, d.name, 'qty', d.packing_size * d.no_of_packages);
                            }
                        }
                    }
                })
            }
        });
    },
    
    cal_total_quantity: function (frm) {
        frappe.db.get_value("Company", frm.doc.company, 'maintain_as_is_new', function (c) {
			if(!c.maintain_as_is_new) {
                let total_quantity = 0.0;
                
                frm.doc.items.forEach(function (d) {
                    total_quantity += flt(d.quantity);
                });
                frm.set_value("total_quantity", total_quantity);
            }
        })
	},
    
});
frappe.ui.form.on("Delivery Note Item", {
    item_code: function (frm, cdt, cdn) {
        
        let d = locals[cdt][cdn];
        setTimeout(function () {
            frappe.db.get_value("Batch", d.batch_no, ['packaging_material', 'packing_size', 'lot_no', 'batch_yield', 'concentration'], function (r) {
                frappe.model.set_value(cdt, cdn, 'packaging_material', r.packaging_material);
                frappe.model.set_value(cdt, cdn, 'packing_size', r.packing_size);
                frappe.model.set_value(cdt, cdn, 'lot_no', r.lot_no);
                frappe.model.set_value(cdt, cdn, 'batch_yield', r.batch_yield);
                frappe.model.set_value(cdt, cdn, 'concentration', r.concentration);
            })
        }, 1000)
    },
    quantity: function(frm,cdt,cdn){
        frm.events.cal_rate_qty(frm,cdt,cdn)
    },
    
    price:function(frm,cdt,cdn){
        frm.events.cal_rate_qty(frm,cdt,cdn)
    },
    packing_size: function (frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    no_of_packages: function (frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    concentration: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },

    batch_no: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        frappe.db.get_value("Batch", d.batch_no, ['packaging_material', 'packing_size', 'lot_no', 'batch_yield', 'concentration', 'valuation_rate'], function (r) {
            console.log(r.packing_size)
            frappe.model.set_value(cdt, cdn, 'packaging_material', r.packaging_material);
            frappe.model.set_value(cdt, cdn, 'packing_size', r.packing_size);
            frappe.model.set_value(cdt, cdn, 'lot_no', r.lot_no);
            frappe.model.set_value(cdt, cdn, 'batch_yield', r.batch_yield);
            frappe.model.set_value(cdt, cdn, 'concentration', r.concentration);
            frappe.model.set_value(cdt, cdn, 'rate', r.valuation_rate);
        });
    }
});