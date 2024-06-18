import os

GOOGLE_CALENDAR_CREDENTIALS_LOCATION = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_LOCATION")

if GOOGLE_CALENDAR_CREDENTIALS_LOCATION is None:
    print("錯誤：未設置 GOOGLE_CALENDAR_CREDENTIALS_LOCATION 環境變量。")
else:
    print(f"Received path: {GOOGLE_CALENDAR_CREDENTIALS_LOCATION}")
    if os.path.exists(GOOGLE_CALENDAR_CREDENTIALS_LOCATION):
        print("文件存在。")
    else:
        print("文件不存在。")

try:
    with open('/Users/mac/Desktop/GCal-Notion-Sync/credentials.json', 'r') as file:
        print("File can be opened. Contents:")
        print(file.read())
except Exception as e:
    print(f"Error opening file: {e}")