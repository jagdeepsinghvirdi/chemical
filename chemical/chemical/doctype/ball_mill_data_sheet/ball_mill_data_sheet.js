// Copyright (c) 2018, Finbyz Tech Pvt Ltd and contributors
// For license information, please see license.txt

cur_frm.add_fetch("batch_no", "concentration", "concentration");
cur_frm.fields_dict.default_source_warehouse.get_query = function(doc) {
	return {
		filters: {
			"is_group": 0,
			'company': doc.company
		}
	}
};
cur_frm.fields_dict.warehouse.get_query = function(doc) {
	return {
		filters: {
			"is_group": 0,
			'company': doc.company
		}
	}
};
cur_frm.fields_dict.cost_center.get_query = function(doc) {
	return {
		filters: {
			"is_group": 0,
			'company': doc.company
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("source_warehouse").get_query = function(doc) {
	return {
		filters: {
			  "is_group": 0,
			  'company': doc.company
		}
	};
};
cur_frm.fields_dict.items.grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: {
			  "is_group": 0,
			  'company': doc.company
		}
	};
};
// cur_frm.fields_dict.sample_no.get_query = function(doc) {
// 	return {
// 		filters: {
// 			"product_name": doc.product_name,
// 			"party": doc.customer_name 
// 		}
// 	}
// };
// cur_frm.fields_dict.sales_order.get_query = function(doc) {
// 	console.log("call")
// 	return {	
// 		filters: {
// 			'docstatus':1,
//             // "product_name": doc.product_name,
//             "customer":doc.customer_name,
// 		}
// 	}
// };

// this.frm.cscript.onload = function(frm) {
// 	this.frm.set_query("sales_order",function(doc) {
// 		console.log("call",doc)
// 		return{
// 						query:"chemical.chemical.doctype.ball_mill_data_sheet.ball_mill_data_sheet.get_sales_order",
// 						filters:{
// 							'doc':doc,
// 							'docstatus':doc.docstatus,
// 							// 'customer':doc.customer_name
// 						}
// 			}
// 	});
// }

this.frm.cscript.onload = function(frm) {
	this.frm.set_query("batch_no", "items", function(doc, cdt, cdn) {
		let d = locals[cdt][cdn];
		if(!d.item_name){
			frappe.msgprint(__("Please select Item"));
		}
		else if(!d.source_warehouse){
			frappe.msgprint(__("Please select source warehouse"));
		}
		else{
			return {
				query: "chemical.batch_valuation.get_batch",
				filters: {
					'item_code': d.item_name,
					'warehouse': d.source_warehouse
				}
			}
		}
	});
	this.frm.set_query("sales_order",function(doc) {
		return{
						query:"chemical.chemical.doctype.ball_mill_data_sheet.ball_mill_data_sheet.get_sales_order",
						filters:{
							'customer_name':doc.customer_name,	
							'product_name':doc.product_name,
						}
			}
	});
	this.frm.set_query("expense_account", "ball_mill_additional_cost", function(doc) {
		return {
			query: "erpnext.controllers.queries.tax_account_query",
			filters: {
				"account_type": ["Tax", "Chargeable", "Income Account", "Expenses Included In Valuation", "Expenses Included In Asset Valuation"],
				"company": doc.company
			}
		};
	});
}
function get_qty(frm) {
	if(flt(frm.doc.target_qty) != 0 && frm.doc.sample_no){
		frappe.run_serially([
			() => { frm.set_value('items',[]) },
			() => {
				frappe.model.with_doc("Outward Sample", frm.doc.sample_no, function() {
					frappe.run_serially([
						() => {
							let os_doc = frappe.model.get_doc("Outward Sample", frm.doc.sample_no)
							$.each(os_doc.details, function(index, row){
								let d = frm.add_child("items");
								d.item_name = row.item_name;
								d.source_warehouse = frm.doc.default_source_warehouse;
								d.quantity = flt(flt(frm.doc.target_qty * row.quantity) / os_doc.total_qty);
								d.required_quantity = flt(flt(frm.doc.target_qty * row.quantity) / os_doc.total_qty);
							})
						},
						() => {
							frm.refresh_fields("items");
						},
					])
				});
			},
		]);
	
	}
}

frappe.ui.form.on('Ball Mill Data Sheet', {
	// validate:function(frm){	
	// 	frm.doc.items.forEach(function(d) {
	// 		if(!d.work_order){
	// 			console.log(d)
	// 		}
	// 	});
	// },
	onload: (frm) => {
		frm.ignore_doctypes_on_cancel_all = ['Outward Sample'];
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	naming_series: function (frm) {
		if (frappe.meta.get_docfield("Ball Mill Data Sheet", "series_value", frm.doc.name)){
			if (frm.doc.__islocal && frm.doc.company && !frm.doc.amended_from) {
				frappe.call({
					method: "finbyzerp.api.check_counter_series",
					args: {
						'name': frm.doc.naming_series,
						'date': frm.doc.transaction_date,
						'company_series': frm.doc.company_series || null,
					},
					callback: function (e) {
						// frm.doc.series_value = e.message;
						frm.set_value('series_value', e.message);
					}
				});
				// frm.refresh_field('series_value')
			}
		}
	},
	company: function (frm) {
		frm.trigger('naming_series');
	},
	refresh: function(frm){
		if(frm.doc.docstatus == 1){
			frm.add_custom_button(__("Outward Sample"), function() {
				frappe.model.open_mapped_doc({
					method : "chemical.chemical.doctype.ball_mill_data_sheet.ball_mill_data_sheet.make_outward_sample",
					frm : cur_frm
				})
			}, __("Make"));
		}
	},
	sales_order:function(frm){
		if(!frm.doc.sales_order || frm.doc.sales_order == undefined ){
			frm.set_value('sample_no','')
			frm.set_value('lot_no','')
			return false;
		}

		frappe.call({
			method : "chemical.chemical.doctype.ball_mill_data_sheet.ball_mill_data_sheet.get_sample_no",
			args:{
				parent:frm.doc.sales_order,	
			   	item_code:frm.doc.product_name,
			},
			callback: function(r) {
				if(!r.exc){
					frm.set_value('sample_no',r.message)
				}
			}
		});
		
	},
	product_name: function(frm) {
		frm.set_value('sales_order','')
		frm.set_value('sample_no','')
       
	},
	sample_no:function(frm){
		get_qty(frm);
	},
	target_qty:function(frm){
		get_qty(frm);
	},
	default_source_warehouse:function(frm){

		frm.doc.items.forEach(function(d) {
			d.source_warehouse = frm.doc.default_source_warehouse;
		});
		frm.refresh_field("items");
	},
	repack_calculation: function(frm,cdt,cdn){
		if (!frappe.db.get_value("Company",self.company,"maintain_as_is_new")){
			var d = locals[cdt][cdn];
			frappe.db.get_value("Item", d.item_name, 'maintain_as_is_stock', function (r) {
				var concentration = d.concentration || 100

				if (d.packing_size && d.no_of_packages){
					frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size) * flt(d.no_of_packages));
					if (r.maintain_as_is_stock) {
						frappe.model.set_value(d.doctype, d.name, 'quantity', (flt(d.qty) * flt(concentration))/100);
						frappe.model.set_value(d.doctype, d.name, 'price', (flt(d.basic_rate) * 100)/flt(concentration));
					}
					else{
						frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
						frappe.model.set_value(d.doctype, d.name, 'price', flt(d.basic_rate));					
					}
				}
				else{
					if (r.maintain_as_is_stock) {
						frappe.model.set_value(d.doctype, d.name, 'price', (flt(d.basic_rate) * 100)/flt(concentration));
						if (d.quantity){
							frappe.model.set_value(d.doctype, d.name, 'qty', (flt(d.quantity)*100) / flt(concentration));
						}
						if (d.qty && !d.quantity){
							frappe.model.set_value(d.doctype, d.name, 'quantity', (flt(d.qty)*flt(concentration)) / 100);
						}
					}
					else{
						frappe.model.set_value(d.doctype, d.name, 'price', flt(d.basic_rate));
						if (d.quantity){
							frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.quantity));
						}
						if (d.qty && !d.quantity){
							frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
						}
					}
				}
			})}
		else{
			var d = locals[cdt][cdn];
			frappe.db.get_value("Item", d.item_name, 'maintain_as_is_stock', function (r) {
				var concentration = d.concentration || 100

				if (d.packing_size && d.no_of_packages){
					frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size) * flt(d.no_of_packages));
				}
				else{
					if (r.maintain_as_is_stock) {
						if (d.qty){
							frappe.model.set_value(d.doctype, d.name, 'quantity', (flt(d.qty)*flt(concentration)) / 100);
						}
					}
					else{
						if (d.qty ){
							frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.qty));
						}
					}
				}
			})
		}		
	},
	packaging_calculation: function(frm,cdt,cdn){
		if (!frappe.db.get_value("Company",self.company,"maintain_as_is_new")){
			var d = locals[cdt][cdn];
			frappe.db.get_value("Item", frm.doc.product_name, 'maintain_as_is_stock', function (r) {
				var concentration = frm.doc.concentration || 100
				if (d.packing_size && d.no_of_packages){
					frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.packing_size) * flt(d.no_of_packages));
					if (r.maintain_as_is_stock) {
						frappe.model.set_value(d.doctype, d.name, 'quantity', (flt(d.qty) * flt(concentration))/100);
					}
					else{
						frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
					}
				}
				else{
					if (r.maintain_as_is_stock) {
						if (d.qty){
							frappe.model.set_value(d.doctype, d.name, 'quantity', (flt(d.qty)*flt(concentration)) / 100);
						}
						if (d.quantity && !d.qty){
							frappe.model.set_value(d.doctype, d.name, 'qty', (flt(d.quantity)*100) / flt(concentration));
						}
					}
					else{
						if (d.qty){
							frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
						}
						if (d.quantity && !d.qty){
							frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.quantity));
						}
					}
				}
			}
		
	)	

}	else{
	var d = locals[cdt][cdn];
			frappe.db.get_value("Item", frm.doc.product_name, 'maintain_as_is_stock', function (r) {
				var concentration = frm.doc.concentration || 100
				if (d.packing_size && d.no_of_packages){
					frappe.model.set_value(d.doctype, d.name, 'qty', (flt(d.packing_size) * flt(d.no_of_packages)));
					if (r.maintain_as_is_stock) {
						frappe.model.set_value(d.doctype, d.name, 'qty', (flt(d.qty) * flt(concentration))/100);
					}
					else{
						frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.qty));
					}
				}
				else{
					if (r.maintain_as_is_stock) {
						if (d.qty){
							frappe.model.set_value(d.doctype, d.name, 'qty', (flt(d.qty)*flt(concentration)) / 100);
						}
					}
					else{
						if (d.qty){
							frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.qty));
						}
					}
				}
			}
		
	)	


}
		
        // frappe.db.get_value("Item", frm.doc.product_name, 'maintain_as_is_stock', function (r) {
		// 	if (r.maintain_as_is_stock) {
		// 		if (d.qty){
		// 			frappe.model.set_value(d.doctype, d.name, 'quantity', (flt(d.qty)*flt(frm.doc.concentration)) / 100);
		// 		}
		// 		if (d.quantity && !d.qty){
		// 			frappe.model.set_value(d.doctype, d.name, 'qty', (flt(d.quantity)*100) / flt(frm.doc.concentration));
		// 		}
		// 	}
		// 	else{
		// 		if (d.qty){
		// 			frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
		// 		}
		// 		if (d.quantity && !d.qty){
		// 			frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.quantity));
		// 		}
		// 	}
		// })
	},
	concentration: function(frm){
		$.each(frm.doc.packaging || [], function(i, d) {
			d.concentration = frm.doc.concentration;
		});
		refresh_field("packaging");
	},
	warehouse: function(frm){
		$.each(frm.doc.packaging || [], function(i, d) {
			d.warehouse = frm.doc.warehouse;
		});
		refresh_field("packaging");
	}
});

