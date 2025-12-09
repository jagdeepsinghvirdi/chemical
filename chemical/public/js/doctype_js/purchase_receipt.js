cur_frm.fields_dict.set_warehouse.get_query = function(doc) {
    return {
        filters: {
            "company": doc.company,

        }
    }
};

cur_frm.fields_dict.taxes_and_charges.get_query = function(doc) {
    return {
        filters: {
            "company": doc.company,

        }
    }
};



frappe.ui.form.on("Purchase Receipt", {
    validate: function(frm) {
		frappe.db.get_value("Company", frm.doc.company, 'maintain_as_is_new', function(c) {
			if(!c.maintain_as_is_new) {
				frm.doc.items.forEach(function(d) {
					var packing_size = 0;
					frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function(r) {
						if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty")) {
							if (frappe.meta.get_docfield("Purchase Receipt Item", "tare_weight")) {
								if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_packing_size") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_no_of_packages")) {
									packing_size = (d.receive_packing_size - d.tare_weight)
									frappe.model.set_value(d.doctype, d.name, 'receive_qty', packing_size * d.receive_no_of_packages);
								}
							} else {
								if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_packing_size") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_no_of_packages")) {
									packing_size = d.receive_packing_size
									frappe.model.set_value(d.doctype, d.name, 'receive_qty', packing_size * d.receive_no_of_packages);
								}
							}
						} else {
							if (d.packing_size && d.no_of_packages) {
								packing_size = d.packing_size
								frappe.model.set_value(d.doctype, d.name, 'qty', d.packing_size * d.no_of_packages);
								frappe.model.set_value(d.doctype, d.name, 'received_qty', d.packing_size * d.no_of_packages);
							}
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_qty")) {
							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_packing_size") && frappe.meta.get_docfield("Purchase Receipt Item", "accepted_no_of_packages")) {
								frappe.model.set_value(d.doctype, d.name, 'accepted_qty', flt(d.accepted_packing_size) * flt(d.accepted_no_of_packages));
							}
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_qty")) {
							if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_packing_size") && frappe.meta.get_docfield("Purchase Receipt Item", "supplier_no_of_packages")) {
								frappe.model.set_value(d.doctype, d.name, 'supplier_qty', flt(d.supplier_packing_size) * flt(d.supplier_no_of_packages));
							}
							if (!d.supplier_qty) {
								frappe.throw(d.doctype + " Row: " + d.idx + " Please add supplier Qty")
							}
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_packing_size")) {
							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_packing_size")) {
								frappe.model.set_value(d.doctype, d.name, 'packing_size', d.accepted_packing_size || packing_size);
								frappe.model.set_value(d.doctype, d.name, 'no_of_packages', d.accepted_no_of_packages || d.receive_no_of_packages);
							} else {
								frappe.model.set_value(d.doctype, d.name, 'packing_size', packing_size);
								frappe.model.set_value(d.doctype, d.name, 'no_of_packages', d.receive_no_of_packages);
							}
						}

						if (r.maintain_as_is_stock) {
							if (frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
								frappe.model.set_value(d.doctype, d.name, 'receive_quantity', flt(d.receive_qty) * d.received_concentration / 100);
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_concentration")) {
								if (!d.supplier_concentration) {
									frappe.throw(d.doctype + " Row: " + d.idx + " Please add supplier concentration")
								}
								frappe.model.set_value(d.doctype, d.name, 'supplier_quantity', flt(d.supplier_qty) * d.supplier_concentration / 100);
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_concentration")) {
								frappe.model.set_value(d.doctype, d.name, 'accepted_quantity', flt(d.accepted_qty) * d.accepted_concentration / 100);
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_qty") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty")) {
								frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.accepted_qty) || flt(d.receive_qty));
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_concentration") && frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
								frappe.model.set_value(d.doctype, d.name, 'concentration', d.accepted_concentration || d.received_concentration);
							}

							if (!frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty") && (!d.packing_size || !d.no_of_packages)) {
								if (d.quantity) {
									frappe.model.set_value(d.doctype, d.name, 'qty', (flt(d.quantity) * 100.0) / flt(d.concentration))
								}
							}

							if (!d.qty) {
								if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty")) {
									frappe.throw(d.doctype + " Row: " + d.idx + " Please add Receive Qty or Accepted Qty")
								} else {
									frappe.throw(d.doctype + " Row: " + d.idx + "  Please add Qty")
								}
							}

							if (!d.concentration) {
								if (frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
									frappe.throw(d.doctype + " Row: " + d.idx + " Please add received or accepted concentration")
								} else {
									frappe.throw(d.doctype + " Row: " + d.idx + "  Please add concentration")
								}
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_quantity") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_quantity")) {
								frappe.model.set_value(d.doctype, d.name, 'quantity', d.accepted_quantity || d.receive_quantity);
							} else {
								frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty) * flt(d.concentration) / 100);
							}
							if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_quantity")) {
								frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.supplier_quantity) * flt(d.price) / flt(d.qty));
							} else {
								frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity) * flt(d.price) / flt(d.qty));
							}
						} else {
							if (frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
								frappe.model.set_value(d.doctype, d.name, 'receive_quantity', flt(d.receive_qty));
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_concentration")) {
								frappe.model.set_value(d.doctype, d.name, 'supplier_quantity', flt(d.supplier_qty));
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_concentration")) {
								frappe.model.set_value(d.doctype, d.name, 'accepted_quantity', flt(d.accepted_qty));
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_qty") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty")) {
								frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.accepted_qty) || flt(d.receive_qty));
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_concentration") && frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
								frappe.model.set_value(d.doctype, d.name, 'concentration', flt(d.accepted_concentration) || flt(d.received_concentration));
							}


							if (!frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty") && (!d.packing_size || !d.no_of_packages)) {
								if (d.quantity) {
									frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.quantity))
								}
							}

							if (!d.qty) {
								if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty")) {
									frappe.throw(d.doctype + " Row: " + d.idx + " Please add Receive Qty or Accepted Qty")
								} else {
									frappe.throw(d.doctype + " Row: " + d.idx + "  Please add Qty")
								}
							}

							if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_quantity") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_quantity")) {
								frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.accepted_quantity) || flt(d.receive_quantity));
							} else {
								frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
							}
							frappe.model.set_value(d.doctype, d.name, 'rate', d.price);
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "short_quantity")) {
							frappe.model.set_value(d.doctype, d.name, 'short_quantity', flt(d.quantity) - flt(d.supplier_quantity));
							if (d.short_quantity) {
								frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.supplier_quantity) * flt(d.price) / flt(d.qty));
							}
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "amount_difference")) {
							frappe.model.set_value(d.doctype, d.name, 'amount_difference', flt(d.price) * flt(d.short_quantity));
						}

					});
				});
			} else {
				frm.doc.items.forEach(function(d) {
					if(!d.ignore_calculation) {
						frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function(r) {
							if(r.maintain_as_is_stock){
								if (d.packing_size && d.no_of_packages && d.concentration) {
									frappe.model.set_value(d.doctype, d.name, 'qty', (d.packing_size * d.no_of_packages * d.concentration) / 100.0);
									frappe.model.set_value(d.doctype, d.name, 'received_qty', (d.packing_size * d.no_of_packages * d.concentration) / 100.0);
								}
							} else {
								if (d.packing_size && d.no_of_packages) {
									frappe.model.set_value(d.doctype, d.name, 'qty', d.packing_size * d.no_of_packages);
									frappe.model.set_value(d.doctype, d.name, 'received_qty', d.packing_size * d.no_of_packages);
								}
							}
						});
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
    before_save: function(frm) {
        frm.trigger("cal_total");
    },
    cal_total: function(frm) {
		frappe.db.get_value("Company", frm.doc.company, 'maintain_as_is_new', function (c) {
			if(!c.maintain_as_is_new) {
				let total_quantity = 0;
				let total_supplier_qty = 0;
				let total_supplier_quantity = 0;
				let total_packages = 0;

				frm.doc.items.forEach(function(d) {
					total_quantity += flt(d.quantity);
					if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_qty")) {
						total_supplier_qty += flt(d.supplier_qty);
						total_supplier_quantity += flt(d.supplier_quantity);
						total_packages += flt(d.no_of_packages);
					}

				});
				frm.set_value("total_quantity", total_quantity);
				if (frappe.meta.get_docfield("Purchase Receipt", "total_supplier_qty")) {
					frm.set_value("total_supplier_qty", total_supplier_qty);
					frm.set_value("total_supplier_quantity", total_supplier_quantity);
					frm.set_value("total_packages", total_packages);
				}
			}
		});

    },

    cal_rate_qty: function(frm, cdt, cdn) {
        let d = locals[cdt][cdn];
        var packing_size = 0;
        if (!d.concentration) {
            d.concentration = 100
        }
		frappe.db.get_value("Company", frm.doc.company, 'maintain_as_is_new', function(c) {
			if(!c.maintain_as_is_new) {
				frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function(r) {
					if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty")) {
						if (frappe.meta.get_docfield("Purchase Receipt Item", "tare_weight")) {
							if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_packing_size") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_no_of_packages")) {
								packing_size = (d.receive_packing_size - d.tare_weight)
								frappe.model.set_value(d.doctype, d.name, 'receive_qty', packing_size * d.receive_no_of_packages);
							}
						} else {
							if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_packing_size") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_no_of_packages")) {
								packing_size = d.receive_packing_size
								frappe.model.set_value(d.doctype, d.name, 'receive_qty', packing_size * d.receive_no_of_packages);
							}
						}
					} else {
						if (d.packing_size && d.no_of_packages) {
							packing_size = d.packing_size
							frappe.model.set_value(d.doctype, d.name, 'qty', d.packing_size * d.no_of_packages);
							frappe.model.set_value(d.doctype, d.name, 'received_qty', d.packing_size * d.no_of_packages);
						}
					}

					if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_qty")) {
						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_packing_size") && frappe.meta.get_docfield("Purchase Receipt Item", "accepted_no_of_packages")) {
							frappe.model.set_value(d.doctype, d.name, 'accepted_qty', flt(d.accepted_packing_size) * flt(d.accepted_no_of_packages));
						}
					}

					if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_qty")) {
						if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_packing_size") && frappe.meta.get_docfield("Purchase Receipt Item", "supplier_no_of_packages")) {
							frappe.model.set_value(d.doctype, d.name, 'supplier_qty', flt(d.supplier_packing_size) * flt(d.supplier_no_of_packages));
						}

					}

					if (frappe.meta.get_docfield("Purchase Receipt Item", "receive_packing_size")) {
						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_packing_size")) {
							frappe.model.set_value(d.doctype, d.name, 'packing_size', d.accepted_packing_size || packing_size);
							frappe.model.set_value(d.doctype, d.name, 'no_of_packages', d.accepted_no_of_packages || d.receive_no_of_packages);
						} else {
							frappe.model.set_value(d.doctype, d.name, 'packing_size', packing_size);
							frappe.model.set_value(d.doctype, d.name, 'no_of_packages', d.receive_no_of_packages);
						}
					}

					if (r.maintain_as_is_stock) {
						if (frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
							frappe.model.set_value(d.doctype, d.name, 'receive_quantity', flt(d.receive_qty) * d.received_concentration / 100);
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_concentration")) {
							if (!d.supplier_concentration) {
								// frappe.throw(d.doctype + " Row: "+ d.idx +" Please add supplier concentration")
							}
							frappe.model.set_value(d.doctype, d.name, 'supplier_quantity', flt(d.supplier_qty) * d.supplier_concentration / 100);
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_concentration")) {
							frappe.model.set_value(d.doctype, d.name, 'accepted_quantity', flt(d.accepted_qty) * d.accepted_concentration / 100);
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_qty") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty")) {
							frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.accepted_qty) || flt(d.receive_qty));
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_concentration") && frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
							frappe.model.set_value(d.doctype, d.name, 'concentration', d.accepted_concentration || d.received_concentration);
						}

						if (!frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty") && (!d.packing_size || !d.no_of_packages)) {
							if (d.quantity) {
								frappe.model.set_value(d.doctype, d.name, 'qty', (flt(d.quantity) * 100.0) / flt(d.concentration))
							}
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_quantity") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_quantity")) {
							frappe.model.set_value(d.doctype, d.name, 'quantity', d.accepted_quantity || d.receive_quantity);
						} else {
							frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty) * flt(d.concentration) / 100);
						}
						if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_quantity")) {
							frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.supplier_quantity) * flt(d.price) / flt(d.qty));
						} else {
							frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.quantity) * flt(d.price) / flt(d.qty));
						}
					} else {
						if (frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
							frappe.model.set_value(d.doctype, d.name, 'receive_quantity', flt(d.receive_qty));
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "supplier_concentration")) {
							frappe.model.set_value(d.doctype, d.name, 'supplier_quantity', flt(d.supplier_qty));
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_concentration")) {
							frappe.model.set_value(d.doctype, d.name, 'accepted_quantity', flt(d.accepted_qty));
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_qty") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty")) {
							frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.accepted_qty) || flt(d.receive_qty));
						}

						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_concentration") && frappe.meta.get_docfield("Purchase Receipt Item", "received_concentration")) {
							frappe.model.set_value(d.doctype, d.name, 'concentration', flt(d.accepted_concentration) || flt(d.received_concentration));
						}

						if (!frappe.meta.get_docfield("Purchase Receipt Item", "receive_qty") && (!d.packing_size || !d.no_of_packages)) {
							if (d.quantity) {
								frappe.model.set_value(d.doctype, d.name, 'qty', flt(d.quantity))
							}
						}
						if (frappe.meta.get_docfield("Purchase Receipt Item", "accepted_quantity") && frappe.meta.get_docfield("Purchase Receipt Item", "receive_quantity")) {
							frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.accepted_quantity) || flt(d.receive_quantity));
						} else {
							frappe.model.set_value(d.doctype, d.name, 'quantity', flt(d.qty));
						}
						frappe.model.set_value(d.doctype, d.name, 'rate', d.price);
					}


					if (frappe.meta.get_docfield("Purchase Receipt Item", "short_quantity")) {
						frappe.model.set_value(d.doctype, d.name, 'short_quantity', flt(d.quantity) - flt(d.supplier_quantity));
						if (d.short_quantity) {
							frappe.model.set_value(d.doctype, d.name, 'rate', flt(d.supplier_quantity) * flt(d.price) / flt(d.qty));
						}
					}

					if (frappe.meta.get_docfield("Purchase Receipt Item", "amount_difference")) {
						frappe.model.set_value(d.doctype, d.name, 'amount_difference', flt(d.price) * flt(d.short_quantity));
					}

				});
			} else {
				frm.doc.items.forEach(function(d) {
					if(!d.ignore_calculation) {
						frappe.db.get_value("Item", d.item_code, 'maintain_as_is_stock', function(r) {
							if(r.maintain_as_is_stock && d.packing_size && d.no_of_packages && d.concentration){
								frappe.model.set_value(d.doctype, d.name, 'qty', (d.packing_size * d.no_of_packages * d.concentration) / 100.0);
								frappe.model.set_value(d.doctype, d.name, 'received_qty', (d.packing_size * d.no_of_packages * d.concentration) / 100.0);
							} else {
								if (d.packing_size && d.no_of_packages) {
									packing_size = d.packing_size
									frappe.model.set_value(d.doctype, d.name, 'qty', d.packing_size * d.no_of_packages);
									frappe.model.set_value(d.doctype, d.name, 'received_qty', d.packing_size * d.no_of_packages);
								}
							}
						});
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
});

frappe.ui.form.on("Purchase Receipt Item", {
    receive_no_of_packages: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    received_concentration: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    concentration: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    packing_size: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    tare_weight: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    supplier_packing_size: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    supplier_no_of_packages: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    supplier_concentration: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    accepted_no_of_packages: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
    accepted_concentration: function(frm, cdt, cdn) {
        frm.events.cal_rate_qty(frm, cdt, cdn)
    },
});