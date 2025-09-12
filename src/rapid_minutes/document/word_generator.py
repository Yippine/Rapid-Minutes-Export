import logging
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.shared import OxmlElement, qn
from typing import Dict, Any, List
from io import BytesIO
from datetime import datetime

logger = logging.getLogger(__name__)


class WordGenerator:
    def __init__(self):
        pass
    
    def generate_document(self, meeting_data: Dict[str, Any]) -> bytes:
        """Generate Word document from meeting data"""
        try:
            doc = Document()
            
            # Set document margins
            sections = doc.sections
            for section in sections:
                section.top_margin = Inches(1)
                section.bottom_margin = Inches(1)
                section.left_margin = Inches(1)
                section.right_margin = Inches(1)
            
            # Add title
            title = doc.add_heading(meeting_data.get("meeting_title", "會議記錄"), 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add meeting basic info
            self._add_meeting_info(doc, meeting_data)
            
            # Add attendees
            self._add_attendees(doc, meeting_data.get("attendees", []))
            
            # Add key topics
            self._add_key_topics(doc, meeting_data.get("key_topics", []))
            
            # Add decisions
            self._add_decisions(doc, meeting_data.get("decisions", []))
            
            # Add action items
            self._add_action_items(doc, meeting_data.get("action_items", []))
            
            # Add next meeting info
            if meeting_data.get("next_meeting"):
                self._add_next_meeting(doc, meeting_data["next_meeting"])
            
            # Add footer
            self._add_footer(doc)
            
            # Save to bytes
            doc_buffer = BytesIO()
            doc.save(doc_buffer)
            doc_buffer.seek(0)
            
            logger.info("Word document generated successfully")
            return doc_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate Word document: {e}")
            raise
    
    def _add_meeting_info(self, doc: Document, meeting_data: Dict[str, Any]):
        """Add basic meeting information"""
        info_table = doc.add_table(rows=4, cols=2)
        info_table.style = 'Table Grid'
        
        # Meeting info data
        info_data = [
            ("會議主題", meeting_data.get("meeting_title", "一般會議")),
            ("會議日期", meeting_data.get("date", "")),
            ("會議時間", meeting_data.get("time", "")),
            ("會議地點", meeting_data.get("location", ""))
        ]
        
        for row_idx, (label, value) in enumerate(info_data):
            row = info_table.rows[row_idx]
            label_cell = row.cells[0]
            value_cell = row.cells[1]
            
            label_cell.text = label
            value_cell.text = value or "未指定"
            
            # Format label cell
            label_run = label_cell.paragraphs[0].runs[0]
            label_run.bold = True
            
        doc.add_paragraph("")  # Add spacing
    
    def _add_attendees(self, doc: Document, attendees: List[str]):
        """Add attendees section"""
        if not attendees:
            return
            
        doc.add_heading("出席人員", level=1)
        
        if attendees:
            for attendee in attendees:
                p = doc.add_paragraph()
                p.style = 'List Bullet'
                p.add_run(attendee)
        else:
            doc.add_paragraph("無記錄")
        
        doc.add_paragraph("")  # Add spacing
    
    def _add_key_topics(self, doc: Document, key_topics: List[str]):
        """Add key discussion topics"""
        doc.add_heading("討論議題", level=1)
        
        if key_topics:
            for idx, topic in enumerate(key_topics, 1):
                p = doc.add_paragraph()
                p.style = 'List Number'
                p.add_run(topic)
        else:
            doc.add_paragraph("無記錄的討論議題")
        
        doc.add_paragraph("")  # Add spacing
    
    def _add_decisions(self, doc: Document, decisions: List[str]):
        """Add decisions made"""
        doc.add_heading("決議事項", level=1)
        
        if decisions:
            for decision in decisions:
                p = doc.add_paragraph()
                p.style = 'List Bullet'
                # Add bullet point manually if style doesn't work
                p.add_run(f"• {decision}")
        else:
            doc.add_paragraph("本次會議無明確決議事項")
        
        doc.add_paragraph("")  # Add spacing
    
    def _add_action_items(self, doc: Document, action_items: List[Dict[str, str]]):
        """Add action items"""
        doc.add_heading("行動事項", level=1)
        
        if action_items:
            # Create table for action items
            action_table = doc.add_table(rows=1, cols=3)
            action_table.style = 'Table Grid'
            
            # Header row
            header_cells = action_table.rows[0].cells
            header_cells[0].text = "事項"
            header_cells[1].text = "負責人"
            header_cells[2].text = "期限"
            
            # Make header bold
            for cell in header_cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.bold = True
            
            # Add action items
            for action in action_items:
                row_cells = action_table.add_row().cells
                row_cells[0].text = action.get("task", "")
                row_cells[1].text = action.get("assignee", "未指定")
                row_cells[2].text = action.get("deadline", "待確認")
        else:
            doc.add_paragraph("無行動事項")
        
        doc.add_paragraph("")  # Add spacing
    
    def _add_next_meeting(self, doc: Document, next_meeting: str):
        """Add next meeting information"""
        doc.add_heading("下次會議", level=1)
        doc.add_paragraph(next_meeting)
        doc.add_paragraph("")  # Add spacing
    
    def _add_footer(self, doc: Document):
        """Add document footer"""
        doc.add_paragraph("")
        doc.add_paragraph("─" * 50)
        
        footer_p = doc.add_paragraph()
        footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        # Add generation info
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        footer_p.add_run(f"本記錄由 Rapid Minutes Export 系統生成於 {current_time}")
        
        # Make footer text smaller and italic
        for run in footer_p.runs:
            run.font.size = Pt(9)
            run.italic = True
    
    def create_template(self) -> bytes:
        """Create a template Word document"""
        try:
            doc = Document()
            
            # Add title placeholder
            title = doc.add_heading("會議記錄範本", 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add template sections
            doc.add_heading("會議基本資訊", level=1)
            doc.add_paragraph("會議主題：[待填入]")
            doc.add_paragraph("會議日期：[待填入]")
            doc.add_paragraph("會議時間：[待填入]")
            doc.add_paragraph("會議地點：[待填入]")
            
            doc.add_heading("出席人員", level=1)
            doc.add_paragraph("• [待填入]")
            
            doc.add_heading("討論議題", level=1)
            doc.add_paragraph("1. [待填入]")
            
            doc.add_heading("決議事項", level=1)
            doc.add_paragraph("• [待填入]")
            
            doc.add_heading("行動事項", level=1)
            action_table = doc.add_table(rows=2, cols=3)
            action_table.style = 'Table Grid'
            
            header_cells = action_table.rows[0].cells
            header_cells[0].text = "事項"
            header_cells[1].text = "負責人"
            header_cells[2].text = "期限"
            
            sample_cells = action_table.rows[1].cells
            sample_cells[0].text = "[待填入]"
            sample_cells[1].text = "[待填入]"
            sample_cells[2].text = "[待填入]"
            
            # Save template
            template_buffer = BytesIO()
            doc.save(template_buffer)
            template_buffer.seek(0)
            
            return template_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise