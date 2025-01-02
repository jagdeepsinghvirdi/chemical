# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import re
import json
from frappe.utils import get_url

#getting all report data
report_data=[]
# getting dynamic column value
dyanmic_column=[]


# function to clean string for names in coloumn
def clean_string(string):
    if string:
        string = string.replace(" ", "_")
        string = string.lower()
        string = re.sub('[^A-Za-z0-9_]+', '', string)
    return string

def execute(filters=None):
    if not filters: filters = {}
    from_date = filters.get("from_date", None)
    to_date = filters.get("to_date", None)

    if from_date and to_date:
        if from_date > to_date:
            frappe.throw(_("From Date cannot be less than To Date"))

    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data

def get_columns(filters):
    columns = [
        {"label": _("Name"), "fieldname": "name", "fieldtype": "Link", "options": "Work Order", "width": 150},
        {"label": _("Date"), "fieldname": "planned_start_date", "fieldtype": "Date", "width": 150},
        {"label": _("Lot No"), "fieldname": "lot_no", "fieldtype": "Data", "width": 120},
        {"label": _("Per Unit Price"), "fieldname": "per_unit_price", "fieldtype": "Data", "width": 100},
        {"label": _("Basic Rate"), "fieldname": "basic_rate", "fieldtype": "Float", "width": 100},
        # {"label": _("Qty To Manufacture"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": _("As is Qty"), "fieldname": "produced_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Manufactured Qty"), "fieldname": "real_produced_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Yield"), "fieldname": "batch_yield", "fieldtype": "Percent", "width": 80},
    ]

    # append dynamic columns for item used for Manufacturing
    data = column_query(filters)
    if data:
        columns.append({"label": _("{}".format(data[0][1])), "fieldname": str(clean_string(data[0][1])), "fieldtype": "Float", "width": 100})
    for d in data:
        if d[0] != d[1]:
            x = {"label": _("{}".format(d[0])), "fieldname": str(clean_string(d[0])), "fieldtype": "Float", "width": 100}
            columns.append(x)

    # columns += [
    # 	# {"label": _("Concentration / Purity"), "fieldname": "concentration", "fieldtype": "Percent", "width": 100},
    # 	# {"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 80},
    # ]

    global dyanmic_column
    dyanmic_column=columns

    return columns


def get_data(filters):
    global report_data
    data = data_query(filters)
    report_data=data
    return data

def column_query(filters):
    # get production item from filters
    production_item = re.escape(filters.get("production_item", ""))
    conditions = ''
    if filters.get("from_date"):		
        conditions += "AND DATE(wo.planned_start_date) >= '{}' \n".format(str(filters.get("from_date")))
        
    if filters.get("to_date"):
        conditions += "AND DATE(wo.planned_start_date) <= '{}' \n".format(str(filters.get("to_date")))

    if re.escape(filters.get("company","")):
        conditions += "AND wo.company = '{}' \n".format(re.escape(filters.get("company","")))

    # Getting dynamic column name
    column = frappe.db.sql("""SELECT item_code,based_on from `tabWork Order Item` as woi
    LEFT JOIN `tabWork Order` as wo ON woi.parent = wo.name 
    WHERE `production_item` = '{}' {}
    GROUP BY item_code
    ORDER BY woi.idx
    """.format(production_item,conditions)
    )


    return column

def data_query(filters):
    # getting data from filters
    production_item = re.escape(filters.get("production_item", ""))
    company = re.escape(filters.get("company", ""))
    from_date = filters.get("from_date", None)
    to_date = filters.get("to_date", None)
    finish_quantity=filters.get("finish_quantity",None)
    
    # adding where condition according to filters
    condition = ''
    format_ = '%Y-%m-%d %H:%M:%S'
    if from_date:		
        condition += 'AND ' if condition != '' else 'WHERE '
        condition += "DATE(wo.planned_start_date) >= '{}' \n".format(str(from_date))
        
    if to_date:
        condition += 'AND ' if condition != '' else 'WHERE '
        condition += "DATE(wo.planned_start_date) <= '{}' \n".format(str(to_date))

    if production_item:
        condition += 'AND ' if condition != '' else 'WHERE '
        condition += "wo.production_item = '{}' \n".format(production_item)
    
    if company:
        condition += 'AND ' if condition != '' else 'WHERE '
        condition += "wo.company = '{}' \n".format(company)
    
    # sql query to get data for column
    data = frappe.db.sql("""SELECT 
    wo.planned_start_date, 
    wo.name,
    wo.qty,
    wo.lot_no,
    se.total_additional_costs,
    sum(sed.basic_rate),
    wo.produced_qty,
    wo.produced_quantity,
    wo.concentration,
    wo.valuation_rate,
    wo.batch_yield
    FROM  `tabWork Order Item` as woi
    LEFT JOIN `tabWork Order` as wo ON woi.parent = wo.name 
    LEFT JOIN `tabStock Entry` as se ON se.work_order = wo.name
    LEFT JOIN `tabStock Entry Detail` as sed ON sed.parent = se.name
    {}
    and wo.docstatus = 1 and se.purpose = 'Manufacture'
    GROUP BY wo.name
    """.format(condition), as_dict=1)

    # sub query to find transferred quantity of item used for manufacturing
    for item in data:
        # frappe.msgprint(str(item))
        if finish_quantity is not None:
            item['per_unit_price'] = item['total_additional_costs'] * finish_quantity
        produced_qty = item.get('produced_qty', 0)
        concentration = item.get('concentration', 0)
        name = item.get('name', '')
        if finish_quantity is not None:
            if produced_qty != 0 and concentration != 0:
             item['produced_qty']= (item['produced_qty']*finish_quantity)/(produced_qty * (concentration / 100))
            else:
                item['produced_qty']=0

        # frappe.msgprint(name)
        sub_data = frappe.db.sql("""SELECT 
        item_code,transferred_qty 
        FROM `tabWork Order Item` 
        WHERE parent = '{}'""".format(name))

        if finish_quantity is not None:
            for key, value in sub_data:
                key = clean_string(key)
                if produced_qty != 0 and concentration != 0:
                  item[key] = (value*finish_quantity)/(produced_qty * (concentration / 100))
                else:
                    item[key]=0

        else:
            for key, value in sub_data:
                key = clean_string(key)
                item[key] = value
        
        # calculating real manufacturing quantity
        if finish_quantity is None:
           item['real_produced_qty'] = produced_qty * (concentration / 100)
        else:
            item['real_produced_qty']=finish_quantity


    return data

