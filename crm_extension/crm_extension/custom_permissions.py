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


def _get_user_roles(user: str) -> list[str]:
	if user == "Administrator":
		return ["Administrator"]
	user_doc = frappe.get_cached_doc("User", user)
	return [r.role for r in (user_doc.roles or [])]

def _get_allowed_branches(user: str) -> list[str]:
	branches = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Branch"},
		pluck="for_value",
	)
	return [b for b in branches if b]

def lead_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user

	if user == "Administrator":
		return ""

	roles = _get_user_roles(user)

	if "System Manager" in roles:
		return ""

	if "Branch Manager" in roles:
		allowed = _get_allowed_branches(user)

		if not allowed:
			return "1=0"

		allowed_sql = ", ".join(frappe.db.escape(b) for b in allowed)

		return f"""
			IFNULL(`tabLead`.`custom_branch`, '') != ''
			AND `tabLead`.`custom_branch` IN ({allowed_sql})
		"""

	elif "Relationship Manager" in roles:
		allowed = _get_allowed_branches(user)

		if not allowed:
			return "1=0"

		allowed_sql = ", ".join(frappe.db.escape(b) for b in allowed)
		user_escaped = frappe.db.escape(user)
		assign_like = frappe.db.escape(f'%"{user}"%')

		return f"""
			IFNULL(`tabLead`.`custom_branch`, '') != ''
			AND `tabLead`.`custom_branch` IN ({allowed_sql})
			AND (
				`tabLead`.`lead_owner` = {user_escaped}
				OR `tabLead`.`_assign` LIKE {assign_like}
			)
		"""

	return ""


# def lead_has_permission(doc, ptype=None, user=None) -> bool:
# 	"""
# 	Blocks opening/reading a Lead doc if Branch Manager doesn't have doc.custom_branch allowed
# 	or if custom_branch is empty.
# 	"""
# 	user = user or frappe.session.user

# 	if user == "Administrator":
# 		return True

# 	roles = _get_user_roles(user)
# 	if "System Manager" in roles:
# 		return True

# 	if "Branch Manager" in roles:
# 		allowed = _get_allowed_branches(user)

# 		# Must have a branch set
# 		if not getattr(doc, "custom_branch", None):
# 			return False

# 		# Must be in allowed branches
# 		return doc.custom_branch in allowed

# 	return True
import json

def lead_has_permission(doc, ptype=None, user=None) -> bool:
	"""
	Permission logic aligned with lead_permission_query_conditions:
	- Administrator / System Manager → full access
	- Branch Manager → only allowed branches (branch must exist)
	- Relationship Manager → allowed branches AND (owner OR assigned)
	"""

	user = user or frappe.session.user

	if user == "Administrator":
		return True

	roles = _get_user_roles(user)

	if "System Manager" in roles:
		return True

	# 🟢 Branch Manager Logic
	if "Branch Manager" in roles:
		allowed = _get_allowed_branches(user)

		if not getattr(doc, "custom_branch", None):
			return False

		return doc.custom_branch in allowed

	# 🔵 Relationship Manager Logic
	if "Relationship Manager" in roles:
		allowed = _get_allowed_branches(user)

		# ❌ No branch access → no permission
		if not allowed:
			return False

		# ❌ Branch must exist and be allowed
		if not getattr(doc, "custom_branch", None):
			return False

		if doc.custom_branch not in allowed:
			return False

		# ✔️ Owner check
		if doc.lead_owner == user:
			return True

		# ✔️ Assigned check (JSON field)
		assign_list = []
		if doc.get("_assign"):
			try:
				assign_list = json.loads(doc.get("_assign"))
			except Exception:
				assign_list = []

		if user in assign_list:
			return True

		# ❌ Not owner and not assigned
		return False

	return True