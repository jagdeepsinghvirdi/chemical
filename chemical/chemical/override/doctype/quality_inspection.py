import frappe
from erpnext.stock.doctype.quality_inspection.quality_inspection import QualityInspection as _QualityInspection # type: ignore

class QualityInspection(_QualityInspection):
	def set_child_row_reference(self):
		if self.child_row_reference:
			return
		if self.reference_type == "Inward Sample":
			return
		if not (self.reference_type and self.reference_name):
			return

		doctype = self.reference_type + " Item"
		if self.reference_type == "Stock Entry":
			doctype = "Stock Entry Detail"
   
		if self.reference_type == "Outward Sample":
				doctype = 'Outward Sample Detail'
    
		child_doc = frappe.qb.DocType(doctype)
		qi_doc = frappe.qb.DocType("Quality Inspection")

		child_row_references = (
			frappe.qb.from_(child_doc)
			.left_join(qi_doc)
			.on(child_doc.name == qi_doc.child_row_reference)
			.select(child_doc.name)
			.where(
				(child_doc.item_code == self.item_code)
				& (child_doc.parent == self.reference_name)
				& (child_doc.docstatus < 2)
				& (qi_doc.name.isnull())
			)
			.orderby(child_doc.idx)
		).run(pluck=True)

		if len(child_row_references):
			self.child_row_reference = child_row_references[0]
	def update_qc_reference(self,remove_reference=False):
		quality_inspection = self.name if self.docstatus == 1 else ""

		if self.reference_type == "Job Card":
			if self.reference_name:
				frappe.db.sql(
					f"""
					UPDATE `tab{self.reference_type}`
					SET quality_inspection = %s, modified = %s
					WHERE name = %s and production_item = %s
				""",
					(quality_inspection, self.modified, self.reference_name, self.item_code),
				)
		elif self.reference_type == "Inward Sample":
			if self.reference_name:
				frappe.db.sql(
					f"""
					UPDATE `tab{self.reference_type}`
					SET quality_inspection = %s, modified = %s
					WHERE name = %s
				""",
					(quality_inspection, self.modified, self.reference_name),
				)

		else:
			args = [quality_inspection, self.modified, self.reference_name, self.item_code]
			doctype = self.reference_type + " Item"

			if self.reference_type == "Stock Entry":
				doctype = "Stock Entry Detail"

			if self.reference_type == "Outward Sample":
				doctype = 'Outward Sample Detail'

			if self.reference_type == "Inward Sample":
				doctype = 'Inward Sample'
				
			

			if self.reference_type and self.reference_name:
				conditions = ""
				if self.batch_no and self.docstatus == 1:
					conditions += " and t1.batch_no = %s"
					args.append(self.batch_no)

				if self.ref_item:
					conditions += " and t1.name = %s"
					args.append(self.ref_item)
				
				if self.docstatus == 2:  # if cancel, then remove qi link wherever same name
					conditions += " and t1.quality_inspection = %s"
					args.append(self.name)
				

				frappe.db.sql(
					f"""
					UPDATE
						`tab{doctype}` t1, `tab{self.reference_type}` t2
					SET
						t1.quality_inspection = %s, t2.modified = %s
					WHERE
						t1.parent = %s
						and t1.item_code = %s
						and t1.parent = t2.name
						{conditions}
				""",
					args,
				)