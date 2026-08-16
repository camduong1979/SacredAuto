# import pyautogui
# import keyboard
# import time

# # --- THAY TOA DO BAN LAY TU PAINT VAO DAY ---
# CHECK_X = 960 
# CHECK_Y = 786 

# def debug_pixel():
#     print(f"--- DANG KIEM TRA TOA DO ({CHECK_X}, {CHECK_Y}) ---")
#     print("Nhan 'ESC' de dung lai.")
    
#     while not keyboard.is_pressed('esc'):
#         try:
#             # Lấy màu thực tế
#             r, g, b = pyautogui.pixel(CHECK_X, CHECK_Y)
            
#             # LOGIC CUA BAN:
#             # Case 1: Quai con song (>50% mau) -> Do dam/nhat (133-151)
#             is_red = r > 100 and (r - g > 40) and (r - b > 40)
            
#             # Case 2: Quai sap chet (<50% mau) -> Mau den (29, 24, 12)
#             # Ta coi mau den cung la dang Target vi thanh UI van dang hien
#             is_black = r < 50 and g < 50 and b < 50 and (r > 10) # Tranh mau den tuyen cua UI an
            
#             status = "DANG TARGET QUAI" if (is_red or is_black) else "KHONG CO MUC TIEU"
            
#             # In ket qua len 1 dong duy nhat de de nhin
#             print(f"\rRGB: ({r:3}, {g:3}, {b:3}) | {status}    ", end="")
            
#         except Exception as e:
#             print(f"\nLoi: {e}")
#             break
#         time.sleep(0.1)

# if __name__ == "__main__":
#     debug_pixel()

import pyautogui
import keyboard
import time

# Tọa độ bạn đã xác định từ thực tế
CHECK_X = 962 
CHECK_Y = 799#801#799 

def debug_pixel():
    print(f"--- DANG KIEM TRA TOA DO ({CHECK_X}, {CHECK_Y}) ---")
    print("Mẹo: Hãy rê chuột vào quái và quan sát dải màu thay đổi.")
    print("Nhan 'ESC' de dung lai.")
    
    while not keyboard.is_pressed('esc'):
        try:
            # Lấy màu thực tế
            r, g, b = pyautogui.pixel(CHECK_X, CHECK_Y)
            
            # --- CHIẾN THUẬT PHỔ MÀU THU HẸP ---
            
            # 1. Quái còn sống (>50%): R nằm trong khoảng của bạn (133-151), 
            # G và B phải thấp và cực kỳ sát nhau (đặc tính thanh UI chuẩn)
            is_red_strict = (110 <= r <= 180) and (g < 90) and (b < 90) and (abs(g - b) < 15)
            
            # 2. Quái sắp chết (<50%): Dựa trên (29, 24, 12). 
            # R vẫn phải nhỉnh hơn G và B một chút
            is_black_strict = (10 <= r <= 26) and (10 <= g <= 26) and (5 <= b <= 19)
            
            # Xác định trạng thái dựa trên các điều kiện thắt chặt
            if is_red_strict:
                status = "DANG TARGET QUAI (RED)"
            elif is_black_strict:
                status = "DANG TARGET QUAI (BLACK)"
            else:
                status = "KHONG CO MUC TIEU       "
            
            # In kết quả theo nhịp 100ms
            print(f"\rRGB: ({r:3}, {g:3}, {b:3}) | {status} | Diff(G,B): {abs(g-b):2}  ", end="")
            
        except Exception as e:
            print(f"\nLoi: {e}")
            break
        time.sleep(0.1)

if __name__ == "__main__":
    debug_pixel()