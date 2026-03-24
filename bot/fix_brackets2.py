import zipfile, re, os

path = "c:/Users/rabot/OneDrive/Desktop/Zeus/templates_queue/template.docx"
out_path = "c:/Users/rabot/OneDrive/Desktop/Zeus/templates_queue/template_fixed.docx"

with zipfile.ZipFile(path, 'r') as zf:
    xml = zf.read('word/document.xml').decode('utf-8')

# Let's print the occurrences of variables to see how they are formatted
variables = ["queue_num", "before_num", "time", "registered_time", "brand", "model", "vin_code", "fio", "qr_image", "qr_placeholder"]

for var in variables:
    # See if the variable is in the xml at all
    print(f"{var} in xml: {var in xml}")

# The nodejs templates use either {var} or {%var%}.
# We should replace \{[^{]*?var[^{]*?\} with {{var}} safely.
# Wait, let's just use re.sub for each variable.
# We look for a `{` followed by optional XML tags or `%`, then the variable name, then optional XML tags or `%`, then `}`.
# This assumes the variable name itself is NOT split by XML tags. Word often splits text!
# Let's print a context around the variable:

for var in variables:
    matches = re.finditer(f".{{0,30}}{var}.{{0,30}}", xml)
    for m in matches:
         print(f"Context for {var}: {m.group(0)}")

# A safe replacement if the word is not split:
for var in variables:
    # Match `{` then anything not `{` or `}`, containing the var, ending in `}`
    # Wait, what if there are no braces? Actually let's assume {var} or {%var%}
    xml = re.sub(r'\{[^}]*?' + var + r'[^}]*?\}', '{{' + var + '}}', xml)

print("Found {: ", xml.count("{"))
print("Found }: ", xml.count("}"))
print("Found {{: ", xml.count("{{"))
print("Found }}: ", xml.count("}}"))

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
