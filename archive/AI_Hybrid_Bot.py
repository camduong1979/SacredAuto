import cv2
import numpy as np
import mss
import pydirectinput
import keyboard
import time
from ultralytics import YOLO
import pyautogui

# --- CẤU HÌNH ---
# Tọa độ trung tâm (đã căn chỉnh theo máy bạn)
CX, CY = 958, 470 
SIZE = 600 
ROI = {"top": CY - (SIZE//2), "left": CX - (SIZE//2), "width": SIZE, "height": SIZE}

# Vùng an toàn (Safe Box)
SAFE_W, SAFE_H = 100, 180 

# Các class mục tiêu
TARGET_CLASSES = ['creep', 'scopes', 'person', 'dog', 'sheep', 'bird', 'cat', 'horse']

# --- HÀM LOGIC TỪ MODULE COMBAT RADAR (Đã tối ưu hóa) ---
# Trích xuất logic so sánh màu từ file CombatRadarClass.py
def is_radar_confirmed(x, y, scan_size=20):
    """
    Quét một vùng nhỏ quanh chuột (x, y) để tìm màu Đỏ/Vàng/Trắng.
    Trả về True nếu xác định đúng là kẻ địch sống.
    """
    try:
        # Chụp vùng nhỏ quanh chuột
        region = (x - scan_size//2, y - scan_size//2, scan_size, scan_size)
        img = pyautogui.screenshot(region=region)
        pixels = list(img.getdata())
        
        for r, g, b in pixels:
            # Logic check màu gốc từ CombatRadarClass.py
            # 1. Màu Trắng (White)
            if r > 250 and g > 250 and b > 250: return True 
            # 2. Màu Vàng (Yellow - Boss/Elite)
            if r > 240 and g > 240 and (100 < b < 150): return True 
            # 3. Màu Đỏ (Red - Máu quái)
            if (110 <= r <= 185) and (g < 95) and (b < 95): return True 
            
        return False
    except:
        return False

def run_hybrid_bot():
    # Load Model (Thay bằng đường dẫn 'best.pt' của bạn nếu có)
    model = YOLO('yolov8n.pt').to('cuda')
    sct = mss.mss()
    
    is_bot_active = False 
    is_pressing = False   
    last_target_time = 0

    print("--- SACRED HYBRID BOT (AI + RADAR) ---")
    print("Logic: AI tìm vị trí -> Di chuột -> Radar check màu -> BEM")
    print("Nhấn 'V' để Bật/Tắt.")

    while True:
        # 1. Xử lý ảnh đầu vào
        sct_img = sct.grab(ROI)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Vẽ Safe Box (Tham chiếu vị trí bản thân)
        mid = SIZE // 2
        cv2.rectangle(img, (mid-SAFE_W//2, mid-SAFE_H//2), 
                      (mid+SAFE_W//2, mid+SAFE_H//2), (0, 255, 255), 1)

        # 2. Toggle Bot
        if keyboard.is_pressed('v'):
            is_bot_active = not is_bot_active
            print(f"\n[SYSTEM] Bot: {'ON' if is_bot_active else 'OFF'}")
            if not is_bot_active:
                pydirectinput.mouseUp(button='left')
                is_pressing = False
            time.sleep(0.3)

        # 3. Logic Chính
        current_target_valid = False # Cờ kiểm tra mục tiêu hiện tại

        if is_bot_active:
            results = model(img, device='cuda', stream=True, conf=0.45, verbose=False) # Tăng conf lên xíu

            # Ưu tiên mục tiêu gần tâm nhất (Logic mới)
            best_target = None
            min_dist = 9999

            for r in results:
                for box in r.boxes:
                    label = model.names[int(box.cls[0])]
                    if label not in TARGET_CLASSES: continue

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                    
                    # --- LỌC SAFE BOX (SELF) ---
                    if (mid-SAFE_W//2 < mx < mid+SAFE_W//2) and \
                       (mid-SAFE_H//2 < my < mid+SAFE_H//2):
                        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 1)
                        cv2.putText(img, "SELF", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
                        continue

                    # Tính khoảng cách từ tâm đến mục tiêu
                    dist = ((mx - mid)**2 + (my - mid)**2)**0.5
                    
                    # Tìm mục tiêu gần nhất
                    if dist < min_dist:
                        min_dist = dist
                        best_target = (x1, y1, x2, y2, mx, my, label)

            # Nếu tìm thấy mục tiêu tiềm năng từ AI
            if best_target:
                x1, y1, x2, y2, mx, my, label = best_target
                
                # Tính tọa độ màn hình thực tế
                tx = x1 + ROI['left'] + ((x2 - x1) // 2)
                ty = y1 + ROI['top'] + ((y2 - y1) // 2) # Lệch lên trên tí để trúng đầu/thanh máu

                # A. DI CHUYỂN CHUỘT ĐẾN MỤC TIÊU
                pydirectinput.moveTo(tx, ty, _pause=False)
                
                # B. VẼ KHUNG DEBUG
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2) # Màu xanh lá: AI thấy
                
                # C. CHECK RADAR (QUAN TRỌNG)
                # Đợi cực nhanh để game hiển thị thanh máu (0.01s - 0.05s)
                # time.sleep(0.01) 
                
                if is_radar_confirmed(tx, ty):
                    # Radar xác nhận: Màu đỏ/vàng xuất hiện -> BEM
                    cv2.putText(img, "LOCKED [RADAR]", (x1, y1-25), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3) # Đổi sang Đỏ đậm
                    
                    current_target_valid = True
                    last_target_time = time.time()

                    if not is_pressing:
                        pydirectinput.mouseDown(button='left')
                        is_pressing = True
                        print(f"[ATTACK] {label} verified by Radar!")
                else:
                    # AI thấy nhưng Radar không thấy (xác chết hoặc nhầm)
                    cv2.putText(img, "FAKE/DEAD", (x1, y1-10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # 4. Cơ chế nhả chuột (Cooldown)
        # Nếu không còn mục tiêu hợp lệ và đã giữ chuột quá lâu -> Nhả ra
        if is_pressing and not current_target_valid:
            # Giữ thêm 0.5s để đánh nốt đòn (Animation canceling)
            if time.time() - last_target_time > 0.5:
                pydirectinput.mouseUp(button='left')
                is_pressing = False
                print("[STOP] Target lost/dead.")

        # Hiển thị
        cv2.imshow("Sacred Hybrid Bot", img)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_hybrid_bot()