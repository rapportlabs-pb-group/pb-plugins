import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
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

# Parse date helper
def parse_date(date_str):
    if not date_str or date_str == '수기':
        return None
    try:
        if '-' in date_str:
            return datetime.strptime(date_str, '%Y-%m-%d')
        elif '/' in date_str:
            return datetime.strptime(date_str, '%Y/%m/%d')
    except:
        return None
    return None

# Analyze in-transit (ordered but not received within lead time)
LEAD_TIME_DAYS = 14
cutoff_date = datetime.now() - timedelta(days=LEAD_TIME_DAYS)

in_transit = defaultdict(lambda: {'ordered': 0, 'received': 0})

for row in data[2:]:  # Skip header and instruction row
    if row[0] != '노어':
        continue
    
    order_date = parse_date(row[2])
    if not order_date:
        continue
    
    barcode = row[3]
    try:
        qty_ordered = int(row[4]) if row[4] else 0
        qty_received = int(row[13]) if row[13] else 0  # Column N
    except:
        qty_ordered = 0
        qty_received = 0
    
    # Only count orders within lead time window
    if order_date >= cutoff_date:
        in_transit[barcode]['ordered'] += qty_ordered
        in_transit[barcode]['received'] += qty_received
        in_transit[barcode]['last_order_date'] = order_date.strftime('%Y-%m-%d')

print("=== In-Transit Analysis (Last 14 Days) ===")
print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
print(f"SKUs with recent orders: {len(in_transit)}")

print("\n=== SKUs with Pending In-Transit ===")
pending_count = 0
for barcode, data in sorted(in_transit.items(), key=lambda x: x[1]['ordered'] - x[1]['received'], reverse=True)[:20]:
    pending = data['ordered'] - data['received']
    if pending > 0:
        pending_count += 1
        print(f"  {barcode}: 발주={data['ordered']}, 입고={data['received']}, 미입고={pending}, 최근발주={data.get('last_order_date', 'N/A')}")

print(f"\nTotal SKUs with pending in-transit: {pending_count}")
print(f"Total in-transit qty: {sum(d['ordered'] - d['received'] for d in in_transit.values() if d['ordered'] > d['received'])}")
