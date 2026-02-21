import gspread
from google.oauth2.service_account import Credentials
from collections import defaultdict

scopes = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]
creds = Credentials.from_service_account_file(
    'credentials/service-account.json',
    scopes=scopes
)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key('1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE')
sheet = spreadsheet.worksheet('발주(리오더)_동대문')
data = sheet.get_all_values()

# Check P column header
print("=== Column P (입고 확인) 구조 ===")
print(f"P열 헤더: {data[0][15] if len(data[0]) > 15 else 'N/A'}")

# Sample P column values
print("\n=== P열 샘플 데이터 ===")
for i, row in enumerate(data[1:20], start=2):
    if row[0] == '노어' and len(row) > 15:
        p_val = row[15]
        print(f"  Row {i}: 품번={row[3][:15]}..., 수량={row[4]}, P열={p_val}")

# Calculate 미수령발주량 (P열 = FALSE or empty)
print("\n=== 미수령발주량 계산 (P열 != TRUE) ===")
in_transit = defaultdict(int)

for row in data[2:]:  # Skip header and instruction
    if row[0] != '노어':
        continue
    if len(row) <= 15:
        continue
    
    barcode = row[3]
    try:
        qty = int(row[4]) if row[4] else 0
    except:
        qty = 0
    
    p_value = row[15].strip().upper() if len(row) > 15 else ''
    
    # P열이 TRUE가 아니면 미입고
    if p_value != 'TRUE':
        in_transit[barcode] += qty

print(f"미입고 품번 수: {len(in_transit)}")
print(f"총 미입고 수량: {sum(in_transit.values())}")

print("\n=== 미입고 상위 10개 ===")
for barcode, qty in sorted(in_transit.items(), key=lambda x: -x[1])[:10]:
    print(f"  {barcode}: {qty}개")
