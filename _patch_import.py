"""
One-shot patch: fix the customer Excel import flow in customers/views.py.

Issues fixed:
1. ``date.strptime()`` does not exist -> every row failed date parsing with
   "type object 'datetime.date' has no attribute 'strptime'" and landed in
   errors, so valid_rows was always empty.
2. The preview stored ``date`` objects and model instances (SalesPerson,
   User) which cannot be JSON-serialized by Django's session serializer ->
   would 500 once dates parsed. Dates are stored as ISO strings and the
   sales person by pk + name.
3. ``total_rows`` double counted duplicates -> uses real processed-row count.
4. ``confirm_import`` reconstructs proper values from the JSON-safe preview.
"""
import io

BASE = r'c:\Users\flp\Documents\Codex\customer'
PATH = BASE + r'\customers\views.py'

text = io.open(PATH, 'r', encoding='utf-8').read()
original = text


def replace(old, new, count_expected=1):
    global text
    n = text.count(old)
    assert n == count_expected, \
        "Expected %d occurrence(s) of:\n%s\n\nFound %d" % (count_expected, old, n)
    text = text.replace(old, new)
    print("OK (%d): %s" % (n, old.splitlines()[0][:80]))


# 1. Import datetime class alongside date
replace(
    'from datetime import date\n',
    'from datetime import date, datetime\n',
)

# 2. Fix parse_date to use datetime.strptime() and normalise datetime cells
replace(
    """                def parse_date(val):
                    if not val:
                        return None
                    if isinstance(val, date):
                        return val
                    if isinstance(val, str):
                        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
                            try:
                                return date.strptime(val.strip(), fmt)
                            except ValueError:
                                continue
                    return None""",
    """                def parse_date(val):
                    if not val:
                        return None
                    if isinstance(val, datetime):
                        return val.date()
                    if isinstance(val, date):
                        return val
                    if isinstance(val, str):
                        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
                            try:
                                return datetime.strptime(val.strip(), fmt).date()
                            except ValueError:
                                continue
                    return None""",
)

# 3. Track the real number of non-empty data rows
replace(
    """        valid_rows = []
        errors = []
        duplicates = 0
        seen_names = set()      # Track within-file duplicates""",
    """        valid_rows = []
        errors = []
        duplicates = 0
        row_count = 0
        seen_names = set()      # Track within-file duplicates""",
)

replace(
    """            if not any(row):
                continue
            
            try:""",
    """            if not any(row):
                continue
            row_count += 1

            try:""",
)

# 4. Store only JSON-safe values in the session preview
replace(
    """                valid_rows.append({
                    'company_name': company_name,
                    'trade_license_number': trade_license or None,
                    'trade_license_expiry': trade_license_expiry,
                    'passport_number': str(row[col_indices.get('passport_number')] or '').strip() if 'passport_number' in col_indices else '',
                    'passport_expiry': passport_expiry,
                    'eid_number': str(row[col_indices.get('eid_number')] or '').strip() if 'eid_number' in col_indices else '',
                    'eid_expiry': eid_expiry,
                    'trn': trn or None,
                    'sales_person': sales_person,
                    'customer_status': Customer.CustomerStatus.ACTIVE,
                    'created_by': request.user,
                    'updated_by': request.user,
                })""",
    """                valid_rows.append({
                    'company_name': company_name,
                    'trade_license_number': trade_license or None,
                    'trade_license_expiry': trade_license_expiry.isoformat() if trade_license_expiry else None,
                    'passport_number': str(row[col_indices.get('passport_number')] or '').strip() if 'passport_number' in col_indices else '',
                    'passport_expiry': passport_expiry.isoformat() if passport_expiry else None,
                    'eid_number': str(row[col_indices.get('eid_number')] or '').strip() if 'eid_number' in col_indices else '',
                    'eid_expiry': eid_expiry.isoformat() if eid_expiry else None,
                    'trn': trn or None,
                    'sales_person_pk': sales_person.pk if sales_person else None,
                    'sales_person_name': sales_person.name if sales_person else '',
                    'customer_status': Customer.CustomerStatus.ACTIVE,
                })""",
)

# 5. total_rows = actual processed rows
replace(
    """        request.session['import_preview'] = {
            'valid_rows': valid_rows,
            'errors': errors,
            'duplicates': duplicates,
            'total_rows': len(valid_rows) + duplicates + len(errors),
        }""",
    """        request.session['import_preview'] = {
            'valid_rows': valid_rows,
            'errors': errors,
            'duplicates': duplicates,
            'total_rows': row_count,
        }""",
)

# 6. Reconstruct model values from the JSON-safe preview on confirm
replace(
    """    def confirm_import(self, request, preview):
        created_count = 0
        for row_data in preview['valid_rows']:
            try:
                customer = Customer.objects.create(**row_data)
                customer.update_copy_status()""",
    """    def confirm_import(self, request, preview):
        created_count = 0
        for row_data in preview['valid_rows']:
            try:
                # Rebuild values from the JSON-safe data stored in the session
                data = {
                    'company_name': row_data['company_name'],
                    'trade_license_number': row_data.get('trade_license_number') or None,
                    'trade_license_expiry': date.fromisoformat(row_data['trade_license_expiry']) if row_data.get('trade_license_expiry') else None,
                    'passport_number': row_data.get('passport_number') or '',
                    'passport_expiry': date.fromisoformat(row_data['passport_expiry']) if row_data.get('passport_expiry') else None,
                    'eid_number': row_data.get('eid_number') or '',
                    'eid_expiry': date.fromisoformat(row_data['eid_expiry']) if row_data.get('eid_expiry') else None,
                    'trn': row_data.get('trn') or None,
                    'sales_person': SalesPerson.objects.filter(pk=row_data.get('sales_person_pk')).first() if row_data.get('sales_person_pk') else None,
                    'customer_status': row_data.get('customer_status', Customer.CustomerStatus.ACTIVE),
                    'created_by': request.user,
                    'updated_by': request.user,
                }
                customer = Customer.objects.create(**data)
                customer.update_copy_status()""",
)

assert text != original
io.open(PATH, 'wb').write(
    text.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8')
)
print('EXCEL-IMPORT PATCH APPLIED')