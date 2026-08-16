import mss
import pyautogui
import time
import keyboard

print("--- TOOL TRINH SÁT V2 (CHỐNG TOOLTIP) ---")
print("BƯỚC 1: Di chuột vào Skill -> Nhấn 'S' để KHÓA TỌA ĐỘ.")
print("BƯỚC 2: Di chuột ra chỗ khác cho mất bảng Info -> Nhấn 'D' để LẤY MÀU.")
print("Nhấn 'ESC' để thoát.")

sct = mss.mss()
saved_x = None
saved_y = None

while True:
    # Lấy tọa độ chuột hiện tại để hiển thị chơi
    cur_x, cur_y = pyautogui.position()
    
    # In thông tin trạng thái
    if saved_x is None:
        status = "CHƯA KHÓA TỌA ĐỘ"
    else:
        status = f"ĐÃ KHÓA: {saved_x}, {saved_y} (Chờ bấm D...)"
        
    print(f"Mouse: {cur_x}, {cur_y} | {status}      ", end="\r")

    # --- BƯỚC 1: KHÓA TỌA ĐỘ (S) ---
    if keyboard.is_pressed('s'):
        saved_x, saved_y = cur_x, cur_y
        print(f"\n[OK] Đã khóa mục tiêu tại: {saved_x}, {saved_y}")
        print("-> Giờ hãy di chuột ra chỗ khác để skill hiện nguyên hình!")
        time.sleep(0.5)

    # --- BƯỚC 2: LẤY MÀU TỪ XA (D) ---
    if keyboard.is_pressed('d'):
        if saved_x is not None:
            # Chụp ảnh tại tọa độ ĐÃ KHÓA (chứ không phải chỗ con chuột đang đứng)
            bbox = {'top': saved_y, 'left': saved_x, 'width': 1, 'height': 1}
            try:
                sct_img = sct.grab(bbox)
                color_bgr = sct_img.pixel(0, 0)
                r, g, b = color_bgr[2], color_bgr[1], color_bgr[0]
                
                print(f"\n[THÀNH CÔNG] Tọa độ: {saved_x}, {saved_y}")
                print(f"              Màu CHUẨN (Không bị che): ({r}, {g}, {b})")
                print("-" * 30)
                
                # Reset để làm lại cái khác nếu muốn
                saved_x = None 
                saved_y = None
                time.sleep(0.5)
            except Exception as e:
                print(f"\nLỗi chụp: {e}")
        else:
            print("\n[LỖI] Chưa khóa tọa độ! Bấm S trước đã.")
            time.sleep(0.5)

    if keyboard.is_pressed('esc'):
        break
        
    time.sleep(0.05)