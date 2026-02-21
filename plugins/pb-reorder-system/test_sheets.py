import gspread
from google.oauth2.service_account import Credentials

# Setup credentials
scopes = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]
creds = Credentials.from_service_account_file(
    'credentials/service-account.json',
    scopes=scopes
)
client = gspread.authorize(creds)

# Open the spreadsheet
spreadsheet_id = '1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE'
spreadsheet = client.open_by_key(spreadsheet_id)

# List all worksheets
print("=== Available Worksheets ===")
for ws in spreadsheet.worksheets():
    print(f"  - {ws.title} (rows: {ws.row_count})")

# Try to access the reorder sheet
print("\n=== 발주(리오더)_동대문 Sheet Sample ===")
try:
    sheet = spreadsheet.worksheet('발주(리오더)_동대문')
    # Get headers and first few rows
    data = sheet.get_all_values()
    if data:
        print(f"Headers: {data[0][:10]}")  # First 10 columns
        print(f"Total rows: {len(data)}")
        # Show last 5 data rows (recent orders)
        print("\nRecent entries (last 5 rows):")
        for row in data[-5:]:
            print(f"  {row[:6]}")  # First 6 columns
except Exception as e:
    print(f"Error: {e}")
