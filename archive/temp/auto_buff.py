# import mss
# import pyautogui
# import pydirectinput
# import time
# import keyboard
# import numpy as np
# import winsound # Thư viện tạo tiếng bíp có sẵn trong Windows

# # ================= CẤU HÌNH =================
# SENTINEL_X = 1316
# SENTINEL_Y = 856
# TARGET_COLOR = (68, 68, 68) # Màu xanh nõn chuối
# SKILL_KEY = '1' 
# TOGGLE_KEY = 'v'
# TOLERANCE = 30 
# # ============================================

# def is_skill_ready(sct):
#     bbox = {'top': SENTINEL_Y, 'left': SENTINEL_X, 'width': 1, 'height': 1}
#     img = np.array(sct.grab(bbox))
#     pixel = img[0, 0]
#     b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
    
#     tr, tg, tb = TARGET_COLOR
    
#     match = (abs(r - tr) < TOLERANCE) and \
#             (abs(g - tg) < TOLERANCE) and \
#             (abs(b - tb) < TOLERANCE)
            
#     # --- DEBUG: IN MÀU RA MÀN HÌNH ĐỂ KIỂM TRA ---
#     # Dòng này sẽ giúp anh biết tool đang nhìn thấy cái gì
#     # Nếu match = False, hãy xem màu thực tế (r,g,b) lệch bao nhiêu so với target
#     print(f"👁️ Đang nhìn: ({r:3}, {g:3}, {b:3}) | Cần: {TARGET_COLOR} | Khớp? {match}   ", end='\r')
    
#     return match

# def main():
#     print("--- DEBUG MODE: AUTO BUFF ---")
#     print("⚠️  LƯU Ý: PHẢI CHẠY BẰNG QUYỀN ADMINISTRATOR MỚI NHẬN PHÍM 'V'")
#     print(f"-> Canh gác tại: {SENTINEL_X}, {SENTINEL_Y}")
    
#     active = False
#     sct = mss.mss()

#     while True:
#         # Xử lý bật tắt
#         if keyboard.is_pressed(TOGGLE_KEY):
#             active = not active
#             state = "BẬT (FIGHT)" if active else "TẮT (SAFE)"
#             print(f"\n\n[SOUND] Bíp! Trạng thái: {state}\n")
            
#             # Kêu bíp một cái để anh nghe thấy trong game
#             if active:
#                 winsound.Beep(1000, 200) # Tần số 1000Hz, 0.2s
#             else:
#                 winsound.Beep(500, 200)  # Tần số thấp hơn khi tắt
                
#             time.sleep(0.3) 

#         if active:
#             if is_skill_ready(sct):
#                 print(f"\n[ACTION] PHÁT HIỆN MÀU XANH! -> CAST SKILL")
                
#                 # 1. Chọn skill (Mở lại dòng này đi anh!)
#                 pydirectinput.press(SKILL_KEY) 
#                 time.sleep(0.05)
                
#                 # 2. Click chuột phải
#                 pydirectinput.click(button='right')
                
#                 # 3. Chờ animation
#                 print("[WAIT] Đang chờ múa skill (1.5s)...")
#                 time.sleep(1.5) 
#                 print("-> Tiếp tục canh gác...")
#             else:
#                 pass

#         if keyboard.is_pressed('esc'):
#             print("\nThoát tool.")
#             break
            
#         time.sleep(0.1)

# if __name__ == "__main__":
#     main()

import mss
import pyautogui
import pydirectinput
import time
import keyboard
import numpy as np
import winsound # Thư viện tạo tiếng bíp có sẵn trong Windows

# ================= CẤU HÌNH =================
SENTINEL_X = 1118
SENTINEL_Y = 856

# Cấu hình logic R = G = B cho phổ XÁM ĐEN
TOLERANCE_RGB = 1       # Chênh lệch tối đa giữa R, G, B (cho phép lệch 0-4 đơn vị do render game)
MAX_BRIGHTNESS = 177    # Giới hạn trên của độ sáng để chốt đúng dải XÁM ĐEN (68, 82, 95...)
MIN_BRIGHTNESS = 14     # Giới hạn dưới để tránh vùng đen tuyền bóng tối (nếu cần)

