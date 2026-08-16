import cv2
import numpy as np
import mss
import pydirectinput
import keyboard
import time
from ultralytics import YOLO

# --- TỌA ĐỘ VÀ VÙNG QUÉT (THEO CHỈNH SỬA CỦA BẠN) ---
CX, CY = 958, 470 
SIZE = 600 
ROI = {"top": CY - (SIZE//2), "left": CX - (SIZE//2), "width": SIZE, "height": SIZE}

# --- VÙNG AN TOÀN (SAFE BOX) ---
SAFE_W, SAFE_H = 100, 180 

TARGET_CLASSES = ['creep', 'scopes','person', 'dog', 'sheep', 'bird', 'cat', 'horse']

def run_v_toggle_test():
    model = YOLO('yolov8n.pt').to('cuda')
    sct = mss.mss()
    
    is_bot_active = False # Trạng thái Bot (V toggle)
    is_pressing = False   # Trạng thái đang đè chuột trái
    
    print("--- DEBUG MELEE TRIGGER (PHÍM V) ---")
    print("Nhấn 'V' để Bật/Tắt chế độ Tự động săn quái.")

    while True:
        # 1. Chụp ảnh Preview liên tục
        sct_img = sct.grab(ROI)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Vẽ Safe Box và Tâm
        mid = SIZE // 2
        cv2.rectangle(img, (mid-50, mid-90), (mid+50, mid+90), (0, 255, 255), 1)

        # 2. Bắt phím Toggle 'V'
        if keyboard.is_pressed('v'):
            is_bot_active = not is_bot_active
            print(f"\n[SYSTEM] Bot: {'ON' if is_bot_active else 'OFF'}")
            # Nếu tắt bot thì phải nhả chuột ngay
            if not is_bot_active and is_pressing:
                pydirectinput.mouseUp(button='left')
                is_pressing = False
            time.sleep(0.3) # Tránh dính phím

        # 3. Logic AI khi Bot đang ON
        if is_bot_active:
            results = model(img, device='cuda', stream=True, conf=0.4, verbose=False)
            target_found = False

            # for r in results:
            #     for box in r.boxes:
            #         label = model.names[int(box.cls[0])]
            #         if label not in TARGET_CLASSES: continue

            #         x1, y1, x2, y2 = map(int, box.xyxy[0])
            #         mx, my = (x1 + x2) // 2, (y1 + y2) // 2

            #         # Lọc Safe Box (Chính mình)
            #         if (mid-50 < mx < mid+50) and (mid-90 < my < mid+90):
            #             continue

            #         # Nếu thấy quái
            #         target_found = True
            #         tx = x1 + ROI['left'] + ((x2 - x1) // 2)
            #         ty = y1 + ROI['top'] + ((y2 - y1) // 2)
                    
            #         pydirectinput.moveTo(tx, ty, _pause=False)
                    
            #         if not is_pressing:
            #             pydirectinput.mouseDown(button='left')
            #             is_pressing = True
            #         break 
            for r in results:
                for box in r.boxes:
                    class_id = int(box.cls[0])
                    label = model.names[class_id]
                    conf = float(box.conf[0]) # Lấy độ tự tin (0.0 - 1.0)
                    
                    if label not in TARGET_CLASSES: continue

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    mx, my = (x1 + x2) // 2, (y1 + y2) // 2

                    # Chuẩn bị nội dung text (Ví dụ: "creep 0.85")
                    display_text = f"{label} {conf:.2f}"

                    # Lọc Safe Box (Chính mình)
                    if (mid-50 < mx < mid+50) and (mid-90 < my < mid+90):
                        # Vẽ khung trắng cho bản thân để nhận diện
                        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 1)
                        cv2.putText(img, f"SELF", (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        continue

                    # Nếu thấy quái (Mục tiêu hợp lệ)
                    target_found = True
                    
                    # Vẽ khung đỏ và in tên class + độ tự tin
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(img, display_text, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
                    tx = x1 + ROI['left'] + ((x2 - x1) // 2)
                    ty = y1 + ROI['top'] + ((y2 - y1) // 2)
                    
                    pydirectinput.moveTo(tx, ty, _pause=False)
                    
                    if not is_pressing:
                        pydirectinput.mouseDown(button='left')
                        is_pressing = True
                    break

            # Nếu đang ON nhưng không thấy quái -> Nhả chuột để nhân vật đứng im
            if not target_found and is_pressing:
                pydirectinput.mouseUp(button='left')
                is_pressing = False

        # Hiển thị trạng thái lên màn hình
        status_color = (0, 255, 0) if is_bot_active else (0, 0, 255)
        cv2.putText(img, f"BOT: {'ACTIVE' if is_bot_active else 'IDLE'}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        cv2.imshow("Melee V-Toggle Test", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_v_toggle_test()