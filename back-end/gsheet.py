# gsheet.py (เพิ่ม/แก้ส่วนนี้)

import random
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ===== ตั้งค่าชีท =====
SPREADSHEET_ID  = "14Ztjiuqj7NT_-ft4A3iU0XteRP9OG7X3Ne6Sn-PpTNc"
PATIENT_SHEET   = "Patient"   # HN, Name, Age, Nationality, Status
QUESTION_SHEET  = "Sheet4"    # Status, Question_th, Question_en
COMMENT_SHEET   = "Comment"   # HN | Status | Question | Rating | Comment | Time

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def _client():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)

def _open_sheet():
    return _client().open_by_key(SPREADSHEET_ID)

# ---------- Patient APIs ----------

def list_hn(limit=200):
    sh = _open_sheet()
    ws = sh.worksheet(PATIENT_SHEET)
    rows = ws.get_all_records()
    hns = [str(r.get("HN", "")).strip() for r in rows if r.get("HN")]
    return hns[:limit]

def get_patient(hn: str):
    sh = _open_sheet()
    ws = sh.worksheet(PATIENT_SHEET)
    rows = ws.get_all_records()
    for r in rows:
        if str(r.get("HN", "")).strip() == str(hn).strip():
            return r
    return None

def get_random_hn(status: str | None = None):
    """สุ่ม HN จากแท็บ Patient ถ้าระบุสถานี จะกรองตามคอลัมน์ Status"""
    sh = _open_sheet()
    ws = sh.worksheet(PATIENT_SHEET)
    rows = ws.get_all_records()
    pool = []
    for r in rows:
        hn = str(r.get("HN", "")).strip()
        st = str(r.get("Status", "")).strip()
        if not hn:
            continue
        if status and st.lower() != status.lower():
            continue
        pool.append(hn)
    if not pool:
        return None
    return random.choice(pool)

# ---------- Questions APIs ----------

def random_question(status: str | None = None):
    """สุ่มคำถามจากแท็บ Sheet4 ตามสถานี (คอลัมน์ Status)"""
    sh = _open_sheet()
    ws = sh.worksheet(QUESTION_SHEET)
    rows = ws.get_all_records()
    items = []
    for r in rows:
        st = str(r.get("Status", "")).strip()
        th = str(r.get("Question_th", "")).strip()
        en = str(r.get("Question_en", "")).strip()
        if status and st.lower() != status.lower():
            continue
        if th or en:
            items.append({"status": st, "th": th, "en": en})
    if not items:
        return None
    return random.choice(items)

# ---------- Append feedback ----------

def append_feedback(hn: str, status: str, question: str, rating: int, comment: str):
    sh = _open_sheet()
    ws = sh.worksheet(COMMENT_SHEET)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([hn, status, question, rating, comment, now], value_input_option="USER_ENTERED")
