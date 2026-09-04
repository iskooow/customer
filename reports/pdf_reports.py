"""
PDF report generation utilities using ReportLab.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, KeepTogether, Frame, PageTemplate, BaseDocTemplate
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date
from io import BytesIO


class PDFReportGenerator:
    """Generate PDF reports for customer records."""
    
    def __init__(self, title='Customer Report', pagesize=landscape(A4)):
        self.title = title
        self.pagesize = pagesize
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self.elements = []
    
    def _setup_styles(self):
        """Setup custom styles."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=6,
            textColor=colors.HexColor('#1F2937'),
        ))
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=12,
            textColor=colors.HexColor('#6B7280'),
        ))
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            leading=16,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#1F2937'),
        ))
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=7,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.white,
            fontName='Helvetica-Bold',
        ))
        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
        ))
        self.styles.add(ParagraphStyle(
            name='TableCellCenter',
            parent=self.styles['Normal'],
            fontSize=6.5,
            leading=8,
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            name='TableCellRight',
            parent=self.styles['Normal'],
            fontSize=6.5,
            leading=8,
            alignment=TA_RIGHT,
        ))
        self.styles.add(ParagraphStyle(
            name='SummaryLabel',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            fontName='Helvetica-Bold',
        ))
        self.styles.add(ParagraphStyle(
            name='SummaryValue',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
        ))
    
    def add_title(self, title=None, subtitle=None):
        """Add report title."""
        title = title or self.title
        self.elements.append(Paragraph(title, self.styles['ReportTitle']))
        
        if subtitle:
            self.elements.append(Paragraph(subtitle, self.styles['ReportSubtitle']))
        
        # Generation info
        gen_info = _('Generated: {}').format(timezone.now().strftime('%d %b %Y %H:%M'))
        self.elements.append(Paragraph(gen_info, self.styles['ReportSubtitle']))
        self.elements.append(Spacer(1, 12))
    
    def add_summary(self, summary_data):
        """Add summary statistics."""
        self.elements.append(Paragraph(_('Summary'), self.styles['SectionTitle']))
        
        summary_table_data = []
        for label, value in summary_data.items():
            summary_table_data.append([
                Paragraph(str(label), self.styles['SummaryLabel']),
                Paragraph(str(value), self.styles['SummaryValue']),
            ])
        
        if summary_table_data:
            summary_table = Table(summary_table_data, colWidths=[6*cm, 4*cm])
            summary_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#E5E7EB')),
            ]))
            self.elements.append(summary_table)
            self.elements.append(Spacer(1, 12))
    
    def add_table(self, headers, data, col_widths=None, row_style_func=None):
        """Add a data table."""
        # Prepare header row
        header_row = [Paragraph(h, self.styles['TableHeader']) for h in headers]
        
        # Prepare data rows
        table_data = [header_row]
        for row in data:
            table_row = []
            for i, cell in enumerate(row):
                style = self.styles['TableCellCenter'] if i in [0, 4, 5, 6, 8, 9, 10, 11, 12, 13] else self.styles['TableCell']
                table_row.append(Paragraph(str(cell) if cell is not None else '', style))
            table_data.append(table_row)
        
        # Calculate column widths if not provided
        if not col_widths:
            num_cols = len(headers)
            available_width = self.pagesize[0] - 2*cm  # 1cm margins each side
            col_widths = [available_width / num_cols] * num_cols
        
        # Create table
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Base table style
        style_commands = [
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Cell style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6.5),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#1F2937')),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]
        
        # Apply alternating row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style_commands.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F9FAFB')))
        
        # Apply custom row styling if provided
        if row_style_func:
            for i, row in enumerate(data, 1):
                row_styles = row_style_func(row, i)
                for cmd in row_styles:
                    style_commands.append(cmd)
        
        table.setStyle(TableStyle(style_commands))
        self.elements.append(table)
        self.elements.append(Spacer(1, 12))
    
    def build(self):
        """Build the PDF document."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=self.pagesize,
            leftMargin=1*cm,
            rightMargin=1*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm,
        )
        
        # Add page numbers
        def add_page_number(canvas, doc):
            page_num = canvas.getPageNumber()
            text = f"Page {page_num}"
            canvas.saveState()
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(colors.HexColor('#9CA3AF'))
            canvas.drawRightString(
                self.pagesize[0] - 1*cm,
                1*cm,
                text
            )
            # Add generation date on left
            canvas.drawString(
                1*cm,
                1*cm,
                timezone.now().strftime('%d %b %Y')
            )
            canvas.restoreState()
        
        doc.build(self.elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
        self.buffer.seek(0)
        return self.buffer


def generate_customer_pdf_report(queryset, title='Customer Compliance Report', filters=None, sales_person=None):
    """Generate customer compliance PDF report."""
    generator = PDFReportGenerator(title)
    
    # Title
    subtitle = f'Sales Person: {sales_person.name}' if sales_person else 'Sales Person: All Sales Persons'
    generator.add_title(title, subtitle=subtitle)
    
    # Summary
    summary = {
        'Total Customers': queryset.count(),
        'Active Customers': queryset.filter(customer_status='active').count(),
    }
    if filters:
        summary['Filters'] = ', '.join(f'{k}: {v}' for k, v in filters.items() if v)
    generator.add_summary(summary)
    
    # Headers
    headers = [
        'S.N', 'Company', 'TRN', 'Trade License', 'TL Expiry', 'TL Days',
        'Passport', 'PP Expiry', 'PP Days', 'EID', 'EID Expiry', 'EID Days',
        'Copy', 'Sec Cheque', 'Sales Person'
    ]
    
    # Data
    data = []
    for i, customer in enumerate(queryset, 1):
        cheque = customer.security_cheques.first()
        
        tl_days = customer.get_trade_license_days_left()
        pp_days = customer.get_passport_days_left()
        eid_days = customer.get_eid_days_left()
        
        # Format days for display
        def fmt_days(d):
            if d is None:
                return '-'
            if d < 0:
                return 'EXPIRED'
            return str(d)
        
        def fmt_date(d):
            return d.strftime('%d/%m/%Y') if d else '-'
        
        data.append([
            str(i),
            customer.company_name[:40],
            customer.trn[:18] if customer.trn else '-',
            customer.trade_license_number[:15] if customer.trade_license_number else '-',
            fmt_date(customer.trade_license_expiry),
            fmt_days(tl_days),
            customer.passport_number[:12] if customer.passport_number else '-',
            fmt_date(customer.passport_expiry),
            fmt_days(pp_days),
            customer.eid_number[:18] if customer.eid_number else '-',
            fmt_date(customer.eid_expiry),
            fmt_days(eid_days),
            customer.get_copy_status_display()[:10],
            cheque.get_status_display()[:12] if cheque else 'Not Received',
            customer.sales_person.name[:15] if customer.sales_person else '-',
        ])
    
    # Column widths (in cm)
    col_widths = [
        1.0*cm,  # S.N
        3.5*cm,  # Company
        2.2*cm,  # TRN
        1.8*cm,  # Trade License
        1.6*cm,  # TL Expiry
        1.0*cm,  # TL Days
        1.8*cm,  # Passport
        1.6*cm,  # PP Expiry
        1.0*cm,  # PP Days
        2.0*cm,  # EID
        1.6*cm,  # EID Expiry
        1.0*cm,  # EID Days
        1.2*cm,  # Copy
        1.8*cm,  # Sec Cheque
        2.0*cm,  # Sales Person
    ]
    
    def row_style_func(row, row_idx):
        """Apply styling based on expiry status."""
        styles = []
        # Check for expired documents (columns 5, 8, 11)
        for col_idx in [5, 8, 11]:
            if row_idx - 1 < len(queryset):
                customer = queryset[row_idx - 1]
                if col_idx == 5:
                    days = customer.get_trade_license_days_left()
                elif col_idx == 8:
                    days = customer.get_passport_days_left()
                else:
                    days = customer.get_eid_days_left()
                
                if days is not None and days < 0:
                    styles.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#DC2626')))
                    styles.append(('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'Helvetica-Bold'))
        return styles
    
    generator.add_table(headers, data, col_widths, row_style_func)
    
    return generator.build()


def generate_expiring_documents_pdf(queryset, doc_type, days_threshold, title=None):
    """Generate expiring documents PDF report."""
    from customers.utils import get_days_left
    
    if not title:
        title = f'{doc_type.replace("_", " ").title()} Expiring in {days_threshold} Days'
    
    generator = PDFReportGenerator(title, pagesize=landscape(A4))
    generator.add_title(title)
    
    summary = {
        'Document Type': doc_type.replace('_', ' ').title(),
        'Threshold': f'{days_threshold} Days',
        'Total Records': queryset.count(),
    }
    generator.add_summary(summary)
    
    headers = ['S.N', 'Company', 'Document No.', 'Expiry Date', 'Days Left', 'Status', 'Sales Person', 'Copy']
    data = []
    
    for i, customer in enumerate(queryset, 1):
        if doc_type == 'trade_license':
            doc_num = customer.trade_license_number
            expiry = customer.trade_license_expiry
            days = customer.get_trade_license_days_left()
            status = customer.get_trade_license_status()
            copy = 'Yes' if customer.documents.filter(document_type='trade_license').exists() else 'No'
        elif doc_type == 'passport':
            doc_num = customer.passport_number
            expiry = customer.passport_expiry
            days = customer.get_passport_days_left()
            status = customer.get_passport_status()
            copy = 'Yes' if customer.documents.filter(document_type='passport').exists() else 'No'
        elif doc_type == 'emirates_id':
            doc_num = customer.eid_number
            expiry = customer.eid_expiry
            days = customer.get_eid_days_left()
            status = customer.get_eid_status()
            copy = 'Yes' if customer.documents.filter(document_type='emirates_id').exists() else 'No'
        else:
            continue
        
        def fmt_days(d):
            if d is None:
                return '-'
            if d < 0:
                return 'EXPIRED'
            return str(d)
        
        def fmt_date(d):
            return d.strftime('%d/%m/%Y') if d else '-'
        
        data.append([
            str(i),
            customer.company_name[:40],
            doc_num[:20] if doc_num else '-',
            fmt_date(expiry),
            fmt_days(days),
            status['label'] if status else '-',
            customer.sales_person.name[:20] if customer.sales_person else '-',
            copy,
        ])
    
    col_widths = [
        1.0*cm, 3.5*cm, 2.5*cm, 1.8*cm, 1.2*cm, 1.8*cm, 2.5*cm, 1.2*cm
    ]
    
    generator.add_table(headers, data, col_widths)
    return generator.build()


def generate_missing_documents_pdf(queryset, title='Missing Documents Report'):
    """Generate missing documents PDF report."""
    generator = PDFReportGenerator(title, pagesize=landscape(A4))
    generator.add_title(title)
    
    summary = {
        'Total Customers': queryset.count(),
    }
    generator.add_summary(summary)
    
    headers = ['S.N', 'Company', 'Missing Documents', 'Trade License', 'Passport', 'EID', 'TRN Certificate', 'Copy Status', 'Sales Person']
    data = []
    
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
        
        data.append([
            str(i),
            customer.company_name[:40],
            ', '.join(missing) if missing else 'None',
            'Yes' if has_tl else 'No',
            'Yes' if has_pp else 'No',
            'Yes' if has_eid else 'No',
            'Yes' if has_trn else 'No',
            customer.get_copy_status_display(),
            customer.sales_person.name[:20] if customer.sales_person else '-',
        ])
    
    col_widths = [
        1.0*cm, 3.5*cm, 3.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2.5*cm
    ]
    
    generator.add_table(headers, data, col_widths)
    return generator.build()


def generate_salesperson_pdf(queryset, title='Salesperson Report'):
    """Generate salesperson performance PDF report."""
    generator = PDFReportGenerator(title, pagesize=landscape(A4))
    generator.add_title(title)
    
    summary = {
        'Total Salespersons': queryset.count(),
    }
    generator.add_summary(summary)
    
    headers = ['S.N', 'Sales Person', 'Email', 'Phone', 'Active', 'Customers', 'Expired', 'Expiring (30d)', 'Missing', 'Pending Cheques']
    data = []
    
    for i, sp in enumerate(queryset, 1):
        data.append([
            str(i),
            sp.name[:25],
            sp.email[:30],
            sp.phone[:15],
            'Yes' if sp.active else 'No',
            str(sp.get_customer_count()),
            str(sp.get_expired_documents_count()),
            str(sp.get_expiring_soon_count(30)),
            str(sp.get_missing_documents_count()),
            str(sp.get_pending_cheques_count()),
        ])
    
    col_widths = [
        1.0*cm, 2.5*cm, 3.0*cm, 2.0*cm, 1.2*cm, 1.5*cm, 1.2*cm, 1.8*cm, 1.2*cm, 1.8*cm
    ]
    
    generator.add_table(headers, data, col_widths)
    return generator.build()


def generate_security_cheque_pdf(queryset, title='Security Cheque Report'):
    """Generate security cheque PDF report."""
    generator = PDFReportGenerator(title, pagesize=landscape(A4))
    generator.add_title(title)
    
    summary = {
        'Total Cheques': queryset.count(),
        'Received': queryset.filter(status='received').count(),
        'Pending': queryset.filter(status='pending').count(),
        'Not Received': queryset.filter(status='not_received').count(),
        'Returned': queryset.filter(status='returned').count(),
    }
    generator.add_summary(summary)
    
    headers = ['S.N', 'Company', 'Status', 'Cheque No.', 'Amount', 'Date', 'Copy', 'Sales Person', 'Created']
    data = []
    
    for i, cheque in enumerate(queryset, 1):
        data.append([
            str(i),
            cheque.customer.company_name[:35],
            cheque.get_status_display()[:12],
            cheque.cheque_number[:15] if cheque.cheque_number else '-',
            f'{cheque.amount:,.2f}' if cheque.amount else '-',
            cheque.cheque_date.strftime('%d/%m/%Y') if cheque.cheque_date else '-',
            '✓' if cheque.file else '✗',
            cheque.customer.sales_person.name[:20] if cheque.customer.sales_person else '-',
            cheque.created_at.strftime('%d/%m/%Y'),
        ])
    
    col_widths = [
        1.0*cm, 3.0*cm, 1.5*cm, 1.8*cm, 1.8*cm, 1.5*cm, 0.8*cm, 2.0*cm, 1.5*cm
    ]
    
    generator.add_table(headers, data, col_widths)
    return generator.build()


def generate_individual_customer_pdf(customer, title=None):
    """Generate individual customer profile PDF."""
    if not title:
        title = f'{customer.company_name} - Customer Record'
    
    generator = PDFReportGenerator(title, pagesize=A4)
    generator.add_title(title)
    
    # Company Information
    generator.elements.append(Paragraph(_('Company Information'), generator.styles['SectionTitle']))
    
    company_data = [
        [_('Company Name'), customer.company_name],
        [_('Trade License'), customer.trade_license_number or _('Not Provided')],
        [_('Trade License Expiry'), customer.trade_license_expiry.strftime('%d %b %Y') if customer.trade_license_expiry else _('Not Set')],
        [_('Trade License Status'), customer.get_trade_license_status()['label'] if customer.get_trade_license_status() else _('Not Set')],
        [_('TRN'), customer.trn or _('Not Provided')],
        [_('Sales Person'), customer.sales_person.name if customer.sales_person else _('Not Assigned')],
        [_('Customer Status'), customer.get_customer_status_display()],
        [_('Notes'), customer.notes or _('None')],
    ]
    
    company_table = Table(company_data, colWidths=[4*cm, 13*cm])
    company_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    generator.elements.append(company_table)
    generator.elements.append(Spacer(1, 12))
    
    # Passport Information
    generator.elements.append(Paragraph(_('Passport Information'), generator.styles['SectionTitle']))
    
    pp_days = customer.get_passport_days_left()
    pp_status = customer.get_passport_status()
    
    passport_data = [
        [_('Passport Number'), customer.passport_number or _('Not Provided')],
        [_('Expiry Date'), customer.passport_expiry.strftime('%d %b %Y') if customer.passport_expiry else _('Not Set')],
        [_('Days Left'), str(pp_days) if pp_days is not None else _('Not Set')],
        [_('Status'), pp_status['label'] if pp_status else _('Not Set')],
        [_('Copy Available'), _('Yes') if customer.documents.filter(document_type='passport').exists() else _('No')],
    ]
    
    passport_table = Table(passport_data, colWidths=[4*cm, 13*cm])
    passport_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    generator.elements.append(passport_table)
    generator.elements.append(Spacer(1, 12))
    
    # Emirates ID Information
    generator.elements.append(Paragraph(_('Emirates ID Information'), generator.styles['SectionTitle']))
    
    eid_days = customer.get_eid_days_left()
    eid_status = customer.get_eid_status()
    
    eid_data = [
        [_('EID Number'), customer.eid_number or _('Not Provided')],
        [_('Expiry Date'), customer.eid_expiry.strftime('%d %b %Y') if customer.eid_expiry else _('Not Set')],
        [_('Days Left'), str(eid_days) if eid_days is not None else _('Not Set')],
        [_('Status'), eid_status['label'] if eid_status else _('Not Set')],
        [_('Copy Available'), _('Yes') if customer.documents.filter(document_type='emirates_id').exists() else _('No')],
    ]
    
    eid_table = Table(eid_data, colWidths=[4*cm, 13*cm])
    eid_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    generator.elements.append(eid_table)
    generator.elements.append(Spacer(1, 12))
    
    # Security Cheque
    generator.elements.append(Paragraph(_('Security Cheque'), generator.styles['SectionTitle']))
    
    cheque = customer.security_cheques.first()
    if cheque:
        cheque_data = [
            [_('Status'), cheque.get_status_display()],
            [_('Cheque Number'), cheque.cheque_number or _('Not Provided')],
            [_('Amount'), f'{cheque.amount:,.2f} AED' if cheque.amount else _('Not Set')],
            [_('Cheque Date'), cheque.cheque_date.strftime('%d %b %Y') if cheque.cheque_date else _('Not Set')],
            [_('Copy Available'), _('Yes') if cheque.file else _('No')],
            [_('Notes'), cheque.notes or _('None')],
        ]
    else:
        cheque_data = [
            [_('Status'), _('Not Received')],
            [_('Cheque Number'), _('Not Provided')],
            [_('Amount'), _('Not Set')],
            [_('Cheque Date'), _('Not Set')],
            [_('Copy Available'), _('No')],
            [_('Notes'), _('None')],
        ]
    
    cheque_table = Table(cheque_data, colWidths=[4*cm, 13*cm])
    cheque_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#E5E7EB')),
    ]))
    generator.elements.append(cheque_table)
    generator.elements.append(Spacer(1, 12))
    
    # Documents
    generator.elements.append(Paragraph(_('Documents'), generator.styles['SectionTitle']))
    
    doc_headers = [_('Document'), _('File Name'), _('Expiry Date'), _('Uploaded By'), _('Uploaded Date')]
    doc_data = [doc_headers]
    
    for doc in customer.documents.all():
        doc_data.append([
            doc.get_document_type_display(),
            doc.file_name,
            doc.expiry_date.strftime('%d %b %Y') if doc.expiry_date else '-',
            doc.uploaded_by.get_full_name() if doc.uploaded_by else '-',
            doc.uploaded_at.strftime('%d %b %Y %H:%M'),
        ])
    
    if len(doc_data) > 1:
        doc_table = Table(doc_data, colWidths=[2.5*cm, 5*cm, 2.5*cm, 3.5*cm, 3.5*cm])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        for i in range(1, len(doc_data)):
            if i % 2 == 0:
                doc_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F9FAFB')),
                ]))
        generator.elements.append(doc_table)
    else:
        generator.elements.append(Paragraph(_('No documents uploaded.'), generator.styles['TableCell']))
    
    return generator.build()