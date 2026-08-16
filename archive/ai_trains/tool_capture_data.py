import time
import cv2
import mss
import numpy as np
import keyboard
import os
# --- TỌA ĐỘ CHUẨN CỦA BẠN ---
CX, CY = 958, 470
SIZE = 600 
REGION = {"top": CY - (SIZE//2), "left": CX - (SIZE//2), "width": SIZE, "height": SIZE}

# --- CẤU HÌNH VÙNG CHỤP (Lấy từ sacred_config.json của bạn) ---
# Tâm radar của bạn là 947, 790. Ta sẽ quét rộng ra xung quanh đó.
# CENTER_X, CENTER_Y = 958, 542
# WIDTH, HEIGHT = 800, 600 # Vùng quét 800x600 px
# TOP = CENTER_Y - (HEIGHT // 2)
# LEFT = CENTER_X - (WIDTH // 2)

#REGION = {"top": TOP, "left": LEFT, "width": WIDTH, "height": HEIGHT}

# Tạo thư mục lưu ảnh nếu chưa có
SAVE_DIR = "sacred_data/images"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def run_collector():
    sct = mss.mss()
    print(f"=== TOOL CHỤP ẢNH DATA ===")
    print(f"Vùng chụp: {REGION}")
    print("Giữ phím 'v' để chụp liên tục. Nhấn 'esa' để thoát.")
    
    count = 0
    
    while True:
        # 1. Chụp màn hình
        sct_img = sct.grab(REGION)
        img = np.array(sct_img)
        
        # 2. Hiển thị cửa sổ xem trước (Preview)
        # Convert hệ màu để hiển thị đúng trên OpenCV
        preview_img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        cv2.imshow("Preview (Nhan Q de thoat)", preview_img)

        # 3. Logic lưu ảnh
        if keyboard.is_pressed('v'):
            # Tạo tên file theo thời gian để không trùng
            filename = f"{SAVE_DIR}/sacred_{int(time.time()*1000)}.jpg"
            cv2.imwrite(filename, preview_img)
            count += 1
            print(f"Đã lưu ảnh thứ {count}: {filename}", end='\r')
            time.sleep(0.2) # Delay nhẹ để không spam quá nhanh

        # 4. Thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_collector()