def convert_to_float(value):
    try:
        return float(value.replace(',', '').strip()) if value else 0.0
    except ValueError:
        return 0.0


#create bom for all selecting row
@frappe.whitelist()
def create_bom_for_all_row(doc,productionItemValue,finish_quantity, rm_cost_as_per, price_list = None):
    global report_data
    # removing unselected data for all selecting all row

    filtered_list = [d for d in report_data if d['name'] not in doc]
    list_length=len(filtered_list)
    new_dict={}
    #filtering the specific field
    key_list=['planned_start_date','lot_no',"Manufactured Qty", 'name','qty', 'produced_qty','produced_quantity','concentration','valuation_rate','batch_yield']
    for dict in filtered_list:
        for key,value in dict.items():
            if key not in key_list:
                if value!=0.000:
                    if key in new_dict:
                        new_dict[key]+=value
                    else:
                        new_dict[key]=value
    # Round the values to 3 decimal places
    for key in new_dict:
        new_dict[key] = round(new_dict[key], 3)

    # global dyanmic_column
    global dyanmic_column
    


    # Create a new dictionary with updated values
    updated_l2 = {}
    for l1_item in dyanmic_column:
        fieldname = l1_item['fieldname']
        if fieldname in new_dict.keys():
            label_name=l1_item['label']
            updated_l2[label_name] = new_dict[fieldname]

    # removing unwanted key
    if 'Manufactured Qty' in updated_l2:
        updated_l2.pop('Manufactured Qty')


    if(len(updated_l2)==0):
        frappe.throw("you have not permission to create Bom because of all item value is zero")
    for key,value in updated_l2.items():
        updated_l2[key]/=list_length

    # code for creating bom
    bom_items=[]
    for key,value in updated_l2.items():
        item_dict={}
        item_dict["item_code"]=key
        item_dict["qty"]=value
        bom_items.append(item_dict)
    # Create a new BOM document
    new_bom = frappe.get_doc({
        "doctype": "BOM",
        "item": productionItemValue,
        "quantity": int(finish_quantity),
        "is_multiple_item": 0,
        "rm_cost_as_per": rm_cost_as_per,
        "price_list": price_list,
        "items": bom_items
    })
    new_bom.flags.ignore_mandatory = True
    new_bom.flags.ignore_permissions = True
    # Insert the BOM document into the database
    new_bom.insert()
    bom_url = get_url("/app/bom/" + new_bom.name)
    message = f"BOM  <strong><a href='{bom_url}'>{new_bom.name}</a></strong>  Created  from {list_length} Work Order"
    frappe.msgprint(_(message))
    return "Successful"

# work only for selecting some row
@frappe.whitelist()
def create_bom(doc,productionItemValue,finish_quantity, rm_cost_as_per, price_list = None):
    json_obj=json.loads(doc)
    new_dict={}
    list_length=len(json_obj)
    key_list=["","As is Qty","Date","Lot No","Manufactured Qty","Name","Yield"]
    for dict in json_obj:
        for key,value in dict.items():
            if key not in key_list:
                if value!='0.000':
                    if key in new_dict:
                        new_dict[key]+=convert_to_float(value)
                    else:
                        new_dict[key]=convert_to_float(value)
    if(len(new_dict)==0):
        frappe.throw("you have not permission to create Bom because of all item value is zero")
    for key,value in new_dict.items():
        new_dict[key]/=list_length

    # code for creating bom
    bom_items=[]
    for key,value in new_dict.items():
        item_dict={}
        item_dict["item_code"]=key
        item_dict["qty"]=value
        bom_items.append(item_dict)
    new_bom = frappe.get_doc({
        "doctype": "BOM",
        "item": productionItemValue,
        "quantity": int(finish_quantity),
        "is_multiple_item": 0,
        "rm_cost_as_per": rm_cost_as_per,
        "price_list": price_list,
        "items": bom_items
    })
    new_bom.flags.ignore_mandatory = True
    new_bom.flags.ignore_permissions = True
    # Insert the BOM document into the database
    new_bom.insert()
    bom_url = get_url("/app/bom/" + new_bom.name)
    message = f"BOM  <strong><a href='{bom_url}'>{new_bom.name}</a></strong>  Created  from {list_length} Work Order"
    frappe.msgprint(_(message))
    return "Successful"
                       