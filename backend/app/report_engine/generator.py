"""Report Generation Engine — HTML and PDF output."""
import os
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Import the report model - handle both package and standalone usage
try:
    from ..models.report import ComplianceReport
    from ..config import settings
except ImportError:
    # Fallback for standalone usage
    settings = type('obj', (object,), {'report_output_dir': 'reports/'})()


class ReportGenerator:
    """Generates HTML and PDF compliance reports from structured data."""

    def __init__(self):
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def render_html(self, report) -> str:
        """Render a compliance report as HTML string."""
        template = self.env.get_template("report.html")
        return template.render(report=report)

    def render_pdf(self, report, output_dir: str = None) -> str:
        """Render a compliance report as PDF file. Returns the file path."""
        output_dir = output_dir or getattr(settings, 'report_output_dir', 'reports/')
        os.makedirs(output_dir, exist_ok=True)

        html_content = self.render_html(report)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"compliance_{report.vessel.name}_{report.vessel.imo}_{timestamp}.pdf"
        pdf_path = os.path.join(output_dir, filename)

        try:
            from weasyprint import HTML
            HTML(string=html_content).write_pdf(pdf_path)
        except ImportError:
            # Fallback: save as HTML if WeasyPrint not available
            html_path = pdf_path.replace('.pdf', '.html')
            with open(html_path, 'w') as f:
                f.write(html_content)
            return html_path

        return pdf_path
