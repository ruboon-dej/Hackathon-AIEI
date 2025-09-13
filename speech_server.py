# speech_server.py
import json, time
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel

SR = 16000
CHUNK_SECONDS = 0.3         # decode more often
MAX_CONTEXT_SECONDS = 12.0
MIN_SECONDS_TO_DECODE = 0.10  # start decoding after 0.1s audio
LANG = None                  # e.g. "th"
TASK = "transcribe"          # or "translate"

app = FastAPI(title="Realtime STT (faster-whisper)")

@app.get("/")
def root():
    return {"ok": True, "ws": "/ws"}

model = WhisperModel("small", device="cpu", compute_type="int8",
                     download_root="models/whisper")

def pcm16_to_float32(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

@app.websocket("/ws")
async def ws_stt(ws: WebSocket):
    await ws.accept()
    print("[WS] connected")
    buf = np.zeros(0, dtype=np.float32)
    last_decode = time.time()
    last_emit = ""
    try:
        while True:
            msg = await ws.receive()
            if "bytes" in msg:
                chunk = pcm16_to_float32(msg["bytes"])
                buf = np.concatenate([buf, chunk])
                if buf.size > int(MAX_CONTEXT_SECONDS * SR):
                    buf = buf[-int(MAX_CONTEXT_SECONDS * SR):]

                sec = buf.size / SR
                if time.time() - last_decode >= CHUNK_SECONDS and sec >= MIN_SECONDS_TO_DECODE:
                    last_decode = time.time()
                    print(f"[DECODE] buffer={sec:.2f}s")
                    segs, _ = model.transcribe(
                        buf, language=LANG, task=TASK,
                        beam_size=1, vad_filter=True,
                        condition_on_previous_text=True
                    )
                    text = "".join((s.text or "") for s in segs).strip()
                    if text and text != last_emit:
                        last_emit = text
                        print(f"[PARTIAL] {text}")
                        await ws.send_text(json.dumps({"type":"partial","result":{"partial":text}}))

            elif "text" in msg and msg["text"].strip().lower() == "flush":
                print("[FLUSH]")
                if buf.size:
                    segs, _ = model.transcribe(
                        buf, language=LANG, task=TASK,
                        beam_size=5, vad_filter=True,
                        condition_on_previous_text=False
                    )
                    text = "".join((s.text or "") for s in segs).strip()
                    print(f"[FINAL] {text}")
                    await ws.send_text(json.dumps({"type":"final","result":{"text":text}}))
                buf = np.zeros(0, dtype=np.float32)
                last_emit = ""
    except WebSocketDisconnect:
        print("[WS] disconnected")
