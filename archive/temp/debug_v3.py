# import pyautogui
# import pydirectinput
# import keyboard
# import time

# # Tọa độ vùng quét của bạn
# CHECK_X = 952#916 
# CHECK_Y = 787#781

# def check_logic_ultimate(r, g, b):
#     # 1. Nhận diện CHỮ TRẮNG (Mob)
#     if r > 250 and g > 250 and b > 250:
#         return "WHITE"
    
#     # 2. Nhận diện CHỮ VÀNG (Boss)
#     if r > 240 and g > 240 and (100 < b < 150):
#         return "YELLOW"
    
#     # 3. Nhận diện MÁU ĐỎ (Quái khỏe)
#     if (110 <= r <= 185) and (g < 95) and (b < 95) and (abs(g - b) < 15):
#         return "RED"
        
#     return None

# def debug_selective_logs():
#     print(f"--- RADAR LOC TIN HIEU CHU TAI ({CHECK_X}, {CHECK_Y}) ---")
#     print("Bot se chi in toa do khi phat hien net chu Trang/Vang.")
#     print("[V]: Bat/Tat Bot | [ESC]: Thoat")
    
#     is_bot_on = False
#     is_pressing = False

#     while not keyboard.is_pressed('esc'):
#         if keyboard.is_pressed('v'):
#             is_bot_on = not is_bot_on
#             if not is_bot_on and is_pressing:
#                 pydirectinput.mouseUp(button='left')
#                 is_pressing = False
#             print(f"\nBot Status: {'ON' if is_bot_on else 'OFF'}")
#             time.sleep(0.3)

#         if is_bot_on:
#             try:
#                 # Quét vùng 3x3 quanh điểm mục tiêu
#                 img = pyautogui.screenshot(region=(CHECK_X - 1, CHECK_Y - 1, 3, 3))
#                 pixels = list(img.getdata())
                
#                 found_text_coords = []
#                 has_red = False
                
#                 for i, p in enumerate(pixels):
#                     res = check_logic_ultimate(p[0], p[1], p[2])
#                     if res in ["WHITE", "YELLOW"]:
#                         # Tính tọa độ thực tế trên màn hình
#                         abs_x = (CHECK_X - 1) + (i % 3)
#                         abs_y = (CHECK_Y - 1) + (i // 3)
#                         found_text_coords.append(f"{res}:({abs_x},{abs_y})")
#                     elif res == "RED":
#                         has_red = True

#                 # LOGIC HANH DONG: Có đỏ hoặc có chữ là đè chuột
#                 if has_red or found_text_coords:
#                     if not is_pressing:
#                         pydirectinput.mouseDown(button='left')
#                         is_pressing = True
                    
#                     # LOGIC IN AN: Chỉ in khi danh sách tọa độ chữ có dữ liệu
#                     if found_text_coords:
#                         logs = " | ".join(found_text_coords)
#                         print(f"\r[DETECTED TEXT] {logs}                ", end="")
#                 else:
#                     if is_pressing:
#                         pydirectinput.mouseUp(button='left')
#                         is_pressing = False
#                     # Xóa dòng log khi không còn mục tiêu để màn hình sạch sẽ
#                     print(f"\r{' ' * 70}", end="")

#             except Exception as e:
#                 if is_pressing: pydirectinput.mouseUp(button='left')
#                 print(f"\nLoi: {e}")
#                 break
        
#         time.sleep(0.04) # Quét nhanh 40ms

# if __name__ == "__main__":
#     debug_selective_logs()
import pyautogui
import pydirectinput
import keyboard
import time

# Tọa độ trung tâm dải quét (Dựa trên dữ liệu 941 - 953 của bạn)
CHECK_X = 947 
CHECK_Y = 790 

# Cấu hình dải quét ngang
SCAN_W = 20 
SCAN_H = 3

def check_logic_ultimate(r, g, b):
    if r > 250 and g > 250 and b > 250: return "WHITE"
    if r > 240 and g > 240 and (100 < b < 150): return "YELLOW"
    if (110 <= r <= 185) and (g < 95) and (b < 95) and (abs(g - b) < 15): return "RED"
    return None

def debug_optimized_with_logs():
    print(f"--- RADAR DAI NGANG + LOG TAI ({CHECK_X}, {CHECK_Y}) ---")
    print("[V]: Bat/Tat Bot | [ESC]: Thoat")
    
    is_bot_on = False
    is_pressing = False

    while not keyboard.is_pressed('esc'):
        if keyboard.is_pressed('v'):
            is_bot_on = not is_bot_on
            if not is_bot_on and is_pressing:
                pydirectinput.mouseUp(button='left')
                is_pressing = False
            print(f"\nBot Status: {'ON' if is_bot_on else 'OFF'}")
            time.sleep(0.3)

        if is_bot_on:
            try:
                # Chụp dải ngang bao quát vùng chữ và máu
                # region=(left, top, width, height)
                start_x = CHECK_X - (SCAN_W // 2)
                start_y = CHECK_Y - (SCAN_H // 2)
                img = pyautogui.screenshot(region=(start_x, start_y, SCAN_W, SCAN_H))
                pixels = list(img.getdata())
                
                found_text_coords = []
                red_count = 0
                
                # Duyệt qua toàn bộ pixel trong dải quét để lấy Log tọa độ
                for i, p in enumerate(pixels):
                    res = check_logic_ultimate(p[0], p[1], p[2])
                    if res in ["WHITE", "YELLOW"]:
                        abs_x = start_x + (i % SCAN_W)
                        abs_y = start_y + (i // SCAN_W)
                        # Chỉ lấy tối đa 2 tọa độ đầu tiên để log không bị quá dài
                        if len(found_text_coords) < 2:
                            found_text_coords.append(f"{res}:({abs_x},{abs_y})")
                    elif res == "RED":
                        red_count += 1

                # LOGIC BEM GIỮ NGUYÊN: Có đỏ (>=2 điểm) hoặc có chữ là đè chuột
                if red_count >= 2 or found_text_coords:
                    if not is_pressing:
                        pydirectinput.mouseDown(button='left')
                        is_pressing = True
                    
                    # PRINT DEBUG: Chỉ hiện log khi có chữ để tránh loạn màn hình
                    if found_text_coords:
                        logs = " | ".join(found_text_coords)
                        print(f"\r[BEM] {logs} R:{red_count}                ", end="")
                    else:
                        print(f"\r[BEM] Only RED Target (R:{red_count})          ", end="")
                else:
                    if is_pressing:
                        pydirectinput.mouseUp(button='left')
                        is_pressing = False
                    print(f"\r{' ' * 70}", end="")

            except Exception as e:
                if is_pressing: pydirectinput.mouseUp(button='left')
                print(f"\nLoi: {e}")
                break
        
        time.sleep(0.04) # Nhịp quét 40ms cực nhanh

if __name__ == "__main__":
    debug_optimized_with_logs()