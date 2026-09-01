import sys
import threading
import time
import keyboard
import winsound
import pymem
import pydirectinput
import mss
import numpy as np

# --- OLD CODE (REPLACED) ---
# # Import các module đã có
# from AutoPotionClass import AutoPotion
# from DangerSystemClass import DangerSystem
# from HotKeySetClass import HotKeySystem
# from CombatRadarClass import CombatRadar
# from VoiceAssistant import VoiceAssistant
# from YOLOManagerClass import YOLOManager
# 
# 
# class SacredBot:
#     def __init__(self):
#         self.config = self.load_config()
#         self.voice = VoiceAssistant()
#         self.pm = None
#         self.module_addr = None
# 
#         # --- KHỞI TẠO BIẾN HỆ THỐNG (Tránh lỗi NoneType) ---
#         self.ai_sys = None       # YOLO AI Module
#         self.radar = None
#         self.potion_sys = None
#         self.danger_sys = None
#         self.hotkey_sys = None
#         
#         # Flags điều khiển trạng thái
#         self.game_connected = False
#         self.is_running = False
#         self.exit_event = threading.Event()
#         self._data_lock = threading.Lock()   # Bảo vệ shared_data giữa 2 thread
# 
#         self.last_threat = 0
#         self.shared_data = {
#             'hp_percent': 100.0,
#             'threat_level': 0
#         }        
#         
#         self.is_in_combat = False
#         self.safe_start_time = 0.0      # Mốc thời gian bắt đầu đếm Safe (giây thực)
#         self.last_speak_time = 0        
#         self.is_pressing = False
# 
#         # Biến điều khiển YOLO Worker (Z bật / X tắt)
#         self.is_yolo_active = False     # Flag bật/tắt luồng YOLO targeting
# 
#         self.sct = None                     # Lazy init trong luồng worker để tránh lỗi thread-local srcdc Windows
#         self.buff_queue = self._init_buff_system()
#         self.last_buff_finish_time = 0    # Mốc thời gian hoàn tất buff gần nhất
#         self.last_buff_cast_delay = 0     # Cast delay của buff vừa xong (giây)
#  
#         self.last_event_msg = "Sẵn sàng"  # Thông điệp sự kiện gần nhất cho Single-line HUD
#         self.last_hud_print_time = 0.0    # Giới hạn tần suất in HUD tránh giật console
# 
# 
#     def print_hud(self, hp, threat):
#         """[NEW 2026-08-16] In trạng thái trực tiếp trên 1 dòng duy nhất (Single-line Live HUD).
#         Sử dụng sys.stdout.write('\r...') để đảm bảo ghi thẳng vào console buffer của Windows.
#         """
#         now = time.time()
#         if now - self.last_hud_print_time < 0.25:
#             return
#         self.last_hud_print_time = now
# 
#         status_text = "ON" if self.is_running else "OFF"
#         clean_msg = (
#             self.last_event_msg.replace("\r", "").replace("\n", " ").strip()
#         )
#         event_short = (
#             (clean_msg[:20] + "..") if len(clean_msg) > 22 else clean_msg
#         )
#         yolo_str = "ON" if self.is_yolo_active else "OFF"
#         target_str = "Aim" if self.is_pressing else "None"
#         hud_line = f"\rHP: {hp:5.1f}% | Threat: {threat:2d} | YOLO: {yolo_str:<3} | Target: {target_str:<4} | {event_short:<18}\033[K"
# 
#         sys.stdout.write(hud_line)
#         sys.stdout.flush()
# ---------------------------

# Import các module đã có
from AutoPotionClass import AutoPotion
from DangerSystemClass import DangerSystem
from HotKeySetClass import HotKeySystem
from CombatRadarClass import CombatRadar
from VoiceAssistant import VoiceAssistant
from YOLOManagerClass import YOLOManager
from SkillCooldownClass import SkillCooldownManager


