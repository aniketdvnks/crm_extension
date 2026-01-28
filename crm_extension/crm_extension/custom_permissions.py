import frappe

@frappe.whitelist()
def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return

	query = ''
	if "Branch Manager" in frappe.get_roles(user):
		query = f"""(`tabLead`.`custom_branch`!='')"""
		
	else:
		query = f"""(`tabLead`.`custom_branch`!='null' and `tabLead`.`lead_owner`={frappe.db.escape(user)})"""

	return query