import pymem
import pymem.process
import keyboard
import time

# ================= CẤU HÌNH POINTER CẢNH BÁO QUÁI =================
PROCESS_NAME = "sacred.exe"

# Base Address từ hình 2: "Sacred.exe" + 013E9FA4
DANGER_BASE_OFFSET = 0x013E9FA4

# Chỉ có 1 offset duy nhất theo hình là CC0
DANGER_OFFSETS = [0xCC0]

# =================================================================

def get_pointer_address(pm, base_addr, offsets):
    """Đọc chuỗi pointer đa tầng (dùng chung logic với hàm HP)"""
    try:
        temp_addr = pm.read_int(base_addr)
        for i, offset in enumerate(offsets):
            if i < len(offsets) - 1:
                temp_addr = pm.read_int(temp_addr + offset)
            else:
                return temp_addr + offset
        return temp_addr
    except Exception:
        return None

def main():
    print(f"--- TEST CẢNH BÁO QUÁI (DANGER SENSOR) ---")
    
    try:
        pm = pymem.Pymem(PROCESS_NAME)
        module = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME).lpBaseOfDll
        print(f"-> Connected! Base Module: {hex(module)}")
    except Exception as e:
        print(f"Lỗi: Không tìm thấy game! ({e})")
        return

    static_danger_base = module + DANGER_BASE_OFFSET

    print("Đang theo dõi... Nhấn ESC để dừng.")

    while True:
        try:
            if keyboard.is_pressed('esc'): break

            # 1. Tìm địa chỉ chứa giá trị cảnh báo quái
            danger_addr = get_pointer_address(pm, static_danger_base, DANGER_OFFSETS)
            
            if danger_addr:
                # 2. Đọc giá trị tại địa chỉ đó
                danger_value = pm.read_int(danger_addr)
                
                # 3. Hiển thị trạng thái
                status = "!!! CÓ QUÁI !!!" if danger_value > 0 else "An toàn"
                print(f"Danger Value: {danger_value} | Trạng thái: {status}      ", end='\r')

        except Exception as e:
            # Nếu có lỗi (ví dụ load map), in ra thông báo nhẹ
            print(f"Đang đọc dữ liệu... {e}", end='\r')
            pass
        
        time.sleep(0.1) # Tốc độ quét 10 lần / giây

if __name__ == "__main__":
    main()