from io import BytesIO
from typing import List

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, SimpleDocTemplate, Table, TableStyle
from reportlab.platypus.flowables import Flowable


class Pdf:

    def create_pdf(
        self,
        children: List[Flowable],
    ) -> BytesIO:
        # Create a BytesIO buffer for the PDF content
        pdf_buffer = BytesIO()

        # Create PDF content using ReportLab
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )

        # Build the PDF content
        doc.build(
            children,
            canvasmaker=_NumberedCanvas,
        )

        # Reset the buffer position to the beginning
        pdf_buffer.seek(0)

        return pdf_buffer

    @staticmethod
    def style():
        return getSampleStyleSheet()

    @staticmethod
    def title_style():
        return getSampleStyleSheet()["Title"]

    @staticmethod
    def heading_style():
        return getSampleStyleSheet()["Heading2"]

    @staticmethod
    def normal_style():
        return getSampleStyleSheet()["BodyText"]

    @staticmethod
    def link_style():
        style = getSampleStyleSheet()["BodyText"]
        style.textColor = colors.darkcyan
        return style

    @staticmethod
    def _footer(
        page_number: int,
        total_pages: int,
    ) -> Table:
        # Create a table with user information

        # Center align style.
        normal_style_center_align = Pdf.normal_style()
        normal_style_center_align.alignment = TA_CENTER

        # Right align style.
        normal_style_right_align = Pdf.normal_style()
        normal_style_right_align.alignment = TA_RIGHT

        footer = Table(
            data=[
                [
                    Paragraph(
                        timezone.now().strftime("%B %d, %Y"),
                        Pdf.normal_style(),
                    ),
                    Paragraph(
                        f"Downstream Systems © {timezone.now().year}",
                        normal_style_center_align,
                    ),
                    Paragraph(
                        f"Page {page_number} of {total_pages}",
                        normal_style_right_align,
                    ),
                ],
            ],
            colWidths=["33%", "33%", "33%"],
        )

        # Remove padding around table.
        footer.setStyle(
            TableStyle(
                [
                    ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                    ("ALIGN", (1, 0), (1, 0), "CENTER"),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ]
            )
        )

        return footer


class _NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        """Draw page number in the bottom-right corner."""
        page_width, page_height = letter  # Use the letter size for width and height

        # Get footer.
        footer = Pdf._footer(
            self._pageNumber,
            page_count,
        )

        # Draw footer.
        w, h = footer.wrap(
            page_width - 60,
            page_height - 60,
        )
        footer.drawOn(self, 30, h)
