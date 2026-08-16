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

class SacredBot:
    def __init__(self):
        self.config = self.load_config()
        self.voice = VoiceAssistant()
        self.pm = None
        self.module_addr = None
        
        # Flags điều khiển trạng thái
        self.game_connected = False
        self.is_running = False
        self.exit_event = threading.Event()

        # --- QUAN TRỌNG: KHAI BÁO BIẾN NÀY ĐỂ HẾT LỖI ---
        self.last_threat = 0
        #self.logs = []
        # --- KHAI BÁO MODULE RADAR ---
        self.radar = None
        # Dữ liệu chia sẻ giữa các luồng
        self.shared_data = {
            'hp_percent': 100.0,
            'threat_level': 0
        }        

    def load_config(self):
        import json
        try:
            with open('sacred_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Không thể load config: {e}")
            return {}

    def connect_game(self):
        """Thực hiện kết nối và khởi tạo lại các module chuyên biệt"""
        try:
            p_name = "sacred.exe"
            self.pm = pymem.Pymem(p_name)
            self.module_addr = pymem.process.module_from_name(self.pm.process_handle, p_name).lpBaseOfDll
            
            # Khởi tạo lại module với Handle mới từ Pymem
            self.potion_sys = AutoPotion(self.pm, self.module_addr)
            self.danger_sys = DangerSystem(self.pm, self.module_addr)
            self.hotkey_sys = HotKeySystem(self.config.get('hotkey_system'))
            
            # --- KHỞI TẠO RADAR TẠI ĐÂY ---
            self.radar = CombatRadar(self.config)

            print(f"\n[SUCCESS] Đã kết nối Sacred.exe (Base: {hex(self.module_addr)})")
            self.voice.speak('Đã kết nối game.')
            #winsound.Beep(800, 300)
            return True
        except Exception:
            return False

    def sensor_worker(self):
        """Luồng quét Memory ngầm (Tần suất 100ms)"""
        while not self.exit_event.is_set():
            if self.game_connected and self.is_running:
                try:
                    # Đọc dữ liệu từ memory và lưu vào shared_data
                    hp = self.potion_sys.get_hp_percent()
                    # # Đọc Threat từ DangerSystem
                    # threat = self.danger_sys.get_threat_level()
                    
                    self.shared_data['hp_percent'] = hp if hp is not None else 100.0
                    self.shared_data['threat_level'] = self.danger_sys.get_threat_level()

                    # HIỂN THỊ TRẠNG THÁI REAL-TIME
                    #print(f"[STATUS] HP: {self.shared_data['hp_percent']:.1f}% | Threat: {threat}    ", end='\r')
                except Exception:
                    # Nếu lỗi đọc (Game crash), reset trạng thái kết nối
                    self.game_connected = False
            time.sleep(0.1)

    def action_worker(self):
        """Luồng thực thi hành động (Tần suất 20ms để bắt phím nhạy)"""
        last_potion_time = 0
        self.is_pressing = False  # Đưa ra ngoài vòng lặp để giữ trạng thái
        while not self.exit_event.is_set():
            if self.game_connected and self.is_running:
                # Lấy dữ liệu từ shared_data
                hp = self.shared_data['hp_percent']
                threat = self.shared_data.get('threat_level', 0)
                threshold = self.config['potion_system']['threshold_percent']
                
                # --- PHẦN 1: CẢNH BÁO ÂM THANH THÔNG MINH ---
                # Nếu vừa phát hiện quái (trước đó bằng 0, giờ lớn hơn 0)
                #if threat > 0 and self.last_threat == 0:
                    #winsound.Beep(1200, 150) # Tít! (Cao, ngắn) báo hiệu có quái để Buff
                    #self.add_log(f"PHÁT HIỆN QUÁI! (Threat: {threat})")
                # Nếu vừa tiêu diệt hết quái (trước đó có quái, giờ bằng 0)
                #elif threat == 0 and self.last_threat > 0:
                    #winsound.Beep(600, 150) # Tút... (Trầm) báo hiệu đã an toàn
                    #self.add_log("ĐÃ DỌN SẠCH QUÁI!")
                    
                #self.last_threat = threat # Cập nhật trạng thái cho vòng lặp sau
                # --- PHẦN 1: CẢNH BÁO ÂM THANH THÔNG MINH ---
                if threat > 0 and self.last_threat == 0:
                    # Chỉ nói KHI VỪA THẤY QUÁI (chuyển từ 0 lên > 0)
                    print('co dich')
                    self.voice.speak('Có địch')
                    # Cập nhật last_threat ngay để vòng lặp sau không gọi speak nữa
                    self.last_threat = threat 

                elif threat == 0 and self.last_threat > 0:
                    # Vừa dọn sạch quái
                    self.last_threat = 0
                # --- PHẦN 2: LOGIC BEM (MELEE HOLD) - ĐÃ HẾT LỖI ---
                # Chỉ quét Radar khi có quái (threat > 0)
                
                if threat > 0:
                    # Kiểm tra xem radar đã được khởi tạo chưa để tránh crash
                    if self.radar and self.radar.is_target_detected():
                        if not self.is_pressing:
                            pydirectinput.mouseDown(button='left') # Đè chuột trái
                            self.is_pressing = True
                            #print("[COMBAT] Đã khóa mục tiêu -> Đang Bem!")
                    else:
                        # Thấy quái nhưng không thấy UI thanh máu/tên -> Nhả chuột
                        if self.is_pressing:
                            pydirectinput.mouseUp(button='left')
                            self.is_pressing = False
                else:
                    # Không còn quái (threat == 0) -> Chắc chắn phải nhả chuột
                    if self.is_pressing:
                        pydirectinput.mouseUp(button='left')
                        self.is_pressing = False
                # --- PHẦN 2: LOGIC TỰ ĐỘNG BƠM MÁU ---
                if hp < threshold:
                    if time.time() - last_potion_time > 2.0:
                        pydirectinput.press('space') # Phím bơm máu mặc định
                        last_potion_time = time.time()
                        #print(f"\n[ACTION] Low HP ({hp:.1f}%) -> Bơm máu!")
                        self.voice.speak('Cấp cứu..Bơm máu!')
                # 2. Logic kiểm tra Hotkey/Combo
                self.hotkey_sys.run_check()

            time.sleep(0.02)

    def run(self):
        # Khởi động các luồng làm việc trước
        threads = [
            threading.Thread(target=self.sensor_worker, daemon=True),
            threading.Thread(target=self.action_worker, daemon=True)
        ]
        for t in threads: t.start()

        print("=== SACRED GOD BOT ACTIVE ===")
        print("- Phím 'V': Bật/Tắt Bot")
        print("- Phím 'ESC': Thoát chương trình")

        while not self.exit_event.is_set():
            # Kiểm tra và duy trì kết nối Game
            if not self.game_connected:
                self.is_running = False # Dừng logic nếu mất game
                self.game_connected = self.connect_game()
                if not self.game_connected:
                    print("Đang tìm Sacred.exe...", end='\r')
                    time.sleep(2)
                    continue

            # Xử lý phím Toggle từ người dùng
            if keyboard.is_pressed('v'):
                self.is_running = not self.is_running
                winsound.Beep(1000 if self.is_running else 500, 200)
                status = "ON" if self.is_running else "OFF"
                print(f"\n[SYSTEM] Trạng thái Bot: {status}")
                time.sleep(0.4)

            if keyboard.is_pressed('esc'):
                self.exit_event.set()
                print("\n[SYSTEM] Đang thoát...")

            time.sleep(0.1)

if __name__ == "__main__":
    bot = SacredBot()
    bot.run()
