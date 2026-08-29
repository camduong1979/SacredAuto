import pymem
import time

# Kết nối với game
try:
    pm = pymem.Pymem("Sacred.exe")
    print("Đã kết nối với Sacred!")
except:
    print("Không tìm thấy game, hãy mở game lên trước.")
    exit()

# THAY ĐỊA CHỈ BẠN TÌM ĐƯỢC VÀO ĐÂY (Ví dụ: 0x156B4E10)
# Lưu ý: Thêm 0x vào trước mã địa chỉ trong Cheat Engine
CURSOR_ADDRESS = 0x042AEFBC 

print("Đang theo dõi trạng thái con trỏ...")

try:
    while True:
        # Đọc giá trị tại địa chỉ
        current_state = pm.read_int(CURSOR_ADDRESS)
        
        if current_state != 0:
            print(f"Phát hiện mục tiêu! Trạng thái: {current_state}")
        else:
            # print("Đang di chuyển / Đất trống")
            pass
            
        time.sleep(0.05) # Kiểm tra 20 lần mỗi giây
except KeyboardInterrupt:
    print("Dừng chương trình.")