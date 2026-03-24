import zipfile, re, os

path = "c:/Users/rabot/OneDrive/Desktop/Zeus/templates_queue/template.docx"
out_path = "c:/Users/rabot/OneDrive/Desktop/Zeus/templates_queue/template_fixed.docx"

with zipfile.ZipFile(path, 'r') as zf:
    xml = zf.read('word/document.xml').decode('utf-8')

# First, remove all XML tags inside a potential bracketed string.
# Actually, the simplest is to un-split XML elements that break brackets, but it's hard.
# Let's just find all {text} and replace with {{text}}.
# The variables are: queue_num, before_num, time, registered_time, brand, model, vin_code, fio, qr_image

variables = ["queue_num", "before_num", "time", "registered_time", "brand", "model", "vin_code", "fio", "qr_image"]

# We will remove any XML tags that appear between { and }
# Wait, a better way is to simply strip XML tags if they interrupt a variable name. 
# But let's assume the user typed {queue_num} cleanly, or we can just brute force replace.
import xml.etree.ElementTree as ET

# Instead of complex XML parsing, let's just do a clean replace 
# If docxtemplater was used, single `{}` is default for docxtemplater! 
# docxtpl uses `{{}}`.
# Let's replace `{` with `{{` and `}` with `}}` for our specific variables.

for var in variables:
    # It could be {var} or { var } or {%var%} or {% var %}
    # Let's replace any `{var}` with `{{var}}`
    xml = re.sub(r'\{%?\s*' + var + r'\s*%?\}', '{{' + var + '}}', xml)

# Let's also check if there are any unbalanced brackets left:
print("Found {:", xml.count("{"))
print("Found }:", xml.count("}"))
print("Found {{:", xml.count("{{"))
print("Found }}:", xml.count("}}"))

with zipfile.ZipFile(path, 'r') as zf_in:
    with zipfile.ZipFile(out_path, 'w') as zf_out:
        for item in zf_in.infolist():
            if item.filename == 'word/document.xml':
                zf_out.writestr(item, xml.encode('utf-8'))
            else:
                zf_out.writestr(item, zf_in.read(item.filename))

os.remove(path)
os.rename(out_path, path)
print("Done!")
