# back-end/app.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os, time
import pandas as pd

# -----------------------------
# Config
# -----------------------------
# Set your Google Sheet CSV URL here OR via env var SHEET_URL
# Example (public CSV export):
# https://docs.google.com/spreadsheets/d/XXXXXXXXXXXX/export?format=csv
SHEET_URL = os.getenv(
    "SHEET_URL",
    "https://docs.google.com/spreadsheets/d/14Ztjiuqj7NT_-ft4A3iU0XteRP9OG7X3Ne6Sn-PpTNc/export?format=csv",
)
SHEET_TTL_SEC = int(os.getenv("SHEET_TTL_SEC", "300"))  # refresh every 5 min

app = FastAPI()

# Allow your Next.js dev server to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# WebSocket manager
# -----------------------------
class WSManager:
    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        # Broadcast to all connected clients, prune broken sockets
        for ws in list(self.active):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)

manager = WSManager()

@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await manager.connect(ws)
    try:
        # Optional: receive pings to keep the socket alive
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

# -----------------------------
# Sheet loader (cached)
# -----------------------------
_sheet_df: Optional[pd.DataFrame] = None
_sheet_ts: float = 0.0

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    for c in ("HN", "Nationality", "Status", "Name", "Age"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df

def load_sheet(force: bool = False) -> Optional[pd.DataFrame]:
    global _sheet_df, _sheet_ts
    # Lazy load + TTL refresh
    if (
        force
        or _sheet_df is None
        or (time.time() - _sheet_ts) > SHEET_TTL_SEC
    ):
        try:
            df = pd.read_csv(SHEET_URL)
            _sheet_df = _normalize_df(df)
            _sheet_ts = time.time()
            print(f"[sheet] loaded {len(_sheet_df)} rows")
        except Exception as e:
            print(f"[sheet] ERROR loading sheet: {e}")
            _sheet_df = None
    return _sheet_df

def find_patient_by_hn(hn: str) -> Optional[dict]:
    df = load_sheet()
    if df is None or "HN" not in df.columns:
        return None
    key = str(hn).strip()
    row = df.loc[df["HN"] == key]
    if row.empty:
        return None
    rec = row.iloc[0].to_dict()
    # Ensure consistent keys
    rec["HN"] = rec.get("HN", key)
    return rec

# -----------------------------
# Models
# -----------------------------
class QRIn(BaseModel):
    hn: str

# -----------------------------
# REST endpoints
# -----------------------------
@app.get("/health")
def health():
    return {"ok": True, "sheet_url": SHEET_URL}

@app.get("/api/patient/{hn}")
def api_patient(hn: str):
    rec = find_patient_by_hn(hn)
    if not rec:
        return {"found": False, "hn": hn}
    # For convenience, return fields flattened (as your FE expects)
    return {"found": True, **rec}

# -----------------------------
# Trigger endpoints (detector calls these)
# -----------------------------
@app.post("/trigger/person")
async def trigger_person():
    await manager.broadcast({"type": "person_detected"})
    return {"ok": True}

@app.post("/trigger/reset")
async def trigger_reset():
    await manager.broadcast({"type": "reset_idle"})
    return {"ok": True}

@app.post("/trigger/qr")
async def trigger_qr(payload: QRIn):
    hn = payload.hn.strip()
    rec = find_patient_by_hn(hn)
    if not rec:
        await manager.broadcast({"type": "qr_not_found", "hn": hn})
        return {"found": False, "hn": hn}
    # Broadcast patient info so the FE can immediately show it
    await manager.broadcast({"type": "qr_found", "patient": rec})
    return {"found": True, "patient": rec}
