import win32gui
import time
import pyautogui

def get_cursor_id():
    """Lấy thông tin Handle của con trỏ hiện tại."""
    # GetCursorInfo trả về (flags, hCursor, (x, y))
    info = win32gui.GetCursorInfo()
    return info[1]  # Trả về hCursor (ID của con trỏ)

print("Đang bắt đầu theo dõi con trỏ... Hãy quay lại game Sacred.")
print("Di chuyển chuột vào quái để xem sự thay đổi ID.")

last_id = get_cursor_id()

try:
    while True:
        current_id = get_cursor_id()
        
        # Nếu ID con trỏ thay đổi so với lần kiểm tra trước
        if current_id != last_id:
            # Lấy tọa độ chuột hiện tại để biết vị trí thay đổi
            x, y = pyautogui.position()
            print(f"Thay đổi nhận diện! ID mới: {current_id} tại vị trí ({x}, {y})")
            
            # Lưu lại ID mới để so sánh tiếp
            last_id = current_id
            
        time.sleep(0.1)  # Kiểm tra 10 lần mỗi giây để tiết kiệm CPU
except KeyboardInterrupt:
    print("Dừng chương trình.")