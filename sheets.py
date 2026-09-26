import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()


SHEET_ID = os.getenv('SHEET_ID')
#CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
WORKSHEET_NAME = os.getenv('WORKSHEET_NAME')
#CREDS_BASE64 = os.getenv("CREDENTIALS_BASE64")


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def add_or_update_user(bale_id, username, full_name, phone):
    try:
        creds_b64 = os.getenv("CREDENTIALS_BASE64")
    
        if not creds_b64:
            raise ValueError("CREDENTIALS_BASE64 not set!")
        
        try:
            decoded = base64.b64decode(creds_b64).decode("utf-8")
            creds_dict = json.loads(decoded)
        except Exception as e:
            print(f"❌ Error: {e}")
            return "error"

        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)

        try:
            ws = sheet.worksheet(WORKSHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=10)

        # سرستون‌ها
        if not ws.row_values(1):
            ws.append_row([
                "Timestamp", "Telegram ID", "Bale ID", "Username",
                "Full Name", "Phone",
                "Day 1", "Day 2", "Day 3",
            ])

       
        all_ids = ws.col_values(3)
        str_id = str(bale_id)

        if str_id in all_ids:
            row = all_ids.index(str_id) + 1
            
     
            ws.update(f"A{row}", [[datetime.now().strftime("%Y-%m-%d %H:%M:%S")]])
            ws.update(f"C{row}:F{row}", [[
                str_id,          # C = Bale ID
                username or "",  # D = Username
                full_name,       # E = Full Name
                phone,           # F = Phone
            ]])
            
            print(f"📊 کاربر {bale_id} آپدیت شد (Telegram ID دست نخورده)")
            return "updated"
        else:
            ws.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "",                   # 👈 Telegram ID خالی
                str_id,               # 👈 Bale ID
                username or "",
                full_name,
                phone,
                "", "", "",
            ])
            print(f"📊 کاربر {bale_id} اضافه شد")
            return "added"

    except Exception as e:
        print(f"❌ خطا در گوگل شیت: {e}")
        return "error"




def mark_day_sent_in_sheet(bale_id, day):
    try:
        creds_b64 = os.getenv("CREDENTIALS_BASE64")
    
        if not creds_b64:
            raise ValueError("CREDENTIALS_BASE64 not set!")
        
        try:
            decoded = base64.b64decode(creds_b64).decode("utf-8")
            creds_dict = json.loads(decoded)
        except Exception as e:
            print(f"❌ Error: {e}")


        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        ws = sheet.worksheet(WORKSHEET_NAME)

        all_ids = ws.col_values(3)
        str_id = str(bale_id)

        if str_id not in all_ids:
            return False

        row = all_ids.index(str_id) + 1
        col_map = {1: "G", 2: "H", 3: "I"}
        ws.update(f"{col_map[day]}{row}", [["✅"]])
        return True
    except Exception as e:
        print(f"❌ خطا در آپدیت شیت: {e}")
        return False