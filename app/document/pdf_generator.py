"""
PDF Generator Module (D3 - Document Processing Layer)
Advanced PDF generation and conversion capabilities
Implements ICE principle - Intuitive PDF generation with comprehensive format support
"""

import logging
import os
import subprocess
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import tempfile

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from ..ai.extractor import MeetingMinutes
from ..config import settings

logger = logging.getLogger(__name__)


class PDFFormat(Enum):
    """PDF format options"""
    A4 = "A4"
    LETTER = "letter"
    A3 = "A3"


class PDFOrientation(Enum):
    """PDF orientation"""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass
class PDFStyle:
    """PDF styling configuration"""
    font_family: str = "Arial"
    font_size: int = 12
    line_height: float = 1.2
    margin_top: float = 2.5
    margin_bottom: float = 2.5
    margin_left: float = 2.5
    margin_right: float = 2.5
    header_font_size: int = 16
    subheader_font_size: int = 14
    table_font_size: int = 10
    colors: Dict[str, str] = field(default_factory=lambda: {
        'primary': '#2C3E50',
        'secondary': '#34495E',
        'accent': '#3498DB',
        'text': '#2C3E50',
        'table_header': '#ECF0F1',
        'table_border': '#BDC3C7'
    })


@dataclass
class PDFGenerationOptions:
    """PDF generation options"""
    format: PDFFormat = PDFFormat.A4
    orientation: PDFOrientation = PDFOrientation.PORTRAIT
    style: Optional[PDFStyle] = None
    include_toc: bool = False
    include_header: bool = True
    include_footer: bool = True
    watermark: Optional[str] = None
    password: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class PDFGenerationResult:
    """PDF generation result"""
    success: bool
    output_path: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    generation_time: Optional[float] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFGenerator:
    """
    Advanced PDF generator for meeting minutes
    Supports multiple generation methods and comprehensive formatting
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize PDF generator"""
        self.output_dir = output_dir or settings.output_dir
        self.temp_dir = settings.temp_dir
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Check available PDF libraries
        self.available_methods = []
        if REPORTLAB_AVAILABLE:
            self.available_methods.append('reportlab')
        if WEASYPRINT_AVAILABLE:
            self.available_methods.append('weasyprint')
        
        # Try to detect system PDF tools
        if self._check_libreoffice():
            self.available_methods.append('libreoffice')
        if self._check_pandoc():
            self.available_methods.append('pandoc')
        
        if not self.available_methods:
            logger.warning("⚠️ No PDF generation methods available")
        else:
            logger.info(f"📄 PDF Generator initialized - methods: {', '.join(self.available_methods)}")
    
    async def generate_from_docx(
        self,
        docx_path: str,
        output_filename: Optional[str] = None,
        options: Optional[PDFGenerationOptions] = None
    ) -> PDFGenerationResult:
        """
        Generate PDF from Word document
        
        Args:
            docx_path: Path to Word document
            output_filename: Desired output filename
            options: PDF generation options
            
        Returns:
            PDFGenerationResult
        """
        start_time = datetime.utcnow()
        options = options or PDFGenerationOptions()
        
        if not os.path.exists(docx_path):
            return PDFGenerationResult(
                success=False,
                error_message=f"Source DOCX file not found: {docx_path}"
            )
        
        logger.info(f"📄 Generating PDF from DOCX: {os.path.basename(docx_path)}")
        
        # Generate output filename
        if not output_filename:
            base_name = Path(docx_path).stem
            output_filename = f"{base_name}.pdf"
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            # Try LibreOffice conversion first (best quality)
            if 'libreoffice' in self.available_methods:
                result = await self._convert_with_libreoffice(docx_path, output_path, options)
                if result.success:
                    result.generation_time = (datetime.utcnow() - start_time).total_seconds()
                    return result
            
            # Fallback to other methods
            if 'pandoc' in self.available_methods:
                result = await self._convert_with_pandoc(docx_path, output_path, options)
                if result.success:
                    result.generation_time = (datetime.utcnow() - start_time).total_seconds()
                    return result
            
            # Last resort: extract text and generate with ReportLab
            if 'reportlab' in self.available_methods:
                result = await self._convert_with_reportlab_extraction(docx_path, output_path, options)
                if result.success:
                    result.generation_time = (datetime.utcnow() - start_time).total_seconds()
                    return result
            
            return PDFGenerationResult(
                success=False,
                error_message="No suitable PDF generation method available"
            )
            
        except Exception as e:
            logger.error(f"❌ PDF generation failed: {e}")
            return PDFGenerationResult(
                success=False,
                error_message=str(e),
                generation_time=(datetime.utcnow() - start_time).total_seconds()
            )
    
    async def generate_from_meeting_minutes(
        self,
        meeting_minutes: MeetingMinutes,
        output_filename: Optional[str] = None,
        options: Optional[PDFGenerationOptions] = None
    ) -> PDFGenerationResult:
        """
        Generate PDF directly from meeting minutes data
        
        Args:
            meeting_minutes: Meeting minutes data
            output_filename: Desired output filename
            options: PDF generation options
            
        Returns:
            PDFGenerationResult
        """
        start_time = datetime.utcnow()
        options = options or PDFGenerationOptions()
        
        logger.info("📄 Generating PDF from meeting minutes data")
        
        # Generate output filename
        if not output_filename:
            title = meeting_minutes.basic_info.title or "meeting_minutes"
            date = meeting_minutes.basic_info.date or datetime.now().strftime('%Y-%m-%d')
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
            safe_title = safe_title.replace(' ', '_')[:50]
            output_filename = f"{safe_title}_{date}.pdf"
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            if REPORTLAB_AVAILABLE:
                result = await self._generate_with_reportlab(meeting_minutes, output_path, options)
            elif WEASYPRINT_AVAILABLE:
                result = await self._generate_with_weasyprint(meeting_minutes, output_path, options)
            else:
                return PDFGenerationResult(
                    success=False,
                    error_message="No PDF generation library available"
                )
            
            result.generation_time = (datetime.utcnow() - start_time).total_seconds()
            return result
            
        except Exception as e:
            logger.error(f"❌ PDF generation failed: {e}")
            return PDFGenerationResult(
                success=False,
                error_message=str(e),
                generation_time=(datetime.utcnow() - start_time).total_seconds()
            )
    
    async def _generate_with_reportlab(
        self,
        meeting_minutes: MeetingMinutes,
        output_path: str,
        options: PDFGenerationOptions
    ) -> PDFGenerationResult:
        """Generate PDF using ReportLab"""
        try:
            # Setup document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4 if options.format == PDFFormat.A4 else letter,
                topMargin=options.style.margin_top*cm if options.style else 2.5*cm,
                bottomMargin=options.style.margin_bottom*cm if options.style else 2.5*cm,
                leftMargin=options.style.margin_left*cm if options.style else 2.5*cm,
                rightMargin=options.style.margin_right*cm if options.style else 2.5*cm
            )
            
            # Setup styles
            styles = getSampleStyleSheet()
            style = options.style or PDFStyle()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=style.header_font_size,
                spaceAfter=12,
                textColor=colors.HexColor(style.colors['primary'])
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=style.subheader_font_size,
                spaceAfter=6,
                textColor=colors.HexColor(style.colors['secondary'])
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=style.font_size,
                leading=style.font_size * style.line_height
            )
            
            # Build document content
            content = []
            
            # Title
            title = meeting_minutes.basic_info.title or "會議記錄"
            content.append(Paragraph(title, title_style))
            content.append(Spacer(1, 12))
            
            # Basic info
            if meeting_minutes.basic_info:
                content.append(Paragraph("會議基本資訊", heading_style))
                
                basic_info = [
                    f"日期: {meeting_minutes.basic_info.date or ''}",
                    f"時間: {meeting_minutes.basic_info.time or ''}",
                    f"地點: {meeting_minutes.basic_info.location or ''}",
                    f"主辦人: {meeting_minutes.basic_info.organizer or ''}"
                ]
                
                for info in basic_info:
                    if info.split(': ')[1]:  # Only add if value exists
                        content.append(Paragraph(info, normal_style))
                
                content.append(Spacer(1, 12))
            
            # Attendees
            if meeting_minutes.attendees:
                content.append(Paragraph("出席人員", heading_style))
                
                attendee_data = [['姓名', '職位', '單位', '出席狀態']]
                for attendee in meeting_minutes.attendees:
                    attendee_data.append([
                        attendee.name,
                        attendee.role or '',
                        attendee.organization or '',
                        '出席' if attendee.present else '缺席'
                    ])
                
                attendee_table = Table(attendee_data)
                attendee_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(style.colors['table_header'])),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(style.colors['text'])),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), style.table_font_size),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor(style.colors['table_border']))
                ]))
                
                content.append(attendee_table)
                content.append(Spacer(1, 12))
            
            # Agenda
            if meeting_minutes.agenda:
                content.append(Paragraph("會議議程", heading_style))
                
                for i, topic in enumerate(meeting_minutes.agenda, 1):
                    content.append(Paragraph(f"{i}. {topic.title}", normal_style))
                    if topic.description:
                        content.append(Paragraph(f"   說明: {topic.description}", normal_style))
                    if topic.key_points:
                        for point in topic.key_points:
                            content.append(Paragraph(f"   • {point}", normal_style))
                
                content.append(Spacer(1, 12))
            
            # Action Items
            if meeting_minutes.action_items:
                content.append(Paragraph("行動項目", heading_style))
                
                action_data = [['項目', '負責人', '截止日期', '狀態']]
                for action in meeting_minutes.action_items:
                    action_data.append([
                        action.task,
                        action.assignee or '',
                        action.due_date or '',
                        action.status or '待處理'
                    ])
                
                action_table = Table(action_data)
                action_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(style.colors['table_header'])),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(style.colors['text'])),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), style.table_font_size),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor(style.colors['table_border']))
                ]))
                
                content.append(action_table)
                content.append(Spacer(1, 12))
            
            # Decisions
            if meeting_minutes.decisions:
                content.append(Paragraph("決議事項", heading_style))
                
                for i, decision in enumerate(meeting_minutes.decisions, 1):
                    content.append(Paragraph(f"{i}. {decision.decision}", normal_style))
                    if decision.rationale:
                        content.append(Paragraph(f"   理由: {decision.rationale}", normal_style))
            
            # Key outcomes
            if meeting_minutes.key_outcomes:
                content.append(Paragraph("重要結論", heading_style))
                
                for outcome in meeting_minutes.key_outcomes:
                    content.append(Paragraph(f"• {outcome}", normal_style))
            
            # Build PDF
            doc.build(content)
            
            # Get file stats
            file_size = os.path.getsize(output_path)
            
            logger.info(f"✅ PDF generated with ReportLab: {output_path}")
            
            return PDFGenerationResult(
                success=True,
                output_path=output_path,
                file_size=file_size,
                metadata={
                    'generation_method': 'reportlab',
                    'page_format': options.format.value,
                    'orientation': options.orientation.value
                }
            )
            
        except Exception as e:
            logger.error(f"❌ ReportLab PDF generation failed: {e}")
            return PDFGenerationResult(success=False, error_message=str(e))
    
    async def _convert_with_libreoffice(
        self,
        docx_path: str,
        output_path: str,
        options: PDFGenerationOptions
    ) -> PDFGenerationResult:
        """Convert DOCX to PDF using LibreOffice"""
        try:
            cmd = [
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', os.path.dirname(output_path),
                docx_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # LibreOffice creates PDF with same name as input
                generated_pdf = os.path.join(
                    os.path.dirname(output_path),
                    Path(docx_path).stem + '.pdf'
                )
                
                if os.path.exists(generated_pdf) and generated_pdf != output_path:
                    os.rename(generated_pdf, output_path)
                
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    
                    logger.info(f"✅ PDF generated with LibreOffice: {output_path}")
                    
                    return PDFGenerationResult(
                        success=True,
                        output_path=output_path,
                        file_size=file_size,
                        metadata={'generation_method': 'libreoffice'}
                    )
            
            return PDFGenerationResult(
                success=False,
                error_message=f"LibreOffice conversion failed: {result.stderr}"
            )
            
        except subprocess.TimeoutExpired:
            return PDFGenerationResult(
                success=False,
                error_message="LibreOffice conversion timeout"
            )
        except Exception as e:
            return PDFGenerationResult(
                success=False,
                error_message=f"LibreOffice error: {str(e)}"
            )
    
    def _check_libreoffice(self) -> bool:
        """Check if LibreOffice is available"""
        try:
            result = subprocess.run(['libreoffice', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _check_pandoc(self) -> bool:
        """Check if Pandoc is available"""
        try:
            result = subprocess.run(['pandoc', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    async def _convert_with_pandoc(
        self,
        docx_path: str,
        output_path: str,
        options: PDFGenerationOptions
    ) -> PDFGenerationResult:
        """Convert using Pandoc"""
        # Placeholder implementation
        return PDFGenerationResult(success=False, error_message="Pandoc conversion not implemented")
    
    async def _convert_with_reportlab_extraction(
        self,
        docx_path: str,
        output_path: str,
        options: PDFGenerationOptions
    ) -> PDFGenerationResult:
        """Extract text from DOCX and generate PDF with ReportLab"""
        # Placeholder implementation
        return PDFGenerationResult(success=False, error_message="ReportLab extraction not implemented")
    
    async def _generate_with_weasyprint(
        self,
        meeting_minutes: MeetingMinutes,
        output_path: str,
        options: PDFGenerationOptions
    ) -> PDFGenerationResult:
        """Generate PDF using WeasyPrint"""
        # Placeholder implementation
        return PDFGenerationResult(success=False, error_message="WeasyPrint generation not implemented")
    
    def get_available_methods(self) -> List[str]:
        """Get available PDF generation methods"""
        return self.available_methods.copy()
    
    def get_supported_formats(self) -> List[str]:
        """Get supported PDF formats"""
        return [fmt.value for fmt in PDFFormat]
    
    async def validate_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Validate generated PDF"""
        if not os.path.exists(pdf_path):
            return {'valid': False, 'error': 'PDF file not found'}
        
        try:
            file_size = os.path.getsize(pdf_path)
            
            # Basic validation - check if file starts with PDF header
            with open(pdf_path, 'rb') as f:
                header = f.read(4)
                is_pdf = header == b'%PDF'
            
            return {
                'valid': is_pdf,
                'file_size': file_size,
                'readable': is_pdf
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}