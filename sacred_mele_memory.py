import sys
import threading
import time
import keyboard
import winsound
import pymem
import pydirectinput
import mss
import numpy as np

# Import các module đã có
from AutoPotionClass import AutoPotion
from DangerSystemClass import DangerSystem
from HotKeySetClass import HotKeySystem
from CombatRadarClass import CombatRadar
from VoiceAssistant import VoiceAssistant
from YOLOManagerClass import YOLOManager
from SkillCooldownClass import SkillCooldownManager


class SacredBotMemory:
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
        self._data_lock = threading.Lock()   # Bảo vệ shared_data giữa 2 thread

        self.last_threat = 0
        self.last_exp = 0                    # [NEW 2026-08-29] Điểm kinh nghiệm mốc trước đó

        # --- OLD CODE (REPLACED: shared_data cũ chỉ có hp và threat) ---
        # self.shared_data = {
        #     'hp_percent': 100.0,
        #     'threat_level': 0
        # }
        # ---------------------------------------------------------------
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

        # --- OLD CODE (REPLACED: is_color_active) ---
        # self.is_color_active = False    # Flag bật/tắt luồng Color targeting
        # -------------------------------------------
        self.is_target_active = False   # [NEW 2026-08-29] Flag bật/tắt luồng Memory targeting
        self.target_detected = False    # Trạng thái phát hiện mục tiêu để hiển thị lên Live HUD & tấn công
        self.target_locked_id = 0       # [NEW 2026-08-29] ID quái đang bị khóa mục tiêu
        self.is_left_down = False       # Trạng thái thực tế chuột trái (Unified Mouse Arbiter)
        self.is_right_down = False      # Trạng thái thực tế chuột phải (Phím X)

        self.sct = None                     # Lazy init trong luồng worker để tránh lỗi thread-local srcdc Windows
        self.buff_queue = self._init_buff_system()
        self.last_buff_finish_time = 0    # Mốc thời gian hoàn tất buff gần nhất
        self.last_buff_cast_delay = 0     # Cast delay của buff vừa xong (giây)
 
        self.last_event_msg = "Sẵn sàng (Memory Mode)"  # Thông điệp sự kiện gần nhất cho Single-line HUD
        self.last_hud_print_time = 0.0    # Giới hạn tần suất in HUD tránh giật console


    # --- OLD CODE (REPLACED: print_hud cũ) ---
    # def print_hud(self, hp, threat):
    #     now = time.time()
    #     if now - self.last_hud_print_time < 0.25:
    #         return
    #     self.last_hud_print_time = now
    #     clean_msg = self.last_event_msg.replace("\r", "").replace("\n", " ").strip()
    #     event_short = (clean_msg[:20] + "..") if len(clean_msg) > 22 else clean_msg
    #     target_str = "Aim" if self.target_detected else "None"
    #     hud_line = f"\rHP: {hp:5.1f}% | Threat: {threat:2d} | Target: {target_str} | {event_short}\033[K"
    #     sys.stdout.write(hud_line)
    #     sys.stdout.flush()
    # -----------------------------------------

    def print_hud(self, hp, threat, monster_count=0, hover_id=0, exp=0):
        """[NEW 2026-08-29] In trạng thái trực tiếp trên 1 dòng duy nhất (Single-line Live HUD).
        Hiển thị chi tiết: HP | Threat | Mobs in area | Hover ID | EXP | Target Lock status.
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
            (clean_msg[:18] + "..") if len(clean_msg) > 20 else clean_msg
        )

        target_str = f"LOCK:{self.target_locked_id}" if self.target_detected else "None"
        hud_line = (
            f"\rHP: {hp:5.1f}% | Thr: {threat:1d} | Mobs: {monster_count:2d} | "
            f"Hover: {hover_id:<6} | EXP: {exp:<8} | Target: {target_str:<10} | {event_short}\033[K"
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

    # --- OLD CODE (REPLACED: is_buff_ready cũ chỉ dùng soi màu Visual Sentinel) ---
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
            self.voice.speak('Hệ thống Memory Target đã sẵn sàng.')
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
    #     while not self.exit_event.is_set():
    #         if self.game_connected and self.is_running:
    #             try:
    #                 hp = self.potion_sys.get_hp_percent()
    #                 threat = self.danger_sys.get_threat_level()
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

    def action_worker(self):
        """Luồng thực thi: Tối ưu hoá Auto Buff, Bơm máu & Giám sát EXP."""
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
            elif self.last_exp == 0 and exp > 0:
                self.last_exp = exp

            if threat > 0:
                self.safe_start_time = 0.0  # Reset đồng hồ Safe khi có quái

                # 1. THÔNG BÁO GIỌNG NÓI (Chỉ nói 1 lần duy nhất khi vừa chớm gặp bãi quái)
                if not self.is_in_combat:
                    self.is_in_combat = True
                    self.voice.speak("Có quái.")

                # --- OLD CODE (REPLACED: Auto Buff tuần tự cũ) ---
                # if self.buff_queue['enabled']:
                #     if current_time - self.last_buff_finish_time >= self.last_buff_cast_delay:
                #         due_buffs = [
                #             b for b in self.buff_queue['buffs']
                #             if b['enabled'] and (current_time - b['last_cast_time'] >= b['interval'])
                #         ]
                # 
                #         if due_buffs:
                #             cast_executed = False
                #             for target_buff in due_buffs:
                #                 if self.is_buff_ready(target_buff):
                #                     self.last_event_msg = f"Buff: {target_buff['name']}"
                #                     self.voice.speak(target_buff['name'])
                #                     self.hotkey_sys.execute_sequence(target_buff['sequence'])
                #                     target_buff['last_cast_time'] = current_time
                #                     target_buff['retry_start_time'] = 0
                #                     self.last_buff_finish_time = time.time()
                #                     self.last_buff_cast_delay = target_buff['cast_delay']
                #                     cast_executed = True
                #                     break
                # 
                #             if not cast_executed:
                #                 primary_buff = due_buffs[0]
                #                 if primary_buff['retry_start_time'] == 0:
                #                     primary_buff['retry_start_time'] = current_time
                #                 elif current_time - primary_buff['retry_start_time'] > primary_buff.get('retry_timeout', 3.0):
                #                     primary_buff['retry_start_time'] = 0
                # --------------------------------------------------

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

            # In HUD trực tiếp trên 1 dòng với đầy đủ thông tin Memory
            self.print_hud(hp, threat, len(monster_ids), hover_id, exp)

            time.sleep(0.02)

    # --- OLD CODE (REPLACED: color_worker quét dải màu pixel HP) ---
    # def color_worker(self):
    #     while not self.exit_event.is_set():
    #         if not (self.game_connected and self.is_running and self.is_color_active):
    #             self.target_detected = False
    #             time.sleep(0.05)
    #             continue
    #         try:
    #             self.target_detected = self.radar.is_target_detected()
    #         except Exception as e:
    #             self.target_detected = False
    #             print(f"\n[COLOR ERROR] {e}")
    #         time.sleep(0.04)
    #     self.target_detected = False
    # ----------------------------------------------------------------

    def memory_target_worker(self):
        """[NEW 2026-08-29] Luồng Nhận diện & Khóa mục tiêu bằng Memory.
        So khớp ID đối tượng dưới trỏ chuột (Hover ID) với Danh sách ID quái vật hiện hữu.
        Nếu Hover ID khớp với 1 con quái trong danh sách -> Xác nhận mục tiêu quái -> Bật cờ target_detected.
        """
        while not self.exit_event.is_set():
            if not (self.game_connected and self.is_running and self.is_target_active):
                self.target_detected = False
                self.target_locked_id = 0
                time.sleep(0.05)
                continue

            try:
                with self._data_lock:
                    hover_id = self.shared_data.get('hover_id', 0)
                    monster_ids = self.shared_data.get('monster_ids', set())

                # Điều kiện khóa mục tiêu:
                # 1. Hover ID > 1 (loại bỏ 0: trống và 1: nhân vật bản thân)
                # 2. Hover ID nằm trong danh sách quái đang hoạt động
                if hover_id > 1 and (hover_id in monster_ids):
                    self.target_detected = True
                    self.target_locked_id = hover_id
                    self.last_event_msg = f"Target Lock: {hover_id}"
                else:
                    # Nếu quái cũ vừa chết hoặc chuột rời khỏi quái
                    if self.target_locked_id not in monster_ids:
                        self.target_detected = False
                        self.target_locked_id = 0
                    elif hover_id <= 1:
                        self.target_detected = False

            except Exception:
                self.target_detected = False
                self.target_locked_id = 0

            time.sleep(0.02)  # Quét nhanh 50 FPS (~20ms)

        self.target_detected = False
        self.target_locked_id = 0

    # --- OLD CODE (REPLACED: manual_control_worker cũ xử lý riêng lẻ theo Threat) ---
    # def manual_control_worker(self):
    #     """[NEW 2026-08-22] Luồng giả lập chuột độc lập qua phím Z (chuột trái) và X (chuột phải).
    #     - Khi threat == 0: Đè Z -> mouseDown('left'), Nhả Z -> mouseUp('left') để di chuyển / đánh thường.
    #     - Khi threat > 0: Vô hiệu hóa phím Z (nhường toàn bộ quyền điều khiển chuột trái cho color_worker auto combat).
    #     - Phím X: Đè X -> mouseDown('right'), Nhả X -> mouseUp('right') để dùng chiêu chuột phải.
    #     """
    #     while not self.exit_event.is_set():
    #         if not (self.game_connected and self.is_running):
    #             if self.is_manual_left_down:
    #                 pydirectinput.mouseUp(button='left')
    #                 self.is_manual_left_down = False
    #             if self.is_manual_right_down:
    #                 pydirectinput.mouseUp(button='right')
    #                 self.is_manual_right_down = False
    #             time.sleep(0.05)
    #             continue
    #         with self._data_lock:
    #             threat = self.shared_data.get('threat_level', 0)
    #         if threat == 0:
    #             if keyboard.is_pressed('z'):
    #                 if not self.is_manual_left_down:
    #                     pydirectinput.mouseDown(button='left')
    #                     self.is_manual_left_down = True
    #             else:
    #                 if self.is_manual_left_down:
    #                     pydirectinput.mouseUp(button='left')
    #                     self.is_manual_left_down = False
    #         else:
    #             if self.is_manual_left_down:
    #                 pydirectinput.mouseUp(button='left')
    #                 self.is_manual_left_down = False
    #         if keyboard.is_pressed('x'):
    #             if not self.is_manual_right_down:
    #                 pydirectinput.mouseDown(button='right')
    #                 self.is_manual_right_down = True
    #         else:
    #             if self.is_manual_right_down:
    #                 pydirectinput.mouseUp(button='right')
    #                 self.is_manual_right_down = False
    #         time.sleep(0.01)
    # ---------------------------------------------------------------------------------

    def mouse_arbiter_worker(self):
        """[NEW 2026-08-22] Bộ Trọng tài chuột thống nhất (Unified Mouse Arbiter).
        - Logic Chuột Trái (OR Condition):
            Đè Chuột Trái = (Auto phát hiện quái [self.target_detected]) OR (Người chơi đè phím Z)
            -> Khi đè Z chạy map: Giữ chuột liên tục.
            -> Khi gặp quái: Giữ chuột mượt mà không ngắt quãng.
            -> Khi nhả Z nhưng quái còn: Auto tiếp tục giữ chuột đánh.
            -> Khi hết quái và nhả Z: Chuột tự động nhả.
        - Logic Chuột Phải:
            Đè Chuột Phải = (Người chơi đè phím X)
        """
        while not self.exit_event.is_set():
            if not (self.game_connected and self.is_running):
                if self.is_left_down:
                    pydirectinput.mouseUp(button='left')
                    self.is_left_down = False
                if self.is_right_down:
                    pydirectinput.mouseUp(button='right')
                    self.is_right_down = False
                time.sleep(0.05)
                continue

            # 1. KIỂM TRA PHÍM THỦ CÔNG
            z_down = keyboard.is_pressed('z')
            x_down = keyboard.is_pressed('x')

            # 2. ĐIỀU PHỐI CHUỘT TRÁI (UNIFIED LOGIC: AUTO TARGET OR PHÍM Z)
            should_left_down = self.target_detected or z_down

            if should_left_down and not self.is_left_down:
                pydirectinput.mouseDown(button='left')
                self.is_left_down = True
            elif not should_left_down and self.is_left_down:
                pydirectinput.mouseUp(button='left')
                self.is_left_down = False

            # 3. ĐIỀU PHỐI CHUỘT PHẢI (PHÍM X)
            if x_down and not self.is_right_down:
                pydirectinput.mouseDown(button='right')
                self.is_right_down = True
            elif not x_down and self.is_right_down:
                pydirectinput.mouseUp(button='right')
                self.is_right_down = False

            time.sleep(0.01)  # Quét nhanh 10ms để phản hồi tức thì

        # Cleanup khi luồng thoát
        if self.is_left_down:
            pydirectinput.mouseUp(button='left')
            self.is_left_down = False
        if self.is_right_down:
            pydirectinput.mouseUp(button='right')
            self.is_right_down = False

    def run(self):
        # --- OLD CODE (REPLACED) ---
        # threads = [
        #     threading.Thread(target=self.sensor_worker, daemon=True),
        #     threading.Thread(target=self.action_worker, daemon=True),
        #     threading.Thread(target=self.color_worker,   daemon=True),
        #     threading.Thread(target=self.mouse_arbiter_worker, daemon=True),
        # ]
        # ---------------------------
        threads = [
            threading.Thread(target=self.sensor_worker, daemon=True),
            threading.Thread(target=self.action_worker, daemon=True),
            threading.Thread(target=self.memory_target_worker, daemon=True),
            threading.Thread(target=self.mouse_arbiter_worker, daemon=True),
        ]
        for t in threads: t.start()

        print("=== SACRED MEMORY TARGET BOT ACTIVE ===")
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
                        # [NEW 2026-08-29] Auto-sync Memory targeting theo N
                        self.is_target_active = True
                    else:
                        # Khi N tắt → tự tắt target; mouse_arbiter_worker guard tự nhả chuột
                        self.is_target_active = False
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

# --- OLD CODE (REPLACED) ---
# if __name__ == "__main__":
#     bot = SacredBot()
#     bot.run()
# ---------------------------

if __name__ == "__main__":
    bot = SacredBotMemory()
    bot.run()