#!/usr/bin/env python3
"""
QR-only scanner (diagnostic):
- Prints status every second.
- Draws bbox even if decode text is empty.
- Tries multiple decode strategies (raw, gray+eq, upscaled, multi).
- On success: prints [QR] <value> and POSTs /trigger/qr {"hn": value}.

Run:
  cd back-end
  source .venv/bin/activate
  python qr_detect.py --backend http://127.0.0.1:8000 --camera 0 --show
"""

import sys, time, argparse
import cv2
import requests
import numpy as np

def open_cam(index: int):
    if sys.platform == "darwin":
        return cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
    return cv2.VideoCapture(index, cv2.CAP_ANY)

def post_qr(base: str, hn: str):
    url = base + "/trigger/qr"
    try:
        r = requests.post(url, json={"hn": hn}, timeout=1.5)
        print(f"[POST] /trigger/qr {{'hn':'{hn}'}} -> {r.status_code}")
    except Exception as e:
        print(f"[WARN] post failed /trigger/qr: {e}")

def try_decode_single(qr, img):
    data, bbox, _ = qr.detectAndDecode(img)
    if data: return [data.strip()], bbox
    return [], bbox  # may still have bbox

def try_decode_multi(qr, img):
    # OpenCV's detectAndDecodeMulti returns (decoded, bboxes, rectified)
    try:
        ok, decoded, bboxes, _ = qr.detectAndDecodeMulti(img)
        if not ok or decoded is None: return [], None
        vals = [d.strip() for d in decoded if d and d.strip()]
        return vals, bboxes
    except Exception:
        return [], None

def draw_bboxes(frame, bboxes, color=(255, 0, 0)):
    if bboxes is None: return
    # bboxes can be Nx1x4x2 or Nx4x2 depending on API
    arr = np.array(bboxes)
    if arr.ndim == 4:  # (N,1,4,2)
        arr = arr.reshape((-1, 4, 2))
    if arr.ndim == 3:
        for quad in arr:
            pts = quad.astype(int)
            for i in range(4):
                p1 = tuple(pts[i]); p2 = tuple(pts[(i + 1) % 4])
                cv2.line(frame, p1, p2, color, 2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="http://127.0.0.1:8000", help="FastAPI base URL")
    ap.add_argument("--camera", type=int, default=0, help="camera index")
    ap.add_argument("--fps", type=float, default=12.0, help="processing FPS")
    ap.add_argument("--show", action="store_true", help="show preview window")
    ap.add_argument("--debounce", type=float, default=2.0, help="seconds to ignore repeated same code")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    cap = open_cam(args.camera)
    if not cap.isOpened():
        sys.exit(f"Camera {args.camera} did not open. Try --camera 1")

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    qr = cv2.QRCodeDetector()
    last_val, last_ts = None, 0.0
    last_log = 0.0
    frame_i = 0

    print(f"[INFO] backend={args.backend} camera={args.camera} show={args.show}")
    print("[INFO] Scanning for QR… (press 'q' to quit if --show)")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[WARN] frame read failed; stopping."); break

            # Periodic heartbeat so you know it's alive
            now = time.time()
            if now - last_log >= 1.0:
                print("[SCAN] running…")
                last_log = now

            decoded_vals = []
            bboxes_all = []

            # 1) Raw frame
            vals, bboxes = try_decode_single(qr, frame)
            if vals: decoded_vals += vals
            if bboxes is not None: bboxes_all.append(bboxes)

            # 2) Grayscale + equalize
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            vals, bboxes = try_decode_single(qr, gray)
            if vals: decoded_vals += vals
            if bboxes is not None: bboxes_all.append(bboxes)

            # 3) Upscaled (helps small QRs)
            up = cv2.resize(gray, dsize=None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
            vals, bboxes = try_decode_single(qr, up)
            if vals: decoded_vals += vals
            if bboxes is not None: bboxes_all.append(bboxes)

            # 4) Multi decode on raw (catches multiple or tricky ones)
            vals, bboxes = try_decode_multi(qr, frame)
            if vals: decoded_vals += vals
            if bboxes is not None: bboxes_all.append(bboxes)

            # Use first new value
            if decoded_vals:
                val = decoded_vals[0]
                if val:
                    if val != last_val or (now - last_ts) > args.debounce:
                        print(f"[QR] {val}")
                        post_qr(args.backend, val)
                        last_val, last_ts = val, now

            # Show preview
            if args.show:
                # draw any bboxes we saw (even when decode text was empty)
                for b in bboxes_all:
                    draw_bboxes(frame, b, color=(255, 0, 0))
                if last_val:
                    cv2.putText(frame, f"QR: {last_val}", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,200,0), 2, cv2.LINE_AA)
                cv2.imshow("QR Scanner (q to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break

            frame_i += 1
            time.sleep(max(0.0, 1.0 / args.fps))

    finally:
        cap.release()
        if args.show: cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
