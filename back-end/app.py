# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import csv, random, os
from gsheet import random_question, append_feedback, get_random_hn

app = Flask(__name__)
CORS(app)  # enable CORS for local dev; restrict in production

# In-memory "DB"
MESSAGES = [{"id": 1, "text": "hello"}]
_next_id = 2
last_hn = None

# @app.get("/api/messages")
# def get_messages():
#     @app.route("/", methods=["GET"])
#     status = (request.args.get("status") or "Register").strip()

#     # ดึงคำถามตามสถานี (ไทยก่อน ถ้าไม่มีค่อยใช้ EN)
#     try:
#         q = random_question(status=status) or {"status": status, "th": "", "en": ""}
#     except Exception as e:
#         print("[WARN] random_question failed:", e)
#         q = {"status": status, "th": "", "en": ""}

#     question_text = q["th"] if q.get("th") else (q.get("en") or "วันนี้ได้รับบริการส่วนนี้เป็นอย่างไร?")

#     # สุ่ม HN ของสถานีเดียวกัน (แสดงเป็นตัวอย่าง/ช่วยพิมพ์)
#     try:
#         hn_prefill = get_random_hn(status=status) or ""
#     except Exception as e:
#         print("[WARN] get_random_hn failed:", e)
#         hn_prefill = ""

    # return render_template(
    #     "form.html",
    #     status=q.get("status", status),
    #     question_text=question_text,
    #     hn_prefill=hn_prefill
    # )
    # return jsonify({"ok": True, "data": MESSAGES})

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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