frappe.ui.form.on('Ball Mill Data Sheet Item', {
	items_add: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if(!row.source_warehouse && row.source_warehouse == undefined){
		 row.source_warehouse = cur_frm.doc.default_source_warehouse;
		 frm.refresh_field("items");
		}
	},
	concentration: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		// if (row.required_quantity){
		// 	frappe.model.set_value(cdt,cdn,"quantity",row.required_quantity*row.concentration)
		// 	frappe.model.set_value(cdt,cdn,"required_quantity",row.required_quantity*row.concentration)
		// }
	},
	quantity: function(frm,cdt,cdn){
		frm.events.repack_calculation(frm, cdt, cdn)
	},
	qty: function(frm,cdt,cdn){
		frm.events.repack_calculation(frm, cdt, cdn)
	},
	no_of_packages: function(frm,cdt,cdn){
		frm.events.repack_calculation(frm, cdt, cdn)
	},
	batch_no: function(frm,cdt,cdn){
		frm.events.repack_calculation(frm, cdt, cdn)
	},
});

frappe.ui.form.on('Ball Mill Packaging', {
	// quantity: function(frm,cdt,cdn){
	// 	frm.events.packaging_calculation(frm, cdt, cdn)
	// },
	qty: function(frm,cdt,cdn){
		frm.events.packaging_calculation(frm, cdt, cdn)
	},
	no_of_packages: function(frm,cdt,cdn){
		frm.events.repack_calculation(frm, cdt, cdn)
		frm.events.packaging_calculation(frm, cdt, cdn)
	},
	packing_size: function(frm,cdt,cdn){
		frm.events.repack_calculation(frm, cdt, cdn)
		frm.events.packaging_calculation(frm, cdt, cdn)
	},
	packaging_add: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.concentration = frm.doc.concentration;
		row.warehouse =  frm.doc.warehouse
		refresh_field("packaging");
	},
});

// frappe.ui.form.on('Ball Mill Additional Cost', {
//     ball_mill_additional_cost_add: function (frm, cdt, cdn) {
//         setTimeout(function() {
//             frappe.db.get_value("Company", frm.doc.company, "expenses_included_in_valuation", function(r) {
//                 if (r.expenses_included_in_valuation) {
//                     console.log(r.expenses_included_in_valuation);
//                     frappe.model.set_value(cdt, cdn, "expense_account", r.expenses_included_in_valuation);
//                 }
//             });
//         }, 500);
//     },
// });
