# import pyautogui
# import keyboard
# import time

# print("--- TOOL LAY TOA DO THANH MAU QUAI ---")
# print("1. Vao game, chi chuot vao quai de HIEN THANH MAU.")
# print("2. Giu nguyen chuot tai vi tri thanh mau (noi co mau do).")
# print("3. Nhan phim 'F' de lay thong tin.")
# print("---------------------------------------")

# while True:
#     if keyboard.is_pressed('v'):
#         # Lay toa do chuot hien tai
#         x, y = pyautogui.position()
#         # Lay mau sac tai toa do do
#         color = pyautogui.pixel(x, y)
        
#         print(f"\n[THANH CONG]")
#         print(f"Toa do X: {x}")v
#         print(f"Toa do Y: {y}")
#         print(f"Ma mau RGB: {color}")
#         print("---------------------------------------")
#         time.sleep(1) # Tranh bam trung lap
    
#     if keyboard.is_pressed('esc'):
#         break

import pyautogui
import keyboard
import time

print("--- TOOL KHOP TOA DO VA LAY MAU QUAI ---")
print("1. Di chuot toi vi tri thanh mau quai, nhan 'V' de LUU TOA DO.")
print("2. Nhan 'N' de LAY MAU RGB tai toa do da luu (khong can di chuot lai).")
print("3. Nhan 'ESC' de THOAT.")
print("--------------------------------------------------")

target_x = None
target_y = None

while True:
    # 1. Luu toa do khi nhan 'V'
    if keyboard.is_pressed('v'):
        target_x, target_y = pyautogui.position()
        print(f"\n[DA LUU TOA DO] X: {target_x} | Y: {target_y}")
        print("-> Gio ban co the nhan 'N' de kiem tra mau tai toa do nay.")
        print("--------------------------------------------------")
        time.sleep(0.3)  # Chống trùng phím

    # 2. Lay mau RGB tai toa do da luu khi nhan 'N'
    if keyboard.is_pressed('n'):
        if target_x is not None and target_y is not None:
            color = pyautogui.pixel(target_x, target_y)
            print(f"\n[MAU TAO DO DA LUU ({target_x}, {target_y})]")
            print(f"RGB: {color}")
            print("--------------------------------------------------")
        else:
            print("\n[CANH BAO] Chua co toa do! Vui long nhan 'V' de luu toa do truoc.")
            print("--------------------------------------------------")
        time.sleep(0.3)

    # 3. Thoat khi nhan 'ESC'
    if keyboard.is_pressed('esc'):
        print("\nDa thoat tool.")
        break

    time.sleep(0.01)  # Giam tải CPUvn