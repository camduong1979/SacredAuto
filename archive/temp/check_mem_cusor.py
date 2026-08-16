import pymem
import time

try:
    # Kết nối với game
    pm = pymem.Pymem("Sacred.exe")
    
    # Cách lấy Base Address chính xác trong phiên bản Pymem mới
    game_module = pymem.process.module_from_name(pm.process_handle, "Sacred.exe")
    base_static_address = game_module.lpBaseOfDll + 0x00285414
    
    print(f"Đã kết nối! Base Address: {hex(game_module.lpBaseOfDll)}")
except Exception as e:
    print(f"Không thể kết nối với game: {e}")
    exit()

def get_pointer_address(base_addr, offsets):
    try:
        # Đọc giá trị tại địa chỉ tĩnh đầu tiên
        addr = pm.read_uint(base_addr)
        # Đi qua các tầng offset trung gian
        for offset in offsets[:-1]:
            addr = pm.read_uint(addr + offset)
        # Cộng offset cuối cùng để ra địa chỉ thực thi
        return addr + offsets[-1]
    except Exception:
        return None

# Cấu trúc Offsets từ hình ảnh bạn cung cấp
# Pointer: "Sacred.exe"+00285414 -> CC -> 20 -> 0 -> CC4
OFFSETS_TARGET = [0xCC, 0x20, 0x0, 0xCC4]

print("--- ĐANG THEO DÕI TARGET ID ---")
print("Di chuột vào quái để kiểm tra...")

try:
    while True:
        target_addr = get_pointer_address(base_static_address, OFFSETS_TARGET)
        
        if target_addr:
            # Đọc ID của vật thể đang bị trỏ vào
            target_id = pm.read_int(target_addr)
            
            if target_id != 0:
                # Dựa vào phát hiện của bạn: 1 thường là nhân vật/không có gì
                if target_id == 1:
                    print("Trạng thái: Đang trỏ vào chính mình hoặc vùng trống đặc biệt")
                else:
                    print(f"Phát hiện Target ID: {target_id} (Có thể là Quái/NPC)")
            else:
                # print("Đất trống")
                pass
        
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Đã dừng chương trình.")