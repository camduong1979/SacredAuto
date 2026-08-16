import pyautogui
import pydirectinput
import keyboard
import time

CHECK_X = 961 
CHECK_Y = 800 

print("--- TEST CLICK HIT & RUN ---")
print("Cach test: Vao game, chi chuot vao quai.")
print("Nhan phim 'V' de BAT/TAT tu dong danh.")
print("Nhan 'ESC' de thoat.")

is_active = False

while not keyboard.is_pressed('esc'):
    # Phím V để bật tắt chế độ tự đánh
    if keyboard.is_pressed('v'):
        is_active = not is_active
        print(f"\nChe do tu danh: {'ON' if is_active else 'OFF'}")
        time.sleep(0.3)

    if is_active:
        try:
            r, g, b = pyautogui.pixel(CHECK_X, CHECK_Y)
            
            # Logic strict của bạn
            is_red = (110 <= r <= 180) and (g < 90) and (b < 90) and (abs(g - b) < 15)
            is_black = (10 <= r <= 26) and (10 <= g <= 26) and (5 <= b <= 19)
            
            if is_red or is_black:
                pydirectinput.click(button='left')
                # Giữ delay khoảng 0.1s để nhân vật kịp thực hiện Animation đánh
                time.sleep(0.1) 
        except:
            pass

    time.sleep(0.02) # Tốc độ quét 20ms