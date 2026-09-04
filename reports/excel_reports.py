"""
Excel report generation utilities.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, numbers
from openpyxl.utils import get_column_letter
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date, datetime, time, timedelta
from io import BytesIO


class ExcelReportGenerator:
    """Generate Excel reports for customer records."""
    
    def __init__(self, title='Customer Report'):
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = 'Report'
        self.title = title
        self.current_row = 1
        
        # Styles
        self.header_font = Font(bold=True, color='FFFFFF', size=11)
        self.header_fill = PatternFill(start_color='1F2937', end_color='1F2937', fill_type='solid')
        self.header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        self.title_font = Font(bold=True, size=14, color='1F2937')
        self.subtitle_font = Font(size=10, color='6B7280')
        self.data_font = Font(size=10)
        self.data_alignment = Alignment(vertical='center', wrap_text=True)
        self.thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin'),
        )
        self.currency_format = '#,##0.00'
        self.date_format = 'YYYY-MM-DD'
        self.header_row = None
    
    def _coerce(self, value):
        """Coerce a value to a type openpyxl can bind to a cell.

        Lazy translation proxies (e.g. ``gettext_lazy``) are string-like but
        not ``str``, which makes openpyxl raise ``TypeError: Cannot convert
        ... to Excel``. Leave numbers, booleans, dates, ``None`` and plain
        strings untouched; coerce anything else that should be textual.
        """
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        if isinstance(value, (datetime, date, time, timedelta)):
            return value
        # Lazy translation proxies / other string-like objects.
        return str(value)
    
    def add_title(self, title=None, subtitle=None):
        """Add report title and subtitle."""
        title = title or self.title
        self.ws.merge_cells(start_row=self.current_row, start_column=1, end_row=self.current_row, end_column=15)
        cell = self.ws.cell(row=self.current_row, column=1, value=title)
        cell.font = self.title_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        self.current_row += 1
        
        if subtitle:
            self.ws.merge_cells(start_row=self.current_row, start_column=1, end_row=self.current_row, end_column=15)
            cell = self.ws.cell(row=self.current_row, column=1, value=subtitle)
            cell.font = self.subtitle_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            self.current_row += 1
        
        # Generation info
        gen_info = _('Generated: {}').format(timezone.now().strftime('%d %b %Y %H:%M'))
        self.ws.merge_cells(start_row=self.current_row, start_column=1, end_row=self.current_row, end_column=15)
        cell = self.ws.cell(row=self.current_row, column=1, value=gen_info)
        cell.font = self.subtitle_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        self.current_row += 2
    
    def add_summary(self, summary_data):
        """Add summary statistics section."""
        self.ws.merge_cells(start_row=self.current_row, start_column=1, end_row=self.current_row, end_column=15)
        # _('Summary') is a lazy translation proxy; openpyxl can only bind plain
        # values, so coerce it (and any lazy labels/values) to a real string
        # with str() before writing to the cell.
        cell = self.ws.cell(row=self.current_row, column=1, value=str(_('Summary')))
        cell.font = Font(bold=True, size=12, color='1F2937')
        self.current_row += 1
        
        for label, value in summary_data.items():
            self.ws.cell(row=self.current_row, column=1, value=str(label)).font = Font(bold=True, size=10)
            self.ws.cell(row=self.current_row, column=2, value=self._coerce(value)).font = self.data_font
            self.current_row += 1
        
        self.current_row += 1
    
    def add_headers(self, headers):
        """Add column headers."""
        for col, header in enumerate(headers, 1):
            cell = self.ws.cell(row=self.current_row, column=col, value=header)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = self.header_alignment
            cell.border = self.thin_border
        self.header_row = self.current_row
        self.current_row += 1
    
    def add_row(self, data, row_style=None):
        """Add a data row."""
        for col, value in enumerate(data, 1):
            cell = self.ws.cell(row=self.current_row, column=col, value=value)
            cell.font = self.data_font
            cell.alignment = self.data_alignment
            cell.border = self.thin_border
            
            # Format dates
            if isinstance(value, date):
                cell.number_format = self.date_format
            
            # Apply custom row style if provided
            if row_style:
                for key, val in row_style.items():
                    setattr(cell, key, val)
        
        self.current_row += 1
    
    def set_column_widths(self, widths):
        """Set column widths."""
        for i, width in enumerate(widths, 1):
            self.ws.column_dimensions[get_column_letter(i)].width = width
    
    def freeze_header(self):
        """Freeze the header row.

        Freeze everything up to and including the column header row (title,
        summary and headers) so the header stays visible while scrolling data.
        """
        # The row one below the header (the first data row) is the freeze
        # anchor; rows above it remain pinned. Fall back to the current row if
        # no headers were written.
        row = (self.header_row + 1) if self.header_row else self.current_row
        self.ws.freeze_panes = f'A{row}'
    
    def add_auto_filter(self, num_cols, num_rows):
        """Add auto filter to headers."""
        self.ws.auto_filter.ref = f'A1:{get_column_letter(num_cols)}{num_rows}'
    
    def set_print_options(self):
        """Set print options for the worksheet."""
        self.ws.sheet_properties.pageSetUpPr = None
        self.ws.page_setup.orientation = 'landscape'
        self.ws.page_setup.fitToWidth = 1
        self.ws.page_setup.fitToHeight = 0
        self.ws.print_title_rows = '1:1'  # Repeat header row
        self.ws.page_margins.left = 0.25
        self.ws.page_margins.right = 0.25
        self.ws.page_margins.top = 0.5
        self.ws.page_margins.bottom = 0.5
    
    def get_response(self, filename=None):
        """Get HTTP response with the Excel file."""
        if not filename:
            filename = f'{self.title.lower().replace(" ", "_")}_{date.today()}.xlsx'
        
        output = BytesIO()
        self.wb.save(output)
        output.seek(0)
        
        from django.http import HttpResponse
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


def _sanitize_filename_component(name):
    """Sanitize a name for safe use inside a Windows filename.

    Removes characters that are illegal on Windows: / \\ : * ? " < > |.
    """
    invalid_chars = '/\\:*?"<>|'
    for ch in invalid_chars:
        name = name.replace(ch, '_')
    return name.strip().replace(' ', '_')


def generate_customer_excel_report(queryset, title='Customer Compliance Report', filters=None, user=None, sales_person=None):
    """Generate a professional customer compliance Excel report.

    The report follows the KB Remicon corporate design: a clean white
    worksheet with dark-navy accents, a branded header block, a simple
    summary, the filter summary, the main customer table (navy header,
    subtle status colouring), notes and a footer line.

    ``queryset`` is the already-filtered Customer queryset; ``filters`` is a
    flat dict of applied GET filters; ``user`` is the authenticated request
    user (used for 'Generated By'); ``sales_person`` is the selected
    SalesPerson object or ``None`` for 'All Sales Persons'.
    """
    return _build_compliance_workbook(queryset, title, filters, user, sales_person)


def _build_compliance_workbook(queryset, title, filters, user, sales_person=None):
    """Build the professionally styled KB Remicon compliance workbook."""
    ws = Workbook().active
    ws.title = 'Customer Compliance Report'

    # ------------------------------------------------------------------
    # Shared styles and constants
    # ------------------------------------------------------------------
    NAVY = '1F2937'
    WHITE = 'FFFFFF'
    DARK_TEXT = '111827'
    GRAY_TEXT = '6B7280'
    BORDER_COLOR = 'D1D5DB'

    thin_side = Side(style='thin', color=BORDER_COLOR)
    thin_border = Border(
        left=thin_side, right=thin_side, top=thin_side, bottom=thin_side
    )
    navy_fill = PatternFill(start_color=NAVY, end_color=NAVY, fill_type='solid')
    white_fill = PatternFill(start_color=WHITE, end_color=WHITE, fill_type='solid')
    gray_fill = PatternFill(start_color='F3F4F6', end_color='F3F4F6', fill_type='solid')

    # Status palette (subtle, print-friendly)
    STATUS_FILLS = {
        'complete': PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid'),
        'partial': PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid'),
        'missing': PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid'),
        'received': PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid'),
        'not_received': PatternFill(start_color='F3F4F6', end_color='F3F4F6', fill_type='solid'),
        'pending': PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid'),
        'returned': PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid'),
    }
    STATUS_FONTS = {
        'complete': Font(name='Calibri', size=10, color='166534', bold=True),
        'partial': Font(name='Calibri', size=10, color='92400E', bold=True),
        'missing': Font(name='Calibri', size=10, color='991B1B', bold=True),
        'received': Font(name='Calibri', size=10, color='166534', bold=True),
        'not_received': Font(name='Calibri', size=10, color='374151', bold=True),
        'pending': Font(name='Calibri', size=10, color='92400E', bold=True),
        'returned': Font(name='Calibri', size=10, color='991B1B', bold=True),
    }

    NUM_COLS = 15
    last_col = get_column_letter(NUM_COLS)
    row = 1

    # ------------------------------------------------------------------
    # 1. Report header block
    # ------------------------------------------------------------------
    # Left column: branding
    ws.merge_cells('A1:C1')
    ws.merge_cells('A2:C2')
    brand_cell = ws.cell(row=1, column=1, value='KB REMICON')
    brand_cell.font = Font(name='Calibri', size=16, bold=True, color=NAVY)
    brand_cell.alignment = Alignment(horizontal='left', vertical='center')
    ws.cell(row=2, column=1, value='CUSTOMER RECORD').font = Font(
        name='Calibri', size=11, bold=True, color=GRAY_TEXT
    )
    ws.cell(row=2, column=1).alignment = Alignment(horizontal='left', vertical='center')

    # Center column: title
    ws.merge_cells('E1:J1')
    ws.merge_cells('E2:J2')
    title_cell = ws.cell(row=1, column=5, value='KB REMICON CUSTOMER RECORD')
    title_cell.font = Font(name='Calibri', size=14, bold=True, color=NAVY)
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=2, column=5, value='CUSTOMER COMPLIANCE REPORT')
    ws.cell(row=2, column=5).font = Font(name='Calibri', size=10, color=GRAY_TEXT)
    ws.cell(row=2, column=5).alignment = Alignment(horizontal='center', vertical='center')

    # Sales Person subtitle directly under the main title (row 3, center).
    selected_name = sales_person.name if sales_person else 'All Sales Persons'
    ws.merge_cells(start_row=3, start_column=5, end_row=3, end_column=11)
    sp_sub = ws.cell(row=3, column=5, value=f'Sales Person: {selected_name}')
    sp_sub.font = Font(name='Calibri', size=9, italic=True, color=GRAY_TEXT)
    sp_sub.alignment = Alignment(horizontal='center', vertical='center')

    # Right column: report metadata
    ws.merge_cells('L1:O1')
    ws.merge_cells('L2:O2')
    meta_cell_1 = ws.cell(row=1, column=12, value='Report Type     : Customer')
    meta_cell_1.font = Font(name='Calibri', size=9, color=DARK_TEXT)
    meta_cell_1.alignment = Alignment(horizontal='right', vertical='center')

    generated_by = user.get_full_name() if user and user.is_authenticated else ''
    if not generated_by and user:
        generated_by = user.get_username()
    meta_cell_2 = ws.cell(row=2, column=12, value=f'Generated By    : {generated_by}')
    meta_cell_2.font = Font(name='Calibri', size=9, color=DARK_TEXT)
    meta_cell_2.alignment = Alignment(horizontal='right', vertical='center')

    generated_on = timezone.now().strftime('%Y-%m-%d %H:%M')
    ws.merge_cells('L3:O3')
    meta_cell_3 = ws.cell(row=3, column=12, value=f'Generated On    : {generated_on}')
    meta_cell_3.font = Font(name='Calibri', size=9, color=DARK_TEXT)
    meta_cell_3.alignment = Alignment(horizontal='right', vertical='center')

    # Row heights for the header block
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 20

    row = 4

    # Thin dark-navy horizontal line under the header
    for col in range(1, NUM_COLS + 1):
        cell = ws.cell(row=row, column=col)
        cell.border = Border(bottom=Side(style='medium', color=NAVY))

    row += 1
# ------------------------------------------------------------------
    # 2. Summary section
    # ------------------------------------------------------------------
    total_customers = queryset.count()
    active_customers = queryset.filter(customer_status='active').count()

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NUM_COLS)
    summary_title = ws.cell(row=row, column=1, value='SUMMARY')
    summary_title.font = Font(name='Calibri', size=11, bold=True, color=NAVY)
    summary_title.alignment = Alignment(horizontal='left', vertical='center')
    row += 1

    summary_items = [
        ('Total Customers', str(total_customers)),
        ('Active Customers', str(active_customers)),
        ('Generated On', generated_on),
    ]
    for label, value in summary_items:
        ws.cell(row=row, column=1, value=label).font = Font(
            name='Calibri', size=10, bold=True, color=DARK_TEXT
        )
        ws.cell(row=row, column=1).alignment = Alignment(
            horizontal='left', vertical='center'
        )
        ws.cell(row=row, column=2, value=value).font = Font(
            name='Calibri', size=10, color=DARK_TEXT
        )
        ws.cell(row=row, column=2).alignment = Alignment(
            horizontal='left', vertical='center'
        )
        row += 1

    row += 1  # blank spacer row

    # ------------------------------------------------------------------
    # 3. Filters section
    # ------------------------------------------------------------------
    applied_filters = {}
    if filters:
        applied_filters = {
            k: v for k, v in filters.items()
            if k not in ('format', 'page') and v not in (None, '', 'None', 'all')
        }

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NUM_COLS)
    filter_title = ws.cell(row=row, column=1, value='FILTERS APPLIED')
    filter_title.font = Font(name='Calibri', size=11, bold=True, color=NAVY)
    filter_title.alignment = Alignment(horizontal='left', vertical='center')
    row += 1

    FILTER_LABELS = {
        'date_from': 'Date From',
        'date_to': 'Date To',
        'sales_person': 'Sales Person',
        'customer_status': 'Customer Status',
        'trade_license_status': 'TL Status',
        'passport_status': 'Passport Status',
        'eid_status': 'EID Status',
        'copy_status': 'Copy Status',
        'cheque_status': 'Security Cheque',
        'doc_type': 'Document Type',
        'report_type': 'Report Type',
        'status': 'Status',
        'search': 'Search',
    }

    if applied_filters:
        for key, value in applied_filters.items():
            label = FILTER_LABELS.get(key, key.replace('_', ' ').title())
            # Show the sales person's name (not its numeric id) in the filter list.
            if key == 'sales_person' and sales_person:
                value = sales_person.name
            ws.cell(row=row, column=1, value=label).font = Font(
                name='Calibri', size=10, bold=True, color=DARK_TEXT
            )
            ws.cell(row=row, column=1).alignment = Alignment(
                horizontal='left', vertical='center'
            )
            ws.cell(row=row, column=2, value=str(value)).font = Font(
                name='Calibri', size=10, color=DARK_TEXT
            )
            ws.cell(row=row, column=2).alignment = Alignment(
                horizontal='left', vertical='center'
            )
            row += 1
    else:
        ws.merge_cells(
            start_row=row, start_column=1, end_row=row, end_column=NUM_COLS
        )
        none_cell = ws.cell(row=row, column=1, value='Filters Applied : None')
        none_cell.font = Font(name='Calibri', size=10, italic=True, color=GRAY_TEXT)
        none_cell.alignment = Alignment(horizontal='left', vertical='center')
        row += 1

    row += 1  # spacer before the table
# ------------------------------------------------------------------
    # 4. Main customer table - header
    # ------------------------------------------------------------------
    headers = [
        'S.N', 'Company Name', 'TRN', 'Trade License', 'TL Expiry', 'TL Days Left',
        'Passport', 'Passport Expiry', 'Passport Days Left', 'EID', 'EID Expiry',
        'EID Days Left', 'Copy Status', 'Security Cheque', 'Sales Person'
    ]

    header_row = row
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = Font(name='Calibri', size=10, bold=True, color=WHITE)
        cell.fill = navy_fill
        cell.alignment = Alignment(
            horizontal='center', vertical='center', wrap_text=True
        )
        cell.border = thin_border

    ws.row_dimensions[row].height = 36  # wrapped header height
    row += 1

    # ------------------------------------------------------------------
    # 5. Main customer table - data rows
    # ------------------------------------------------------------------
    data_start_row = row

    for i, customer in enumerate(queryset, 1):
        cheque = customer.security_cheques.first()
        cheque_status = cheque.status if cheque else 'not_received'
        cheque_display = cheque.get_status_display() if cheque else 'Not Received'

        copy_status = customer.copy_status
        copy_display = customer.get_copy_status_display()

        tl_days = customer.get_trade_license_days_left()
        pp_days = customer.get_passport_days_left()
        eid_days = customer.get_eid_days_left()

        values = [
            i,
            customer.company_name,
            customer.trn or '',
            customer.trade_license_number or '',
            customer.trade_license_expiry,
            tl_days if tl_days is not None else '',
            customer.passport_number or '',
            customer.passport_expiry,
            pp_days if pp_days is not None else '',
            customer.eid_number or '',
            customer.eid_expiry,
            eid_days if eid_days is not None else '',
            copy_display,
            cheque_display,
            customer.sales_person.name if customer.sales_person else '',
        ]

        base_font = Font(name='Calibri', size=10, color=DARK_TEXT)
        red_font = Font(name='Calibri', size=10, color='DC2626', bold=True)
        is_odd = (i % 2 == 1)

        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = thin_border
            cell.fill = white_fill if is_odd else gray_fill

            # Horizontal alignment
            if col == 1:  # S.N
                cell.alignment = Alignment(horizontal='center', vertical='center')
            elif col in (2, 15):  # Company Name, Sales Person
                cell.alignment = Alignment(horizontal='left', vertical='center')
            elif col == 13 or col == 14:  # Copy Status, Security Cheque
                cell.alignment = Alignment(horizontal='center', vertical='center')
            else:  # numbers, dates, document numbers
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # Date formatting
            if isinstance(value, (date, datetime)):
                cell.number_format = 'YYYY-MM-DD'

            # Cell-specific fonts/colours
            if col == 6 and tl_days is not None and tl_days < 0:
                cell.font = red_font
            elif col == 9 and pp_days is not None and pp_days < 0:
                cell.font = red_font
            elif col == 12 and eid_days is not None and eid_days < 0:
                cell.font = red_font
            elif col == 13:
                cell.fill = STATUS_FILLS.get(copy_status, white_fill)
                cell.font = STATUS_FONTS.get(copy_status, base_font)
            elif col == 14:
                cell.fill = STATUS_FILLS.get(cheque_status, white_fill)
                cell.font = STATUS_FONTS.get(cheque_status, base_font)
            else:
                cell.font = base_font

        ws.row_dimensions[row].height = 20
        row += 1

    # ------------------------------------------------------------------
    # Empty report handling
    # ------------------------------------------------------------------
    if total_customers == 0:
        ws.merge_cells(
            start_row=row, start_column=1, end_row=row, end_column=NUM_COLS
        )
        empty_cell = ws.cell(
            row=row, column=1,
            value='No customer records found for the selected filters.'
        )
        empty_cell.font = Font(name='Calibri', size=11, italic=True, color=GRAY_TEXT)
        empty_cell.alignment = Alignment(horizontal='center', vertical='center')
        empty_cell.fill = gray_fill
        empty_cell.border = thin_border
        ws.row_dimensions[row].height = 24
        row += 1

    row += 1  # spacer
# ------------------------------------------------------------------
    # 6. Footer / notes
    # ------------------------------------------------------------------
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NUM_COLS)
    notes_title = ws.cell(row=row, column=1, value='NOTES')
    notes_title.font = Font(name='Calibri', size=11, bold=True, color=NAVY)
    notes_title.alignment = Alignment(horizontal='left', vertical='center')
    row += 1

    notes = [
        '•  TL = Trade License',
        '•  EID = Emirates ID',
        '•  Days Left is calculated from the current date.',
        '',
        'This is an auto-generated report.',
        'Please contact the administrator for any discrepancies.',
    ]
    for note in notes:
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=10)
        note_cell = ws.cell(row=row, column=1, value=note)
        note_cell.font = Font(name='Calibri', size=9, color=GRAY_TEXT)
        note_cell.alignment = Alignment(horizontal='left', vertical='center')
        row += 1

    row += 1

    # Footer branding line (thin separator + branding)
    for col in range(1, NUM_COLS + 1):
        ws.cell(row=row, column=col).border = Border(
            top=Side(style='thin', color=BORDER_COLOR)
        )
    row += 1

    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=NUM_COLS)
    footer = ws.cell(row=row, column=1, value='KB Remicon Customer Record System')
    footer.font = Font(name='Calibri', size=10, italic=True, color=GRAY_TEXT)
    footer.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[row].height = 24

    # ------------------------------------------------------------------
    # 7. Column widths
    # ------------------------------------------------------------------
    column_widths = [
        6,      # S.N
        28,     # Company Name
        18,     # TRN
        16,     # Trade License
        13,     # TL Expiry
        12,     # TL Days Left
        16,     # Passport
        15,     # Passport Expiry
        15,     # Passport Days Left
        18,     # EID
        13,     # EID Expiry
        13,     # EID Days Left
        14,     # Copy Status
        16,     # Security Cheque
        20,     # Sales Person
    ]
    for idx, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    # ------------------------------------------------------------------
    # 8. AutoFilter, freeze panes, print settings
    # ------------------------------------------------------------------
    if total_customers > 0:
        ws.auto_filter.ref = (
            f'A{header_row}:{last_col}{header_row + total_customers}'
        )
        ws.freeze_panes = f'A{header_row + 1}'
    else:
        ws.auto_filter.ref = f'A{header_row}:{last_col}{header_row}'
        ws.freeze_panes = f'A{header_row + 1}'

    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = f'{header_row}:{header_row}'  # repeat header on each page
    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5
    ws.page_margins.header = 0.3
    ws.page_margins.footer = 0.3

    # ------------------------------------------------------------------
    # 9. Return response
    # ------------------------------------------------------------------
    output = BytesIO()
    wb = ws.parent
    wb.save(output)
    output.seek(0)

    from django.http import HttpResponse
    if sales_person:
        safe_name = _sanitize_filename_component(sales_person.name)
        filename = f'KB_Remicon_Customer_Compliance_Report_{safe_name}.xlsx'
    else:
        filename = 'KB_Remicon_Customer_Compliance_Report.xlsx'
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generate_expiring_documents_excel(queryset, doc_type, days_threshold, title=None):
    """Generate expiring documents Excel report."""
    from customers.utils import get_days_left
    
    if not title:
        title = f'{doc_type.replace("_", " ").title()} Expiring in {days_threshold} Days'
    
    generator = ExcelReportGenerator(title)
    generator.add_title(title)
    
    summary = {
        'Document Type': doc_type.replace('_', ' ').title(),
        'Threshold': f'{days_threshold} Days',
        'Total Records': queryset.count(),
        'Generated': timezone.now().strftime('%d %b %Y %H:%M'),
    }
    generator.add_summary(summary)
    
    headers = [
        'S.N', 'Company Name', 'Document Number', 'Expiry Date', 'Days Left',
        'Status', 'Sales Person', 'Copy Available'
    ]
    generator.add_headers(headers)
    
    for i, customer in enumerate(queryset, 1):
        if doc_type == 'trade_license':
            doc_num = customer.trade_license_number
            expiry = customer.trade_license_expiry
            days = customer.get_trade_license_days_left()
            status = customer.get_trade_license_status()
            copy = customer.documents.filter(document_type='trade_license').exists()
        elif doc_type == 'passport':
            doc_num = customer.passport_number
            expiry = customer.passport_expiry
            days = customer.get_passport_days_left()
            status = customer.get_passport_status()
            copy = customer.documents.filter(document_type='passport').exists()
        elif doc_type == 'emirates_id':
            doc_num = customer.eid_number
            expiry = customer.eid_expiry
            days = customer.get_eid_days_left()
            status = customer.get_eid_status()
            copy = customer.documents.filter(document_type='emirates_id').exists()
        else:
            continue
        
        generator.add_row([
            i,
            customer.company_name,
            doc_num,
            expiry,
            days if days is not None else '',
            status['label'] if status else '',
            customer.sales_person.name if customer.sales_person else '',
            'Yes' if copy else 'No',
        ])
    
    generator.set_column_widths([6, 30, 25, 15, 12, 15, 20, 15])
    generator.freeze_header()
    generator.add_auto_filter(len(headers), queryset.count() + 1)
    generator.set_print_options()
    
    return generator.get_response()


def generate_missing_documents_excel(queryset, title='Missing Documents Report'):
    """Generate missing documents Excel report."""
    generator = ExcelReportGenerator(title)
    generator.add_title(title)
    
    summary = {
        'Total Customers': queryset.count(),
        'Generated': timezone.now().strftime('%d %b %Y %H:%M'),
    }
    generator.add_summary(summary)
    
    headers = [
        'S.N', 'Company Name', 'Missing Documents', 'Trade License', 'Passport', 'EID',
        'TRN Certificate', 'Copy Status', 'Sales Person'
    ]
    generator.add_headers(headers)
    
    for i, customer in enumerate(queryset, 1):
        missing = []
        has_tl = customer.documents.filter(document_type='trade_license').exists()
        has_pp = customer.documents.filter(document_type='passport').exists()
        has_eid = customer.documents.filter(document_type='emirates_id').exists()
        has_trn = customer.documents.filter(document_type='trn_certificate').exists()
        
        if not has_tl:
            missing.append('Trade License')
        if not has_pp:
            missing.append('Passport')
        if not has_eid:
            missing.append('EID')
        if not has_trn:
            missing.append('TRN Certificate')
        
        generator.add_row([
            i,
            customer.company_name,
            ', '.join(missing) if missing else 'None',
            'Yes' if has_tl else 'No',
            'Yes' if has_pp else 'No',
            'Yes' if has_eid else 'No',
            'Yes' if has_trn else 'No',
            customer.get_copy_status_display(),
            customer.sales_person.name if customer.sales_person else '',
        ])
    
    generator.set_column_widths([6, 30, 30, 15, 15, 15, 15, 15, 20])
    generator.freeze_header()
    generator.add_auto_filter(len(headers), queryset.count() + 1)
    generator.set_print_options()
    
    return generator.get_response()


def generate_salesperson_excel(queryset, title='Salesperson Report'):
    """Generate salesperson performance Excel report."""
    generator = ExcelReportGenerator(title)
    generator.add_title(title)
    
    summary = {
        'Total Salespersons': queryset.count(),
        'Generated': timezone.now().strftime('%d %b %Y %H:%M'),
    }
    generator.add_summary(summary)
    
    headers = [
        'S.N', 'Sales Person', 'Email', 'Phone', 'Active', 'Total Customers',
        'Expired Docs', 'Expiring (30d)', 'Missing Docs', 'Pending Cheques'
    ]
    generator.add_headers(headers)
    
    for i, sp in enumerate(queryset, 1):
        generator.add_row([
            i,
            sp.name,
            sp.email,
            sp.phone,
            'Yes' if sp.active else 'No',
            sp.get_customer_count(),
            sp.get_expired_documents_count(),
            sp.get_expiring_soon_count(30),
            sp.get_missing_documents_count(),
            sp.get_pending_cheques_count(),
        ])
    
    generator.set_column_widths([6, 25, 30, 20, 10, 15, 12, 15, 12, 15])
    generator.freeze_header()
    generator.add_auto_filter(len(headers), queryset.count() + 1)
    generator.set_print_options()
    
    return generator.get_response()


def generate_security_cheque_excel(queryset, title='Security Cheque Report'):
    """Generate security cheque Excel report."""
    generator = ExcelReportGenerator(title)
    generator.add_title(title)
    
    summary = {
        'Total Cheques': queryset.count(),
        'Received': queryset.filter(status='received').count(),
        'Pending': queryset.filter(status='pending').count(),
        'Not Received': queryset.filter(status='not_received').count(),
        'Returned': queryset.filter(status='returned').count(),
        'Generated': timezone.now().strftime('%d %b %Y %H:%M'),
    }
    generator.add_summary(summary)
    
    headers = [
        'S.N', 'Company Name', 'Status', 'Cheque Number', 'Amount', 'Cheque Date',
        'Has Copy', 'Sales Person', 'Created At'
    ]
    generator.add_headers(headers)
    
    for i, cheque in enumerate(queryset, 1):
        generator.add_row([
            i,
            cheque.customer.company_name,
            cheque.get_status_display(),
            cheque.cheque_number,
            float(cheque.amount) if cheque.amount else '',
            cheque.cheque_date,
            'Yes' if cheque.file else 'No',
            cheque.customer.sales_person.name if cheque.customer.sales_person else '',
            cheque.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    
    generator.set_column_widths([6, 30, 15, 20, 15, 15, 12, 20, 20])
    generator.freeze_header()
    generator.add_auto_filter(len(headers), queryset.count() + 1)
    generator.set_print_options()
    
    return generator.get_response()