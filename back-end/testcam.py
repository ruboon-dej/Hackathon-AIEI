# detect_cam.py  — minimal stable preview
import cv2, sys

CAM_INDEX = 0  # or 1 if that's your working one

cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_AVFOUNDATION)
if not cap.isOpened():
    sys.exit(f"Camera {CAM_INDEX} did not open. Try CAM_INDEX=1")

# optional: tighten buffering; helps with “freezing”
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("Reading frames… press q to quit")
while True:
    ok, frame = cap.read()
    if not ok:
        print("Frame read failed (camera switched or in use).")
        break
    cv2.imshow("Preview", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
