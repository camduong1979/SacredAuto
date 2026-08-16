# import pyautogui
# import keyboard
# import time

# # Tọa độ trung tâm vùng 3x3
# CENTER_X = 961 
# CENTER_Y = 798 

# def check_logic_strict(r, g, b):
#     """Logic nhận diện chặt chẽ dựa trên thông số RGB thực tế của bạn"""
#     # 1. Logic Đỏ (Quái khỏe): R rõ rệt, G & B sát nhau
#     is_red = (110 <= r <= 185) and (g < 95) and (b < 95) and (abs(g - b) < 15)
    
#     # 2. Logic Đen/Tương phản (Quái yếu): Sáng hơn nền tối 0-20, xám nhẹ
#     # Nới lỏng một chút khoảng R,G,B để bù trừ cho sự pha màu nền
#     is_black = (10 <= r <= 45) and (10 <= g <= 45) and (5 <= b <= 35)
    
#     return "RED" if is_red else ("BLACK" if is_black else None)

# def debug_pixel_3x3():
#     print(f"--- DANG SCAN VUNG 3x3 QUANH ({CENTER_X}, {CENTER_Y}) ---")
#     print("Logic: Quét 9 điểm ảnh để tăng độ chính xác khi bị pha màu nền.")
    
#     while not keyboard.is_pressed('esc'):
#         try:
#             # Chụp vùng 3x3 xung quanh tọa độ trung tâm
#             img = pyautogui.screenshot(region=(CENTER_X - 1, CENTER_Y - 1, 3, 3))
#             pixels = list(img.getdata())
            
#             red_count = 0
#             black_count = 0
            
#             # Kiểm tra từng pixel trong 9 điểm
#             for p in pixels:
#                 res = check_logic_strict(p[0], p[1], p[2])
#                 if res == "RED": red_count += 1
#                 if res == "BLACK": black_count += 1
            
#             # --- CHIẾN THUẬT QUYẾT ĐỊNH ---
#             # Chỉ cần 3/9 điểm khớp màu đỏ HOẶC 3/9 điểm khớp màu đen là xác nhận Target
#             if red_count >= 3:
#                 status = "DANG TARGET QUAI (RED)  "
#             elif black_count >= 3:
#                 status = "DANG TARGET QUAI (BLACK)"
#             else:
#                 status = "KHONG CO MUC TIEU         "
            
#             # Lấy màu tại điểm trung tâm để hiển thị RGB debug
#             r, g, b = pixels[4] # Điểm thứ 5 là tâm của 3x3
#             print(f"\rTâm RGB:({r:3},{g:3},{b:3}) | RedPts:{red_count}/9 | BlackPts:{black_count}/9 | {status}", end="")
            
#         except Exception as e:
#             print(f"\nLoi: {e}")
#             break
#         time.sleep(0.1)

# if __name__ == "__main__":
#     debug_pixel_3x3()
import pyautogui
import pydirectinput
import keyboard
import time

# Tọa độ vùng quét của bạn
CHECK_X = 920 
CHECK_Y = 790

def check_logic_hybrid(r, g, b):
    """Logic Đỏ và Tương phản Đen dựa trên thông số bạn cung cấp"""
    # 1. Bắt Đỏ: R chiếm ưu thế
    is_red = (110 <= r <= 185) and (g < 95) and (b < 95) and (abs(g - b) < 15)
    
    # 2. Bắt Tương phản Đen: Dựa trên Avg sáng hơn nền đất
    avg = (r + g + b) / 3
    is_black = (25 <= avg <= 55) and (abs(r - g) < 12)
    
    return "RED" if is_red else ("BLACK" if is_black else None)

def debug_melee_logic():
    print(f"--- DEBUG CẬN CHIẾN (HOLD MOUSE) TẠI ({CHECK_X}, {CHECK_Y}) ---")
    print("Cơ chế: Đè chuột trái khi thấy quái - Nhả chuột khi mất Target.")
    print("[V]: Bật/Tắt Bot | [ESC]: Thoát")
    
    is_bot_on = False
    is_pressing = False # Trạng thái đang đè chuột hay không

    while not keyboard.is_pressed('esc'):
        if keyboard.is_pressed('v'):
            is_bot_on = not is_bot_on
            if not is_bot_on and is_pressing:
                pydirectinput.mouseUp(button='left') # Nhả chuột nếu tắt bot đột ngột
                is_pressing = False
            print(f"\nBot: {'BAT' if is_bot_on else 'TAT'}")
            time.sleep(0.3)

        if is_bot_on:
            try:
                # Quét vùng 3x3
                img = pyautogui.screenshot(region=(CHECK_X - 1, CENTER_Y - 1, 3, 3))
                pixels = list(img.getdata())
                
                red_pts = sum(1 for p in pixels if check_logic_hybrid(p[0], p[1], p[2]) == "RED")
                black_pts = sum(1 for p in pixels if check_logic_hybrid(p[0], p[1], p[2]) == "BLACK")

                # CHIẾN THUẬT QUYẾT ĐỊNH
                if red_pts >= 3 or black_pts >= 3:
                    if not is_pressing:
                        pydirectinput.mouseDown(button='left') # Đè chuột trái
                        is_pressing = True
                    status = f">>> DANG CHEM (R:{red_pts} B:{black_pts}) <<<"
                else:
                    if is_pressing:
                        pydirectinput.mouseUp(button='left') # Nhả chuột khi mất Target
                        is_pressing = False
                    status = "--- DANG DI CHUYEN / TIM QUAI ---"

                print(f"\r{status}", end="")
                
            except Exception as e:
                if is_pressing: pydirectinput.mouseUp(button='left')
                print(f"\nLỗi: {e}")
                break
        
        time.sleep(0.05) # Nhịp quét 50ms để đảm bảo độ nhạy

if __name__ == "__main__":
    # Lưu ý: CENTER_Y chưa định nghĩa ở trên, dùng CHECK_Y thay thế
    CENTER_Y = CHECK_Y 
    debug_melee_logic()