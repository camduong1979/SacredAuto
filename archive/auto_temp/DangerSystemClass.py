# # ================= MODULE 2: CẢM BIẾN QUÁI (DANGER SYSTEM) =================
# class DangerSystem:
#     def __init__(self, config, pm, module_addr):
#         self.cfg = config
#         self.pm = pm
#         self.module_addr = module_addr

#     def get_threat_level(self):
#         if not self.pm: 
#             return 0
        
#         try:
#             # 1. Tính địa chỉ tĩnh
#             ptr_addr = self.module_addr + self.cfg['base_pointer_offset']
            
#             # 2. Đọc giá trị Base (Pointer cấp 1)
#             base_val = self.pm.read_int(ptr_addr)
            
#             # 3. Tính địa chỉ cuối
#             final_addr = base_val + self.cfg['offsets'][0]
            
#             # 4. Đọc Threat
#             threat_value = self.pm.read_int(final_addr)

#             # --- LOGIC DEBUG THÔNG MINH ---
#             # Chỉ in ra màn hình nếu địa chỉ Base đọc được khác với lần trước
#             # (Để anh biết ngay là Pointer có trỏ đúng chỗ không hay đang trỏ vào 0)
#             if base_val != self.last_debug_base:
#                 print(f"\n[MEM CHECK] Base: {hex(base_val)} | Final: {hex(final_addr)} | Threat: {threat_value}")
#                 self.last_debug_base = base_val
            
#             # Nếu Base = 0, nghĩa là Pointer sai hoặc Game chưa load
#             if base_val == 0:
#                 # Trả về 0 nhưng vẫn in cảnh báo 1 lần
#                 return 0

#             return threat_value

#         except Exception as e:
#             # In lỗi rõ ràng, xuống dòng đàng hoàng
#             print(f"\n[LỖI MEMORY] {e}")
#             return 0
# """
#     def get_threat_level(self):
#         if not self.pm: return 0
#         try:
#             # Đọc Pointer Chain: Base + Offset 1 -> Value + Offset 2 -> Threat
#             ptr_addr = self.module_addr + self.cfg['base_pointer_offset']
#             addr = self.pm.read_int(ptr_addr)
            
#             for offset in self.cfg['offsets']:
#                 addr = addr + offset 
                
#             threat_value = self.pm.read_int(addr)
#             return threat_value
#         except:
#             return 0
# """
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
        except:
            pass
        return 0