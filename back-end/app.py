# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import csv, random, os
from gsheet import random_question, append_feedback, get_random_hn
from datetime import datetime

app = Flask(__name__)
CORS(app)  # enable CORS for local dev; restrict in production

# In-memory "DB"
MESSAGES = [{"id": 1, "text": "hello"}]
_next_id = 2
last_hn = None
CSV_FILE = os.path.join(os.path.dirname(__file__), "feedback.csv")
CSV_HEADER = ["HN", "Topic", "Rating", "Time"]
USE_SHEETS = False
gs = None

CSV_QUESTIONS = os.path.join(os.path.dirname(__file__), "questions.csv")

# ---- Tiny cache so we don't re-read CSV every request ----
_QUESTIONS_BY_STATUS = None

def load_questions():
    """Load questions.csv into a dict: {status_upper: [(th, en), ...]}."""
    global _QUESTIONS_BY_STATUS
    if _QUESTIONS_BY_STATUS is not None:
        return _QUESTIONS_BY_STATUS

    data = {}
    # utf-8-sig handles BOM if the file came from Excel
    with open(CSV_QUESTIONS, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = (row.get("Status") or "").strip().upper()
            th = (row.get("Question_th") or "").strip()
            en = (row.get("Question_en") or "").strip()
            if not status or (not th and not en):
                continue
            data.setdefault(status, []).append((th, en))
    _QUESTIONS_BY_STATUS = data
    return _QUESTIONS_BY_STATUS

def random_question_from_csv(status: str | None) -> str:
    """Pick a random question for a given status; prefer TH, fallback EN."""
    allq = load_questions()
    key = (status or "").strip().upper()
    # If no status or not found, you can choose to fallback to a default pool
    if key and key in allq:
        th, en = random.choice(allq[key])
        return th or en
    # Fallback: any status (optional)
    if allq:
        th, en = random.choice(random.choice(list(allq.values())))
        return th or en
    # Final fallback
    return "วันนี้ได้รับบริการส่วนนี้เป็นอย่างไร?"

def ensure_csv():
    """สร้างไฟล์ CSV พร้อมหัวคอลัมน์ถ้ายังไม่มี"""
    exists = os.path.exists(CSV_FILE)
    if not exists:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)


def append_csv_row(hn: str, topic: str, rating: int, comment: str):
    """บันทึก 1 แถวลง feedback.csv"""
    ensure_csv()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([hn, topic, rating, comment, now])

@app.post("/api/feedback")
def save_feedback():
    body = request.get_json(silent=True) or {}
    hn = (body.get("hn") or "").strip()
    status = (body.get("status") or "").strip()
    question = (body.get("question") or "").strip()
    rating = int(body.get("rating") or 0)
    comment = (body.get("comment") or "").strip()

    if not hn:
        return jsonify({"ok": False, "error": "HN is required"}), 400

    try:
        from gsheet import append_feedback
        append_feedback(hn, status, question, rating, comment)
        return jsonify({"ok": True, "msg": "Feedback saved"})
    except Exception as e:
        print("[ERROR] append_feedback:", e)
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/api/messages")
def create_message():
    global _next_id
    body = request.get_json(silent=True) or {}
    text = body.get("text")
    if not text:
        return jsonify({"ok": False, "error": "Field 'text' is required"}), 400
    msg = {"id": _next_id, "text": text}
    MESSAGES.append(msg)
    _next_id += 1
    return jsonify({"ok": True, "data": msg}), 201

@app.post("/trigger/qr")
def trigger_qr():
    global last_hn
    # Parse safely
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    hn = data.get("hn") or data.get("code") or request.args.get("hn") or request.args.get("code")

    # Debug logs (dev only)
    print("Headers:", dict(request.headers))
    print("Raw data:", request.data)
    print("Parsed data:", data)

    if not hn:
        return jsonify({"ok": False, "error": "Field 'hn' (or 'code') is required"}), 400
    
    last_hn = hn

    # ... do your logic here ...
    return jsonify({"ok": True, "hn": hn}), 200

@app.get("/trigger/qr")
def get_last_hn():
    if not last_hn:
        return jsonify({"ok": False, "error": "No HN posted yet"}), 404
    return jsonify({"ok": True, "hn": last_hn}), 200

@app.get("/api/question")
def api_form():
    """
    Query: ?status=Register/Vital/Doctor/Prep/Payment (optional)
    Returns: { "question": "...", "hn": "<last_hn or null>" }
    """
    global last_hn
    status = (request.args.get("status") or "").strip()

    # 1) Try CSV
    question_text = random_question_from_csv(status)

    # 2) (Optional) If you later turn on Sheets, you can override here
    if USE_SHEETS and hasattr(gs, "random_question"):
        try:
            q = gs.random_question(status=status)
            if q:
                question_text = q.get("th") or q.get("en") or question_text
        except Exception as e:
            print("[WARN] random_question (sheets) failed, keep CSV:", e)

    return jsonify({"question": question_text, "hn": last_hn})

@app.post("/api/submit")
def api_feedback():
    """
    body:
    {
      "hn": "AAAU0GAI",
      "status": "Register",
      "question": "การลงทะเบียนสะดวกหรือไม่?",
      "rating": 5,
    }
    """
    body = request.get_json(silent=True) or {}
    hn = (body.get("hn") or "").strip()
    status = (body.get("status") or "").strip()
    rating = int(body.get("rating") or 0)
    comment = (body.get("comment") or "").strip()

    if not hn:
        return jsonify({"ok": False, "error": "HN is required"}), 400

    # 1) ถ้าเปิดโหมด Sheets และใช้ได้ ให้พยายามลงชีทก่อน
    sheet_saved = False
    sheet_error = None
    if USE_SHEETS and hasattr(gs, "append_feedback"):
        try:
            gs.append_feedback(hn, status, "", rating, comment)  # ไม่เก็บ question ตามหัวคอลัมน์ที่ระบุ
            sheet_saved = True
        except Exception as e:
            sheet_error = str(e)
            print("[WARN] append_feedback to Google Sheet failed, fallback CSV:", e)

    # 2) ถ้า sheet ใช้ไม่ได้ หรือเลือกใช้ CSV ก็ลง CSV เสมอ
    try:
        append_csv_row(hn, status, rating, comment)
    except Exception as e:
        return jsonify({"ok": False, "error": f"CSV write failed: {e}"}), 500

    return jsonify({
        "ok": True,
        "saved": True,
        "sheet_saved": sheet_saved,
        "sheet_error": sheet_error
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
