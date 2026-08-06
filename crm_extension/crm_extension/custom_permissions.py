import json

import frappe


SYSTEM_ROLES = {"System Manager"}

TELECALLER_ROLES = {"Tele Caller", "Telecaller","Sales User"}
BRANCH_ACCESS_ROLES = {"Branch Manager", "Stake Holder", "Stakeholder"}
WEALTH_MANAGER_ROLES = {
	"Relationship Manager",
	"Wealth Relationship Manager",
	"Wealth Realtionship Manager",
}

LEAD_ACCESS_ROLES = TELECALLER_ROLES | BRANCH_ACCESS_ROLES | WEALTH_MANAGER_ROLES

# Roles that may see every lead when they hold a Head Quarter branch permission.
HEADQUARTER_BYPASS_ROLES = TELECALLER_ROLES | BRANCH_ACCESS_ROLES

# Holding any of these disqualifies a user from the Head Quarter bypass, whatever
# else they carry: two Relationship Managers must never see each other's leads,
# even in the same branch. This is a subtraction rather than an omission from
# HEADQUARTER_BYPASS_ROLES on purpose — every RM also holds Sales User, so
# widening the bypass set would otherwise hand them blanket access again.
HEADQUARTER_BYPASS_EXCLUDED_ROLES = WEALTH_MANAGER_ROLES

# Keep these names in sync with the Branch records used for head office users.
HEADQUARTER_BRANCHES = {
	"Head Quarter",
	"Head Quarters",
	"Headquarter",
	"Headquarters",
	"Head Office",
	"HQ",
	"HO",
}

LEAD = "`tabLead`"


def get_permission_query_conditions(user=None, doctype=None):
	"""Backward-compatible wrapper if this method is referenced directly."""
	return lead_permission_query_conditions(user=user, doctype=doctype)


def lead_permission_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user

	if user == "Administrator":
		return ""

	roles = _get_user_roles(user)
	if roles & SYSTEM_ROLES:
		return ""

	if not (roles & LEAD_ACCESS_ROLES):
		return "1=0"

	allowed_branches = _get_allowed_branches(user)
	if _has_headquarter_access(roles, allowed_branches):
		return ""

	conditions = []

	if roles & TELECALLER_ROLES:
		conditions.append(_user_owned_condition(user))

	if roles & BRANCH_ACCESS_ROLES:
		branch_condition = _branch_condition(allowed_branches)
		if branch_condition:
			conditions.append(branch_condition)
		conditions.append(_own_unbranched_condition(user))

	if roles & WEALTH_MANAGER_ROLES:
		conditions.append(_wealth_manager_condition(user))

	conditions = [condition for condition in conditions if condition]
	if not conditions:
		return "1=0"

	return "(" + " OR ".join(f"({condition})" for condition in conditions) + ")"


def lead_has_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user

	if user == "Administrator":
		return True

	roles = _get_user_roles(user)
	if roles & SYSTEM_ROLES:
		return True

	if not (roles & LEAD_ACCESS_ROLES):
		return False

	allowed_branches = _get_allowed_branches(user)
	if _has_headquarter_access(roles, allowed_branches):
		return True

	if doc.is_new():
		return _can_create_doc(doc, user, roles, allowed_branches)

	return _can_access_existing_doc(doc, user, roles, allowed_branches)


def _get_user_roles(user):
	return set(frappe.get_roles(user) or [])


def _get_allowed_branches(user):
	permissions = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Branch"},
		fields=["for_value", "applicable_for"],
	)

	return {
		permission.for_value
		for permission in permissions
		if permission.for_value and permission.applicable_for in (None, "", "Lead")
	}


def _has_headquarter_access(roles, allowed_branches):
	if roles & HEADQUARTER_BYPASS_EXCLUDED_ROLES:
		return False

	return bool(roles & HEADQUARTER_BYPASS_ROLES) and any(
		_is_headquarter_branch(branch) for branch in allowed_branches
	)


def _is_headquarter_branch(branch):
	normalized = str(branch or "").strip().casefold().replace("-", " ").replace("_", " ")
	headquarter_names = {
		branch.casefold().replace("-", " ").replace("_", " ")
		for branch in HEADQUARTER_BRANCHES
	}
	return normalized in headquarter_names


def _branch_condition(allowed_branches):
	if not allowed_branches:
		return ""

	allowed_sql = ", ".join(frappe.db.escape(branch) for branch in sorted(allowed_branches))
	return f"IFNULL({LEAD}.`custom_branch`, '') != '' AND {LEAD}.`custom_branch` IN ({allowed_sql})"


def _user_owned_condition(user):
	user_sql = frappe.db.escape(user)
	return f"({LEAD}.`lead_owner` = {user_sql} OR {LEAD}.`owner` = {user_sql})"


def _assigned_condition(user):
	return f"{LEAD}.`_assign` LIKE {frappe.db.escape(f'%\"{user}\"%')}"


def _own_unbranched_condition(user):
	return (
		f"{LEAD}.`owner` = {frappe.db.escape(user)} "
		f"AND IFNULL({LEAD}.`custom_branch`, '') = ''"
	)


def _wealth_manager_condition(user):
	"""A Relationship Manager sees only leads they own, created, or are assigned.

	Branch is deliberately not part of this: two RMs in the same branch must not
	see each other's leads, and most leads carry no branch at all.
	"""
	return " OR ".join(
		f"({condition})"
		for condition in (
			f"{LEAD}.`lead_owner` = {frappe.db.escape(user)}",
			f"{LEAD}.`owner` = {frappe.db.escape(user)}",
			_assigned_condition(user),
		)
	)


def _can_create_doc(doc, user, roles, allowed_branches):
	if roles & TELECALLER_ROLES:
		return not doc.get("lead_owner") or doc.get("lead_owner") == user

	branch = doc.get("custom_branch")
	if not branch:
		return True

	return branch in allowed_branches


def _can_access_existing_doc(doc, user, roles, allowed_branches):
	if roles & TELECALLER_ROLES and _is_user_owned_doc(doc, user):
		return True

	branch = doc.get("custom_branch")

	if roles & BRANCH_ACCESS_ROLES:
		if branch and branch in allowed_branches:
			return True
		if not branch and doc.get("owner") == user:
			return True

	if roles & WEALTH_MANAGER_ROLES:
		if _is_user_owned_doc(doc, user) or _is_user_assigned_doc(doc, user):
			return True

	return False


def _is_user_owned_doc(doc, user):
	return doc.get("lead_owner") == user or doc.get("owner") == user


def _is_user_assigned_doc(doc, user):
	assign_list = []
	if doc.get("_assign"):
		try:
			assign_list = json.loads(doc.get("_assign"))
		except (TypeError, ValueError):
			assign_list = []

	return user in assign_list
