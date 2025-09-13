#!/usr/bin/env python3
"""
Kiosk detector (macOS-friendly).
- Face presence -> POST /trigger/person (enter) and /trigger/reset (leave)
- Optional QR decode -> POST /trigger/qr {"hn": "..."}
- Preview overlays when --show

Usage:
  python detect.py --backend http://127.0.0.1:8000 --camera 0 --show --qr --confirm 3
"""

import sys, os, time, argparse
import cv2
import requests

def post(base: str, route: str, json_body: dict | None = None):
    url = base + route
    try:
        r = requests.post(url, json=json_body, timeout=1.5)
        print(f"[POST] {route} -> {r.status_code}")
    except Exception as e:
        print(f"[WARN] post failed {route}: {e}")

def open_cam(index: int):
    # On macOS use AVFoundation; elsewhere CAP_ANY
    if sys.platform == "darwin":
        cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
    else:
        cap = cv2.VideoCapture(index, cv2.CAP_ANY)
    return cap

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=os.getenv("BACKEND_URL", "http://127.0.0.1:8000"),
                    help="FastAPI base URL (default: %(default)s)")
    ap.add_argument("--camera", type=int, default=0, help="camera index (0/1 on mac)")
    ap.add_argument("--confirm", type=int, default=5, help="consecutive frames to confirm presence/absence")
    ap.add_argument("--fps", type=float, default=12.0, help="processing FPS")
    ap.add_argument("--show", action="store_true", help="show preview window with overlays")
    ap.add_argument("--qr", action="store_true", help="enable QR detection")
    ap.add_argument("--scale", type=float, default=1.2, help="face detect scaleFactor")
    ap.add_argument("--neighbors", type=int, default=5, help="face detect minNeighbors")
    ap.add_argument("--minsize", type=int, default=60, help="face detect min size (pixels)")
    ap.add_argument("--person_cooldown", type=float, default=2.0, help="seconds between repeated person posts")
    ap.add_argument("--reset_cooldown", type=float, default=2.0, help="seconds between repeated reset posts")
    ap.add_argument("--qr_debounce", type=float, default=3.0, help="seconds before reposting same QR")
    ap.add_argument("--width", type=int, default=1280, help="request capture width")
    ap.add_argument("--height", type=int, default=720, help="request capture height")
    args = ap.parse_args()

    cap = open_cam(args.camera)
    if not cap.isOpened():
        sys.exit(f"Camera {args.camera} did not open. Try --camera 1")

    # Tweak buffering & size
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    qr = cv2.QRCodeDetector() if args.qr else None

    present_streak = 0
    absent_streak = 0
    active = False
    last_person_ts = 0.0
    last_reset_ts = 0.0
    last_qr_value = None
    last_qr_ts = 0.0
    frame_i = 0

    print(f"[INFO] backend={args.backend} camera={args.camera} show={args.show} qr={args.qr}")
    print("Detecting… (press 'q' to quit if --show)")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[WARN] frame read failed; stopping.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face.detectMultiScale(
                gray, args.scale, args.neighbors, minSize=(args.minsize, args.minsize)
            )
            num_faces = len(faces)

            # Update streaks
            if num_faces > 0:
                present_streak += 1
                absent_streak = 0
            else:
                absent_streak += 1
                present_streak = 0

            # Logs
            if frame_i % 10 == 0:
                if not active:
                    print(f"[FACES] {num_faces} (present_streak {present_streak}/{args.confirm})")
                else:
                    print(f"[FACES] {num_faces} (absent_streak {absent_streak}/{args.confirm})")

            now = time.time()

            # Enter ACTIVE
            if (not active) and present_streak >= args.confirm and (now - last_person_ts) >= args.person_cooldown:
                print("[ACTIVE] person_detected")
                post(args.backend, "/trigger/person")
                active = True
                last_person_ts = now
                present_streak = 0

            # Back to IDLE
            if active and absent_streak >= args.confirm and (now - last_reset_ts) >= args.reset_cooldown:
                print("[IDLE] reset_idle")
                post(args.backend, "/trigger/reset")
                active = False
                last_reset_ts = now
                absent_streak = 0

            # Optional QR decode
            bbox = None
            if qr is not None:
                data, bbox, _ = qr.detectAndDecode(frame)
                if data:
                    hn = str(data).strip()
                    if hn:
                        if hn != last_qr_value or (now - last_qr_ts) > args.qr_debounce:
                            print(f"[QR] {hn}")
                            post(args.backend, "/trigger/qr", {"hn": hn})
                            last_qr_value, last_qr_ts = hn, now

            # Overlays
            if args.show:
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                status = "ACTIVE" if active else "IDLE"
                color = (0, 200, 0) if active else (0, 0, 255)
                cv2.putText(frame, status, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)
                cv2.putText(frame, f"faces={num_faces}", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"present={present_streak}", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1, cv2.LINE_AA)
                cv2.putText(frame, f"absent={absent_streak}",  (20, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1, cv2.LINE_AA)

                if bbox is not None and len(bbox) > 0:
                    pts = bbox.astype(int).reshape(-1, 2)
                    for i in range(len(pts)):
                        p1 = tuple(pts[i]); p2 = tuple(pts[(i + 1) % len(pts)])
                        cv2.line(frame, p1, p2, (255, 0, 0), 2)

                cv2.imshow("Kiosk Detector (q to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            frame_i += 1
            time.sleep(max(0.0, 1.0 / args.fps))

    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
