import zipfile, re, os

path = "c:/Users/rabot/OneDrive/Desktop/Zeus/companies/ЛТС/template.docx"
out_path = "c:/Users/rabot/OneDrive/Desktop/Zeus/companies/ЛТС/template_fixed.docx"

oreon_keys = [
    'contract_date', 'full_name', 'passport_number', 'passport_issued_by', 
    'passport_issued_date', 'address', 'phone', 'car_model', 'car_release_year', 
    'vin_code', 'mileage', 'engine_volume', 'fuel_type', 'car_color', 
    'customs_rub', 'price_rub', 'total_price', 'delivery_address'
]

# We want to replace delivery_address FIRST so that 'address' doesn't override it.
# Actually, if we use regex to match the exact word surrounded by non-alphanumeric, it avoids substring issues.
with zipfile.ZipFile(path, 'r') as zf:
    xml = zf.read('word/document.xml').decode('utf-8')

for i, k in enumerate(oreon_keys):
    # Match the exact key surrounded by non-alphanumeric (like `<w:t>address</w:t>`)
    # var{i+1}
    xml = re.sub(r'(?<![A-Za-z_])' + k + r'(?![A-Za-z_])', f'var{i+1}', xml)

with zipfile.ZipFile(path, 'r') as zin:
    with zipfile.ZipFile(out_path, 'w') as zout:
        for item in zin.infolist():
            if item.filename == 'word/document.xml':
                zout.writestr(item, xml.encode('utf-8'))
            else:
                zout.writestr(item, zin.read(item.filename))

os.remove(path)
os.rename(out_path, path)
print('Fixed securely!')
