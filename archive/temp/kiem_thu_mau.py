import pyautogui
import keyboard
import time

# CHỈ CẦN 1 VÙNG DUY NHẤT: (x, y, w, h)
MASTER_REGION = (916, 780, 40, 30)

def check_color_logic(r, g, b):
    # Trắng (Mob)
    if r > 250 and g > 250 and b > 250: return "WHITE"
    # Vàng (Boss)
    if r > 240 and g > 240 and (100 < b < 150): return "YELLOW"
    # Đỏ (Máu)
    if (110 <= r <= 185) and (g < 95) and (b < 95) and (abs(g - b) < 15): return "RED"
    return None

def master_radar():
    print(f"--- MASTER RADAR: {MASTER_REGION} ---")
    print("Quét vùng lớn để tìm điểm giao thoa tốt nhất...")
    
    best_results = {"WHITE": None, "YELLOW": None, "RED": None}

    while not keyboard.is_pressed('esc'):
        # Chụp 1 tấm ảnh duy nhất cho toàn vùng để tiết kiệm tài nguyên
        img = pyautogui.screenshot(region=MASTER_REGION)
        pix = img.load()
        
        found_now = []
        for x in range(img.width):
            for y in range(img.height):
                r, g, b = pix[x, y]
                color_type = check_color_logic(r, g, b)
                
                if color_type:
                    abs_x, abs_y = MASTER_REGION[0] + x, MASTER_REGION[1] + y
                    best_results[color_type] = (abs_x, abs_y)
                    found_now.append(color_type)
                    # Sau khi tìm thấy 1 loại màu, không cần quét tiếp pixel của màu đó trong ảnh này
                    break 

        # Hiển thị
        now_str = " | ".join(set(found_now)) if found_now else "Searching..."
        print(f"\r[FOUND] {now_str.ljust(25)} | BEST -> W:{best_results['WHITE']} Y:{best_results['YELLOW']} R:{best_results['RED']}", end="")
        time.sleep(0.05)

if __name__ == "__main__":
    master_radar()