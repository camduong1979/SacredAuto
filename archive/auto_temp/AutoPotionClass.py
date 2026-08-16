# import pydirectinput
# import time

# class AutoPotion:
#     def __init__(self, config, pm, module_addr):
#         self.cfg = config
#         self.pm = pm
#         self.module_addr = module_addr
#         self.last_potion_time = 0

#     def get_pointer_address(self, base_addr, offsets):
#         try:
#             temp_addr = self.pm.read_int(base_addr)
#             for i, offset in enumerate(offsets):
#                 if i < len(offsets) - 1:
#                     temp_addr = self.pm.read_int(temp_addr + offset)
#                 else:
#                     return temp_addr + offset
#             return temp_addr
#         except:
#             return None

#     def run_check(self):
#         if not self.pm or self.module_addr is None: return

#         try:
#             static_base = self.module_addr + self.cfg['base_pointer_offset']
#             current_hp_addr = self.get_pointer_address(static_base, self.cfg['offsets'])
            
#             if current_hp_addr:
#                 current_hp = self.pm.read_int(current_hp_addr)
#                 # Dùng logic Max HP = Current HP - 4 như anh đã test
#                 max_hp = self.pm.read_int(current_hp_addr - 4)

#                 if max_hp > 0:
#                     hp_percent = (current_hp / max_hp) * 100
#                     print(f"[STATUS] HP: {current_hp}/{max_hp} ({hp_percent:.1f}%)      ", end='\r')

#                     if 0 < hp_percent < self.cfg['threshold_percent']:
#                         if time.time() - self.last_potion_time > 0.5:
#                             pydirectinput.press(self.cfg['key'])
#                             self.last_potion_time = time.time()
#                             print(f"\n[ACTION] Auto Potion ({hp_percent:.1f}%)!")
#         except Exception as e:
#             # In ra lỗi cụ thể thay vì chỉ 'error' để dễ debug
#             print(f"\n[POTION ERROR]: {e}")
#             pass

# File: AutoPotionClass.py
from SacredUtils import get_pointer_address # Import hàm dùng chung

class AutoPotion:
    # --- HARD-CODE ĐỊA CHỈ TẠI ĐÂY (KHÔNG SỢ SAI) ---
    BASE_OFFSET = 0x006D5C40        # Base Máu
    OFFSETS = [0x4, 0x4, 0x4D8]     # Offset Máu
    # -----------------------------------------------

    def __init__(self, pm, module_addr):
        self.pm = pm
        self.module_addr = module_addr

    def get_hp_percent(self):
        if not self.pm or self.module_addr is None: return None
        try:
            # 1. Tính địa chỉ gốc
            static_base = self.module_addr + self.BASE_OFFSET
            
            # 2. Gọi hàm dùng chung để lấy địa chỉ Máu
            hp_addr = get_pointer_address(self.pm, static_base, self.OFFSETS)
            
            if hp_addr:
                curr_hp = self.pm.read_int(hp_addr)
                max_hp = self.pm.read_int(hp_addr - 4) # Max HP nằm ngay trước đó 4 byte

                if max_hp > 0:
                    percent = (curr_hp / max_hp) * 100
                    # print(f"HP: {curr_hp}/{max_hp}", end='\r') # Bật nếu muốn test
                    return percent
        except:
            pass
        return None