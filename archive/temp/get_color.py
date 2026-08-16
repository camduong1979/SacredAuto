import mss
import keyboard
import time

# Tọa độ cứng mà anh đã chốt
FIXED_X = 998
FIXED_Y = 793

print(f"--- TOOL LẤY MÀU TỨC THÌ TẠI ({FIXED_X}, {FIXED_Y}) ---")
print("1. Vào game, di chuột ra chỗ khác (để không hiện bảng Info).")
print("2. Bấm phím 'G' để lấy màu ngay lập tức.")
print("3. Bấm 'ESC' để thoát.")

sct = mss.mss()

while True:
    if keyboard.is_pressed('g'):
        # Chụp ngay lập tức tại tọa độ cố định
        bbox = {'top': FIXED_Y, 'left': FIXED_X, 'width': 1, 'height': 1}
        
        try:
            sct_img = sct.grab(bbox)
            
            # mss trả về BGR -> Đổi sang RGB
            pixel = sct_img.pixel(0, 0)
            r, g, b = pixel[2], pixel[1], pixel[0]
            
            print(f"\n[BẮT ĐƯỢC] Tại {FIXED_X}, {FIXED_Y} | MÀU RGB: ({r}, {g}, {b})")
            
            # Chống lặp phím (Debounce)
            time.sleep(0.3)
            
        except Exception as e:
            print(f"Lỗi: {e}")

    if keyboard.is_pressed('esc'):
        break
        
    time.sleep(0.01)