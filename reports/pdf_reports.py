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


# ---------------------------------------------------------------------------
# Shared palette constants (mirror of KBRemiconReport in excel_reports.py)
# ---------------------------------------------------------------------------
NAVY = colors.HexColor('#1F2937')
WHITE = colors.white
DARK_TEXT = colors.HexColor('#111827')
GRAY_TEXT = colors.HexColor('#6B7280')
BORDER_CLR = colors.HexColor('#D1D5DB')
ALT_ROW = colors.HexColor('#F3F4F6')

_STATUS_FILLS = {
    'complete': colors.HexColor('#DCFCE7'),
    'partial': colors.HexColor('#FEF3C7'),
    'missing': colors.HexColor('#FEE2E2'),
    'received': colors.HexColor('#DCFCE7'),
    'not_received': colors.HexColor('#F3F4F6'),
    'pending': colors.HexColor('#FEF3C7'),
    'returned': colors.HexColor('#FEE2E2'),
}
_STATUS_FONT_COLORS = {
    'complete': colors.HexColor('#166534'),
    'partial': colors.HexColor('#92400E'),
    'missing': colors.HexColor('#991B1B'),
    'received': colors.HexColor('#166534'),
    'not_received': colors.HexColor('#374151'),
    'pending': colors.HexColor('#92400E'),
    'returned': colors.HexColor('#991B1B'),
}



