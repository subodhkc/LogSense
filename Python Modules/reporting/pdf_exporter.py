# Generate downloadable PDFs from RCA summaries
# report/pdf_exporter.py

from fpdf import FPDF

class PDF(FPDF):
    """
    Custom FPDF subclass for SKC Log Analyzer reports.
    Includes header formatting and a reusable section method.
    """

    def header(self):
        # Report title header centered on every page
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "SKC Log Analyzer Report", ln=True, align='C')
        self.ln(5)  # Add a small line break

    def section(self, title, content):
        """
        Adds a titled section with multi-line body content.

        Args:
            title (str): Section heading
            content (str): Multi-line string content
        """
        self.set_font("Arial", "B", 11)
        self.cell(0, 10, title, ln=True)
        self.set_font("Arial", "", 10)
        for line in content.splitlines():
            self.multi_cell(0, 8, line)
        self.ln(5)  # Space after section


def export_report_to_pdf(text_report, filename="skc_report.pdf"):
    """
    Generates a PDF file from a given text report.

    Args:
        text_report (str): Text-based report content.
        filename (str): Output PDF file name.

    Returns:
        None: Writes PDF file to disk.
    """
    pdf = PDF()
    pdf.add_page()
    pdf.section("Analysis Summary", text_report)
    pdf.output(filename)
