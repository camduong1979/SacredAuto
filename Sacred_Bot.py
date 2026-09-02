import sys
import threading
import time
import keyboard
import winsound
import pymem
import pydirectinput
import mss
import numpy as np

# Import Backend Base & Subsystems
from BotEngine import BotEngine
from AutoPotionClass import AutoPotion
from DangerSystemClass import DangerSystem
from HotKeySetClass import HotKeySystem
from SkillCooldownClass import SkillCooldownManager
from CombatStateManager import CombatStateManager
from PotionPump import PotionPump
from BuffScheduler import BuffScheduler

# ==============================================================================
# [NEW 2026-09-01] REFACTORED MELEE MEMORY BOT (KẾ THỪA BOTENGINE)
# ==============================================================================
class SacredBotMemory(BotEngine):
    """
    Bot Melee vận hành thuần túy trên Memory Scanning (DRY/SOLID Architecture).
    Chỉ tập trung vào:
      1. connect_game(): Kết nối Sacred.exe, khởi tạo Memory Readers & Backend Managers.
      2. targeting_worker(): Quản lý Hover ID + Danh sách ID quái trong RAM -> Tự động giữ/nhả chuột.
    Mọi logic vận hành nền (Buff, Bơm máu, Combat State, HotKey, HUD) do BotEngine quản lý.
    """

    def connect_game(self) -> bool:
        """Kết nối Sacred.exe và khởi tạo các module chuyên biệt."""
        try:
            # 1. An toàn: Gỡ hook cũ nếu reconnect để tránh memory leak / double hook
            if self.cooldown_hook and getattr(self.cooldown_hook, 'is_hooked', False):
                self.cooldown_hook.uninstall()
                self.cooldown_hook = None

            p_name = "sacred.exe"
            self.pm = pymem.Pymem(p_name)
            self.module_addr = pymem.process.module_from_name(self.pm.process_handle, p_name).lpBaseOfDll

            # 2. Khởi tạo Memory Reading Modules
            self.potion_sys = AutoPotion(self.pm, self.module_addr)
            self.danger_sys = DangerSystem(self.pm, self.module_addr)

            # 3. Khởi tạo & Cài đặt Cooldown Memory Hook (00562B13)
            self.cooldown_hook = SkillCooldownManager(self.pm, self.module_addr)
            self.cooldown_hook.install()

            # 4. Khởi tạo Input & Backend Managers
            self.hotkey_sys = HotKeySystem(self.config.get('hotkey_system', {}))
            self.combat_state = CombatStateManager(self.voice)
            self.potion_pump = PotionPump(self.config.get('potion_system', {}), self.voice)
            self.buff_scheduler = BuffScheduler(
                self.voice,
                self.config.get('auto_buff_system', {}),
                self.hotkey_sys,
                self.cooldown_hook,
                self.combat_state
            )

            print(f"\n[SUCCESS] Đã kết nối Sacred.exe (Base: {hex(self.module_addr)})")
            self.voice.speak('Hệ thống Memory Target đã sẵn sàng.')
            return True

        except pymem.exception.ProcessNotFound:
            print("\n[CONNECT ERROR] KHÔNG tìm thấy game Sacred.exe. Vui lòng mở game trước khi chạy Bot!")
            return False
        except pymem.exception.CouldNotOpenProcess:
            print("\n[CONNECT ERROR] KHÔNG THỂ kết nối vào game! Hãy chạy với quyền Administrator (Run as administrator).")
            return False
        except Exception as e:
            print(f"[CONNECT ERROR]: {e}")
            return False

    def targeting_worker(self):
        """
        [NEW 2026-09-01] Luồng Nhận diện & Khóa mục tiêu bằng Memory (Hover ID + monster_ids).
        - Tích hợp cờ is_buffing: Tạm hoãn giữ chuột trái trong lúc Buff để tạo Clean State.
        - Tự động Re-engage: Đè lại chuột trái ngay lập tức sau khi Buff xong nếu mục tiêu vẫn còn sống.
        """
        last_hover_id = -1
        was_buffing = False

        while not self.exit_event.is_set():
            if not (self.game_connected and self.is_running):
                if self.combat_state:
                    self.combat_state.release_target()
                time.sleep(0.05)
                continue

            try:
                with self._data_lock:
                    hover_id = self.shared_data.get('hover_id', 0)
                    monster_ids = self.shared_data.get('monster_ids', set())

                is_buffing = self.combat_state.is_buffing if self.combat_state else False

                # 1. Phục hồi trạng thái giữ chuột tấn công sau khi Buff hoàn tất (Post-Buff Re-engage)
                if was_buffing and not is_buffing:
                    was_buffing = False
                    if self.combat_state and self.combat_state.target_detected and (self.combat_state.target_locked_id in monster_ids):
                        # --- OLD CODE (REPLACED: luon mouseDown, khong kiem tra auto_attack) ---
                        # pydirectinput.mouseDown(button='left')
                        # -----------------------------------------------------------------------
                        # [NEW 2026-09-01] Chi mouseDown khi auto_attack = true trong config
                        auto_attack = self.config.get('combat_system', {}).get('auto_attack', True)
                        if auto_attack:
                            pydirectinput.mouseDown(button='left')

                # 2. Nếu đang trong tiến trình thi triển Buff, nhường quyền điều khiển chuột
                if is_buffing:
                    was_buffing = True
                    time.sleep(0.02)
                    continue

                # 3. Phát hiện mục tiêu mới khi hover_id thay đổi
                if hover_id != last_hover_id:
                    last_hover_id = hover_id
                    if hover_id > 1:
                        if hover_id in monster_ids:
                            # Khóa quái sống hợp lệ
                            if self.combat_state:
                                self.combat_state.target_detected = True
                                self.combat_state.target_locked_id = hover_id
                            self.last_event_msg = f"Lock: {hover_id}"
                            # --- OLD CODE (REPLACED: luon mouseDown, khong kiem tra auto_attack) ---
                            # pydirectinput.mouseDown(button='left')
                            # -----------------------------------------------------------------------
                            # [NEW 2026-09-01] Chi mouseDown khi auto_attack = true trong config
                            auto_attack = self.config.get('combat_system', {}).get('auto_attack', True)
                            if auto_attack:
                                pydirectinput.mouseDown(button='left')
                    else:
                        # Rời trỏ chuột khỏi quái (vào đất hoặc nhân vật)
                        if self.combat_state and self.combat_state.target_detected:
                            self.combat_state.release_target()
                            pydirectinput.mouseUp(button='left')

                # 4. Kiểm tra mục tiêu đang khóa có còn sống trong RAM không (Dead Monster Detection)
                if self.combat_state and self.combat_state.target_locked_id > 0:
                    if self.combat_state.target_locked_id not in monster_ids:
                        # Quái đã chết / biến mất khỏi RAM -> Nhả chuột & nhả lock ngay
                        self.combat_state.release_target()
                        pydirectinput.mouseUp(button='left')
                        self.last_event_msg = "Target: Dead"

            except Exception:
                if self.combat_state:
                    self.combat_state.release_target()

            time.sleep(0.02)  # Quét nhanh 50 FPS (~20ms)

        # Cleanup khi luồng kết thúc
        pydirectinput.mouseUp(button='left')


if __name__ == "__main__":
    bot = SacredBotMemory()
    bot.run()