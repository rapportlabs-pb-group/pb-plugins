import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

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

# Get all data
data = sheet.get_all_values()
headers = data[0]

print("=== Column Structure ===")
for i, h in enumerate(headers[:15]):
    print(f"  [{chr(65+i)}] Col {i}: {h}")

print("\n=== Sample Data (rows 2-10) ===")
for row in data[1:10]:
    if row[0]:  # If brand exists
        print(f"  브랜드:{row[0]}, 발주일:{row[2]}, 바코드:{row[3]}, 수량:{row[4]}")

print("\n=== Recent Orders (non-empty rows from end) ===")
count = 0
for row in reversed(data[1:]):
    if row[0] and row[2]:  # Brand and date exist
        print(f"  브랜드:{row[0]}, 발주일:{row[2]}, 바코드:{row[3]}, 수량:{row[4]}")
        count += 1
        if count >= 10:
            break

# Count by brand
print("\n=== Orders by Brand ===")
brand_counts = {}
for row in data[1:]:
    if row[0]:
        brand = row[0]
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
for brand, cnt in sorted(brand_counts.items(), key=lambda x: -x[1]):
    print(f"  {brand}: {cnt}")
