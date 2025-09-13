# back-end/app.py  (VERBOSE)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os, time, asyncio, logging, sys
import pandas as pd

# -----------------------------
# Logging (timestamps + level)
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("kiosk")

# -----------------------------
# Config
# -----------------------------
SHEET_URL = os.getenv(
    "SHEET_URL",
    "https://docs.google.com/spreadsheets/d/14Ztjiuqj7NT_-ft4A3iU0XteRP9OG7X3Ne6Sn-PpTNc/export?format=csv",
)
SHEET_TTL_SEC = int(os.getenv("SHEET_TTL_SEC", "300"))  # 5 min

app = FastAPI()

# CORS (Next.js dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Global state (for debug)
# -----------------------------
state = {
    "active": False,          # person present?
    "person_count": 0,        # # of /trigger/person
    "reset_count": 0,         # # of /trigger/reset
    "qr_count": 0,            # # of /trigger/qr
    "ws_clients": 0,          # connected websockets
    "last_event": None,       # "person" | "reset" | "qr" | None
}

def print_state(prefix: str = "[STATE]"):
    log.info(
        f"{prefix} active={state['active']} ws={state['ws_clients']} "
        f"person_count={state['person_count']} reset_count={state['reset_count']} "
        f"qr_count={state['qr_count']} last_event={state['last_event']}"
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
        state["ws_clients"] = len(self.active)
        log.info(f"[WS] connect -> clients={state['ws_clients']}")
        print_state()

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
            state["ws_clients"] = len(self.active)
            log.info(f"[WS] disconnect -> clients={state['ws_clients']}")
            print_state()

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
        if dead:
            log.warning(f"[WS] pruned {len(dead)} sockets")

manager = WSManager()

@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # optional: keepalive from client
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
    if force or _sheet_df is None or (time.time() - _sheet_ts) > SHEET_TTL_SEC:
        try:
            df = pd.read_csv(SHEET_URL)
            _sheet_df = _normalize_df(df)
            _sheet_ts = time.time()
            log.info(f"[SHEET] loaded rows={len(_sheet_df)} from {SHEET_URL}")
        except Exception as e:
            log.error(f"[SHEET] ERROR: {e}")
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
    return {"ok": True, "sheet_url": SHEET_URL, "state": state}

@app.get("/api/patient/{hn}")
def api_patient(hn: str):
    rec = find_patient_by_hn(hn)
    if not rec:
        log.info(f"[API] patient NOT FOUND hn={hn}")
        return {"found": False, "hn": hn}
    log.info(f"[API] patient FOUND hn={hn} name={rec.get('Name','')}")
    return {"found": True, **rec}

# -----------------------------
# Triggers (detector -> backend)
# -----------------------------
@app.post("/trigger/person")
async def trigger_person():
    state["active"] = True
    state["person_count"] += 1
    state["last_event"] = "person"
    log.info("[TRIGGER] person_detected")
    print_state()
    await manager.broadcast({"type": "person_detected"})
    return {"ok": True, "state": state}

@app.post("/trigger/reset")
async def trigger_reset():
    state["active"] = False
    state["reset_count"] += 1
    state["last_event"] = "reset"
    log.info("[TRIGGER] reset_idle")
    print_state()
    await manager.broadcast({"type": "reset_idle"})
    return {"ok": True, "state": state}

@app.post("/trigger/qr")
async def trigger_qr(payload: QRIn):
    hn = payload.hn.strip()
    state["qr_count"] += 1
    state["last_event"] = "qr"
    rec = find_patient_by_hn(hn)
    if not rec:
        log.info(f"[TRIGGER] qr_not_found hn={hn}")
        print_state()
        await manager.broadcast({"type": "qr_not_found", "hn": hn})
        return {"found": False, "hn": hn, "state": state}
    log.info(f"[TRIGGER] qr_found hn={hn} name={rec.get('Name','')}")
    print_state()
    await manager.broadcast({"type": "qr_found", "patient": rec})
    return {"found": True, "patient": rec, "state": state}

# -----------------------------
# Heartbeat logger (prints every 5s)
# -----------------------------
@app.on_event("startup")
async def start_heartbeat():
    async def ticker():
        while True:
            print_state("[HEARTBEAT]")
            await asyncio.sleep(5)
    asyncio.create_task(ticker())
