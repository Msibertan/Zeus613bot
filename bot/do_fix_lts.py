import zipfile
import os
import re

path = r"c:\Users\rabot\OneDrive\Desktop\Zeus\companies\ЛТС\template.docx"
out_path = r"c:\Users\rabot\OneDrive\Desktop\Zeus\companies\ЛТС\template_fixed.docx"

mapping = {
    'contract_date': 'var1',
    'full_name': 'var2',
    'passport_number': 'var3',
    'passport_issued_by': 'var4',
    'passport_issued_date': 'var5',
    'address': 'var6',
    'phone': 'var7',
    'car_model': 'var8',
    'car_release_year': 'var9',
    'vin_code': 'var10',
    'mileage': 'var11',
    'engine_volume': 'var12',
    'fuel_type': 'var13',
    'car_color': 'var14',
    'customs_rub': 'var15',
    'price_rub': 'var16',
    'total_price': 'var17',
    'delivery_address': 'var18',
    'contract_number': 'contract_number'
}

with zipfile.ZipFile(path, 'r') as zf:
    xml = zf.read('word/document.xml').decode('utf-8')

# The xml might have formatting tags intermixed within the braces {} like {</w:t><w:t> contract_date </w:t>}
# To handle this robustly, we first replace exact keys we find if they have `{ key }` logic
# Actually, since word formats can split text arbitrarily, the safest is to look for the literal words 
# if they are guaranteed to only appear as variables. But it's safer to deal with the exact fragments.
# Let's clean up any tags between { and } first, or we can just replace the raw names if we assume 
# curly braces are already separate.

# The user's earlier script `fix_lts.py` did: re.sub(r'(?<![A-Za-z_])' + k + r'(?![A-Za-z_])', f'var{i+1}', xml)
# Let's see if we can do something similar but also format with {{ }}
# But wait, if they ALREADY have { } around them, and we replace `contract_date` with `{{ var1 }}`, 
# we will get `{ {{ var1 }} }`!
# So we need to clean up `{` and `}` around them.
# Let's do a direct approach: replace `{` and `}` with nothing when they are near our variables, or just replace the whole `{ key }` block.
# Since Word XML splits text, the `{` and `}` might be in separate XML text nodes.

# Let's strip all XML tags to find the EXACT text, then we know what the user sees.
text_only = re.sub(r'<[^>]+>', '', xml)

# We will just iterate through the mapping, and do a regex replace on the XML
for old_key, new_var in mapping.items():
    # We want to replace `{ old_key }` with `{{ new_var }}`
    # old_key might be split by XML tags. 
    # Example: {<w:t> contract_date </w:t>}
    # We will build a regex that allows optional XML tags and whitespace between every character of `{ old_key }`
    
    # Construct an expression that matches '{' + optional spaces/tags + old_key + optional spaces/tags + '}'
    # But wait, building a regex for every char is complex. 
    # Since we saw in the earlier python run: '{ contract_date }' were found, it means they are somewhat intact.
    # Let's just find `{` then any HTML tags/spaces then `old_key` then any HTML tags/spaces then `}`
    
    pattern = r'\{([\s<a-zA-Z0-9/:\-=">]*?)' + old_key + r'([\s<a-zA-Z0-9/:\-=">]*?)\}'
    
    def repl(match):
        # We need to preserve the XML tags that might be inside to not break styling,
        # but the {{ and }} must be properly formed.
        # Safest is to just place {{ new_var }} in the exact same XML node where the old variable was.
        # Actually, DocxTemplate handles tags inside {{ }} natively if they are well-formed!
        # But even better: we replace the whole match with `{{ ` + new_var + ` }}`
        return f'{{{{ {new_var} }}}}'
        
    xml, count = re.subn(pattern, repl, xml)
    print(f"Replaced {old_key} -> {new_var} ({count} times)")

with zipfile.ZipFile(path, 'r') as zin:
    with zipfile.ZipFile(out_path, 'w') as zout:
        for item in zin.infolist():
            if item.filename == 'word/document.xml':
                zout.writestr(item, xml.encode('utf-8'))
            else:
                zout.writestr(item, zin.read(item.filename))

os.remove(path)
os.rename(out_path, path)
print("Finished saving fixed template.")
