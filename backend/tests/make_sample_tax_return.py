"""Generate a FICTIONAL 1040-style return. All names, numbers and addresses are invented."""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "fixtures" / "sample_tax_return.pdf"


def build(path=OUT):
    c = canvas.Canvas(str(path), pagesize=letter)
    def page(lines):
        y = 740
        for line in lines:
            c.setFont("Helvetica-Bold" if line.isupper() else "Helvetica", 11)
            c.drawString(60, y, line); y -= 20
        c.showPage()
    page(["FORM 1040 - U.S. INDIVIDUAL INCOME TAX RETURN (SAMPLE - FICTIONAL DATA)",
          "Tax year 2025",
          "Taxpayer name: Jordan A. Sample",
          "Your social security number: 123-45-6789",
          "Spouse name: Riley Sample",
          "Spouse social security number: 234-56-7891",
          "Date of birth: 04/12/1984",
          "Home address: 742 Evergreen Terrace, Springfield, IL 62704",
          "Phone: (555) 010-4477   Email: jordan.sample@example.com",
          "Dependent: Casey Sample, SSN 345-67-8912",
          "Wages, salaries, tips (line 1a): 84,250",
          "Total income (line 9): 91,480",
          "Adjusted gross income (line 11): 88,120"])
    page(["REFUND - DIRECT DEPOSIT",
          "Routing number: 021000021",
          "Account number: 4938291034",
          "Type: Checking",
          "Payer EIN: 12-3456789",
          "Note: For questions, the taxpayer's savings account ending in 4931 was also used.",
          "Amount you owe (line 37): 0"])
    c.save()


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    build()
