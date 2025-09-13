import os, json, time
import numpy as np
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel
import gspread
from google.oauth2.service_account import Credentials

SR = 16000
CHUNK_SECONDS = 0.2
MAX_CONTEXT_SECONDS = 12.0
MIN_SECONDS_TO_DECODE = 0.05
LANG = None
TASK = "transcribe"

SERVICE_ACCOUNT_JSON = r"C:\keys\stt-sa.json"
SPREADSHEET_ID = "PUT_YOUR_SHEET_ID_HERE"
WORKSHEET_NAME = "Transcripts"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

def gsheets_client():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    return gspread.authorize(creds)

def get_worksheet(gc):
    sh = gc.open_by_key(SPREADSHEET_ID)
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows="1000", cols="10")
        ws.append_row(["#", "Start(s)", "End(s)", "Duration(s)", "Language", "Text", "SavedAt"])
    return ws

_gc = gsheets_client()
_ws = get_worksheet(_gc)
print("[SHEETS] Ready. Spreadsheet:", SPREADSHEET_ID, "Worksheet:", WORKSHEET_NAME)

def append_row_sheets(idx, start_s, end_s, dur_s, lang, text, ts):
    global _gc, _ws
    try:
        _ws.append_row([idx, start_s, end_s, dur_s, lang, text, ts], value_input_option="RAW")
    except gspread.exceptions.APIError:
        _gc = gsheets_client()
        _ws = get_worksheet(_gc)
        _ws.append_row([idx, start_s, end_s, dur_s, lang, text, ts], value_input_option="RAW")

app = FastAPI(title="Realtime STT → Google Sheets")

@app.get("/")
def root():
    return {"ok": True, "ws": "/ws", "sheet": SPREADSHEET_ID, "tab": WORKSHEET_NAME, "lang": LANG, "task": TASK}

model = WhisperModel("small", device="cpu", compute_type="int8", download_root="models/whisper")

def pcm16_to_float32(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

@app.websocket("/ws")
async def ws_stt(ws: WebSocket):
    await ws.accept()
    print("[WS] connected")
    buf = np.zeros(0, dtype=np.float32)
    last_decode = time.time()
    last_partial = ""
    utt_index = 1
    try:
        while True:
            msg = await ws.receive()
            if "bytes" in msg:
                buf = np.concatenate([buf, pcm16_to_float32(msg["bytes"])])
                if buf.size > int(MAX_CONTEXT_SECONDS * SR):
                    buf = buf[-int(MAX_CONTEXT_SECONDS * SR):]
                sec = buf.size / SR
                if time.time() - last_decode >= CHUNK_SECONDS and sec >= MIN_SECONDS_TO_DECODE:
                    last_decode = time.time()
                    segs, info = model.transcribe(
                        buf, language=LANG, task=TASK,
                        beam_size=1, vad_filter=True,
                        condition_on_previous_text=True, temperature=0.0
                    )
                    partial_text = "".join((s.text or "") for s in segs).strip()
                    if partial_text and partial_text != last_partial:
                        last_partial = partial_text
                        await ws.send_text(json.dumps({
                            "type":"partial",
                            "result":{"partial":partial_text, "detected_language":getattr(info,"language",None)}
                        }))
                    final_cut_sec = 0.2
                    finals = [s for s in segs if s.end is not None and (buf.size/SR - s.end) >= final_cut_sec]
                    if finals:
                        for s in finals:
                            text = (s.text or "").strip()
                            if not text:
                                continue
                            lang = getattr(info, "language", None)
                            start_s = round(float(s.start or 0.0), 3)
                            end_s   = round(float(s.end or 0.0), 3)
                            dur_s   = round(end_s - start_s, 3)
                            saved   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            await ws.send_text(json.dumps({
                                "type":"final",
                                "result":{"index":utt_index,"start":start_s,"end":end_s,
                                          "text":text,"detected_language":lang}
                            }))
                            try:
                                append_row_sheets(utt_index, start_s, end_s, dur_s, lang, text, saved)
                                print(f"[SHEETS] wrote row #{utt_index}")
                            except Exception as e:
                                print(f"[SHEETS] ERROR: {e}")
                            utt_index += 1
                        last_end = max(s.end for s in finals if s.end is not None)
                        cut = int(last_end * SR)
                        if 0 < cut <= buf.size:
                            buf = buf[cut:]
                            last_partial = ""
            elif "text" in msg and msg["text"].strip().lower() == "flush":
                if buf.size:
                    segs, info = model.transcribe(
                        buf, language=LANG, task=TASK,
                        beam_size=1, vad_filter=True,
                        condition_on_previous_text=False, temperature=0.0
                    )
                    text = "".join((s.text or "") for s in segs).strip()
                    if text:
                        lang = getattr(info, "language", None)
                        saved = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        try:
                            append_row_sheets(utt_index, None, None, None, lang, text, saved)
                            print(f"[SHEETS] wrote row #{utt_index}")
                        except Exception as e:
                            print(f"[SHEETS] ERROR: {e}")
                        await ws.send_text(json.dumps({"type":"final","result":{"index":utt_index,"text":text,"detected_language":lang}}))
                        utt_index += 1
                buf = np.zeros(0, dtype=np.float32); last_partial = ""
    except WebSocketDisconnect:
        print("[WS] disconnected")
