"""Turn the sample income documents (.txt) into PDFs for testing uploads."""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_income_documents"


def text_to_pdf(text_path: Path) -> Path:
    pdf_path = text_path.with_suffix(".pdf")
    styles = getSampleStyleSheet()
    lines = text_path.read_text(encoding="utf-8").splitlines()

    story = [Paragraph(lines[0], styles["Title"]), Spacer(1, 12)]
    for line in lines[1:]:
        story.append(Paragraph(line if line.strip() else "&nbsp;", styles["BodyText"]))

    SimpleDocTemplate(str(pdf_path), pagesize=A4).build(story)
    return pdf_path


if __name__ == "__main__":
    for txt in sorted(SAMPLE_DIR.glob("*.txt")):
        print("created", text_to_pdf(txt).name)
