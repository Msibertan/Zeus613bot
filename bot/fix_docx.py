import zipfile
import os

docx_path = "templates_queue/template.docx"
temp_dir = "templates_queue/temp_docx"

# Extract
with zipfile.ZipFile(docx_path, 'r') as zf:
    zf.extractall(temp_dir)

# Read and modify document.xml
xml_path = os.path.join(temp_dir, "word", "document.xml")
with open(xml_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace Node.js docxtemplater syntax with Python docxtpl syntax
content = content.replace("{%", "{{").replace("%}", "}}")

# Write back
with open(xml_path, "w", encoding="utf-8") as f:
    f.write(content)

# Re-zip
with zipfile.ZipFile(docx_path.replace(".docx", "_fixed.docx"), 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, temp_dir)
            zf.write(file_path, arcname)

print("DOCX fixed!")