class KBRemiconPDFReport:
    """Shared builder for KB Remicon branded PDF list/table reports."""

    def __init__(self, title, pagesize=landscape(A4)):
        self.title = title
        self.pagesize = pagesize
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self.elements = []

    def _setup_styles(self):
        s = self.styles
        s.add(ParagraphStyle('BrandName', parent=s['Normal'],
            fontSize=16, leading=20, fontName='Helvetica-Bold',
            textColor=NAVY, alignment=TA_LEFT))
        s.add(ParagraphStyle('BrandLabel', parent=s['Normal'],
            fontSize=10, leading=13, fontName='Helvetica-Bold',
            textColor=GRAY_TEXT, alignment=TA_LEFT))
        s.add(ParagraphStyle('KBTitle', parent=s['Normal'],
            fontSize=14, leading=18, fontName='Helvetica-Bold',
            textColor=NAVY, alignment=TA_CENTER))
        s.add(ParagraphStyle('KBSubtitle', parent=s['Normal'],
            fontSize=10, leading=13, textColor=GRAY_TEXT,
            alignment=TA_CENTER))
        s.add(ParagraphStyle('KBMeta', parent=s['Normal'],
            fontSize=9, leading=12, textColor=DARK_TEXT,
            alignment=TA_LEFT))
        s.add(ParagraphStyle('SummaryHeader', parent=s['Normal'],
            fontSize=11, leading=14, fontName='Helvetica-Bold',
            textColor=NAVY, alignment=TA_LEFT,
            spaceBefore=4, spaceAfter=4))
        s.add(ParagraphStyle('SummaryLabel', parent=s['Normal'],
            fontSize=9, leading=12, fontName='Helvetica-Bold',
            textColor=DARK_TEXT))
        s.add(ParagraphStyle('SummaryValue', parent=s['Normal'],
            fontSize=9, leading=12, textColor=DARK_TEXT))
        s.add(ParagraphStyle('TableHeader', parent=s['Normal'],
            fontSize=7, leading=9, fontName='Helvetica-Bold',
            textColor=WHITE, alignment=TA_CENTER))
        s.add(ParagraphStyle('TableCell', parent=s['Normal'],
            fontSize=6.5, leading=8, alignment=TA_LEFT))
        s.add(ParagraphStyle('FooterNote', parent=s['Normal'],
            fontSize=8, leading=10, textColor=GRAY_TEXT,
            alignment=TA_LEFT))
        s.add(ParagraphStyle('FooterBrand', parent=s['Normal'],
            fontSize=9, leading=12, fontName='Helvetica-Oblique',
            textColor=GRAY_TEXT, alignment=TA_CENTER))


    def _draw_page(self, canvas, doc):
        canvas.saveState()
        w, h = self.pagesize
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(0.5)
        canvas.line(1*cm, 1.3*cm, w - 1*cm, 1.3*cm)
        canvas.setFont('Helvetica-Oblique', 7)
        canvas.setFillColor(GRAY_TEXT)
        canvas.drawString(1*cm, 0.85*cm,
                          'KB Remicon Customer Record System')
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#9CA3AF'))
        canvas.drawString(1*cm, 1.0*cm,
                          timezone.now().strftime('%d %b %Y'))
        canvas.drawRightString(
            w - 1*cm, 0.85*cm,
            'Page {0}'.format(canvas.getPageNumber()))
        canvas.restoreState()

    def add_header_block(self, title, subtitle=None, report_type=None,
                         generated_by=None):
        pw = self.pagesize[0] - 2 * cm
        left_w, centre_w, right_w = pw * 0.22, pw * 0.48, pw * 0.30
        left_parts = [
            Paragraph('KB REMICON', self.styles['BrandName']),
            Paragraph(report_type or 'REPORT', self.styles['BrandLabel']),
        ]
        centre_parts = [
            Paragraph(title, self.styles['KBTitle']),
            Paragraph(report_type or 'REPORT', self.styles['KBSubtitle']),
        ]
        if subtitle:
            centre_parts.append(Spacer(1, 2))
            centre_parts.append(
                Paragraph(subtitle, self.styles['KBSubtitle']))
        gen_on = timezone.now().strftime('%d %b %Y %H:%M')
        right_parts = [
            Paragraph('Report Type    : {0}'.format(
                report_type or 'Report'), self.styles['KBMeta']),
        ]
        if generated_by:
            right_parts.append(Paragraph(
                'Generated By    : {0}'.format(generated_by),
                self.styles['KBMeta']))
        right_parts.append(Paragraph(
            'Generated On    : {0}'.format(gen_on),
            self.styles['KBMeta']))
        tbl = Table(
            [[left_parts, centre_parts, right_parts]],
            colWidths=[left_w, centre_w, right_w])
        tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        self.elements.append(tbl)
        self.elements.append(Spacer(1, 6))
        self.elements.append(HRFlowable(
            width='100%', thickness=1.5, color=NAVY,
            spaceBefore=2, spaceAfter=8))


    def add_summary(self, pairs):
        self.elements.append(
            Paragraph('SUMMARY', self.styles['SummaryHeader']))
        self.elements.append(Spacer(1, 4))
        rows = [
            [Paragraph(str(lab), self.styles['SummaryLabel']),
             Paragraph(str(val), self.styles['SummaryValue'])]
            for lab, val in pairs
        ]
        if rows:
            tbl = Table(rows, colWidths=[6*cm, 6*cm])
            tbl.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, BORDER_CLR),
            ]))
            self.elements.append(tbl)
        self.elements.append(Spacer(1, 10))

    def add_table(self, headers, data, col_widths=None,
                  status_col_index=None, status_key_func=None):
        hdr = [Paragraph(h, self.styles['TableHeader']) for h in headers]
        tbl_data = [hdr]
        for row in data:
            tbl_data.append([
                Paragraph(str(c) if c is not None else '',
                          self.styles['TableCell'])
                for c in row])
        nc = len(headers)
        if not col_widths:
            avail = self.pagesize[0] - 2 * cm
            col_widths = [avail / nc] * nc
        tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
        cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6.5),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_CLR),
            ('LINEBELOW', (0, 0), (-1, 0), 1, NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]
        for i in range(1, len(tbl_data)):
            if i % 2 == 0:
                cmds.append(('BACKGROUND', (0, i), (-1, i), ALT_ROW))
        if status_col_index is not None and data:
            for ri, rd in enumerate(data, 1):
                if status_key_func:
                    key = status_key_func(rd)
                else:
                    raw = (rd[status_col_index]
                           if status_col_index < len(rd) else '')
                    key = (str(raw).lower().replace(' ', '_')
                           if raw else None)
                if key and key in _STATUS_FILLS:
                    cmds.append(('BACKGROUND',
                        (status_col_index, ri), (status_col_index, ri),
                        _STATUS_FILLS[key]))
                    cmds.append(('TEXTCOLOR',
                        (status_col_index, ri), (status_col_index, ri),
                        _STATUS_FONT_COLORS[key]))
        tbl.setStyle(TableStyle(cmds))
        self.elements.append(tbl)
        self.elements.append(Spacer(1, 8))


    def add_footer(self, notes=None):
        self.elements.append(Spacer(1, 8))
        if notes:
            for note in notes:
                self.elements.append(
                    Paragraph(note, self.styles['FooterNote']))
            self.elements.append(Spacer(1, 6))
        self.elements.append(HRFlowable(
            width='100%', thickness=0.5, color=BORDER_CLR,
            spaceBefore=4, spaceAfter=6))
        self.elements.append(Paragraph(
            'KB Remicon Customer Record System',
            self.styles['FooterBrand']))

    def build(self):
        doc = SimpleDocTemplate(
            self.buffer, pagesize=self.pagesize,
            leftMargin=1*cm, rightMargin=1*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm)
        doc.build(self.elements,
                  onFirstPage=self._draw_page,
                  onLaterPages=self._draw_page)
        self.buffer.seek(0)
        return self.buffer

    def get_response(self, filename):
        self.build()
        from django.http import HttpResponse
        resp = HttpResponse(
            self.buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = \
            'attachment; filename="{0}"'.format(filename)
        return resp


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


def generate_customer_pdf_report(queryset, title='Customer Compliance Report',
                                 filters=None, sales_person=None):
    """Generate customer compliance PDF report."""
    gen = KBRemiconPDFReport(title)

    subtitle = ('Sales Person: {0}'.format(sales_person.name)
                if sales_person else 'Sales Person: All Sales Persons')
    gen.add_header_block(title, subtitle=subtitle,
                         report_type='Customer Compliance Report')

    # Summary
    total = queryset.count()
    active = queryset.filter(customer_status='active').count()
    pairs = [
        ('Total Customers', total),
        ('Active Customers', active),
    ]
    if filters:
        flt = ', '.join('{0}: {1}'.format(k, v)
                        for k, v in filters.items() if v)
        if flt:
            pairs.append(('Filters', flt))
    gen.add_summary(pairs)

    # Headers
    headers = [
        'S.N', 'Company', 'TRN', 'Trade License', 'TL Expiry', 'TL Days',
        'Passport', 'PP Expiry', 'PP Days', 'EID', 'EID Expiry', 'EID Days',
        'Copy', 'Sec Cheque', 'Sales Person',
    ]

    # Data
    def fmt_days(d):
        if d is None:
            return '-'
        if d < 0:
            return 'EXPIRED'
        return str(d)

    def fmt_date(d):
        return d.strftime('%d/%m/%Y') if d else '-'

    data = []
    for i, customer in enumerate(queryset, 1):
        cheque = customer.security_cheques.first()
        tl_days = customer.get_trade_license_days_left()
        pp_days = customer.get_passport_days_left()
        eid_days = customer.get_eid_days_left()

        data.append([
            str(i),
            customer.company_name[:40],
            customer.trn[:18] if customer.trn else '-',
            customer.trade_license_number[:15]
                if customer.trade_license_number else '-',
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
            customer.sales_person.name[:15]
                if customer.sales_person else '-',
        ])

    col_widths = [
        1.0*cm, 3.5*cm, 2.2*cm, 1.8*cm, 1.6*cm, 1.0*cm,
        1.8*cm, 1.6*cm, 1.0*cm, 2.0*cm, 1.6*cm, 1.0*cm,
        1.2*cm, 1.8*cm, 2.0*cm,
    ]

    gen.add_table(headers, data, col_widths)
    gen.add_footer()
    return gen.build()


def generate_expiring_documents_pdf(queryset, doc_type, days_threshold,
                                    title=None):
    """Generate expiring documents PDF report."""
    from customers.utils import get_days_left

    if not title:
        title = '{0} Expiring in {1} Days'.format(
            doc_type.replace('_', ' ').title(), days_threshold)

    gen = KBRemiconPDFReport(title)
    gen.add_header_block(title,
                         report_type='Expiring Documents Report')

    pairs = [
        ('Document Type', doc_type.replace('_', ' ').title()),
        ('Threshold', '{0} Days'.format(days_threshold)),
        ('Total Records', queryset.count()),
    ]
    gen.add_summary(pairs)

    headers = ['S.N', 'Company', 'Document No.', 'Expiry Date',
               'Days Left', 'Status', 'Sales Person', 'Copy']
    data = []

    def fmt_days(d):
        if d is None:
            return '-'
        if d < 0:
            return 'EXPIRED'
        return str(d)

    def fmt_date(d):
        return d.strftime('%d/%m/%Y') if d else '-'

    for i, customer in enumerate(queryset, 1):
        if doc_type == 'trade_license':
            doc_num = customer.trade_license_number
            expiry = customer.trade_license_expiry
            days = customer.get_trade_license_days_left()
            status = customer.get_trade_license_status()
            copy = ('Yes' if customer.documents
                    .filter(document_type='trade_license').exists()
                    else 'No')
        elif doc_type == 'passport':
            doc_num = customer.passport_number
            expiry = customer.passport_expiry
            days = customer.get_passport_days_left()
            status = customer.get_passport_status()
            copy = ('Yes' if customer.documents
                    .filter(document_type='passport').exists()
                    else 'No')
        elif doc_type == 'emirates_id':
            doc_num = customer.eid_number
            expiry = customer.eid_expiry
            days = customer.get_eid_days_left()
            status = customer.get_eid_status()
            copy = ('Yes' if customer.documents
                    .filter(document_type='emirates_id').exists()
                    else 'No')
        else:
            continue

        data.append([
            str(i),
            customer.company_name[:40],
            doc_num[:20] if doc_num else '-',
            fmt_date(expiry),
            fmt_days(days),
            status['label'] if status else '-',
            customer.sales_person.name[:20]
                if customer.sales_person else '-',
            copy,
        ])

    col_widths = [
        1.0*cm, 3.5*cm, 2.5*cm, 1.8*cm, 1.2*cm, 1.8*cm, 2.5*cm, 1.2*cm,
    ]

    gen.add_table(headers, data, col_widths)
    gen.add_footer()
    return gen.build()

def generate_missing_documents_pdf(queryset,
                                   title='Missing Documents Report'):
    """Generate missing documents PDF report."""
    gen = KBRemiconPDFReport(title)
    gen.add_header_block(title, report_type='Missing Documents Report')

    gen.add_summary([('Total Customers', queryset.count())])

    headers = ['S.N', 'Company', 'Missing Documents', 'Trade License',
               'Passport', 'EID', 'TRN Certificate', 'Copy Status',
               'Sales Person']
    data = []

    for i, customer in enumerate(queryset, 1):
        missing = []
        has_tl = customer.documents.filter(
            document_type='trade_license').exists()
        has_pp = customer.documents.filter(
            document_type='passport').exists()
        has_eid = customer.documents.filter(
            document_type='emirates_id').exists()
        has_trn = customer.documents.filter(
            document_type='trn_certificate').exists()

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
            customer.sales_person.name[:20]
                if customer.sales_person else '-',
        ])

    col_widths = [
        1.0*cm, 3.5*cm, 3.5*cm, 1.5*cm, 1.5*cm, 1.5*cm,
        1.5*cm, 1.5*cm, 2.5*cm,
    ]

    gen.add_table(headers, data, col_widths)
    gen.add_footer()
    return gen.build()


