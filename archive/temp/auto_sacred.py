import pymem
import pymem.process
import keyboard
import pydirectinput
import time

# ================= CẤU HÌNH POINTER (CHÍNH XÁC TỪ HÌNH ẢNH) =================
PROCESS_NAME = "sacred.exe"

# Base Address: "Sacred.exe" + 0162B380
BASE_POINTER_OFFSET = 0x006D5C40

# Danh sách Offsets theo thứ tự từ dưới lên trên trong hình (từ Base -> Giá trị cuối)
# C0 -> DAC -> 3AC -> 4D8
OFFSETS = [0x4, 0x4, 0x4D8]

# Giả định: Nếu 4D8 là địa chỉ Máu hiện tại, thì Máu Max thường nằm kế bên (ví dụ 4DC)
# Bạn nên kiểm tra lại trong Cheat Engine xem Max HP lệch bao nhiêu byte so với 4D8
OFFSET_HP_CURRENT = 0x4D8
OFFSET_HP_MAX     = 0x4D4         # Thông thường là Current + 4, hãy chỉnh lại nếu khác

POTION_PERCENT_THRESHOLD = 30 
POTION_COOLDOWN = 0.5         
# ============================================================================

def get_pointer_address(pm, base_addr, offsets):
    """Đọc chuỗi pointer đa tầng"""
    try:
        temp_addr = pm.read_int(base_addr)
        for i, offset in enumerate(offsets):
            if i < len(offsets) - 1:
                # Nếu chưa tới offset cuối, tiếp tục đọc nội dung địa chỉ
                temp_addr = pm.read_int(temp_addr + offset)
            else:
                # Nếu là offset cuối, trả về địa chỉ cuối cùng để đọc giá trị
                return temp_addr + offset
        return temp_addr
    except Exception:
        return None

def main():
    print(f"--- TOOL AUTO SACRED (CẬP NHẬT THEO HÌNH) ---")
    
    try:
        pm = pymem.Pymem(PROCESS_NAME)
        module = pymem.process.module_from_name(pm.process_handle, PROCESS_NAME).lpBaseOfDll
        print(f"-> Connected! Base Module: {hex(module)}")
    except Exception as e:
        print(f"Lỗi: Không tìm thấy game! ({e})")
        return

    last_potion_time = 0
    static_base = module + BASE_POINTER_OFFSET

    while True:
        try:
            if keyboard.is_pressed('esc'): break

            # 1. Tìm địa chỉ máu hiện tại từ chuỗi pointer
            current_hp_addr = get_pointer_address(pm, static_base, OFFSETS)
            
            if current_hp_addr:
                # 2. Đọc giá trị
                current_hp = pm.read_int(current_hp_addr)
                # Max HP thường nằm ngay sau Current HP (4D8 + 4 = 4DC)
                max_hp = pm.read_int(current_hp_addr - 4) 

                if max_hp > 0:
                    hp_percent = (current_hp / max_hp) * 100
                    print(f"HP: {current_hp}/{max_hp} ({hp_percent:.1f}%)    ", end='\r')

                    # 3. Logic bơm máu
                    if hp_percent < POTION_PERCENT_THRESHOLD and current_hp > 0:
                        if time.time() - last_potion_time > POTION_COOLDOWN:
                            print(f"\n[AUTO] HP thấp ({hp_percent:.1f}%) -> Bơm Space!")
                            pydirectinput.press('space')
                            last_potion_time = time.time()

            # 4. Combo Q
            if keyboard.is_pressed('q'):
                pydirectinput.press('6')
                time.sleep(0.05)
                pydirectinput.press('f1')
                while keyboard.is_pressed('q'): time.sleep(0.05)

        except:
            print('errro')
            pass
        
        time.sleep(0.05)

if __name__ == "__main__":
    main()