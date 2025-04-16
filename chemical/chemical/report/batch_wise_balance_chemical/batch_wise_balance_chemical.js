// Copyright (c) 2016, FinByz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

function getUrlParameter(name) {
    name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
    var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
    var results = regex.exec(location.search);
    return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
};

frappe.query_reports["Batch Wise Balance Chemical"] = {
	onload: function(report){
		var item_code = getUrlParameter("item_code");
		var warehouse = getUrlParameter("warehouse");
		// console.log(getUrlParameter("item_code"))
		// console.log(warehouse)
		if(item_code){
			setTimeout(()=>{
				frappe.query_report.set_filter_value('item_code', item_code);
			},150)
		}
		if(warehouse){
			setTimeout(()=>{
				frappe.query_report.set_filter_value('warehouse', warehouse);
			},150)
		}
		frappe.call({
			method:"chemical.chemical.report.stock_ledger_chemical.stock_ledger_chemical.show_party_hidden",
			callback: function(r){
				if (r.message==0){
					frappe.query_report.get_filter('show_party').toggle(false)
				}
			}
		})
	},
	"filters": [
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"width": "80",
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": "80",
		},
		{
			"fieldname": "warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": "80",
		},
		{
			"fieldname": "show_party",
			"label": __("Show party"),
			"fieldtype": "Check",
		}
		
	]
}
function view_stock_leder_report(item_code, filter_company,from_date, to_date, batch_no) {
	let fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today());
	frappe.db.get_value("Fiscal Year", {"name": fiscal_year}, "year_start_date", function(value) {
	window.open(window.location.href.split('app')[0] + "app/query-report/Stock Ledger" + "?" + "company="  + filter_company + "&"  + "from_date=" + value.year_start_date + "&" + "to_date=" + to_date + "&" + "item_code=" + encodeURIComponent(item_code)  + "&" + "batch_no=" + batch_no,"_blank")
	// window.open(window.location.href.split('app')[0] + "app/query-report/Stock Ledger" + "?"  + "company= "  + filter_company +"&"  + "from_date=" + from_date + "&" + "to_date=" + to_date )
	// window.open(`/app/query-report/Stock Ledger/%3Fitem_code%3D${item_code}%26company%3D %26from_date%3D${from_date}%26to_date%3D${to_date}%26batch_no%3D${batch_no}`,"_blank")
	});
}
