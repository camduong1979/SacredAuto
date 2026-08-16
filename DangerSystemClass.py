# File: DangerSystemClass.py
from SacredUtils import get_pointer_address # Import hàm dùng chung

class DangerSystem:
    # --- HARD-CODE ĐỊA CHỈ TẠI ĐÂY ---
    BASE_OFFSET = 0x013E9FA4        # Base Quái
    OFFSETS = [0xCC0]               # Offset Quái
    # -------------------------------

    def __init__(self, pm, module_addr):
        self.pm = pm
        self.module_addr = module_addr

    def get_threat_level(self):
        if not self.pm or self.module_addr is None: return 0
        try:
            # 1. Tính địa chỉ gốc
            static_base = self.module_addr + self.BASE_OFFSET
            
            # 2. Gọi hàm dùng chung để lấy địa chỉ Threat
            danger_addr = get_pointer_address(self.pm, static_base, self.OFFSETS)
            
            if danger_addr:
                threat = self.pm.read_int(danger_addr)
                return threat
        except Exception as e:
            print(f"[DANGER ERROR] {e}")
        return 0