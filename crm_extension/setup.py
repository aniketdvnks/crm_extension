import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	create_custom_fields(get_custom_fields(), ignore_validate=True)
	# run_post_install_patches()

def get_custom_fields():
	return {
		"Lead": [
					{
						"fieldname": 'branch',
						"label": 'Branch',
						"fieldtype": "Link",
						"options": 'Branch',
						"insert_after": 'last_name',
						"owner": "Administrator",
					}
				]
			}

# def get_post_install_patches():
# 	return (
# 		"crm_extention.patches.v15.create_custom_fields_in_lead"
# 		)
# def run_post_install_patches():
# 	print("\nPatching Existing Data...")

# 	POST_INSTALL_PATCHES = get_post_install_patches()
# 	frappe.flags.in_patch = True

# 	try:
# 		for patch in POST_INSTALL_PATCHES:
# 			patch_name = patch.split(".")[-1]
# 			if not patch_name:
# 				continue

# 			frappe.get_attr(f"hrms.patches.post_install.{patch_name}.execute")()
# 	finally:
# 		frappe.flags.in_patch = False