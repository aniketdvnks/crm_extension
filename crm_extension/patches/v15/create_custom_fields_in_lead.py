
def execute():
    df = {
        "fieldname": 'custom_branch',
        "label": 'Branch',
        "fieldtype": "Link",
        "options": 'Branch',
        "insert_after": 'last_name',
        "owner": "Administrator",
    }
    create_custom_field(doctype, df, ignore_validate=True)