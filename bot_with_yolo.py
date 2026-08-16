import threading
import time
import keyboard
import winsound
import pymem
import pydirectinput

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
        self.ai_sys = None 
        self.radar = None
        self.potion_sys = None
        self.danger_sys = None
        self.hotkey_sys = None
        
        # Flags điều khiển trạng thái
        self.game_connected = False
        self.is_running = False
        self.exit_event = threading.Event()

        self.last_threat = 0
        self.shared_data = {
            'hp_percent': 100.0,
            'threat_level': 0
        }        
        
        self.is_in_combat = False       
        self.safe_timer = 0             
        self.last_speak_time = 0        
        self.is_pressing = False

        # Biến quản lý Manual Override (Phương án C + A)
        self.manual_override_until = 0  # Cooldown tạm dừng bot khi bấm 'd' hoặc giật chuột
        self.last_bot_mouse_pos = None  # Lưu vị trí chuột bot vừa di chuyển

        self.last_buff_time = 0      # Mốc thời gian buff lần cuối
        self.BUFF_INTERVAL = 33      # Khoảng cách giữa các lần buff (30 giây)

    def load_config(self):
        import json
        try:
            with open('sacred_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Không thể load config: {e}")
            return {}

    def connect_game(self):
        """Khởi tạo tất cả các module. Phải đảm bảo ai_sys được nạp tại đây."""
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
            
            # 3. Khởi tạo AI Module (QUAN TRỌNG: Sửa lỗi thiếu dòng này)
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
                    
                    self.shared_data['hp_percent'] = hp if hp is not None else 100.0
                    self.shared_data['threat_level'] = threat
                except:
                    self.game_connected = False
            time.sleep(0.1)

    def action_worker(self):
        """Luồng thực thi: Tối ưu hoá Hybrid AI + Radar"""
        last_potion_time = 0
        
        while not self.exit_event.is_set():
            # KIỂM TRA AN TOÀN TRƯỚC KHI CHẠY (Tránh lỗi NoneType)
            if not (self.game_connected and self.is_running and self.ai_sys and self.radar):
                # Nếu Bot đang bật mà chưa nạp xong AI/Radar thì tạm dừng
                time.sleep(0.1)
                continue

            # 1. LẤY DỮ LIỆU
            hp = self.shared_data['hp_percent']
            threat = self.shared_data.get('threat_level', 0)
            threshold = self.config['potion_system']['threshold_percent']
            current_time = time.time()

            # --- PHÍM TẮT 'D': HỦY KHÓA MỤC TIÊU VÀ ĐƯA VÀO DANH SÁCH ĐEN 3 GIÂY ---
            if keyboard.is_pressed('d'):
                if self.ai_sys:
                    self.ai_sys.ignore_current_target(duration=3.0)
                if self.is_pressing:
                    pydirectinput.mouseUp(button='left')
                    self.is_pressing = False
                winsound.Beep(800, 100)
                time.sleep(0.2)

            # --- LOGIC CHIẾN ĐẤU ---
            if threat > 0:
                self.safe_timer = 0
                if not self.is_in_combat:
                    self.is_in_combat = True
                    self.voice.speak(f"Phát hiện mục tiêu.")

                # CODE CŨ (Đo khoảng cách giật chuột tự động - Đã loại bỏ do lỗi DirectInput):
                # if self.last_bot_mouse_pos and self.ai_sys and self.ai_sys.locked_target:
                #     cx, cy = pydirectinput.position()
                #     ...

                # Bước A: AI tìm mục tiêu (hoặc lấy mục tiêu đang lock)
                target_pos = self.ai_sys.get_best_target(debug=True)
                
                if target_pos:
                    tx, ty = target_pos
                    pydirectinput.moveTo(tx, ty, _pause=False)
                    
                    # Bước B: Radar xác nhận màu
                    if self.radar.is_target_detected():
                        # KÍCH HOẠT KHÓA MỤC TIÊU KHI RADAR THẤY THANH MÁU QUÁI
                        self.ai_sys.confirm_lock(target_pos)

                        if not self.is_pressing:
                            pydirectinput.mouseDown(button='left')
                            self.is_pressing = True
                    else:
                        # Nếu chưa lock được mục tiêu nào mà radar false (không có thanh máu) thì nhả chuột
                        if not self.ai_sys.locked_target:
                            if self.is_pressing:
                                pydirectinput.mouseUp(button='left')
                                self.is_pressing = False
                else:
                    # Khi target_pos là None (mất dấu quái/lock), lập tức nhả chuột!
                    if self.is_pressing:
                        pydirectinput.mouseUp(button='left')
                        self.is_pressing = False
            else:
                # Reset trạng thái Lock khi sạch quái (Threat == 0)
                if self.ai_sys:
                    self.ai_sys.reset_lock()

                # Xử lý khi quét sạch quái (Safe Timer)
                if self.is_in_combat:
                    self.safe_timer += 1
                    if self.safe_timer > 75: 
                        self.voice.speak('Sạch quái rồi.')
                        self.is_in_combat = False
                        self.safe_timer = 0
                
                if self.is_pressing:
                    pydirectinput.mouseUp(button='left')
                    self.is_pressing = False
           
                
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

            if keyboard.is_pressed('n'):
                self.is_running = not self.is_running
                winsound.Beep(1000 if self.is_running else 500, 200)
                # Đảm bảo nhả chuột khi tắt bot bằng phím V
                if not self.is_running and self.is_pressing:
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