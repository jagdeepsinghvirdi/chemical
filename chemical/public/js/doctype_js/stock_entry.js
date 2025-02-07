cur_frm.fields_dict.from_warehouse.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company,
            "is_group":0,
        }
    }
};
cur_frm.fields_dict.to_warehouse.get_query = function (doc) {
    return {
        filters: {
            "company": doc.company,
            "is_group":0,
        }
    }
};
cur_frm.fields_dict.items.grid.get_field("s_warehouse").get_query = function (doc) {
    return {
        filters: {
            "company": doc.company,
            "is_group":0,
        }
    }
};
cur_frm.fields_dict.items.grid.get_field("t_warehouse").get_query = function (doc) {
    return {
        filters: {
            "company": doc.company,
            "is_group":0,
        }
    }
};
cur_frm.fields_dict.items.grid.get_field("bom_no").get_query = function (doc) {
    return {
        filters: {
            "docstatus": 1,
        }
    }
};

frappe.ui.form.on("Stock Entry", {
    onload: function(frm){
        
    },
    before_save: function (frm) {
        frappe.db.get_value("Company", frm.doc.company, 'abbr', function (r) {
            if (frm.doc.is_opening == "Yes") {
                $.each(frm.doc.items || [], function (i, d) {
                    d.expense_account = 'Temporary Opening - ' + r.abbr;
                });
            }
        });

        if (frm.doc.purpose == "Manufacture" && frm.doc.work_order) {
            frm.call({
                method: 'get_stock_and_rate',
                doc: frm.doc
            });
        }
    },
    validate: function(frm) {
        frappe.run_serially([
            () => {
                frm.doc.items.forEach(function(d) {
                    frm.events.set_basic_rate(frm, d.doctype, d.name)
                });
            },
            () => {
                frm.doc.items.forEach(function(d) {
                    frm.events.calculate_qty(frm, d.doctype, d.name)
                });
            }
        ])
    },
    set_basic_rate: function (frm, cdt, cdn) {
        const item = locals[cdt][cdn];
        if (item.t_warehouse) {
            return;
        }
        item.transfer_qty = flt(item.qty) * flt(item.conversion_factor);

        let batch = '';
        if (!item.t_warehouse) {
            batch = item.batch_no;
        }

        const args = {
            'item_code': item.item_code,
            'posting_date': frm.doc.posting_date,
            'posting_time': frm.doc.posting_time,
            'warehouse': cstr(item.s_warehouse) || cstr(item.t_warehouse),
            'serial_no': item.serial_no,
            'company': frm.doc.company,
            'qty': item.s_warehouse ? -1 * flt(item.transfer_qty) : flt(item.transfer_qty),
            'voucher_type': frm.doc.doctype,
            'voucher_no': item.name,
            'allow_zero_valuation': 1,
            'batch_no': batch || ''
        };

        if (item.item_code || item.serial_no) {
            frappe.call({
                method: "erpnext.stock.utils.get_incoming_rate",
                args: {
                    args: args
                },
                callback: function (r) {
                    if(!item.set_basic_rate_manually){
                        frappe.model.set_value(cdt, cdn, 'basic_rate', (r.message || 0.0));
                    }
                }
            });
        }
    },
    calculate_qty: function(frm, cdt, cdn){
        let d = locals[cdt][cdn];

        // if (!(frm.doc.purpose == "Material Receipt" || frm.doc.purpose == "Repack")){
        //     return ;
        // }

        frappe.run_serially([
            () => {
                if (d.batch_no && d.s_warehouse) {
                    frappe.db.get_value("Batch", d.batch_no, ['packaging_material', 'packing_size', 'lot_no', 'batch_yield', 'concentration'], function (r) {
                        frappe.model.set_value(d.doctype, d.name, 'packaging_material', r.packaging_material);
                        frappe.model.set_value(d.doctype, d.name, 'packing_size', r.packing_size);
                        frappe.model.set_value(d.doctype, d.name, 'lot_no', r.lot_no);
                        frappe.model.set_value(d.doctype, d.name, 'batch_yield', r.batch_yield);
                        frappe.model.set_value(d.doctype, d.name, 'concentration', r.concentration);
                    });

                    frm.refresh_field("items");
                }
            },
            () => {
                frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function(r) {
                    let concentration = d.concentration || 100.0;
        
                    if (d.packing_size && d.no_of_packages){
                        if (r.maintain_as_is_stock && !d.ignore_calculation) {
                            frappe.model.set_value(d.doctype, d.name, "qty", (d.packing_size * d.no_of_packages * concentration) / 100.0);
                        }
                        else {
                            frappe.model.set_value(d.doctype, d.name, "qty", (d.packing_size * d.no_of_packages));
                        }
                    }

                    frm.refresh_field("items");
                });
            }
        ]);
    },
});

frappe.ui.form.on("Stock Entry Detail", {
    form_render: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        var item_grid = frm.get_field('items').grid;
        let batch_no = item_grid.grid_rows[d.idx - 1].get_field('batch_no');
        if (!in_list(["Material Issue", "Material Transfer", "Material Transfer for Manufacture"], frm.doc.purpose)) {
            if (d.s_warehouse) {
                batch_no.df.read_only = 0;
            }
            else if (d.t_warehouse) {
                batch_no.df.read_only = 1;
            }
        }
    },
    s_warehouse: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        var item_grid = frm.get_field('items').grid;
        let batch_no = item_grid.grid_rows[d.idx - 1].get_field('batch_no');
        if (!in_list(["Material Issue", "Material Transfer", "Material Transfer for Manufacture"], frm.doc.purpose)) {
            if (d.s_warehouse) {
                batch_no.df.read_only = 0;
            }
            else if (d.t_warehouse) {
                batch_no.df.read_only = 1;
            }
        }
    },
    t_warehouse: function (frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        var item_grid = frm.get_field('items').grid;
        let batch_no = item_grid.grid_rows[d.idx - 1].get_field('batch_no');
        if (!in_list(["Material Issue", "Material Transfer", "Material Transfer for Manufacture"], frm.doc.purpose)) {
            if (d.s_warehouse) {
                batch_no.df.read_only = 0;
            }
            else if (d.t_warehouse) {
                batch_no.df.read_only = 1;
            }
        }
        frm.refresh_field('items');
    },
    conversion_factor: function (frm, cdt, cdn) {
        frm.events.set_basic_rate(frm, cdt, cdn);
    },
    qty: function (frm, cdt, cdn) {
        frm.events.calculate_qty(frm, cdt, cdn)
    },  
    concentration: function(frm, cdt, cdn){
        frm.events.calculate_qty(frm, cdt, cdn)
    },
    packing_size: function (frm, cdt, cdn) {
        frm.events.calculate_qty(frm, cdt, cdn)
    },
    no_of_packages: function (frm, cdt, cdn) {
        frm.events.calculate_qty(frm, cdt, cdn)
    },
    batch_no:function(frm,cdt,cdn){
        frm.events.calculate_qty(frm)
    },
});