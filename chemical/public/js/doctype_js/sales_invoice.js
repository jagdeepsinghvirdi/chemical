
cur_frm.fields_dict.set_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
            "is_group":0,
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("warehouse").get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
            "is_group":0,
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


// Add searchfield to Item query
cur_frm.cscript.onload = function (frm) {
    cur_frm.set_query("item_code", "items", function () {
        return {
            query: "chemical.query.new_item_query",
            filters: {
                'is_sales_item': 1
            }
        }
    });
    cur_frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
        let d = locals[cdt][cdn];
        if (!d.item_code) {
            frappe.throw(__("Please enter Item Code to get batch no"));
        }
        else {
            if (d.item_group == "Finished Products"){
                return {
                    query: "chemical.query.get_batch_no",
                    filters: {
                        'item_code': d.item_code,
                        'warehouse': d.warehouse,
                    }
                }
            } else {
                return {
                    query: "chemical.query.get_batch_no",
                    filters: {
                        'item_code': d.item_code,
                        'warehouse': d.warehouse
                    }
                }
            }
        }
    });
},

frappe.ui.form.on("Sales Invoice", {
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
        })
    },
    validate: function(frm) {
        frappe.db.get_value("Company", frm.doc.company, 'maintain_as_is_new', function (c) {
            if(!c.maintain_as_is_new) {
                frm.doc.items.forEach(function (d) {
                    frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function (r) {
                        if (r.maintain_as_is_stock){
                            if(!d.concentration || d.concentration == 0){
                                frappe.throw("Please add concentration for Item " + d.item_code)
                            }
                        }
                        if (d.packing_size && d.no_of_packages) {
                            if(frm.doc.is_return == 1){
                                frappe.model.set_value(d.doctype, d.name, 'no_of_packages', -Math.abs(d.no_of_packages));
                            }
                            frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size * d.no_of_packages));
                            console.log("I am Here");
                            if (r.maintain_as_is_stock) {
                                frappe.model.set_value(d.doctype, d.name, 'quantity', d.qty * d.concentration / 100);
                                if (d.price) {
                                    frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity * d.price) / flt(d.qty));
                                }
                            }
                            else {
                                frappe.model.set_value(d.doctype, d.name, 'quantity', d.qty);
                                if (d.price) {
                                    frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.price));
                                }
                            }
                        }
                        else {
                            
                            if (r.maintain_as_is_stock) {
                                if(d.quantity){
                                    frappe.model.set_value(d.doctype, d.name, 'qty', d.quantity * 100 / d.concentration);
                                }
                                if (!d.quantity && d.qty){
                                    frappe.model.set_value(d.doctype, d.name, 'quantity', d.qty * d.concentration / 100);
                                }
                                if (d.price) {
                                    frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity * d.price) / flt(d.qty));
                                }
                            }
                            else {
                                if(d.quantity){
                                    frappe.model.set_value(d.doctype, d.name, 'qty', d.quantity);
                                }
                                if(!d.quantity && d.qty){
                                    frappe.model.set_value(d.doctype, d.name, 'quantity', d.qty);
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
                                    console.log('test')
                                    frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size * d.no_of_packages));
                                }
                            }
                        } 
                        else {
                            frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function (r) {
                                if (r.maintain_as_is_stock && d.packing_size >0  && d.no_of_packages > 0 && d.concentration > 0 && !d.calculate_qty_manually) {
                                    console.log('testtyty')
                                    frappe.model.set_value(d.doctype, d.name, 'qty', (d.packing_size * d.no_of_packages * d.concentration) / 100.0);
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
                });
            }
        });
        frm.trigger("cal_total_quantity");
    },
    cal_rate_qty: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        frappe.db.get_value("Company", frm.doc.company, 'maintain_as_is_new', function (c) {
            if(!c.maintain_as_is_new) {
                frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function (r) {
                    if (d.packing_size && d.no_of_packages) {
                        if(frm.doc.is_return == 1){
                            frappe.model.set_value(d.doctype, d.name, 'no_of_packages', -Math.abs(d.no_of_packages));
                        }
                        frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size * d.no_of_packages));
                        if (r.maintain_as_is_stock) {
                            if(d.quantity != (d.qty * d.concentration / 100)){
                                frappe.model.set_value(d.doctype, d.name, 'quantity', d.qty * d.concentration / 100);
                            }
                            if (d.price) {
                                frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity * d.price) / flt(d.qty));
                            }
                        }
                        else {
                            frappe.model.set_value(d.doctype, d.name, 'quantity', d.qty);
                            if (d.price) {
                                frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.price));
                            }
                        }
                    }
                    else {
                        if (r.maintain_as_is_stock) {
                            if(d.quantity){
                                frappe.model.set_value(d.doctype, d.name, 'qty', d.quantity * 100 / d.concentration);
                            }
                            if (!d.quantity && d.qty){
                                frappe.model.set_value(d.doctype, d.name, 'quantity', d.qty * d.concentration / 100);
                            }
                            if (d.price) {
                                frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity * d.price) / flt(d.qty));
                            }
                        }
                        else {
                            if(d.quantity){
                                frappe.model.set_value(d.doctype, d.name, 'qty', d.quantity);
                            }
                            if(!d.quantity && d.qty){
                                frappe.model.set_value(d.doctype, d.name, 'quantity', d.qty);
                            }
                            if (d.price) {
                                frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.price));
                            }
                        }
                    }
                });
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
                                if (r.maintain_as_is_stock && d.packing_size >0  && d.no_of_packages > 0 && d.concentration > 0) {
                                    frappe.model.set_value(d.doctype, d.name, 'qty', (d.packing_size * d.no_of_packages * d.concentration) / 100.0);
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
                });
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
        });
	},

    company: function (frm) {
        if (frm.doc.company) {
            frappe.db.get_value("Company", frm.doc.company, 'cost_center', function (r) {
                frm.doc.items.forEach(function (d) {
                    frappe.model.set_value(d.doctype, d.name, 'cost_center', r.cost_center)
                });
            });
        }
    },
   
}),
frappe.ui.form.on("Sales Invoice Item", {
    item_code: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        if(d.batch_no){

            setTimeout(function () {
                frappe.db.get_value("Batch", d.batch_no, ['packaging_material', 'packing_size', 'lot_no', 'batch_yield', 'concentration'], function (r) {
                    frappe.model.set_value(cdt, cdn, 'packaging_material', r.packaging_material);
                    frappe.model.set_value(cdt, cdn, 'packing_size', r.packing_size);
                    frappe.model.set_value(cdt, cdn, 'lot_no', r.lot_no);
                    frappe.model.set_value(cdt, cdn, 'batch_yield', r.batch_yield);
                    frappe.model.set_value(cdt, cdn, 'concentration', r.concentration);
                })
            }, 1000)
        }
    },

    batch_no: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        if (d.batch_no){
            frappe.db.get_value("Batch", d.batch_no, ['packaging_material', 'packing_size', 'lot_no', 'batch_yield', 'concentration'], function (r) {
                frappe.model.set_value(cdt, cdn, 'packaging_material', r.packaging_material);
                frappe.model.set_value(cdt, cdn, 'packing_size', r.packing_size);
                frappe.model.set_value(cdt, cdn, 'lot_no', r.lot_no);
                frappe.model.set_value(cdt, cdn, 'batch_yield', r.batch_yield);
                frappe.model.set_value(cdt, cdn, 'concentration', r.concentration);
            });
            
        }
    },
    discount_percentage:function(frm,cdt,cdn){
       
        let d = locals[cdt][cdn];
    
            if(d.discount_percentage){
                d.discount_amount = (flt(d.discount_percentage) * flt(d.price_list_rate))/100
            }
            d.rate = flt(d.price_list_rate) - flt(d.discount_amount) 
            d.price = flt(d.rate)
            d.amount = flt(d.rate) * flt(d.quantity)
            
        
    }

   
}),

erpnext.selling.SellingController = class SellingController extends erpnext.TransactionController{
    
};
