from pathlib import Path
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
try:
    from docx2pdf import convert
except Exception:
    convert = None

def render_doc(template_path: str, context: dict, output_dir: str, filename_stem: str, images: dict = None):
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    t = Path(template_path)
    if not t.exists():
        raise FileNotFoundError(f"Template not found: {t}")
    doc = DocxTemplate(str(t))
    
    if images:
        for key, img_data in images.items():
            context[key] = InlineImage(doc, image_descriptor=img_data['stream'], width=Mm(img_data.get('width_mm', 45)))
            
    doc.render(context)
    docx_path = output_dir / f"{filename_stem}.docx"
    doc.save(str(docx_path))
    pdf_path = None
    if convert:
        try:
            pdf_path = docx_path.with_suffix(".pdf")
            convert(str(docx_path), str(pdf_path))
        except Exception:
            pdf_path = None
    return docx_path, pdf_path
