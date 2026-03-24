import os
import uuid
from docxtpl import DocxTemplate
from docx2pdf import convert

def generate_docx(template_path, context, output_dir="generated"):
    os.makedirs(output_dir, exist_ok=True)
    doc = DocxTemplate(template_path)

    # Заполняем переменные
    doc.render(context)

    # Сохраняем .docx
    file_id = str(uuid.uuid4())
    docx_path = os.path.join(output_dir, f"{file_id}.docx")
    doc.save(docx_path)
    return docx_path

def generate_pdf(docx_path):
    pdf_path = docx_path.replace(".docx", ".pdf")
    convert(docx_path, pdf_path)
    return pdf_path