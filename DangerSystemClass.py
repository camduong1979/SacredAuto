# File: DangerSystemClass.py
from SacredUtils import get_pointer_address # Import hàm dùng chung

class DangerSystem:
    # --- HARD-CODE ĐỊA CHỈ TẠI ĐÂY ---
    BASE_OFFSET = 0x013E9FA4        # Base Quái / Threat
    OFFSETS = [0xD38]               # Offset Quái [0xCC0]    

    # --- ĐỊA CHỈ DANH SÁCH QUÁI & MOUSE HOVER ---
    MONSTER_STRUCT_SIZE = 0x88      # Bước nhảy giữa các slot quái
    MONSTER_START_OFFSET = 0xE30    # Offset quái đầu tiên
    
    MOUSE_HOVER_BASE = 0x008DDB5C   # Base chuột trỏ vật thể
    MOUSE_HOVER_OFFSET = 0x6C       # Offset ID đối tượng dưới chuột
    # ---------------------------------------------

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

    def get_monster_ids(self, max_monsters=10):
        """Quét danh sách ID quái vật hiện hữu trong bộ nhớ game (tối đa max_monsters).
        Trả về: set chứa các monster_id > 0
        """
        if not self.pm or self.module_addr is None:
            return set()
        
        monster_ids = set()
        try:
            # 1. Đọc con trỏ gốc từ Sacred.exe + 0x013E9FA4
            base_ptr_addr = self.module_addr + self.BASE_OFFSET
            base_address = self.pm.read_int(base_ptr_addr)

            if not base_address or base_address == 0:
                return monster_ids

            # 2. Quét từng slot quái
            for i in range(max_monsters):
                current_monster_ptr = base_address + self.MONSTER_START_OFFSET + (i * self.MONSTER_STRUCT_SIZE)
                try:
                    monster_id = self.pm.read_int(current_monster_ptr)
                    if monster_id and monster_id > 0:
                        monster_ids.add(monster_id)
                except Exception:
                    continue
        except Exception as e:
            pass
        return monster_ids

    def get_mouse_hover_id(self):
        """Đọc ID đối tượng mà con trỏ chuột đang hover vào.
        Giá trị:
          0: Không trỏ vào đối tượng nào
          1: Trỏ vào nhân vật của mình
          > 1: ID của NPC, Quái vật, vật thể...
        """
        if not self.pm or self.module_addr is None:
            return 0
        try:
            # Base 0x008DDB5C -> Offset 0x6C
            static_base = self.module_addr + self.MOUSE_HOVER_BASE
            hover_addr = get_pointer_address(self.pm, static_base, [self.MOUSE_HOVER_OFFSET])
            if hover_addr:
                return self.pm.read_int(hover_addr)
        except Exception:
            pass
        return 0

    def is_hovering_monster(self, monster_ids=None, max_monsters=10):
        """Kiểm tra con trỏ chuột hiện tại có đang trỏ trúng một con quái hợp lệ hay không.
        Trả về: (is_monster: bool, hover_id: int)
        """
        hover_id = self.get_mouse_hover_id()
        if hover_id <= 1:
            return False, hover_id

        if monster_ids is None:
            monster_ids = self.get_monster_ids(max_monsters=max_monsters)

        is_monster = hover_id in monster_ids
        return is_monster, hover_id