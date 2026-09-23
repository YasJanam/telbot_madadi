import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import base64
import os
from dotenv import load_dotenv



load_dotenv()

# ---------- تنظیمات ----------
"""SHEET_ID = "1AGU9oEj2xMN6Fb0x2wrgMoqICkeDKlnu0UvdXExAN4g" 
CREDENTIALS_FILE = "telegram-bot-madadi-1-c01d2cec4eb5.json"            
WORKSHEET_NAME = "bot-sheet-users"                
"""

SHEET_ID = os.getenv('SHEET_ID')
#CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME')


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def add_or_update_user(telegram_id, username, full_name, phone):
    try:
        creds_b64 = os.getenv("TELEGRAM_CREDENTIALS_BASE64")
    
        if not creds_b64:
            raise ValueError("TELEGRAM_CREDENTIALS_BASE64 not set!")
        
        creds_dict = json.loads(base64.b64decode(creds_b64).decode("utf-8"))
        print(f"📌 client_email: {creds_dict.get('client_email')}")
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)

       
        try:
            ws = sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=10)

       
        if not ws.row_values(1):
            ws.append_row([
                "Timestamp", "Telegram ID", "Username",
                "Full Name", "Phone",
                "Day 1", "Day 2", "Day 3",
            ])

        
        all_ids = ws.col_values(2)
        str_id = str(telegram_id)

        if str_id in all_ids:
            
            row = all_ids.index(str_id) + 1
            ws.update(
                f"A{row}:E{row}",
                [[
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    str_id,
                    username or "",
                    full_name,
                    phone,
                ]],
            )
            print(f"📊 کاربر {telegram_id} آپدیت شد")
            return "updated"
        else:
            
            ws.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str_id,
                username or "",
                full_name,
                phone,
                "", "", "",
            ])
            print(f"📊 کاربر {telegram_id} اضافه شد")
            return "added"

    except Exception as e:
        print(f"❌ خطا در گوگل شیت: {e}")
        return "error"