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
# --- OLD CODE (REPLACED: MONOLITHIC SACRED BOT MEMORY V2.5) ---
# ==============================================================================
# class SacredBotMemoryOld:
#     def __init__(self):
#         self.config = self.load_config()
#         self.voice = VoiceAssistant()
#         self.pm = None
#         self.module_addr = None
#         self.cooldown_hook = None
#         self.ai_sys = None
#         self.radar = None
#         self.potion_sys = None
#         self.danger_sys = None
#         self.hotkey_sys = None
#         self.game_connected = False
#         self.is_running = False
#         self.exit_event = threading.Event()
#         self._data_lock = threading.Lock()
#         self.last_threat = 0
#         self.last_exp = 0
#         self.shared_data = {'hp_percent': 100.0, 'threat_level': 0, 'exp': 0, 'monster_ids': set(), 'hover_id': 0}
#         self.is_in_combat = False
#         self.safe_start_time = 0.0
#         self.last_speak_time = 0
#         self.is_pressing = False
#         self.is_target_active = False
#         self.target_detected = False
#         self.target_locked_id = 0
#         self.is_left_down = False
#         self.is_right_down = False
#         self.sct = None
#         self.buff_queue = self._init_buff_system()
#         self.last_buff_finish_time = 0
#         self.last_buff_cast_delay = 0
#         self.last_event_msg = "Sẵn sàng (Memory Mode)"
#         self.last_hud_print_time = 0.0
#
#     def print_hud(self, hp, threat, monster_count=0, hover_id=0, exp=0):
#         now = time.time()
#         if now - self.last_hud_print_time < 0.2:
#             return
#         self.last_hud_print_time = now
#         clean_msg = self.last_event_msg.replace("\r", "").replace("\n", " ").strip()
#         event_short = (clean_msg[:18] + "..") if len(clean_msg) > 20 else clean_msg
#         target_str = f"LOCK:{self.target_locked_id}" if self.target_detected else "None"
#         hud_line = f"\rHP: {hp:5.1f}% | Target: {target_str:<12} | {event_short}\033[K"
#         sys.stdout.write(hud_line)
#         sys.stdout.flush()
#
#     def load_config(self):
#         import json
#         try:
#             with open('sacred_config.json', 'r', encoding='utf-8') as f:
#                 return json.load(f)
#         except Exception as e:
#             return {}
#
#     def _init_buff_system(self):
#         buff_cfg = self.config.get('auto_buff_system', {})
#         buffs = []
#         for buff_data in buff_cfg.get('buffs', []):
#             buff_id = buff_data.get('id', 'unknown')
#             mode = buff_data.get('mode', 'visual' if 'co' in buff_id else 'memory')
#             buffs.append({
#                 'id': buff_id,
#                 'name': buff_data.get('name', 'Buff'),
#                 'enabled': buff_data.get('enabled', False),
#                 'mode': mode,
#                 'interval': buff_data.get('interval', 30),
#                 'cast_delay': buff_data.get('cast_delay', 0.5),
#                 'fast_retry_delay': buff_data.get('fast_retry_delay', 0.3),
#                 'max_retries': buff_data.get('max_retries', 3),
#                 'use_memory': buff_data.get('use_memory', (mode == 'memory')),
#                 'sentinel_enabled': buff_data.get('sentinel_enabled', (mode == 'visual')),
#                 'sentinel_x': buff_data.get('sentinel_x', 0),
#                 'sentinel_y': buff_data.get('sentinel_y', 0),
#                 'tolerance_rgb': buff_data.get('tolerance_rgb', 1),
#                 'min_brightness': buff_data.get('min_brightness', 14),
#                 'max_brightness': buff_data.get('max_brightness', 177),
#                 'retry_timeout': buff_data.get('retry_timeout', 3.0),
#                 'sequence': buff_data.get('sequence', []),
#                 'last_cast_time': 0.0,
#                 'retry_count': 0,
#                 'next_retry_time': 0.0
#             })
#         return {'enabled': buff_cfg.get('enabled', False), 'buffs': buffs}
#
#     def is_buff_ready(self, buff):
#         mode = buff.get('mode', 'memory' if buff.get('use_memory', False) else 'visual')
#         if mode == 'memory' or buff.get('use_memory', False):
#             if self.cooldown_hook and self.cooldown_hook.is_hooked:
#                 cd_val = self.cooldown_hook.get_cooldown()
#                 if cd_val is not None:
#                     return cd_val <= 0.001
#             if not buff.get('sentinel_enabled', False):
#                 return True
#         if not buff.get('sentinel_enabled', True):
#             return True
#         x = buff.get('sentinel_x', 0)
#         y = buff.get('sentinel_y', 0)
#         if x <= 0 or y <= 0:
#             return True
#         try:
#             if self.sct is None:
#                 self.sct = mss.mss()
#             bbox = {'top': y, 'left': x, 'width': 1, 'height': 1}
#             img = np.array(self.sct.grab(bbox))
#             pixel = img[0, 0]
#             b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
#             tol = buff.get('tolerance_rgb', 1)
#             min_b = buff.get('min_brightness', 14)
#             max_b = buff.get('max_brightness', 177)
#             is_equal_rgb = (abs(r - g) <= tol) and (abs(g - b) <= tol) and (abs(r - b) <= tol)
#             avg_brightness = (r + g + b) / 3.0
#             return not (is_equal_rgb and (min_b <= avg_brightness <= max_b))
#         except Exception:
#             self.sct = None
#             return True
#
#     def cast_buff_guarded(self, target_buff):
#         sequence = target_buff.get('sequence', [])
#         if not sequence or len(sequence) < 3:
#             return False
#         select_step, cast_step, restore_steps = sequence[0], sequence[1], sequence[2:]
#         self.hotkey_sys.release_all_inputs()
#         time.sleep(0.01)
#         self.hotkey_sys.execute_step(select_step)
#         time.sleep(0.05)
#         if not self.is_buff_ready(target_buff):
#             for step in restore_steps:
#                 self.hotkey_sys.execute_step(step)
#             return False
#         self.hotkey_sys.execute_step(cast_step)
#         cast_success = False
#         for _ in range(3):
#             time.sleep(0.06)
#             if self.cooldown_hook and self.cooldown_hook.is_hooked:
#                 cd_after = self.cooldown_hook.get_cooldown()
#                 if cd_after is not None and cd_after > 0.001:
#                     cast_success = True
#                     break
#             elif not self.is_buff_ready(target_buff):
#                 cast_success = True
#                 break
#         for step in restore_steps:
#             self.hotkey_sys.execute_step(step)
#         return cast_success
#
#     def connect_game(self):
#         try:
#             p_name = "sacred.exe"
#             self.pm = pymem.Pymem(p_name)
#             self.module_addr = pymem.process.module_from_name(self.pm.process_handle, p_name).lpBaseOfDll
#             self.potion_sys = AutoPotion(self.pm, self.module_addr)
#             self.danger_sys = DangerSystem(self.pm, self.module_addr)
#             self.cooldown_hook = SkillCooldownManager(self.pm, self.module_addr)
#             self.cooldown_hook.install()
#             self.hotkey_sys = HotKeySystem(self.config.get('hotkey_system'))
#             self.radar = CombatRadar(self.config)
#             return True
#         except Exception:
#             return False
#
#     def sensor_worker(self):
#         while not self.exit_event.is_set():
#             if self.game_connected and self.is_running:
#                 try:
#                     hp = self.potion_sys.get_hp_percent()
#                     threat = self.danger_sys.get_threat_level()
#                     exp = self.potion_sys.get_exp()
#                     monster_ids = self.danger_sys.get_monster_ids(max_monsters=15)
#                     hover_id = self.danger_sys.get_mouse_hover_id()
#                     with self._data_lock:
#                         self.shared_data['hp_percent'] = hp if hp is not None else 100.0
#                         self.shared_data['threat_level'] = threat
#                         self.shared_data['exp'] = exp if exp is not None else 0
#                         self.shared_data['monster_ids'] = monster_ids
#                         self.shared_data['hover_id'] = hover_id
#                 except Exception:
#                     self.game_connected = False
#             time.sleep(0.05)

