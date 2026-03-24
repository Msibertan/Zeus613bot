import zipfile
import os
import re

path = r"c:\Users\rabot\OneDrive\Desktop\Zeus\companies\ЛТС\template.docx"
out_path = r"c:\Users\rabot\OneDrive\Desktop\Zeus\companies\ЛТС\template_fixed.docx"

mapping = {
    'var1': ['var1', 'contract_date'],
    'var2': ['var2', 'full_name'],
    'var3': ['var3', 'passport_number'],
    'var4': ['var4', 'passport_issued_by'],
    'var5': ['var5', 'passport_issued_date'],
    'var6': ['var6', 'address', 'delivery_address'],
    'var7': ['var7', 'phone'],
    'var8': ['var8', 'car_model'],
    'var9': ['var9', 'car_release_year'],
    'var10': ['var10', 'vin_code'],
    'var11': ['var11', 'mileage'],
    'var12': ['var12', 'engine_volume'],
    'var13': ['var13', 'fuel_type'],
    'var14': ['var14', 'car_color'],
    'var15': ['var15', 'customs_rub'],
    'var16': ['var16', 'price_rub'],
    'var17': ['var17', 'total_price'],
    'var18': ['var18', 'delivery_address'],
    'contract_number': ['contract_number']
}

with zipfile.ZipFile(path, 'r') as zf:
    xml = zf.read('word/document.xml').decode('utf-8')

original_xml = xml

# Pass 1: Replace matching keywords (or previously changed var1) with a robust marker
for new_var, old_keys in mapping.items():
    for old_key in old_keys:
        # We replace the text node containing the keyword.
        # But wait, we just replace the whole word. 
        xml = re.sub(r'(?<![A-Za-z0-9_])' + old_key + r'(?![A-Za-z0-9_])', f'__MARK_{new_var}__', xml)

# Pass 2: Clean up braces ONLY around __MARK_varX__
for new_var in mapping.keys():
    # Attempt to replace `{ ... __MARK_varX__ ... }` with `{{ varX }}` stripping internal formatting.
    # We must restrict it loosely to allow XML tags between `{` and `__MARK_` and `}`
    # E.g. {<w:t xml:space="preserve"> __MARK_var1__ </w:t>} => {{ var1 }}
    # We remove anything from { to the marker, and from the marker to }
    pattern = r'\{([\s<a-zA-Z0-9/:\-=">]*?)__MARK_' + new_var + r'__([\s<a-zA-Z0-9/:\-=">]*?)\}'
    
    # We use a repl function to keep the tags intact but place `{{ varX }}` inside them
    # Wait, the safest is to just KEEP the formatting and just place `{{ new_var }}`!
    # If we keep the formatting, we just change { to {{ and } to }} but wait, { is one char, {{ is two.
    def repl(match):
        tags1 = match.group(1)
        tags2 = match.group(2)
        # return {{ with the exact same tags inside. Docxtpl handles split {{...}} but it's risky.
        # Even simpler: just replace '{' with '' and '}' with '' in the pattern, 
        # and instead place {{ new_var }} replacing the marker!
        return f'{tags1}{{{{ {new_var} }}}}{tags2}'
        
    xml = re.sub(pattern, repl, xml)
    
    # Pass 3: If any markers are still left (meaning they weren't inside {} originally or 
    # the regex above missed them because of weird characters), just replace the marker directly!
    xml = xml.replace(f'__MARK_{new_var}__', f'{{{{ {new_var} }}}}')

with zipfile.ZipFile(path, 'r') as zin:
    with zipfile.ZipFile(out_path, 'w') as zout:
        for item in zin.infolist():
            if item.filename == 'word/document.xml':
                zout.writestr(item, xml.encode('utf-8'))
            else:
                zout.writestr(item, zin.read(item.filename))

os.remove(path)
os.rename(out_path, path)
print('Fixed successfully!')

text = re.sub(r'<[^>]+>', '', xml)
matches = re.findall(r'\{\{[^{}]*?\}\}|var\d+|contract_\w+', text)
print('FINAL VARIABLES IN FILE:', list(set(matches)))
