import cv2
import pandas as pd
import numpy as np

# ถ้าใช้ Google Sheets โดย public/share ได้
# คุณสามารถ export เป็น CSV แล้วโหลดด้วย pandas ได้ เช่น:
sheet_url = "https://docs.google.com/spreadsheets/d/14Ztjiuqj7NT_-ft4A3iU0XteRP9OG7X3Ne6Sn-PpTNc/export?format=csv"
df = pd.read_csv(sheet_url)

# หรือถ้าใช้ Google Sheets API: gspread หรือ oauth แล้วแปลงเป็น DataFrame

cap = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
qr_detector = cv2.QRCodeDetector()

sent_flag = False
qr_found = False

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # ตรวจว่าเข้าใกล้ (กรอบใหญ่เกิน threshold) และยังไม่ส่งค่า
        if w > 200 and h > 200 and not sent_flag:
            sent_flag = True
            # ส่งค่า 1 — คุณอาจจะทำอะไรกับมัน (เช่น print หรือส่งผ่าน network)
            print("ส่งค่า 1")

            # แสดงข้อความ
            cv2.putText(frame, "Value: 1", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2, cv2.LINE_AA)

    # ถ้า QR ยังไม่อ่านได้
    if not qr_found:
        data, bbox, _ = qr_detector.detectAndDecode(frame)
        if data:
            qr_found = True
            print("QR Detected:", data)
            # สมมติ data เป็น HN ตามใน Sheet
            # หาใน DataFrame
            # อาจจะ strip / แปลง format ให้ตรงกัน
            df_hn = df[df['HN'] == data]
            if not df_hn.empty:
                nationality = df_hn.iloc[0]['Nationality']
                status = df_hn.iloc[0]['Status']
                text = f"HN: {data}, Nationality: {nationality}, Status: {status}"
                cv2.putText(frame, text, (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,0,0), 2, cv2.LINE_AA)
                print(text)

    cv2.imshow("Camera", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
