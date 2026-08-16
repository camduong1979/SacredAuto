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


class SacredBot:
    def __init__(self):
        self.config = self.load_config()
        self.voice = VoiceAssistant()
        self.pm = None
        self.module_addr = None

        # --- KHỞI TẠO BIẾN HỆ THỐNG (Tránh lỗi NoneType) ---
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

        # --- [CHANGELOG 2026-08-13] OLD: Khởi tạo mss ở Luồng chính (Main Thread) ---
        # self.sct = mss.mss()              # [NEW 2026-08-13] Mss Screen Grabber cho Visual Sentinel
        # --- [END OLD] ---
        self.sct = None                     # Lazy init trong luồng worker để tránh lỗi thread-local srcdc Windows
        self.buff_queue = self._init_buff_system()
        self.last_buff_finish_time = 0    # Mốc thời gian hoàn tất buff gần nhất
        self.last_buff_cast_delay = 0     # Cast delay của buff vừa xong (giây)

    def load_config(self):
        import json
        try:
            with open('sacred_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Không thể load config: {e}")
            return {}

    # --- [CHANGELOG 2026-08-13] OLD: Init Buff System v1.0 (Timer Only) ---
    # def _init_buff_system(self):
    #     """[NEW 2026-08-11] Khởi tạo hệ thống Auto Buff từ config (3 loại: CA/MA/CO).
    #     Mỗi buff có timer riêng, sequence riêng, và có thể bật/tắt độc lập.
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
    #             'sequence': buff_data.get('sequence', []),
    #             'last_cast_time': 0
    #         })
    #     enabled = buff_cfg.get('enabled', False)
    #     print(f"[BUFF SYSTEM] {'BẬT' if enabled else 'TẮT'} — Loaded {len(buffs)} loại buff.")
    #     return {
    #         'enabled': enabled,
    #         'buffs': buffs
    #     }
    # --- [END OLD] ---

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
                'retry_backoff': buff_data.get('retry_backoff', 2.0),
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

    # --- [CHANGELOG 2026-08-15] OLD: Vòng lặp retry click_right nhiều lần gây nghẽn luồng ---
    # def execute_buff_with_verification(self, buff, max_retries=2):
    #     sequence = buff.get('sequence', [])
    #     if not sequence:
    #         return False
    #     sentinel_enabled = buff.get('sentinel_enabled', True)
    #     cast_confirmed = False
    #     for step in sequence:
    #         action = step.get('action', 'press')
    #         key    = step.get('key', '')
    #         wait   = step.get('wait', 0.1)
    #         if action == 'click_right' and sentinel_enabled:
    #             for attempt in range(max_retries + 1):
    #                 pydirectinput.mouseUp(button='right')
    #                 pydirectinput.mouseDown(button='right')
    #                 time.sleep(0.08)
    #                 pydirectinput.mouseUp(button='right')
    #                 time.sleep(0.12)
    #                 if not self.is_buff_ready(buff):
    #                     cast_confirmed = True
    #                     break
    #             remaining_wait = max(0.0, wait - 0.2)
    #             if remaining_wait > 0:
    #                 time.sleep(remaining_wait)
    #         elif action == 'press':
    #             pydirectinput.keyUp(key)
    #             pydirectinput.keyDown(key)
    #             time.sleep(0.03)
    #             pydirectinput.keyUp(key)
    #             time.sleep(wait)
    #     return cast_confirmed
    # --- [END OLD] ---

    def execute_buff_with_verification(self, buff):
        """[NEW 2026-08-15] Thực thi buff Đơn Lượt (Single-Attempt) + Xác nhận màu Sentinel.
        - Thực thi chọn phím skill.
        - Click chuột phải 1 lần duy nhất -> Chờ 120ms -> Soi màu Sentinel xem đã vào Cooldown (Xám Đen) chưa.
        - Tiếp tục thực thi toàn bộ các bước còn lại (như trả về phím skill chính) để không kẹt phím.
        - Thoát ngay lập tức (Zero-blocking) và trả về kết quả True (thành công) / False (miss).
        """
        sequence = buff.get('sequence', [])
        if not sequence:
            return False

        sentinel_enabled = buff.get('sentinel_enabled', True)
        cast_confirmed = False

        for step in sequence:
            action = step.get('action', 'press')
            key    = step.get('key', '')
            wait   = step.get('wait', 0.1)

            if action == 'click_right' and sentinel_enabled:
                # 1. Click chuột phải 1 lần duy nhất
                pydirectinput.mouseUp(button='right')
                pydirectinput.mouseDown(button='right')
                time.sleep(0.08)
                pydirectinput.mouseUp(button='right')

                # 2. Độ trễ ngắn để game cập nhật hiệu ứng đổi màu icon sang xám đen (CD)
                time.sleep(0.12)

                # 3. Soi màu: is_buff_ready == False có nghĩa là icon đã xám đen -> Đã kích hoạt thành công!
                if not self.is_buff_ready(buff):
                    cast_confirmed = True
                else:
                    print(f"[BUFF VERIFY] ⚠️ Miss click chuột phải cho '{buff['name']}'.")

                # Chờ phần thời gian còn lại của step wait nếu còn
                remaining_wait = max(0.0, wait - 0.2)
                if remaining_wait > 0:
                    time.sleep(remaining_wait)
            elif action == 'press':
                pydirectinput.keyUp(key)
                pydirectinput.keyDown(key)
                time.sleep(0.03)
                pydirectinput.keyUp(key)
                time.sleep(wait)
            elif action == 'click_right':
                # Trường hợp sentinel_enabled bị tắt -> click thông thường
                pydirectinput.mouseUp(button='right')
                pydirectinput.mouseDown(button='right')
                time.sleep(0.08)
                pydirectinput.mouseUp(button='right')
                cast_confirmed = True
                time.sleep(wait)
            elif action == 'click_left':
                pydirectinput.mouseUp(button='left')
                pydirectinput.mouseDown(button='left')
                time.sleep(0.08)
                pydirectinput.mouseUp(button='left')
                time.sleep(wait)

        if not sentinel_enabled:
            cast_confirmed = True

        return cast_confirmed

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
                # Nếu Bot đang bật mà chưa nạp xong AI/Radar thì tạm dừng
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


                # --- [CHANGELOG 2026-08-13] OLD: Auto Buff v1.0 (Timer Only) ---
                # if self.buff_queue['enabled']:
                #     # Đảm bảo cast_delay sau buff gần nhất đã trôi qua trước khi cast buff tiếp
                #     if current_time - self.last_buff_finish_time >= self.last_buff_cast_delay:
                #         for buff in self.buff_queue['buffs']:
                #             if not buff['enabled']:
                #                 continue
                #             if current_time - buff['last_cast_time'] >= buff['interval']:
                #                 self.voice.speak(buff['name'])
                #                 self.hotkey_sys.execute_sequence(buff['sequence'])
                #                 buff['last_cast_time'] = current_time
                #                 self.last_buff_finish_time = time.time()
                #                 self.last_buff_cast_delay = buff['cast_delay']
                #                 break  # Chỉ chạy 1 buff mỗi vòng lặp — tránh xung đột phím
                # --- [END OLD] ---

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

                            # --- [CHANGELOG 2026-08-13] OLD: Scheduler không in log ---
                            # # 2. Thử trinh sát màu Visual Sentinel từng buff đến hạn (Chuyển mạch ưu tiên)
                            # for target_buff in due_buffs:
                            #     if self.is_buff_ready(target_buff):
                            #         self.voice.speak(target_buff['name'])
                            #         self.hotkey_sys.execute_sequence(target_buff['sequence'])
                            #         target_buff['last_cast_time'] = current_time
                            #         target_buff['retry_start_time'] = 0  # Reset mốc retry khi đã buff thành công
                            #         self.last_buff_finish_time = time.time()
                            #         self.last_buff_cast_delay = target_buff['cast_delay']
                            #         cast_executed = True
                            #         break  # Chỉ cast 1 buff thành công duy nhất trong mỗi lượt
                            # --- [END OLD] ---

                            # [DEBUG LOG - COMMENTED OUT] Log scheduler trinh sát màu
                            # buff_names = [b['name'] for b in due_buffs]
                            # print(f"\n[BUFF SCHEDULER] Có {len(due_buffs)} buff đến hạn: {buff_names}. Đang trinh sát màu...")

                            # --- [CHANGELOG 2026-08-15] OLD: Blind Execution qua execute_sequence (Không check miss chuột phải) ---
                            # for target_buff in due_buffs:
                            #     if self.is_buff_ready(target_buff):
                            #         print(f"[BUFF EXECUTE] ✅ Kích hoạt buff: {target_buff['name']}")
                            #         self.voice.speak(target_buff['name'])
                            #         self.hotkey_sys.execute_sequence(target_buff['sequence'])
                            #         target_buff['last_cast_time'] = current_time
                            #         target_buff['retry_start_time'] = 0  # Reset mốc retry khi đã buff thành công
                            #         self.last_buff_finish_time = time.time()
                            #         self.last_buff_cast_delay = target_buff['cast_delay']
                            #         cast_executed = True
                            #         break  # Chỉ cast 1 buff thành công duy nhất trong mỗi lượt
                            # --- [END OLD] ---

                            # [NEW 2026-08-15] 2. Thử trinh sát màu Visual Sentinel & Thực thi Closed-Loop (Phương án A: Đơn lượt + Backoff Delay)
                            for target_buff in due_buffs:
                                if self.is_buff_ready(target_buff):
                                    print(f"[BUFF EXECUTE] ✅ Bắt đầu thi triển buff: {target_buff['name']}")
                                    self.voice.speak(target_buff['name'])
                                    
                                    # Thực thi chuỗi buff 1 lần duy nhất kèm xác nhận đổi màu sau click_right
                                    is_success = self.execute_buff_with_verification(target_buff)
                                    
                                    if is_success:
                                        target_buff['last_cast_time'] = current_time
                                        target_buff['retry_start_time'] = 0  # Reset mốc retry khi đã buff thành công
                                        self.last_buff_finish_time = time.time()
                                        self.last_buff_cast_delay = target_buff['cast_delay']
                                        cast_executed = True
                                        print(f"[BUFF EXECUTE] 🎯 Buff '{target_buff['name']}' thành công (Đã xác nhận chuyển màu CD).")
                                        break  # Chỉ hoàn tất 1 buff trong mỗi lượt
                                    else:
                                        # XỬ LÝ KHI MISS CHUỘT PHẢI (Phương án A): Hoãn tạm thời 2s để tránh nghẽn luồng / spam 20ms
                                        backoff = target_buff.get('retry_backoff', 2.0)
                                        target_buff['last_cast_time'] = current_time - target_buff['interval'] + backoff
                                        self.last_buff_finish_time = time.time()
                                        self.last_buff_cast_delay = 0.2
                                        cast_executed = True
                                        print(f"[BUFF EXECUTE] ⚠️ Buff '{target_buff['name']}' miss chuột phải. Tạm hoãn {backoff}s trước khi thử lại để tránh nghẽn luồng.")
                                        break

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
                        # LƯU Ý: Tuyệt đối KHÔNG reset self.last_buff_time ở đây
                        # để thời gian hồi chiêu buff tiếp tục được đếm chuẩn xác xuyên suốt các bãi quái.
                
                
            # --- LOGIC HỖ TRỢ ---
            # Bơm máu
            if hp < threshold and (current_time - last_potion_time > 0.8):
                pydirectinput.press(self.config['potion_system']['key'])
                last_potion_time = current_time
                if current_time - self.last_speak_time > 3.0:
                    self.voice.speak('Bơm máu!')
                    self.last_speak_time = current_time

            # Chạy Hotkey
            self.hotkey_sys.run_check()

            time.sleep(0.02)

    def run(self):
        threads = [
            threading.Thread(target=self.sensor_worker, daemon=True),
            threading.Thread(target=self.action_worker, daemon=True)
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
                else:
                    # Đảm bảo nhả chuột khi tắt bot
                    if self.is_pressing:
                        pydirectinput.mouseUp(button='left')
                        self.is_pressing = False
                
                status_msg = 'Bot đã bật.' if self.is_running else 'Bot nghỉ ngơi.'
                self.voice.speak(status_msg)
                time.sleep(0.4)

            if keyboard.is_pressed('esc'):
                self.exit_event.set()
            time.sleep(0.1)

if __name__ == "__main__":
    bot = SacredBot()
    bot.run()