def generate_salesperson_pdf(queryset, title='Salesperson Report'):
    """Generate salesperson performance PDF report."""
    gen = KBRemiconPDFReport(title)
    gen.add_header_block(title, report_type='Salesperson Report')

    gen.add_summary([('Total Salespersons', queryset.count())])

    headers = ['S.N', 'Sales Person', 'Email', 'Phone', 'Active',
               'Customers', 'Expired', 'Expiring (30d)', 'Missing',
               'Pending Cheques']
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
        1.0*cm, 2.5*cm, 3.0*cm, 2.0*cm, 1.2*cm, 1.5*cm,
        1.2*cm, 1.8*cm, 1.2*cm, 1.8*cm,
    ]

    gen.add_table(headers, data, col_widths)
    gen.add_footer()
    return gen.build()


def generate_security_cheque_pdf(queryset, title='Security Cheque Report'):
    """Generate security cheque PDF report."""
    gen = KBRemiconPDFReport(title)
    gen.add_header_block(title, report_type='Security Cheque Report')

    gen.add_summary([
        ('Total Cheques', queryset.count()),
        ('Received', queryset.filter(status='received').count()),
        ('Pending', queryset.filter(status='pending').count()),
        ('Not Received', queryset.filter(status='not_received').count()),
        ('Returned', queryset.filter(status='returned').count()),
    ])

    headers = ['S.N', 'Company', 'Status', 'Cheque No.', 'Amount',
               'Date', 'Copy', 'Sales Person', 'Created']
    data = []

    for i, cheque in enumerate(queryset, 1):
        data.append([
            str(i),
            cheque.customer.company_name[:35],
            cheque.get_status_display()[:12],
            cheque.cheque_number[:15] if cheque.cheque_number else '-',
            '{0:,.2f}'.format(cheque.amount) if cheque.amount else '-',
            cheque.cheque_date.strftime('%d/%m/%Y')
                if cheque.cheque_date else '-',
            '\u2714' if cheque.file else '\u2718',
            cheque.customer.sales_person.name[:20]
                if cheque.customer.sales_person else '-',
            cheque.created_at.strftime('%d/%m/%Y'),
        ])

    col_widths = [
        1.0*cm, 3.0*cm, 1.5*cm, 1.8*cm, 1.8*cm, 1.5*cm,
        0.8*cm, 2.0*cm, 1.5*cm,
    ]

    gen.add_table(headers, data, col_widths,
                  status_col_index=2, status_key_func=lambda r: r[2].lower())
    gen.add_footer()
    return gen.build()

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