#     def action_worker(self):
#         last_potion_time = 0
#         while not self.exit_event.is_set():
#             if not (self.game_connected and self.is_running):
#                 time.sleep(0.1)
#                 continue
#             with self._data_lock:
#                 hp = self.shared_data['hp_percent']
#                 threat = self.shared_data['threat_level']
#                 exp = self.shared_data['exp']
#                 monster_ids = self.shared_data['monster_ids']
#                 hover_id = self.shared_data['hover_id']
#             threshold = self.config['potion_system']['threshold_percent']
#             current_time = time.time()
#             if threat > 0:
#                 self.safe_start_time = 0.0
#                 if not self.is_in_combat:
#                     self.is_in_combat = True
#                     self.voice.speak("Có quái.")
#             else:
#                 if self.is_in_combat:
#                     if self.safe_start_time == 0.0:
#                         self.safe_start_time = current_time
#                     elif current_time - self.safe_start_time > 3.0:
#                         self.voice.speak('Clear.')
#                         self.is_in_combat = False
#                         self.safe_start_time = 0.0
#                         self.target_detected = False
#                         self.target_locked_id = 0
#             if hp < threshold and (current_time - last_potion_time > 0.8):
#                 pydirectinput.press(self.config['potion_system']['key'])
#                 last_potion_time = current_time
#             self.hotkey_sys.run_check()
#             time.sleep(0.02)
#
#     def memory_target_worker(self):
#         while not self.exit_event.is_set():
#             if not (self.game_connected and self.is_running and self.is_target_active):
#                 self.target_detected = False
#                 self.target_locked_id = 0
#                 time.sleep(0.05)
#                 continue
#             try:
#                 with self._data_lock:
#                     hover_id = self.shared_data.get('hover_id', 0)
#                     monster_ids = self.shared_data.get('monster_ids', set())
#                 if hover_id > 1:
#                     is_id_match = hover_id in monster_ids
#                     is_hp_visible = self.radar.is_target_detected() if self.radar else False
#                     if is_id_match and is_hp_visible:
#                         self.target_detected = True
#                         self.target_locked_id = hover_id
#                     else:
#                         self.target_detected = False
#                         self.target_locked_id = 0
#                 else:
#                     self.target_detected = False
#                     self.target_locked_id = 0
#             except Exception:
#                 self.target_detected = False
#                 self.target_locked_id = 0
#             time.sleep(0.02)
#
#     def mouse_arbiter_worker(self):
#         while not self.exit_event.is_set():
#             if not (self.game_connected and self.is_running):
#                 time.sleep(0.05)
#                 continue
#             z_down = keyboard.is_pressed('z')
#             x_down = keyboard.is_pressed('x')
#             should_left_down = self.target_detected or z_down
#             if should_left_down and not self.is_left_down:
#                 pydirectinput.mouseDown(button='left')
#                 self.is_left_down = True
#             elif not should_left_down and self.is_left_down:
#                 pydirectinput.mouseUp(button='left')
#                 self.is_left_down = False
#             if x_down and not self.is_right_down:
#                 pydirectinput.mouseDown(button='right')
#                 self.is_right_down = True
#             elif not x_down and self.is_right_down:
#                 pydirectinput.mouseUp(button='right')
#                 self.is_right_down = False
#             time.sleep(0.01)
#
#     def run(self):
#         threads = [
#             threading.Thread(target=self.sensor_worker, daemon=True),
#             threading.Thread(target=self.action_worker, daemon=True),
#             threading.Thread(target=self.memory_target_worker, daemon=True),
#             threading.Thread(target=self.mouse_arbiter_worker, daemon=True),
#         ]
#         for t in threads: t.start()
#         while not self.exit_event.is_set():
#             time.sleep(0.1)
# ==============================================================================
# ------------------------------------------------------------------------------


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

    # --- OLD CODE (REPLACED: targeting_worker v1.0 thiếu đồng bộ is_buffing và re-engage sau khi buff) ---
    # def targeting_worker(self):
    #     last_hover_id = -1
    #     while not self.exit_event.is_set():
    #         if not (self.game_connected and self.is_running):
    #             if self.combat_state:
    #                 self.combat_state.release_target()
    #             time.sleep(0.05)
    #             continue
    #         try:
    #             with self._data_lock:
    #                 hover_id = self.shared_data.get('hover_id', 0)
    #                 monster_ids = self.shared_data.get('monster_ids', set())
    #             if hover_id != last_hover_id:
    #                 last_hover_id = hover_id
    #                 if hover_id > 1:
    #                     if hover_id in monster_ids:
    #                         if self.combat_state:
    #                             self.combat_state.target_detected = True
    #                             self.combat_state.target_locked_id = hover_id
    #                         self.last_event_msg = f"Lock: {hover_id}"
    #                         pydirectinput.mouseDown(button='left')
    #                 else:
    #                     if self.combat_state and self.combat_state.target_detected:
    #                         self.combat_state.release_target()
    #                         pydirectinput.mouseUp(button='left')
    #             if self.combat_state and self.combat_state.target_locked_id > 0:
    #                 if self.combat_state.target_locked_id not in monster_ids:
    #                     self.combat_state.release_target()
    #                     pydirectinput.mouseUp(button='left')
    #                     self.last_event_msg = "Target: Dead"
    #         except Exception:
    #             if self.combat_state:
    #                 self.combat_state.release_target()
    #         time.sleep(0.02)
    # ------------------------------------------------------------------------------------------------------

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