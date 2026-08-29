# File: AutoPotionClass.py
from SacredUtils import get_pointer_address # Import hàm dùng chung

class AutoPotion:
    # --- HARD-CODE ĐỊA CHỈ TẠI ĐÂY (KHÔNG SỢ SAI) ---
    BASE_OFFSET = 0x006D5C40        # Base Máu & EXP Nhân vật
    OFFSETS = [0x4, 0x4, 0x4D8]     # Offset Máu
    EXP_OFFSETS = [0x4, 0x4, 0x3B4] # Offset Kinh nghiệm (EXP)
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
        except Exception as e:
            print(f"[POTION ERROR] {e}")
        return None

    def get_exp(self):
        """Đọc tổng điểm kinh nghiệm (EXP) hiện tại của nhân vật."""
        if not self.pm or self.module_addr is None:
            return None
        try:
            static_base = self.module_addr + self.BASE_OFFSET
            exp_addr = get_pointer_address(self.pm, static_base, self.EXP_OFFSETS)
            if exp_addr:
                return self.pm.read_int(exp_addr)
        except Exception as e:
            print(f"[EXP ERROR] {e}")
        return None