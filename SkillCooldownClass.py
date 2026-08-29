import struct
import pymem


class SkillCooldownManager:
    """[NEW 2026-08-29] Quản lý Tự động Inject Hook ASM tại 00562B13 để lấy Pointer Cooldown Skill.
    - Code ASM gốc của Sacred:
        fsubr dword ptr [esi+ecx+12]   (Bytes: D8 6C 0E 12)  [Lưu ý: 0x6C là FSUBR (ST(0) = mem - ST(0)), 0x64 là FSUB]
        fstp dword ptr [esi+ecx+12]    (Bytes: D9 5C 0E 12)
    - Hook thay thế bằng:
        jmp newmem + 3 * NOP (8 bytes tại 00562B13)
    - newmem:
        push eax
        lea eax, [esi+ecx+12]
        mov ds:[cooldownAddressPtr], eax
        pop eax
        fsubr dword ptr [esi+ecx+12]
        fstp dword ptr [esi+ecx+12]
        jmp returnhere
    """
    # 8 byte mã máy gốc chuẩn của game tại 00562B13
    ORIGINAL_BYTES = bytes([0xD8, 0x6C, 0x0E, 0x12, 0xD9, 0x5C, 0x0E, 0x12])
    HOOK_OFFSET = 0x00162B13  # 0x00562B13 - 0x00400000

    def __init__(self, pm, module_addr):
        self.pm = pm
        self.module_addr = module_addr
        self.hook_addr = module_addr + self.HOOK_OFFSET
        self.allocated_mem = None
        self.ptr_addr = None
        self.is_hooked = False

    def install(self):
        """Cấp phát bộ nhớ, ghi bytecode hook và kích hoạt chuyển hướng tại 00562B13."""
        if self.is_hooked:
            return True
        try:
            # 1. Cấp phát 2048 bytes trong process Sacred.exe
            self.allocated_mem = self.pm.allocate(2048)
            if not self.allocated_mem:
                print("[HOOK ERROR] Không thể cấp phát bộ nhớ trong game cho Cooldown Hook!")
                return False

            # Vị trí biến lưu con trỏ cooldownAddressPtr (đặt tại offset +0x100)
            self.ptr_addr = self.allocated_mem + 0x100
            self.pm.write_uint(self.ptr_addr, 0)

            # returnhere = hook_addr + 8 bytes (00562B1B)
            return_addr = self.hook_addr + 8

            # 2. Xây dựng bytecode cho newmem
            code = bytearray()
            code.extend([0x50])                                      # push eax
            code.extend([0x8D, 0x44, 0x0E, 0x12])                    # lea eax, [esi+ecx+12]
            code.append(0xA3)                                        # mov ds:[ptr_addr], eax
            code.extend(struct.pack('<I', self.ptr_addr))
            code.extend([0x58])                                      # pop eax
            code.extend([0xD8, 0x6C, 0x0E, 0x12])                    # fsubr dword ptr [esi+ecx+12] (FSUBR 0x6C)
            code.extend([0xD9, 0x5C, 0x0E, 0x12])                    # fstp dword ptr [esi+ecx+12]

            # jmp returnhere
            curr_ip_after_jmp = self.allocated_mem + len(code) + 5
            rel_to_return = return_addr - curr_ip_after_jmp
            code.append(0xE9)                                        # jmp rel32
            code.extend(struct.pack('<i', rel_to_return))

            # Ghi mã máy vào vùng newmem đã alloc
            self.pm.write_bytes(self.allocated_mem, bytes(code), len(code))

            # 3. Patch tại hook_addr (00562B13) -> jmp allocated_mem + 3 * NOP (8 bytes)
            rel_to_newmem = self.allocated_mem - (self.hook_addr + 5)
            patch = bytearray()
            patch.append(0xE9)
            patch.extend(struct.pack('<i', rel_to_newmem))
            patch.extend([0x90, 0x90, 0x90])                         # 3 NOPs -> total 8 bytes

            self.pm.write_bytes(self.hook_addr, bytes(patch), len(patch))
            self.is_hooked = True
            print(f"[HOOK SUCCESS] Auto Cooldown Hook Active @ {hex(self.hook_addr)} -> Code: {hex(self.allocated_mem)} | Ptr: {hex(self.ptr_addr)}")
            return True
        except Exception as e:
            print(f"[HOOK ERROR] Lỗi khi inject Cooldown Hook: {e}")
            return False

    def get_cooldown(self):
        """Đọc giá trị cooldown hiện tại từ con trỏ thực.
        Trả về:
            float: Thời gian cooldown còn lại (0.0 = Sẵn sàng / Ready, > 0 = Đang cast/hồi chiêu).
            None: Chưa có địa chỉ hợp lệ hoặc lỗi đọc bộ nhớ.
        """
        if not self.is_hooked or not self.ptr_addr:
            return None
        try:
            real_cd_addr = self.pm.read_uint(self.ptr_addr)
            if real_cd_addr == 0:
                return 0.0  # Chưa có skill nào kích hoạt cooldown
            val = self.pm.read_float(real_cd_addr)
            return val
        except Exception:
            return None

    def is_ready(self):
        """Kiểm tra skill đã hoàn toàn sẵn sàng (Cooldown <= 0.001) hay chưa."""
        cd = self.get_cooldown()
        if cd is None:
            return True  # Fallback nếu hook chưa ghi nhận
        return cd <= 0.001

    def is_on_cooldown(self):
        """Kiểm tra skill đang trong thời gian hồi chiêu hoặc đang cast (Cooldown > 0.001)."""
        cd = self.get_cooldown()
        if cd is None:
            return False
        return cd > 0.001

    def uninstall(self):
        """Khôi phục mã máy gốc của game."""
        if self.is_hooked:
            try:
                self.pm.write_bytes(self.hook_addr, self.ORIGINAL_BYTES, len(self.ORIGINAL_BYTES))
                print("[HOOK] Đã gỡ bỏ Cooldown Memory Hook và khôi phục mã gốc game an toàn.")
            except Exception as e:
                print(f"[HOOK UNINSTALL ERROR] Lỗi gỡ hook: {e}")
            self.is_hooked = False

    def __del__(self):
        self.uninstall()