class SacredBot:
    def __init__(self):
        self.config = self.load_config()
        self.voice = VoiceAssistant()
        self.pm = None
        self.module_addr = None
        self.cooldown_hook = None  # [NEW 2026-08-29] Bộ Hook Memory Cooldown Skill

        # --- KHỞI TẠO BIẾN HỆ THỐNG (Tránh lỗi NoneType) ---
        self.ai_sys = None       # YOLO AI Module
        self.radar = None
        self.potion_sys = None
        self.danger_sys = None
        self.hotkey_sys = None
        
        # Flags điều khiển trạng thái
        self.game_connected = False
        self.is_running = False
        self.exit_event = threading.Event()
        self._data_lock = threading.Lock()   # Bảo vệ shared_data giữa các thread

        self.last_threat = 0
        self.last_exp = 0                    # [NEW 2026-08-29] Điểm kinh nghiệm mốc trước đó

        self.shared_data = {
            'hp_percent': 100.0,
            'threat_level': 0,
            'exp': 0,
            'monster_ids': set(),
            'hover_id': 0
        }        
        
        self.is_in_combat = False
        self.safe_start_time = 0.0      # Mốc thời gian bắt đầu đếm Safe (giây thực)
        self.last_speak_time = 0        
        self.is_pressing = False

        # Biến điều khiển YOLO Targeting & Unified Mouse
        self.is_yolo_active = False     # Flag bật/tắt luồng YOLO targeting
        self.target_detected = False    # Trạng thái phát hiện mục tiêu để hiển thị lên Live HUD & kích hoạt chuột
        self.target_locked_id = 0       # ID quái đang bị khóa mục tiêu (Memory + YOLO)
        self.is_left_down = False       # Trạng thái thực tế chuột trái (Unified Mouse Arbiter)
        self.is_right_down = False      # Trạng thái thực tế chuột phải (Phím X)

        self.sct = None                     # Lazy init trong luồng worker để tránh lỗi thread-local srcdc Windows
        self.buff_queue = self._init_buff_system()
        self.last_buff_finish_time = 0    # Mốc thời gian hoàn tất buff gần nhất
        self.last_buff_cast_delay = 0     # Cast delay của buff vừa xong (giây)
 
        self.last_event_msg = "Sẵn sàng (YOLO Mode)"  # Thông điệp sự kiện gần nhất cho Single-line HUD
        self.last_hud_print_time = 0.0    # Giới hạn tần suất in HUD tránh giật console


    def print_hud(self, hp, threat, monster_count=0, hover_id=0, exp=0):
        """[NEW 2026-08-29] In trạng thái trực tiếp trên 1 dòng duy nhất (Single-line Live HUD v2.5).
        Hiển thị chi tiết: HP | Threat | Mobs | Hover | EXP | YOLO Lock status | Event.
        """
        now = time.time()
        if now - self.last_hud_print_time < 0.2:
            return
        self.last_hud_print_time = now

        # 1. Triệt tiêu toàn bộ ký tự xuống dòng trong msg để không làm vỡ HUD
        clean_msg = (
            self.last_event_msg.replace("\r", "").replace("\n", " ").strip()
        )
        event_short = (
            (clean_msg[:16] + "..") if len(clean_msg) > 18 else clean_msg
        )

        yolo_str = "ON" if self.is_yolo_active else "OFF"
        target_str = f"LOCK:{self.target_locked_id}" if self.target_detected else ("Aim" if self.target_detected else "None")
        hud_line = (
            f"\rHP: {hp:5.1f}% | Thr: {threat:1d} | Mobs: {monster_count:2d} | "
            f"Hover: {hover_id:<6} | EXP: {exp:<8} | YOLO: {yolo_str:<3} | Target: {target_str:<10} | {event_short}\033[K"
        )

        sys.stdout.write(hud_line)
        sys.stdout.flush()

    def load_config(self):
        import json
        try:
            with open('sacred_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Không thể load config: {e}")
            return {}

    # --- OLD CODE (REPLACED: _init_buff_system & is_buff_ready cũ) ---
    # def _init_buff_system(self):
    #     """[NEW 2026-08-13] Khởi tạo hệ thống Auto Buff v2.0 từ config (Visual Sentinel + Priority Scheduler).
    #     Hỗ trợ 3 loại buff (CA/MA/CO) độc lập kèm điểm trinh sát Sentinel điểm ảnh.
    #     """
    #     buff_cfg = self.config.get('auto_buff_system', {})
    #     buffs = []
    #     for buff_data in buff_cfg.get('buffs', []):
    #         buffs.append({
    #             'id': buff_data.get('id', 'unknown'),
    #             'name': buff_data.get('name', 'Buff'),
    #             'enabled': buff_data.get('enabled', False),
    #             'interval': buff_data.get('interval', 30),
    #             'cast_delay': buff_data.get('cast_delay', 0.5),
    #             'sentinel_enabled': buff_data.get('sentinel_enabled', True),
    #             'sentinel_x': buff_data.get('sentinel_x', 0),
    #             'sentinel_y': buff_data.get('sentinel_y', 0),
    #             'tolerance_rgb': buff_data.get('tolerance_rgb', 1),
    #             'min_brightness': buff_data.get('min_brightness', 14),
    #             'max_brightness': buff_data.get('max_brightness', 177),
    #             'retry_timeout': buff_data.get('retry_timeout', 3.0),
    #             'sequence': buff_data.get('sequence', []),
    #             'last_cast_time': 0,
    #             'retry_start_time': 0
    #         })
    #     enabled = buff_cfg.get('enabled', False)
    #     print(f"[BUFF SYSTEM v2.0] {'BẬT' if enabled else 'TẮT'} — Loaded {len(buffs)} loại buff (Visual Sentinel Active).")
    #     return {
    #         'enabled': enabled,
    #         'buffs': buffs
    #     }
    # 
    # def is_buff_ready(self, buff):
    #     """[NEW 2026-08-13] Trinh sát màu Visual Sentinel cho Auto Buff.
    #     Nếu điểm ảnh rơi vào phổ Xám Đen (R=G=B) -> Skill đang Cooldown / Casting -> Trả về False (Chưa sẵn sàng).
    #     Nếu điểm ảnh thoát khỏi phổ Xám Đen -> Skill sáng màu -> Trả về True (Ready).
    #     """
    #     if not buff.get('sentinel_enabled', True):
    #         return True
    # 
    #     x = buff.get('sentinel_x', 0)
    #     y = buff.get('sentinel_y', 0)
    #     if x <= 0 or y <= 0:
    #         return True
    # 
    #     try:
    #         if self.sct is None:
    #             self.sct = mss.mss()        # Khởi tạo mss ngay trong luồng worker để tránh lỗi thread-local srcdc
    # 
    #         bbox = {'top': y, 'left': x, 'width': 1, 'height': 1}
    #         img = np.array(self.sct.grab(bbox))
    #         pixel = img[0, 0]
    #         b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
    # 
    #         tol = buff.get('tolerance_rgb', 1)
    #         min_b = buff.get('min_brightness', 14)
    #         max_b = buff.get('max_brightness', 177)
    # 
    #         is_equal_rgb = (abs(r - g) <= tol) and (abs(g - b) <= tol) and (abs(r - b) <= tol)
    #         avg_brightness = (r + g + b) / 3.0
    #         is_dark_range = min_b <= avg_brightness <= max_b
    #         is_casting = is_equal_rgb and is_dark_range
    # 
    #         return not is_casting
    #     except Exception as e:
    #         self.sct = None                 # Reset handle khi gặp lỗi để tự động khởi tạo lại
    #         print(f"[BUFF SENTINEL ERROR] Lỗi soi màu '{buff.get('name')}': {e}")
    #         return True
    # -----------------------------------------------------------------------------

    def _init_buff_system(self):
        """[NEW 2026-08-13] Khởi tạo hệ thống Auto Buff v2.0 từ config (Visual Sentinel + Priority Scheduler).
        [NEW 2026-08-29] Tái cấu trúc Hệ thống Buff Độc lập: Combo (Visual Sentinel) + Magic/CA (Memory Cooldown).
        Hỗ trợ Post-Cast Verification và Smart Fast-Retry riêng biệt cho từng buff.
        """
        buff_cfg = self.config.get('auto_buff_system', {})
        buffs = []
        for buff_data in buff_cfg.get('buffs', []):
            buff_id = buff_data.get('id', 'unknown')
            mode = buff_data.get('mode', 'visual' if 'co' in buff_id else 'memory')
            buffs.append({
                'id': buff_id,
                'name': buff_data.get('name', 'Buff'),
                'enabled': buff_data.get('enabled', False),
                'mode': mode,  # 'visual' (Combo) hoặc 'memory' (Magic/CA)
                'interval': buff_data.get('interval', 30),
                'cast_delay': buff_data.get('cast_delay', 0.5),
                'fast_retry_delay': buff_data.get('fast_retry_delay', 0.3),
                'max_retries': buff_data.get('max_retries', 3),
                'use_memory': buff_data.get('use_memory', (mode == 'memory')),
                'sentinel_enabled': buff_data.get('sentinel_enabled', (mode == 'visual')),
                'sentinel_x': buff_data.get('sentinel_x', 0),
                'sentinel_y': buff_data.get('sentinel_y', 0),
                'tolerance_rgb': buff_data.get('tolerance_rgb', 1),
                'min_brightness': buff_data.get('min_brightness', 14),
                'max_brightness': buff_data.get('max_brightness', 177),
                'retry_timeout': buff_data.get('retry_timeout', 3.0),
                'sequence': buff_data.get('sequence', []),
                'last_cast_time': 0.0,
                'retry_count': 0,
                'next_retry_time': 0.0
            })
        enabled = buff_cfg.get('enabled', False)
        print(f"[BUFF SYSTEM v2.0] {'BẬT' if enabled else 'TẮT'} — Loaded {len(buffs)} loại buff (Independent Scheduler Active).")
        return {
            'enabled': enabled,
            'buffs': buffs
        }

    def is_buff_ready(self, buff):
        """[NEW 2026-08-29] Kiểm tra trạng thái sẵn sàng của Buff theo từng chế độ độc lập.
        1. Chế độ Memory (Magic, CA): Đọc trực tiếp Cooldown từ Memory Hook (00562B13).
           - Cooldown <= 0.001 -> Skill sẵn sàng (Ready -> True).
           - Cooldown > 0.001 -> Skill đang cooldown/casting (Busy -> False).
        2. Chế độ Visual Sentinel (Combo): Soi màu RGB pixel icon.
           - Pixel sáng màu -> Sẵn sàng (Ready -> True).
           - Pixel xám tối -> Đang hiệu lực / Cooldown (False).
        """
        mode = buff.get('mode', 'memory' if buff.get('use_memory', False) else 'visual')

        # 1. KIỂM TRA BẰNG MEMORY COOLDOWN HOOK (Cho Magic & CA)
        if mode == 'memory' or buff.get('use_memory', False):
            if self.cooldown_hook and self.cooldown_hook.is_hooked:
                cd_val = self.cooldown_hook.get_cooldown()
                if cd_val is not None:
                    if cd_val > 0.001:
                        return False  # Đang hồi chiêu / đang cast
                    return True       # Sẵn sàng 100%
            # Fallback nếu hook chưa sẵn sàng
            if not buff.get('sentinel_enabled', False):
                return True

        # 2. KIỂM TRA BẰNG VISUAL SENTINEL (Cho Combo hoặc Fallback)
        if not buff.get('sentinel_enabled', True):
            return True

        x = buff.get('sentinel_x', 0)
        y = buff.get('sentinel_y', 0)
        if x <= 0 or y <= 0:
            return True

        try:
            if self.sct is None:
                self.sct = mss.mss()        # Khởi tạo mss ngay trong luồng worker để tránh lỗi thread-local srcdc

            bbox = {'top': y, 'left': x, 'width': 1, 'height': 1}
            img = np.array(self.sct.grab(bbox))
            pixel = img[0, 0]
            b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])

            tol = buff.get('tolerance_rgb', 1)
            min_b = buff.get('min_brightness', 14)
            max_b = buff.get('max_brightness', 177)

            is_equal_rgb = (abs(r - g) <= tol) and (abs(g - b) <= tol) and (abs(r - b) <= tol)
            avg_brightness = (r + g + b) / 3.0
            is_dark_range = min_b <= avg_brightness <= max_b
            is_casting = is_equal_rgb and is_dark_range

            return not is_casting
        except Exception as e:
            self.sct = None                 # Reset handle khi gặp lỗi để tự động khởi tạo lại
            print(f"[BUFF SENTINEL ERROR] Lỗi soi màu '{buff.get('name')}': {e}")
            return True

    # --- OLD CODE (REPLACED: connect_game cũ) ---
    # def connect_game(self):
    #     """Kết nối game và khởi tạo tất cả các module."""
    #     try:
    #         p_name = "sacred.exe"
    #         self.pm = pymem.Pymem(p_name)
    #         self.module_addr = pymem.process.module_from_name(self.pm.process_handle, p_name).lpBaseOfDll
    #         
    #         # 1. Khởi tạo Memory Modules
    #         self.potion_sys = AutoPotion(self.pm, self.module_addr)
    #         self.danger_sys = DangerSystem(self.pm, self.module_addr)
    #         
    #         # 2. Khởi tạo Logic Modules
    #         self.hotkey_sys = HotKeySystem(self.config.get('hotkey_system'))
    #         self.radar = CombatRadar(self.config)
    #         
    #         # 3. Khởi tạo AI Module (YOLO)
    #         if self.config.get('ai_system'):
    #             self.ai_sys = YOLOManager(self.config)
    # 
    #         print(f"\n[SUCCESS] Đã kết nối Sacred.exe (Base: {hex(self.module_addr)})")
    #         self.voice.speak('Hệ thống đã sẵn sàng. Chiến thôi đại ca!')
    #         return True
    #     except pymem.exception.ProcessNotFound:
    #         print("\n[CONNECT ERROR] KHÔNG tìm thấy game Sacred.exe. Vui lòng mở game trước khi chạy Bot!")
    #         return False
    #     except pymem.exception.CouldNotOpenProcess:
    #         print("\n[CONNECT ERROR] KHÔNG THỂ kết nối vào game! Hãy chạy Command Prompt / VS Code / file .bat này bằng quyền Administrator (Run as administrator).")
    #         return False
    #     except Exception as e:
    #         print(f"[CONNECT ERROR]: {e}")
    #         return False
    # ---------------------------------------------

    def connect_game(self):
        """Kết nối game và khởi tạo tất cả các module."""
        try:
            p_name = "sacred.exe"
            self.pm = pymem.Pymem(p_name)
            self.module_addr = pymem.process.module_from_name(self.pm.process_handle, p_name).lpBaseOfDll
            
            # 1. Khởi tạo Memory Modules
            self.potion_sys = AutoPotion(self.pm, self.module_addr)
            self.danger_sys = DangerSystem(self.pm, self.module_addr)

            # [NEW 2026-08-29] Khởi tạo & Cài đặt Tự động Cooldown Memory Hook
            self.cooldown_hook = SkillCooldownManager(self.pm, self.module_addr)
            self.cooldown_hook.install()
            
            # 2. Khởi tạo Logic Modules
            self.hotkey_sys = HotKeySystem(self.config.get('hotkey_system'))
            self.radar = CombatRadar(self.config)
            
            # 3. Khởi tạo AI Module (YOLO)
            if self.config.get('ai_system'):
                self.ai_sys = YOLOManager(self.config)

            # [NEW 2026-08-29] Lấy EXP ban đầu của nhân vật
            initial_exp = self.potion_sys.get_exp()
            if initial_exp is not None:
                self.last_exp = initial_exp

            print(f"\n[SUCCESS] Đã kết nối Sacred.exe (Base: {hex(self.module_addr)})")
            print(f"[INIT] EXP ban đầu: {self.last_exp}")
            self.voice.speak('Hệ thống YOLO AI Vision đã sẵn sàng.')
            return True
        except pymem.exception.ProcessNotFound:
            print("\n[CONNECT ERROR] KHÔNG tìm thấy game Sacred.exe. Vui lòng mở game trước khi chạy Bot!")
            return False
        except pymem.exception.CouldNotOpenProcess:
            print("\n[CONNECT ERROR] KHÔNG THỂ kết nối vào game! Hãy chạy Command Prompt / VS Code / file .bat này bằng quyền Administrator (Run as administrator).")
            return False
        except Exception as e:
            print(f"[CONNECT ERROR]: {e}")
            return False

    # --- OLD CODE (REPLACED: sensor_worker cũ) ---
    # def sensor_worker(self):
    #     """Luồng quét Memory (100ms)"""
    #     while not self.exit_event.is_set():
    #         if self.game_connected and self.is_running:
    #             try:
    #                 hp = self.potion_sys.get_hp_percent()
    #                 threat = self.danger_sys.get_threat_level()
    #                 
    #                 with self._data_lock:
    #                     self.shared_data['hp_percent'] = hp if hp is not None else 100.0
    #                     self.shared_data['threat_level'] = threat
    #             except Exception as e:
    #                 print(f"[SENSOR ERROR] Mất kết nối game: {e}")
    #                 self.game_connected = False
    #         time.sleep(0.1)
    # ---------------------------------------------

    def sensor_worker(self):
        """[NEW 2026-08-29] Luồng quét Memory: HP, Threat, EXP, Danh sách quái & Hover ID (50ms)."""
        while not self.exit_event.is_set():
            if self.game_connected and self.is_running:
                try:
                    hp = self.potion_sys.get_hp_percent()
                    threat = self.danger_sys.get_threat_level()
                    exp = self.potion_sys.get_exp()
                    monster_ids = self.danger_sys.get_monster_ids(max_monsters=15)
                    hover_id = self.danger_sys.get_mouse_hover_id()
                    
                    with self._data_lock:
                        self.shared_data['hp_percent'] = hp if hp is not None else 100.0
                        self.shared_data['threat_level'] = threat
                        self.shared_data['exp'] = exp if exp is not None else 0
                        self.shared_data['monster_ids'] = monster_ids
                        self.shared_data['hover_id'] = hover_id
                except Exception as e:
                    print(f"[SENSOR ERROR] Mất kết nối game: {e}")
                    self.game_connected = False
            time.sleep(0.05)

    # --- OLD CODE (REPLACED: action_worker cũ) ---
    # def action_worker(self):
    #     """Luồng thực thi: Tối ưu hoá Hybrid AI + Radar"""
    #     last_potion_time = 0
    #     
    #     while not self.exit_event.is_set():
    #         # KIỂM TRA AN TOÀN TRƯỚC KHI CHẠY (Tránh lỗi NoneType)
    #         if not (self.game_connected and self.is_running and self.radar):
    #             # Nếu Bot đang bật mà chưa nạp xong Radar thì tạm dừng
    #             time.sleep(0.1)
    #             continue
    # 
    #         # 1. LẤY DỮ LIỆU (thread-safe)
    #         with self._data_lock:
    #             hp     = self.shared_data['hp_percent']
    #             threat = self.shared_data['threat_level']
    #         threshold    = self.config['potion_system']['threshold_percent']
    #         current_time = time.time()
    # 
    #         if threat > 0:
    #             self.safe_start_time = 0.0  # Reset đồng hồ Safe khi có quái
    # 
    #             # 1. THÔNG BÁO GIỌNG NÓI (Chỉ nói 1 lần duy nhất khi vừa chớm gặp bãi quái)
    #             if not self.is_in_combat:
    #                 self.is_in_combat = True
    #                 self.voice.speak("Có quái.")
    # 
    #             # [NEW 2026-08-13] AUTO BUFF SYSTEM v2.0 (Visual Sentinel + Priority Scheduler)
    #             if self.buff_queue['enabled']:
    #                 # Đảm bảo cast_delay sau buff gần nhất đã trôi qua trước khi cast buff tiếp
    #                 if current_time - self.last_buff_finish_time >= self.last_buff_cast_delay:
    #                     # 1. Lọc tất cả các buff đã chạm mốc interval
    #                     due_buffs = [
    #                         b for b in self.buff_queue['buffs']
    #                         if b['enabled'] and (current_time - b['last_cast_time'] >= b['interval'])
    #                     ]
    # 
    #                     if due_buffs:
    #                         cast_executed = False
    # 
    #                         # 2. Thử trinh sát màu Visual Sentinel từng buff đến hạn (Chuyển mạch ưu tiên)
    #                         for target_buff in due_buffs:
    #                             if self.is_buff_ready(target_buff):
    #                                 self.last_event_msg = f"Buff: {target_buff['name']}"
    #                                 self.voice.speak(target_buff['name'])
    #                                 self.hotkey_sys.execute_sequence(target_buff['sequence'])
    #                                 target_buff['last_cast_time'] = current_time
    #                                 target_buff['retry_start_time'] = 0  # Reset mốc retry khi đã buff thành công
    #                                 self.last_buff_finish_time = time.time()
    #                                 self.last_buff_cast_delay = target_buff['cast_delay']
    #                                 cast_executed = True
    #                                 break  # Chỉ cast 1 buff thành công duy nhất trong mỗi lượt
    # 
    #                         # 3. NẾU TẤT CẢ BUFF ĐẾN HẠN ĐỀU CHƯA READY (Đang dính CD / Tối màu)
    #                         if not cast_executed:
    #                             primary_buff = due_buffs[0]
    #                             if primary_buff['retry_start_time'] == 0:
    #                                 primary_buff['retry_start_time'] = current_time
    #                                 elif current_time - primary_buff['retry_start_time'] > primary_buff.get('retry_timeout', 3.0):
    #                                 # Hết thời gian gác 2-3s mà chiêu vẫn chưa hồi -> Reset mốc retry để giải phóng vòng lặp
    #                                 primary_buff['retry_start_time'] = 0
    # 
    #         else:
    #             # 3. XỬ LÝ KHI QUÉT SẠCH QUÁI (Safe Timer dùng giây thực)
    #             if self.is_in_combat:
    #                 if self.safe_start_time == 0.0:
    #                     self.safe_start_time = current_time
    #                 elif current_time - self.safe_start_time > 3.0:
    #                     self.voice.speak('Clear.')
    #                     self.is_in_combat = False
    #                     self.safe_start_time = 0.0
    #                     self.last_event_msg = "Clear"
    #                     # LƯU Ý: Tuyệt đối KHÔNG reset self.last_buff_time ở đây
    #                     # để thời gian hồi chiêu buff tiếp tục được đếm chuẩn xác xuyên suốt các bãi quái.
    #             
    #             
    #         # --- LOGIC HỖ TRỢ ---
    #         # Bơm máu
    #         if hp < threshold and (current_time - last_potion_time > 0.8):
    #             pydirectinput.press(self.config['potion_system']['key'])
    #             last_potion_time = current_time
    #             self.last_event_msg = "Bom mau"
    #             if current_time - self.last_speak_time > 3.0:
    #                 self.voice.speak('Bơm máu!')
    #                 self.last_speak_time = current_time
    # 
    #         # Chạy Hotkey với callback HUD (văn bản thuần không emoji)
    #         self.hotkey_sys.run_check(on_trigger=lambda name: setattr(self, 'last_event_msg', f"Combo: {name}"))
    # 
    #         # In HUD trực tiếp trên 1 dòng
    #         self.print_hud(hp, threat)
    # 
    #         time.sleep(0.02)
    # ---------------------------------------------

    def action_worker(self):
        """Luồng thực thi: Tối ưu hoá Auto Buff, Bơm máu, Giám sát EXP & Live HUD."""
        last_potion_time = 0
        
        while not self.exit_event.is_set():
            if not (self.game_connected and self.is_running):
                time.sleep(0.1)
                continue

            # 1. LẤY DỮ LIỆU (thread-safe)
            with self._data_lock:
                hp = self.shared_data['hp_percent']
                threat = self.shared_data['threat_level']
                exp = self.shared_data['exp']
                monster_ids = self.shared_data['monster_ids']
                hover_id = self.shared_data['hover_id']

            threshold = self.config['potion_system']['threshold_percent']
            current_time = time.time()

            # [NEW 2026-08-29] THEO DÕI BIẾN ĐỘNG EXP (Quái chết)
            if self.last_exp > 0 and exp > self.last_exp:
                exp_gained = exp - self.last_exp
                self.last_exp = exp
                self.last_event_msg = f"+{exp_gained} EXP!"
                # Khi EXP tăng -> Quái mục tiêu đã chết -> Nhả lock để tìm mục tiêu mới
                if self.target_detected:
                    self.target_detected = False
                    self.target_locked_id = 0
                    if self.ai_sys:
                        self.ai_sys.reset_lock()
            elif self.last_exp == 0 and exp > 0:
                self.last_exp = exp

            if threat > 0:
                self.safe_start_time = 0.0  # Reset đồng hồ Safe khi có quái

                # 1. THÔNG BÁO GIỌNG NÓI (Chỉ nói 1 lần duy nhất khi vừa chớm gặp bãi quái)
                if not self.is_in_combat:
                    self.is_in_combat = True
                    self.voice.speak("Có quái.")

                # [NEW 2026-08-29] HỆ THỐNG BUFF ĐỘC LẬP (Decoupled Scheduler + Post-Cast Verification + Smart Fast-Retry)
                if self.buff_queue['enabled']:
                    # 1. Kiểm tra Kênh Thi Triển Không Nghẽn (Cast Channel Free)
                    if current_time - self.last_buff_finish_time >= self.last_buff_cast_delay:
                        target_buff = None

                        # Ưu tiên 1: Các buff đang trong trạng thái Fast-Retry cần thử lại ngay khi đến hạn
                        for b in self.buff_queue['buffs']:
                            if b['enabled'] and b['retry_count'] > 0:
                                if current_time >= b['next_retry_time'] and self.is_buff_ready(b):
                                    target_buff = b
                                    break

                        # Ưu tiên 2: Các buff đến hạn bình thường (Combo theo visual, Magic/CA theo interval + memory)
                        if not target_buff:
                            for b in self.buff_queue['buffs']:
                                if b['enabled'] and b['retry_count'] == 0:
                                    if (current_time - b['last_cast_time'] >= b['interval']) and self.is_buff_ready(b):
                                        target_buff = b
                                        break

                        # Thực hiện thi triển và xác thực khi tìm thấy buff đủ điều kiện
                        if target_buff:
                            buff_name = target_buff['name']
                            is_retry = target_buff['retry_count'] > 0
                            self.last_event_msg = f"Buff: {buff_name}" + (f" (Retry #{target_buff['retry_count']})" if is_retry else "")
                            if not is_retry:
                                self.voice.speak(buff_name)

                            # A. Gửi chuỗi phím thi triển (Hotkey Sequence)
                            self.hotkey_sys.execute_sequence(target_buff['sequence'])
                            time.sleep(0.15)  # Nghỉ ngắn để game xử lý animation & cập nhật trạng thái

                            # B. XÁC THỰC HOÀN TẤT THI TRIỂN (Post-Cast Verification)
                            mode = target_buff.get('mode', 'memory' if target_buff.get('use_memory') else 'visual')
                            cast_success = False

                            if mode == 'memory' and self.cooldown_hook and self.cooldown_hook.is_hooked:
                                # Magic/CA: Cooldown trong memory phải chuyển sang > 0
                                cd_after = self.cooldown_hook.get_cooldown()
                                cast_success = (cd_after is not None and cd_after > 0.001)
                            else:
                                # Combo: Pixel Sentinel chuyển sang dải tối/xám (đang cooldown/casting)
                                cast_success = not self.is_buff_ready(target_buff)

                            # C. PHÂN NHÁNH XỬ LÝ KẾT QUẢ (Success / Fast-Retry)
                            now_time = time.time()
                            if cast_success:
                                # Thi triển thành công 100% -> Reset retry và cập nhật chu kỳ mới
                                target_buff['last_cast_time'] = now_time
                                target_buff['retry_count'] = 0
                                target_buff['next_retry_time'] = 0.0
                                self.last_event_msg = f"Buff {buff_name}: OK"
                            else:
                                # Bị miss / hụt phím -> Kích hoạt Fast-Retry
                                target_buff['retry_count'] += 1
                                max_retries = target_buff.get('max_retries', 3)
                                if target_buff['retry_count'] <= max_retries:
                                    retry_delay = target_buff.get('fast_retry_delay', 0.3)
                                    target_buff['next_retry_time'] = now_time + retry_delay
                                    self.last_event_msg = f"Buff {buff_name}: Retry #{target_buff['retry_count']}"
                                else:
                                    # Quá số lần retry cho phép -> Hủy lượt retry, chuyển sang chu kỳ tiếp theo
                                    target_buff['last_cast_time'] = now_time
                                    target_buff['retry_count'] = 0
                                    target_buff['next_retry_time'] = 0.0
                                    self.last_event_msg = f"Buff {buff_name}: Missed"

                            self.last_buff_finish_time = time.time()
                            self.last_buff_cast_delay = target_buff['cast_delay']

            else:
                # 3. XỬ LÝ KHI QUÉT SẠCH QUÁI (Safe Timer dùng giây thực)
                if self.is_in_combat:
                    if self.safe_start_time == 0.0:
                        self.safe_start_time = current_time
                    elif current_time - self.safe_start_time > 3.0:
                        self.voice.speak('Clear.')
                        self.is_in_combat = False
                        self.safe_start_time = 0.0
                        self.last_event_msg = "Clear"
                        self.target_detected = False
                        self.target_locked_id = 0
                        if self.ai_sys:
                            self.ai_sys.reset_lock()
                
            # --- LOGIC HỖ TRỢ ---
            # Bơm máu
            if hp < threshold and (current_time - last_potion_time > 0.8):
                pydirectinput.press(self.config['potion_system']['key'])
                last_potion_time = current_time
                self.last_event_msg = "Bom mau"
                if current_time - self.last_speak_time > 3.0:
                    self.voice.speak('Bơm máu!')
                    self.last_speak_time = current_time

            # Chạy Hotkey với callback HUD (văn bản thuần không emoji)
            self.hotkey_sys.run_check(on_trigger=lambda name: setattr(self, 'last_event_msg', f"Combo: {name}"))

            # In HUD trực tiếp trên 1 dòng với đầy đủ thông tin Memory & YOLO
            self.print_hud(hp, threat, len(monster_ids), hover_id, exp)

            time.sleep(0.02)

    # --- OLD CODE (REPLACED: yolo_worker & run cũ) ---
    # def yolo_worker(self):
    #     """Luồng YOLO targeting độc lập: Z bật / X tắt.
    #     Toàn quyền kiểm soát mouseDown/Up — không phụ thuộc action_worker.
    #     """
    #     while not self.exit_event.is_set():
    # 
    #         # --- TOGGLE Z / X ---
    #         if keyboard.is_pressed('z') and not self.is_yolo_active:
    #             self.is_yolo_active = True
    #             winsound.Beep(1000, 150)
    #             self.last_event_msg = "YOLO Bật"
    #             time.sleep(0.3)  # debounce
    # 
    #         if keyboard.is_pressed('x') and self.is_yolo_active:
    #             self.is_yolo_active = False
    #             if self.ai_sys:
    #                 self.ai_sys.reset_lock()
    #             if self.is_pressing:
    #                 pydirectinput.mouseUp(button='left')
    #                 self.is_pressing = False
    #             winsound.Beep(500, 150)
    #             self.last_event_msg = "YOLO Tắt"
    #             time.sleep(0.3)  # debounce
    # 
    #         # --- GUARD: Dừng nếu chưa sẵn sàng hoặc bị tạm dừng ---
    #         if not (self.game_connected and self.is_running
    #                 and self.is_yolo_active
    #                 and self.ai_sys and self.radar):
    #             if self.ai_sys and self.ai_sys.locked_target:
    #                 self.ai_sys.reset_lock()
    #             if self.is_pressing:        # Nhả chuột nếu bị gián đoạn giữa chừng
    #                 pydirectinput.mouseUp(button='left')
    #                 self.is_pressing = False
    #             time.sleep(0.05)
    #             continue
    # 
    #         try:
    #             target_pos = self.ai_sys.get_best_target(debug=True)
    # 
    #             if target_pos:
    #                 tx, ty = target_pos
    #                 pydirectinput.moveTo(tx, ty, _pause=False)
    # 
    #                 if self.radar.is_target_detected():     # Thanh HP xác nhận → BEM & KHÓA MỤC TIÊU
    #                     self.ai_sys.confirm_lock(target_pos) # Kích hoạt trạng thái TRACKING trong YOLO
    #                     if not self.is_pressing:
    #                         pydirectinput.mouseDown(button='left')
    #                         self.is_pressing = True
    #                 else:                                   # Radar fail (quái chết/mất máu) → Hủy khóa & nhả tay
    #                     self.ai_sys.reset_lock()
    #                     if self.is_pressing:
    #                         pydirectinput.mouseUp(button='left')
    #                         self.is_pressing = False
    #             else:                                       # Mất target → Hủy khóa & nhả tay
    #                 self.ai_sys.reset_lock()
    #                 if self.is_pressing:
    #                     pydirectinput.mouseUp(button='left')
    #                     self.is_pressing = False
    # 
    #         except Exception as e:
    #             print(f"\n[YOLO ERROR] {e}")
    #             if self.ai_sys:
    #                 self.ai_sys.reset_lock()
    #             if self.is_pressing:
    #                 pydirectinput.mouseUp(button='left')
    #                 self.is_pressing = False
    # 
    #         time.sleep(0.02)
    # 
    #     # --- EXIT CLEANUP: Đảm bảo nhả chuột khi app thoát ---
    #     if self.is_pressing:
    #         pydirectinput.mouseUp(button='left')
    #         self.is_pressing = False
    # 
    # def run(self):
    #     threads = [
    #         threading.Thread(target=self.sensor_worker, daemon=True),
    #         threading.Thread(target=self.action_worker, daemon=True),
    #         threading.Thread(target=self.yolo_worker,   daemon=True),
    #     ]
    #     for t in threads: t.start()
    # 
    #     print("=== SACRED GOD BOT ACTIVE ===")
    #     while not self.exit_event.is_set():
    #         if not self.game_connected:
    #             self.is_running = False
    #             self.game_connected = self.connect_game()
    #             if not self.game_connected:
    #                 time.sleep(2)
    #                 continue
    # 
    #         toggle_key = self.config.get('global', {}).get('toggle_key', 'n')
    #         if keyboard.is_pressed(toggle_key):
    #             self.is_running = not self.is_running
    #             winsound.Beep(1000 if self.is_running else 500, 200)
    #             if self.is_running:
    #                 # [NEW 2026-08-11] Reset tất cả buff timers khi bật lại
    #                 for buff in self.buff_queue['buffs']:
    #                     buff['last_cast_time'] = 0
    #                     buff['retry_start_time'] = 0
    #                 self.last_buff_finish_time = 0
    #                 self.last_buff_cast_delay = 0
    #             
    #             status_msg = 'Bot đã bật.' if self.is_running else 'Bot nghỉ ngơi.'
    #             self.voice.speak(status_msg)
    #             time.sleep(0.4)
    # 
    #         if keyboard.is_pressed('esc'):
    #             self.exit_event.set()
    #         time.sleep(0.1)
    # ----------------------------------------------------

    # --- OLD CODE (REPLACED: yolo_worker & mouse_arbiter_worker cũ) ---
    # def yolo_worker(self):
    #     """[NEW 2026-08-29] Luồng YOLO Targeting AI kết hợp Memory & CombatRadar Đa Tầng.
    #     1. Quét bbox quái bằng YOLOv8 AI.
    #     2. Di chuột đến tọa độ tối ưu.
    #     3. Xác thực bằng Hover ID (Memory) hoặc Thanh máu (CombatRadar).
    #     4. Gửi cờ target_detected cho Unified Mouse Arbiter thực thi chuột mượt mà.
    #     """
    #     while not self.exit_event.is_set():
    #         # --- GUARD: Dừng nếu chưa sẵn sàng hoặc bot tắt ---
    #         if not (self.game_connected and self.is_running and self.is_yolo_active and self.ai_sys):
    #             if self.ai_sys and self.ai_sys.locked_target:
    #                 self.ai_sys.reset_lock()
    #             self.target_detected = False
    #             self.target_locked_id = 0
    #             time.sleep(0.05)
    #             continue
    # 
    #         try:
    #             # 1. ĐỌC DỮ LIỆU BỘ NHỚ
    #             with self._data_lock:
    #                 hover_id = self.shared_data.get('hover_id', 0)
    #                 monster_ids = self.shared_data.get('monster_ids', set())
    # 
    #             # 2. YOLO AI PHÁT HIỆN MỤC TIÊU
    #             target_pos = self.ai_sys.get_best_target(debug=False)
    # 
    #             if target_pos:
    #                 tx, ty = target_pos
    #                 pydirectinput.moveTo(tx, ty, _pause=False)
    # 
    #                 # 3. XÁC NHẬN MỤC TIÊU ĐA TẦNG (Memory Hover ID HOẶC Radar HP Bar)
    #                 is_memory_confirmed = (hover_id > 1 and (hover_id in monster_ids or len(monster_ids) == 0))
    #                 is_radar_confirmed = self.radar.is_target_detected() if self.radar else False
    # 
    #                 if is_memory_confirmed or is_radar_confirmed:
    #                     # Khóa mục tiêu thành công
    #                     self.ai_sys.confirm_lock(target_pos)
    #                     self.target_detected = True
    #                     if is_memory_confirmed:
    #                         self.target_locked_id = hover_id
    #                     self.last_event_msg = f"YOLO Aim: {self.target_locked_id if self.target_locked_id > 0 else 'Locked'}"
    #                 else:
    #                     # Mất dấu quái tại điểm hover
    #                     self.ai_sys.reset_lock()
    #                     self.target_detected = False
    #                     self.target_locked_id = 0
    #             else:
    #                 # Không thấy bbox nào phù hợp
    #                 self.ai_sys.reset_lock()
    #                 self.target_detected = False
    #                 self.target_locked_id = 0
    # 
    #         except Exception as e:
    #             if self.ai_sys:
    #                 self.ai_sys.reset_lock()
    #             self.target_detected = False
    #             self.target_locked_id = 0
    # 
    #         time.sleep(0.02)
    # 
    #     # Exit cleanup
    #     self.target_detected = False
    #     self.target_locked_id = 0
    # 
    # def mouse_arbiter_worker(self):
    #     """[NEW 2026-08-29] Bộ Trọng tài chuột thống nhất (Unified Mouse Arbiter cho YOLO Bot).
    #     - Logic Chuột Trái (OR Condition):
    #         Đè Chuột Trái = (YOLO phát hiện & khóa quái [self.target_detected]) OR (Người chơi đè phím Z)
    #         -> Khi đè Z chạy map: Giữ chuột liên tục.
    #         -> Khi YOLO tìm thấy quái: Tự động giữ chuột tấn công.
    #         -> Khi quái chết (EXP tăng / mất dấu): Tự động nhả chuột chuyển target.
    #     - Logic Chuột Phải:
    #         Đè Chuột Phải = (Người chơi đè phím X)
    #     """
    #     while not self.exit_event.is_set():
    #         if not (self.game_connected and self.is_running):
    #             if self.is_left_down:
    #                 pydirectinput.mouseUp(button='left')
    #                 self.is_left_down = False
    #             if self.is_right_down:
    #                 pydirectinput.mouseUp(button='right')
    #                 self.is_right_down = False
    #             time.sleep(0.05)
    #             continue
    # 
    #         # 1. KIỂM TRA PHÍM THỦ CÔNG
    #         z_down = keyboard.is_pressed('z')
    #         x_down = keyboard.is_pressed('x')
    # 
    #         # 2. ĐIỀU PHỐI CHUỘT TRÁI (UNIFIED LOGIC: YOLO TARGET OR PHÍM Z)
    #         should_left_down = self.target_detected or z_down
    # 
    #         if should_left_down and not self.is_left_down:
    #             pydirectinput.mouseDown(button='left')
    #             self.is_left_down = True
    #         elif not should_left_down and self.is_left_down:
    #             pydirectinput.mouseUp(button='left')
    #             self.is_left_down = False
    # 
    #         # 3. ĐIỀU PHỐI CHUỘT PHẢI (PHÍM X)
    #         if x_down and not self.is_right_down:
    #             pydirectinput.mouseDown(button='right')
    #             self.is_right_down = True
    #         elif not x_down and self.is_right_down:
    #             pydirectinput.mouseUp(button='right')
    #             self.is_right_down = False
    # 
    #         time.sleep(0.01)  # Quét 100 FPS (10ms)
    # 
    #     # Cleanup khi luồng thoát
    #     if self.is_left_down:
    #         pydirectinput.mouseUp(button='left')
    #         self.is_left_down = False
    #     if self.is_right_down:
    #         pydirectinput.mouseUp(button='right')
    #         self.is_right_down = False
    # ---------------------------------------------------------------------------------

    # --- OLD CODE (REPLACED: yolo_worker cũ spam moveTo liên tục) ---
    # def yolo_worker(self):
    #     """[NEW 2026-08-29] Luồng YOLO Targeting AI độc lập: Z bật / X tắt (Không phụ thuộc Threat).
    #     1. Phím Z: Bật trạng thái đánh bằng YOLO (Beep 1000Hz).
    #     2. Phím X: Tắt trạng thái đánh bằng YOLO (Beep 500Hz, nhả chuột ngay).
    #     3. Hiển thị màn hình OpenCV Debug trực quan (debug=True).
    #     4. Di chuột tới quái $\rightarrow$ Xác nhận Đa Tầng $\rightarrow$ Set cờ target_detected cho Mouse Arbiter.
    #     """
    #     while not self.exit_event.is_set():
    #         # --- 1. TOGGLE PHÍM Z BẬT / PHÍM X TẮT YOLO TARGETING ---
    #         if keyboard.is_pressed('z') and not self.is_yolo_active:
    #             self.is_yolo_active = True
    #             winsound.Beep(1000, 150)
    #             self.last_event_msg = "YOLO Bật"
    #             time.sleep(0.3)  # debounce
    # 
    #         if keyboard.is_pressed('x') and self.is_yolo_active:
    #             self.is_yolo_active = False
    #             if self.ai_sys:
    #                 self.ai_sys.reset_lock()
    #             self.target_detected = False
    #             self.target_locked_id = 0
    #             if self.is_left_down:
    #                 pydirectinput.mouseUp(button='left')
    #                 self.is_left_down = False
    #             winsound.Beep(500, 150)
    #             self.last_event_msg = "YOLO Tắt"
    #             time.sleep(0.3)  # debounce
    # 
    #         # --- GUARD: Dừng nếu bot tắt hoặc chưa bật Z hoặc AI chưa sẵn sàng ---
    #         if not (self.game_connected and self.is_running and self.is_yolo_active and self.ai_sys):
    #             if self.ai_sys and self.ai_sys.locked_target:
    #                 self.ai_sys.reset_lock()
    #             self.target_detected = False
    #             self.target_locked_id = 0
    #             time.sleep(0.05)
    #             continue
    # 
    #         try:
    #             # 2. ĐỌC DỮ LIỆU BỘ NHỚ (Thread-safe)
    #             with self._data_lock:
    #                 hover_id = self.shared_data.get('hover_id', 0)
    #                 monster_ids = self.shared_data.get('monster_ids', set())
    # 
    #             # 3. YOLO AI PHÁT HIỆN MỤC TIÊU (Bật màn hình Debug trực quan)
    #             target_pos = self.ai_sys.get_best_target(debug=True)
    # 
    #             if target_pos:
    #                 tx, ty = target_pos
    #                 pydirectinput.moveTo(tx, ty, _pause=False)
    # 
    #                 # 4. XÁC NHẬN MỤC TIÊU ĐA TẦNG (Memory Hover ID HOẶC Radar HP Bar)
    #                 is_memory_confirmed = (hover_id > 1 and (hover_id in monster_ids or len(monster_ids) == 0))
    #                 is_radar_confirmed = self.radar.is_target_detected() if self.radar else False
    # 
    #                 if is_memory_confirmed or is_radar_confirmed:
    #                     # Khóa mục tiêu thành công
    #                     self.ai_sys.confirm_lock(target_pos)
    #                     self.target_detected = True
    #                     if is_memory_confirmed:
    #                         self.target_locked_id = hover_id
    #                     self.last_event_msg = f"YOLO Aim: {self.target_locked_id if self.target_locked_id > 0 else 'Locked'}"
    #                 else:
    #                     # Mất dấu quái tại điểm hover
    #                     self.ai_sys.reset_lock()
    #                     self.target_detected = False
    #                     self.target_locked_id = 0
    #             else:
    #                 # Không thấy bbox nào phù hợp
    #                 self.ai_sys.reset_lock()
    #                 self.target_detected = False
    #                 self.target_locked_id = 0
    # 
    #         except Exception as e:
    #             if self.ai_sys:
    #                 self.ai_sys.reset_lock()
    #             self.target_detected = False
    #             self.target_locked_id = 0
    # 
    #         time.sleep(0.02)
    # 
    #     # Exit cleanup
    #     self.target_detected = False
    #     self.target_locked_id = 0
    # ---------------------------------------------------------------------------------

    # --- OLD CODE (REPLACED: Xác nhận nới lỏng cũ gây nhận nhầm NPC) ---
    # def yolo_worker(self):
    #     """[NEW 2026-08-29] Luồng YOLO Targeting AI: Z bật / X tắt, Màn hình Debug & Smart Blacklist.
    #     - Khắc phục lỗi chiếm chuột: Nếu di chuột tới vị trí mà sau 2 frame không có Hover ID / HP bar
    #       $\rightarrow$ Đưa ngay vào Danh sách đen tạm thời (2.5s) để trả chuột tự do và tìm quái khác.
    #     """
    #     unconfirmed_pos = None
    #     unconfirmed_count = 0
    # 
    #     while not self.exit_event.is_set():
    #         # --- 1. TOGGLE PHÍM Z BẬT / PHÍM X TẮT YOLO TARGETING ---
    #         if keyboard.is_pressed('z') and not self.is_yolo_active:
    #             self.is_yolo_active = True
    #             winsound.Beep(1000, 150)
    #             self.last_event_msg = "YOLO Bật"
    #             time.sleep(0.3)  # debounce
    # 
    #         if keyboard.is_pressed('x') and self.is_yolo_active:
    #             self.is_yolo_active = False
    #             if self.ai_sys:
    #                 self.ai_sys.reset_lock()
    #             self.target_detected = False
    #             self.target_locked_id = 0
    #             unconfirmed_pos = None
    #             unconfirmed_count = 0
    #             if self.is_left_down:
    #                 pydirectinput.mouseUp(button='left')
    #                 self.is_left_down = False
    #             winsound.Beep(500, 150)
    #             self.last_event_msg = "YOLO Tắt"
    #             time.sleep(0.3)  # debounce
    # 
    #         # --- GUARD: Dừng nếu bot tắt hoặc chưa bật Z hoặc AI chưa sẵn sàng ---
    #         if not (self.game_connected and self.is_running and self.is_yolo_active and self.ai_sys):
    #             if self.ai_sys and self.ai_sys.locked_target:
    #                 self.ai_sys.reset_lock()
    #             self.target_detected = False
    #             self.target_locked_id = 0
    #             unconfirmed_pos = None
    #             unconfirmed_count = 0
    #             time.sleep(0.05)
    #             continue
    # 
    #         try:
    #             # 2. ĐỌC DỮ LIỆU BỘ NHỚ (Thread-safe)
    #             with self._data_lock:
    #                 hover_id = self.shared_data.get('hover_id', 0)
    #                 monster_ids = self.shared_data.get('monster_ids', set())
    # 
    #             # 3. YOLO AI PHÁT HIỆN MỤC TIÊU (Bật màn hình Debug trực quan)
    #             target_pos = self.ai_sys.get_best_target(debug=True)
    # 
    #             if target_pos:
    #                 tx, ty = target_pos
    #                 pydirectinput.moveTo(tx, ty, _pause=False)
    # 
    #                 # 4. XÁC NHẬN MỤC TIÊU ĐA TẦNG (Memory Hover ID HOẶC Radar HP Bar)
    #                 is_memory_confirmed = (hover_id > 1 and (hover_id in monster_ids or len(monster_ids) == 0))
    #                 is_radar_confirmed = self.radar.is_target_detected() if self.radar else False
    # 
    #                 if is_memory_confirmed or is_radar_confirmed:
    #                     # Khóa mục tiêu thành công 100%
    #                     self.ai_sys.confirm_lock(target_pos)
    #                     self.target_detected = True
    #                     if is_memory_confirmed:
    #                         self.target_locked_id = hover_id
    #                     self.last_event_msg = f"YOLO Aim: {self.target_locked_id if self.target_locked_id > 0 else 'Locked'}"
    #                     unconfirmed_pos = None
    #                     unconfirmed_count = 0
    #                 else:
    #                     # Điểm này chưa xác nhận được máu hoặc ID quái (xác chết / vật thể nhầm)
    #                     if unconfirmed_pos and (((tx - unconfirmed_pos[0])**2 + (ty - unconfirmed_pos[1])**2)**0.5 < 80):
    #                         unconfirmed_count += 1
    #                     else:
    #                         unconfirmed_pos = (tx, ty)
    #                         unconfirmed_count = 1
    # 
    #                     # Sau 2 frame (~40ms) trỏ vào mà vẫn không có quái -> Đưa ngay vào Blacklist tạm thời
    #                     if unconfirmed_count >= 2:
    #                         self.ai_sys.ignore_target_at((tx, ty), duration=2.5)
    #                         unconfirmed_pos = None
    #                         unconfirmed_count = 0
    # 
    #                     self.ai_sys.reset_lock()
    #                     self.target_detected = False
    #                     self.target_locked_id = 0
    #             else:
    #                 # Không thấy bbox nào phù hợp trên màn hình
    #                 self.ai_sys.reset_lock()
    #                 self.target_detected = False
    #                 self.target_locked_id = 0
    #                 unconfirmed_pos = None
    #                 unconfirmed_count = 0
    # 
    #         except Exception as e:
    #             if self.ai_sys:
    #                 self.ai_sys.reset_lock()
    #             self.target_detected = False
    #             self.target_locked_id = 0
    #             unconfirmed_pos = None
    #             unconfirmed_count = 0
    # 
    #         time.sleep(0.02)
    # ---------------------------------------------------------------------------------

    def yolo_worker(self):
        """[NEW 2026-08-29] Luồng YOLO Targeting AI: Z bật / X tắt, Strict Monster Verification & NPC Blacklist.
        - Khắc phục triệt để lỗi target NPC / Mobs=0:
          1. Quái vật hợp lệ BẮT BUỘC: hover_id > 1 VÀ hover_id in monster_ids (chỉ quái sống thực sự).
          2. Nếu trỏ vào NPC (hover_id > 1 nhưng không thuộc monster_ids) hoặc khi Mobs=0:
             $\rightarrow$ Tự động đưa ngay vào Blacklist (3.0s) để bỏ qua NPC, không chiếm chuột.
        """
        unconfirmed_pos = None
        unconfirmed_count = 0

        while not self.exit_event.is_set():
            # --- 1. TOGGLE PHÍM Z BẬT / PHÍM X TẮT YOLO TARGETING ---
            if keyboard.is_pressed('z') and not self.is_yolo_active:
                self.is_yolo_active = True
                winsound.Beep(1000, 150)
                self.last_event_msg = "YOLO Bật"
                time.sleep(0.3)  # debounce

            if keyboard.is_pressed('x') and self.is_yolo_active:
                self.is_yolo_active = False
                if self.ai_sys:
                    self.ai_sys.reset_lock()
                self.target_detected = False
                self.target_locked_id = 0
                unconfirmed_pos = None
                unconfirmed_count = 0
                if self.is_left_down:
                    pydirectinput.mouseUp(button='left')
                    self.is_left_down = False
                winsound.Beep(500, 150)
                self.last_event_msg = "YOLO Tắt"
                time.sleep(0.3)  # debounce

            # --- GUARD: Dừng nếu bot tắt hoặc chưa bật Z hoặc AI chưa sẵn sàng ---
            if not (self.game_connected and self.is_running and self.is_yolo_active and self.ai_sys):
                if self.ai_sys and self.ai_sys.locked_target:
                    self.ai_sys.reset_lock()
                self.target_detected = False
                self.target_locked_id = 0
                unconfirmed_pos = None
                unconfirmed_count = 0
                time.sleep(0.05)
                continue

            try:
                # 2. ĐỌC DỮ LIỆU BỘ NHỚ (Thread-safe)
                with self._data_lock:
                    hover_id = self.shared_data.get('hover_id', 0)
                    monster_ids = self.shared_data.get('monster_ids', set())

                # 3. YOLO AI PHÁT HIỆN MỤC TIÊU (Bật màn hình Debug trực quan)
                target_pos = self.ai_sys.get_best_target(debug=True)

                if target_pos:
                    tx, ty = target_pos
                    pydirectinput.moveTo(tx, ty, _pause=False)

                    # 4. XÁC NHẬN MỤC TIÊU NGHIÊM NGẶT (Strict Memory Monster ID Check)
                    # Quái vật hợp lệ BẮT BUỘC: hover_id > 1 VÀ hover_id nằm trong danh sách slot quái thực sự
                    is_memory_confirmed = (hover_id > 1) and (hover_id in monster_ids)
                    is_radar_confirmed = (self.radar.is_target_detected() and len(monster_ids) > 0) if self.radar else False

                    is_valid_monster = is_memory_confirmed or is_radar_confirmed

                    if is_valid_monster:
                        # Khóa mục tiêu thành công 100%
                        self.ai_sys.confirm_lock(target_pos)
                        self.target_detected = True
                        if is_memory_confirmed:
                            self.target_locked_id = hover_id
                        self.last_event_msg = f"YOLO Aim: {self.target_locked_id if self.target_locked_id > 0 else 'Locked'}"
                        unconfirmed_pos = None
                        unconfirmed_count = 0
                    else:
                        # Điểm này không phải quái hợp lệ (NPC, đồng minh, xác chết hoặc Mobs = 0)
                        is_npc_or_empty = (hover_id > 1 and hover_id not in monster_ids) or (len(monster_ids) == 0)

                        if is_npc_or_empty:
                            # 100% là NPC hoặc khu vực không có quái -> Blacklist ngay 3.0s để không giật chuột vào
                            self.ai_sys.ignore_target_at((tx, ty), duration=3.0)
                            unconfirmed_pos = None
                            unconfirmed_count = 0
                        else:
                            # Bbox thông thường nhưng chưa vào tâm hoặc trượt frame
                            if unconfirmed_pos and (((tx - unconfirmed_pos[0])**2 + (ty - unconfirmed_pos[1])**2)**0.5 < 80):
                                unconfirmed_count += 1
                            else:
                                unconfirmed_pos = (tx, ty)
                                unconfirmed_count = 1

                            # Sau 2 frame (~40ms) không xác nhận được -> Blacklist tạm thời
                            if unconfirmed_count >= 2:
                                self.ai_sys.ignore_target_at((tx, ty), duration=2.5)
                                unconfirmed_pos = None
                                unconfirmed_count = 0

                        self.ai_sys.reset_lock()
                        self.target_detected = False
                        self.target_locked_id = 0
                else:
                    # Không thấy bbox nào phù hợp trên màn hình
                    self.ai_sys.reset_lock()
                    self.target_detected = False
                    self.target_locked_id = 0
                    unconfirmed_pos = None
                    unconfirmed_count = 0

            except Exception as e:
                if self.ai_sys:
                    self.ai_sys.reset_lock()
                self.target_detected = False
                self.target_locked_id = 0
                unconfirmed_pos = None
                unconfirmed_count = 0

            time.sleep(0.02)

        # Exit cleanup
        self.target_detected = False
        self.target_locked_id = 0

    def mouse_arbiter_worker(self):
        """[NEW 2026-08-29] Bộ Trọng tài chuột thống nhất cho YOLO Bot.
        - Logic Chuột Trái:
            Đè Chuột Trái = (YOLO phát hiện & khóa quái [self.target_detected] VÀ is_yolo_active)
            -> Khi YOLO tìm thấy quái: Tự động giữ chuột tấn công.
            -> Khi quái chết (EXP tăng / mất dấu / bấm X tắt): Tự động nhả chuột ngay lập tức.
        """
        while not self.exit_event.is_set():
            if not (self.game_connected and self.is_running and self.is_yolo_active):
                if self.is_left_down:
                    pydirectinput.mouseUp(button='left')
                    self.is_left_down = False
                time.sleep(0.05)
                continue

            # ĐIỀU PHỐI CHUỘT TRÁI THEO TRẠNG THÁI TARGET CỦA YOLO
            should_left_down = self.target_detected and self.is_yolo_active

            if should_left_down and not self.is_left_down:
                pydirectinput.mouseDown(button='left')
                self.is_left_down = True
            elif not should_left_down and self.is_left_down:
                pydirectinput.mouseUp(button='left')
                self.is_left_down = False

            time.sleep(0.01)  # Quét 100 FPS (10ms)

        # Cleanup khi luồng thoát
        if self.is_left_down:
            pydirectinput.mouseUp(button='left')
            self.is_left_down = False

    def run(self):
        threads = [
            threading.Thread(target=self.sensor_worker, daemon=True),
            threading.Thread(target=self.action_worker, daemon=True),
            threading.Thread(target=self.yolo_worker,   daemon=True),
            threading.Thread(target=self.mouse_arbiter_worker, daemon=True),
        ]
        for t in threads: t.start()

        print("=== SACRED YOLO VISION AI BOT ACTIVE ===")
        try:
            while not self.exit_event.is_set():
                if not self.game_connected:
                    self.is_running = False
                    self.game_connected = self.connect_game()
                    if not self.game_connected:
                        time.sleep(2)
                        continue

                toggle_key = self.config.get('global', {}).get('toggle_key', 'n')
                if keyboard.is_pressed(toggle_key):
                    self.is_running = not self.is_running
                    winsound.Beep(1000 if self.is_running else 500, 200)
                    if self.is_running:
                        # [NEW 2026-08-11] Reset tất cả buff timers khi bật lại
                        for buff in self.buff_queue['buffs']:
                            buff['last_cast_time'] = 0.0
                            buff['retry_count'] = 0
                            buff['next_retry_time'] = 0.0
                        self.last_buff_finish_time = 0
                        self.last_buff_cast_delay = 0
                    else:
                        self.is_yolo_active = False
                        if self.is_left_down:
                            pydirectinput.mouseUp(button='left')
                            self.is_left_down = False
                        if self.is_right_down:
                            pydirectinput.mouseUp(button='right')
                            self.is_right_down = False
                    
                    status_msg = 'Bot đã bật.' if self.is_running else 'Bot nghỉ ngơi.'
                    self.voice.speak(status_msg)
                    time.sleep(0.4)

                if keyboard.is_pressed('esc'):
                    self.exit_event.set()
                time.sleep(0.1)
        finally:
            if self.cooldown_hook:
                self.cooldown_hook.uninstall()


if __name__ == "__main__":
    bot = SacredBot()
    bot.run()