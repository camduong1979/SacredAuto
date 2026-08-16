# File: SacredUtils.py
def get_pointer_address(pm, base_addr, offsets):
    """
    Hàm đọc chuỗi pointer đa tầng dùng chung.
    pm: Đối tượng Pymem
    base_addr: Địa chỉ tĩnh bắt đầu
    offsets: Danh sách offset [0x4, 0x4...]
    """
    try:
        # Đọc giá trị đầu tiên từ Base
        addr = pm.read_int(base_addr)
        
        # Duyệt qua các tầng offset
        for i, offset in enumerate(offsets):
            if i < len(offsets) - 1:
                # Nếu chưa phải tầng cuối, đọc tiếp giá trị bên trong
                addr = pm.read_int(addr + offset)
            else:
                # Nếu là tầng cuối, cộng offset để ra địa chỉ thật
                return addr + offset
        return addr
    except Exception:
        return None