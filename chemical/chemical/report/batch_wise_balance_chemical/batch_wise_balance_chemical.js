frappe.query_reports["Batch Wise Balance Chemical"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			width: "80",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			width: "80",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "item_code",
			label: __("Item Code"),
			fieldtype: "Link",
			options: "Item",
			get_query: function () {
				return {
					filters: {
						has_batch_no: 1,
					},
				};
			},
		},
		{
			fieldname: "warehouse_type",
			label: __("Warehouse Type"),
			fieldtype: "Link",
			width: "80",
			options: "Warehouse Type",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
			get_query: function () {
				let warehouse_type = frappe.query_report.get_filter_value("warehouse_type");
				let company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						...(warehouse_type && { warehouse_type }),
						...(company && { company }),
					},
				};
			},
		},
		{
			fieldname: "batch_no",
			label: __("Batch No"),
			fieldtype: "Link",
			options: "Batch",
			get_query: function () {
				let item_code = frappe.query_report.get_filter_value("item_code");
				return {
					filters: {
						item: item_code,
					},
				};
			},
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname == "Batch" && data && !!data["Batch"]) {
			value = data["Batch"];
			column.link_onclick =
				"frappe.query_reports['Batch-Wise Balance History'].set_batch_route_to_stock_ledger(" +
				JSON.stringify(data) +
				")";
		}

		value = default_formatter(value, row, column, data);
		return value;
	},
	set_batch_route_to_stock_ledger: function (data) {
		frappe.route_options = {
			batch_no: data["Batch"],
		};

		frappe.set_route("query-report", "Stock Ledger");
	},
};
function view_stock_leder_report(item_code, filter_company,from_date, to_date, batch_no) {
	let fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today());
	frappe.db.get_value("Fiscal Year", {"name": fiscal_year}, "year_start_date", function(value) {
	window.open(window.location.hostname + "app/query-report/Stock Ledger" + "?" + "company="  + filter_company + "&"  + "from_date=" + value.year_start_date + "&" + "to_date=" + to_date + "&" + "item_code=" + encodeURIComponent(item_code)  + "&" + "batch_no=" + batch_no,"_blank")
	// window.open(window.location.href.split('app')[0] + "app/query-report/Stock Ledger" + "?"  + "company= "  + filter_company +"&"  + "from_date=" + from_date + "&" + "to_date=" + to_date )
	// window.open(`/app/query-report/Stock Ledger/%3Fitem_code%3D${item_code}%26company%3D %26from_date%3D${from_date}%26to_date%3D${to_date}%26batch_no%3D${batch_no}`,"_blank")
	});
}