SKILL_KEY = '1' 
TOGGLE_KEY = 'v'
# ============================================

def is_dark_gray_rgb(r, g, b):
    """
    Logic kiểm tra màu Xám Đen dựa trên R = G = B:
    1. Các kênh R, G, B xấp xỉ bằng nhau (R ≈ G ≈ B).
    2. Độ sáng nằm trong khoảng xám đen (30 <= R, G, B <= 120).
    """
    # 1. Kiểm tra R = G = B với dung sai cho phép
    is_equal_rgb = (abs(r - g) <= TOLERANCE_RGB) and \
                   (abs(g - b) <= TOLERANCE_RGB) and \
                   (abs(r - b) <= TOLERANCE_RGB)
                   
    # 2. Kiểm tra độ sáng có nằm trong dải Xám Đen không
    avg_brightness = (r + g + b) / 3.0
    is_dark_range = MIN_BRIGHTNESS <= avg_brightness <= MAX_BRIGHTNESS
    
    return is_equal_rgb and is_dark_range

def needs_buff(sct):
    bbox = {'top': SENTINEL_Y, 'left': SENTINEL_X, 'width': 1, 'height': 1}
    img = np.array(sct.grab(bbox))
    pixel = img[0, 0]
    b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
    
    # Kiểm tra xem màu hiện tại có thuộc Phổ Xám Đen (R=G=B) hay không
    is_casting = is_dark_gray_rgb(r, g, b)
            
    # DEBUG: In thông số màu ra console
    print(f"👁️ Đang nhìn: R={r:3} G={g:3} B={b:3} | Trong phổ xám R=G=B (Đang cast)? {is_casting}   ", end='\r')
    
    # Nếu KHÔNG NẰM TRONG PHỔ XÁM (is_casting == False) -> Skill đã sẵn sàng -> Cần buff!
    return not is_casting

def main():
    print("--- AUTO BUFF: LOGIC PHỔ XÁM ĐEN (R=G=B) ---")
    print(f"-> Ngưỡng R=G=B dung sai: ±{TOLERANCE_RGB} | Độ sáng xám đen: {MIN_BRIGHTNESS}-{MAX_BRIGHTNESS}")
    print("⚠️  LƯU Ý: PHẢI CHẠY BẰNG QUYỀN ADMINISTRATOR MỚI NHẬN PHÍM 'V'")
    print(f"-> Canh gác tại: {SENTINEL_X}, {SENTINEL_Y}\n")
    
    active = False
    sct = mss.mss()

    while True:
        # Xử lý bật/tắt tool bằng phím hotkey
        if keyboard.is_pressed(TOGGLE_KEY):
            active = not active
            state = "BẬT (FIGHT)" if active else "TẮT (SAFE)"
            print(f"\n\n[SOUND] Bíp! Trạng thái: {state}\n")
            
            if active:
                winsound.Beep(1000, 200) # Tiếng bíp cao khi BẬT
            else:
                winsound.Beep(500, 200)  # Tiếng bíp trầm khi TẮT
                
            time.sleep(3) 

        if active:
            # Nếu điểm ảnh THOÁT KHỎI PHỔ XÁM R=G=B -> Kích hoạt buff
            if needs_buff(sct):
                print(f"\n[ACTION] ĐÃ THOÁT PHỔ XÁM (Skill hết cast/sẵn sàng)! -> CAST SKILL")
                
                # 1. Chọn skill
                pydirectinput.press(SKILL_KEY) 
                time.sleep(0.5)
                
                # 2. Click chuột phải
                pydirectinput.click(button='right')
                
                # 3. Chờ animation / chờ điểm ảnh chuyển lại thành màu xám đen
                print("[WAIT] Đang chờ múa skill (3s)...")
                time.sleep(3) 
                print("-> Tiếp tục canh gác...")

        if keyboard.is_pressed('esc'):
            print("\nThoát tool.")
            break
            
        time.sleep(0.1)

if __name__ == "__main__":
    main()