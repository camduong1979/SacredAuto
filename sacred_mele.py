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


class SacredBot:
    def __init__(self):
        self.config = self.load_config()
        self.voice = VoiceAssistant()
        self.pm = None
        self.module_addr = None

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
        self.shared_data = {
            'hp_percent': 100.0,
            'threat_level': 0
        }        
        
        self.is_in_combat = False
        self.safe_start_time = 0.0      # Mốc thời gian bắt đầu đếm Safe (giây thực)
        self.last_speak_time = 0        
        self.is_pressing = False

        # Biến điều khiển Color Worker (N auto-sync)
        self.is_color_active = False    # Flag bật/tắt luồng Color targeting
        self.target_detected = False    # Trạng thái phát hiện mục tiêu để hiển thị lên Live HUD
        self.is_left_down = False       # Trạng thái thực tế chuột trái (Unified Mouse Arbiter)
        self.is_right_down = False      # Trạng thái thực tế chuột phải (Phím X)

        self.sct = None                     # Lazy init trong luồng worker để tránh lỗi thread-local srcdc Windows
        self.buff_queue = self._init_buff_system()
        self.last_buff_finish_time = 0    # Mốc thời gian hoàn tất buff gần nhất
        self.last_buff_cast_delay = 0     # Cast delay của buff vừa xong (giây)
 
        self.last_event_msg = "Sẵn sàng"  # Thông điệp sự kiện gần nhất cho Single-line HUD
        self.last_hud_print_time = 0.0    # Giới hạn tần suất in HUD tránh giật console


    def print_hud(self, hp, threat):
        """[NEW 2026-08-16] In trạng thái trực tiếp trên 1 dòng duy nhất (Single-line Live HUD).
        Sử dụng sys.stdout.write('\r...') để đảm bảo ghi thẳng vào console buffer của Windows.
        """
        now = time.time()
        if now - self.last_hud_print_time < 0.25:
            return
        self.last_hud_print_time = now

        status_text = "ON" if self.is_running else "OFF"
        # event_short = (self.last_event_msg[:20] + '..') if len(self.last_event_msg) > 22 else self.last_event_msg
        # hud_line = f"\r[HUD] Bot: {status_text:<3} | HP: {hp:5.1f}% | Threat: {threat:2d} | {event_short:<22}"
        
        # 1. Triệt tiêu toàn bộ ký tự xuống dòng trong msg để không làm vỡ HUD
        clean_msg = (
            self.last_event_msg.replace("\r", "").replace("\n", " ").strip()
        )
        event_short = (
            (clean_msg[:20] + "..") if len(clean_msg) > 22 else clean_msg
        )

        # 2. Thêm \033[K ở cuối để xóa sạch các ký tự dư thừa của dòng cũ
        # --- OLD CODE (REPLACED) ---
        # clr_text = "ON " if self.is_color_active else "OFF"
        # hud_line = f"\rHP: {hp:5.1f}% | Threat: {threat:2d} | CLR: {clr_text} | {event_short:<22}\033[K"
        # ---------------------------
        target_str = "Aim" if self.target_detected else "None"
        hud_line = f"\rHP: {hp:5.1f}% | Threat: {threat:2d} | Target: {target_str} | {event_short}\033[K"

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
        Hỗ trợ 3 loại buff (CA/MA/CO) độc lập kèm điểm trinh sát Sentinel điểm ảnh.
        """
        buff_cfg = self.config.get('auto_buff_system', {})
        buffs = []
        for buff_data in buff_cfg.get('buffs', []):
            buffs.append({
                'id': buff_data.get('id', 'unknown'),
                'name': buff_data.get('name', 'Buff'),
                'enabled': buff_data.get('enabled', False),
                'interval': buff_data.get('interval', 30),
                'cast_delay': buff_data.get('cast_delay', 0.5),
                'sentinel_enabled': buff_data.get('sentinel_enabled', True),
                'sentinel_x': buff_data.get('sentinel_x', 0),
                'sentinel_y': buff_data.get('sentinel_y', 0),
                'tolerance_rgb': buff_data.get('tolerance_rgb', 1),
                'min_brightness': buff_data.get('min_brightness', 14),
                'max_brightness': buff_data.get('max_brightness', 177),
                'retry_timeout': buff_data.get('retry_timeout', 3.0),
                'sequence': buff_data.get('sequence', []),
                'last_cast_time': 0,
                'retry_start_time': 0
            })
        enabled = buff_cfg.get('enabled', False)
        print(f"[BUFF SYSTEM v2.0] {'BẬT' if enabled else 'TẮT'} — Loaded {len(buffs)} loại buff (Visual Sentinel Active).")
        return {
            'enabled': enabled,
            'buffs': buffs
        }

    def is_buff_ready(self, buff):
        """[NEW 2026-08-13] Trinh sát màu Visual Sentinel cho Auto Buff.
        Nếu điểm ảnh rơi vào phổ Xám Đen (R=G=B) -> Skill đang Cooldown / Casting -> Trả về False (Chưa sẵn sàng).
        Nếu điểm ảnh thoát khỏi phổ Xám Đen -> Skill sáng màu -> Trả về True (Ready).
        """
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

            # --- [CHANGELOG 2026-08-13] OLD: Return not is_casting without debug log ---
            # return not is_casting
            # except Exception:
            #     return True
            # --- [END OLD] ---
            # [DEBUG LOG - COMMENTED OUT] In log debug trinh sát màu Visual Sentinel cho Auto Buff
            # status_str = "⏳ CHỜ (Đang CD/Cast)" if is_casting else "✅ SẴN SÀNG (Sáng màu)"
            # print(f"[BUFF SENTINEL] '{buff['name']}' (X:{x}, Y:{y}) | RGB=({r},{g},{b}) | Brightness={avg_brightness:.1f} | IsGray={is_equal_rgb} -> {status_str}")

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
            
            # 2. Khởi tạo Logic Modules
            self.hotkey_sys = HotKeySystem(self.config.get('hotkey_system'))
            self.radar = CombatRadar(self.config)
            
            # 3. Khởi tạo AI Module (YOLO)
            if self.config.get('ai_system'):
                self.ai_sys = YOLOManager(self.config)

            print(f"\n[SUCCESS] Đã kết nối Sacred.exe (Base: {hex(self.module_addr)})")
            self.voice.speak('Hệ thống đã sẵn sàng. Chiến thôi đại ca!')
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

    def sensor_worker(self):
        """Luồng quét Memory (100ms)"""
        while not self.exit_event.is_set():
            if self.game_connected and self.is_running:
                try:
                    hp = self.potion_sys.get_hp_percent()
                    threat = self.danger_sys.get_threat_level()
                    
                    with self._data_lock:
                        self.shared_data['hp_percent'] = hp if hp is not None else 100.0
                        self.shared_data['threat_level'] = threat
                except Exception as e:
                    print(f"[SENSOR ERROR] Mất kết nối game: {e}")
                    self.game_connected = False
            time.sleep(0.1)

    def action_worker(self):
        """Luồng thực thi: Tối ưu hoá Hybrid AI + Radar"""
        last_potion_time = 0
        
        while not self.exit_event.is_set():
            # KIỂM TRA AN TOÀN TRƯỚC KHI CHẠY (Tránh lỗi NoneType)
            if not (self.game_connected and self.is_running and self.radar):
                # Nếu Bot đang bật mà chưa nạp xong Radar thì tạm dừng
                time.sleep(0.1)
                continue

            # 1. LẤY DỮ LIỆU (thread-safe)
            with self._data_lock:
                hp     = self.shared_data['hp_percent']
                threat = self.shared_data['threat_level']
            threshold    = self.config['potion_system']['threshold_percent']
            current_time = time.time()

            if threat > 0:
                self.safe_start_time = 0.0  # Reset đồng hồ Safe khi có quái

                # 1. THÔNG BÁO GIỌNG NÓI (Chỉ nói 1 lần duy nhất khi vừa chớm gặp bãi quái)
                if not self.is_in_combat:
                    self.is_in_combat = True
                    self.voice.speak("Có quái.")

                # [NEW 2026-08-13] AUTO BUFF SYSTEM v2.0 (Visual Sentinel + Priority Scheduler)
                if self.buff_queue['enabled']:
                    # Đảm bảo cast_delay sau buff gần nhất đã trôi qua trước khi cast buff tiếp
                    if current_time - self.last_buff_finish_time >= self.last_buff_cast_delay:
                        # 1. Lọc tất cả các buff đã chạm mốc interval
                        due_buffs = [
                            b for b in self.buff_queue['buffs']
                            if b['enabled'] and (current_time - b['last_cast_time'] >= b['interval'])
                        ]

                        if due_buffs:
                            cast_executed = False

                            # 2. Thử trinh sát màu Visual Sentinel từng buff đến hạn (Chuyển mạch ưu tiên)
                            for target_buff in due_buffs:
                                if self.is_buff_ready(target_buff):
                                    self.last_event_msg = f"Buff: {target_buff['name']}"
                                    self.voice.speak(target_buff['name'])
                                    self.hotkey_sys.execute_sequence(target_buff['sequence'])
                                    target_buff['last_cast_time'] = current_time
                                    target_buff['retry_start_time'] = 0  # Reset mốc retry khi đã buff thành công
                                    self.last_buff_finish_time = time.time()
                                    self.last_buff_cast_delay = target_buff['cast_delay']
                                    cast_executed = True
                                    break  # Chỉ cast 1 buff thành công duy nhất trong mỗi lượt

                            # 3. NẾU TẤT CẢ BUFF ĐẾN HẠN ĐỀU CHƯA READY (Đang dính CD / Tối màu)
                            if not cast_executed:
                                primary_buff = due_buffs[0]
                                if primary_buff['retry_start_time'] == 0:
                                    primary_buff['retry_start_time'] = current_time
                                elif current_time - primary_buff['retry_start_time'] > primary_buff.get('retry_timeout', 3.0):
                                    # Hết thời gian gác 2-3s mà chiêu vẫn chưa hồi -> Reset mốc retry để giải phóng vòng lặp
                                    primary_buff['retry_start_time'] = 0

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
                        # LƯU Ý: Tuyệt đối KHÔNG reset self.last_buff_time ở đây
                        # để thời gian hồi chiêu buff tiếp tục được đếm chuẩn xác xuyên suốt các bãi quái.
                
                
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

            # In HUD trực tiếp trên 1 dòng
            self.print_hud(hp, threat)

            time.sleep(0.02)

    # --- OLD CODE (REPLACED: yolo_worker dùng YOLO + ai_sys) ---
    # def yolo_worker(self):
    #     """Luồng YOLO targeting độc lập: Z bật / X tắt."""
    #     ...  # (Toàn bộ logic YOLO cũ đã được thay bằng color_worker bên dưới)
    # ------------------------------------------------------------

    def color_worker(self):
        """Luồng nhận diện quái bằng mã màu HP — không dùng YOLO.
        Cấu trúc giống yolo_worker (Z bật / X tắt).
        Toàn quyền kiểm soát mouseDown/Up — không phụ thuộc action_worker.
        [REFACTORED] Scan loop + check_logic đã chuyển vào CombatRadarClass.is_target_detected().
        """
        # --- OLD CODE (REPLACED: scan loop + check_logic nội bộ trùng với CombatRadarClass) ---
        # scan_cfg = self.config.get('color_radar', {})
        # CHECK_X  = scan_cfg.get('check_x', 947)
        # CHECK_Y  = scan_cfg.get('check_y', 790)
        # SCAN_W   = scan_cfg.get('scan_w',  20)
        # SCAN_H   = scan_cfg.get('scan_h',  3)
        #
        # def check_logic(r, g, b):
        #     if r > 250 and g > 250 and b > 250: return "WHITE"
        #     if r > 240 and g > 240 and (100 < b < 150): return "YELLOW"
        #     if (110 <= r <= 185) and (g < 95) and (b < 95) and (abs(g - b) < 15): return "RED"
        #     return None
        # ---------------------------

        while not self.exit_event.is_set():

            # --- OLD CODE (REPLACED: Toggle Z / X thủ công cho Color targeting) ---
            # if keyboard.is_pressed('z') and not self.is_color_active:
            #     self.is_color_active = True
            #     winsound.Beep(1000, 150)
            #     print("\n[COLOR] BẬT targeting (thủ công)")
            #     time.sleep(0.3)  # debounce
            #
            # if keyboard.is_pressed('x') and self.is_color_active:
            #     self.is_color_active = False
            #     if self.is_pressing:
            #         pydirectinput.mouseUp(button='left')
            #         self.is_pressing = False
            #     winsound.Beep(500, 150)
            #     print("\n[COLOR] TẮT targeting (thủ công)")
            #     time.sleep(0.3)  # debounce
            # ---------------------------------------------------------------------

            # --- GUARD: Dừng nếu chưa sẵn sàng hoặc bị tạm dừng ---
            if not (self.game_connected and self.is_running and self.is_color_active):
                self.target_detected = False
                time.sleep(0.05)
                continue

            # --- SCAN MÃ MÀU HP — Dùng CombatRadarClass (nguồn sự thật duy nhất) ---
            try:
                # --- OLD CODE (REPLACED: color_worker tự gọi mouseDown/Up gây tranh chấp chuột) ---
                # detected = self.radar.is_target_detected()
                # self.target_detected = detected
                # if detected:
                #     if not self.is_pressing:
                #         pydirectinput.mouseDown(button='left')
                #         self.is_pressing = True
                # else:
                #     if self.is_pressing:
                #         pydirectinput.mouseUp(button='left')
                #         self.is_pressing = False
                # --------------------------------------------------------------------------------
                self.target_detected = self.radar.is_target_detected()

            except Exception as e:
                self.target_detected = False
                print(f"\n[COLOR ERROR] {e}")

            time.sleep(0.04)    # ~25 FPS — giống debug_v3.py

        # --- EXIT CLEANUP ---
        self.target_detected = False

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
        # ]
        # ---------------------------
        threads = [
            threading.Thread(target=self.sensor_worker, daemon=True),
            threading.Thread(target=self.action_worker, daemon=True),
            threading.Thread(target=self.color_worker,   daemon=True),
            threading.Thread(target=self.mouse_arbiter_worker, daemon=True),
        ]
        for t in threads: t.start()

        print("=== SACRED GOD BOT ACTIVE ===")
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
                        buff['last_cast_time'] = 0
                        buff['retry_start_time'] = 0
                    self.last_buff_finish_time = 0
                    self.last_buff_cast_delay = 0
                    # [NEW 2026-08-16] Auto-sync Color targeting theo N (Z/X vẫn override thủ công được)
                    self.is_color_active = True
                else:
                    # Khi N tắt → tự tắt color targeting; mouse_arbiter_worker guard tự nhả chuột
                    self.is_color_active = False
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

if __name__ == "__main__":
    bot = SacredBot()
    bot.run()