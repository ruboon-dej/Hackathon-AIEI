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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
