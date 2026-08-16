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
        # --- QUẢN LÝ TRẠNG THÁI CHIẾN ĐẤU (State Management) ---
        self.is_in_combat = False       # Đang đánh nhau hay không?
        self.safe_timer = 0             # Bộ đếm thời gian an toàn để xác nhận hết quái
        self.last_speak_time = 0        # Thời điểm nói gần nhất để chống spam

        # [MỚI] Biến theo dõi số lượng quái vòng lặp trước
        self.last_enemy_count = 0

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
            self.voice.speak('Úm ba la xì bùa, tìm thấy game rồi nha. Vào việc thôi đại ca ơi!')
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
        """Luồng thực thi: Logic đếm số lượng quái thông minh"""
        last_potion_time = 0
        self.is_pressing = False
        
        while not self.exit_event.is_set():
            if self.game_connected and self.is_running:
                # 1. Lấy dữ liệu
                hp = self.shared_data['hp_percent']
                threat = self.shared_data.get('threat_level', 0)
                threshold = self.config['potion_system']['threshold_percent']
                current_time = time.time()

                # [MỚI] Tính số lượng quái dựa trên Threat (100 threat = 1 quái)
                # Dùng int() để làm tròn, ví dụ 190 vẫn tính là 1 con, 200 là 2 con
                current_enemy_count = int(threat / 100)

                # --- LOGIC 1: QUẢN LÝ TRẠNG THÁI CHIẾN ĐẤU ---
                
                # TRƯỜNG HỢP A: ĐANG CÓ QUÁI
                if current_enemy_count > 0:
                    self.safe_timer = 0 # Reset bộ đếm an toàn

                    # 1. Nếu mới bắt đầu vào Combat (trước đó chưa đánh)
                    if not self.is_in_combat:
                        if current_time - self.last_speak_time > 2.0:
                            msg = f"Có {current_enemy_count} địch."
                            print(f"[COMBAT START] {msg}")
                            self.voice.speak(msg)
                            self.last_speak_time = current_time
                        
                        self.is_in_combat = True
                        self.last_enemy_count = current_enemy_count # Lưu lại số lượng ban đầu

                    # 2. Nếu đang đánh mà số lượng quái TĂNG LÊN (Viện binh tới)
                    elif current_enemy_count > self.last_enemy_count:
                        # Chỉ báo nếu chưa vừa nói xong (tránh spam khi threat nhảy loạn)
                        if current_time - self.last_speak_time > 2.0:
                            msg = f"Thêm {current_enemy_count} địch."
                            print(f"[WARNING] {msg}")
                            self.voice.speak(msg)
                            self.last_speak_time = current_time
                        
                        self.last_enemy_count = current_enemy_count # Cập nhật mốc mới

                    # 3. Nếu số lượng quái GIẢM ĐI (Đã tiêu diệt bớt)
                    elif current_enemy_count < self.last_enemy_count:
                        # Im lặng, chỉ cập nhật lại số lượng để bot biết
                        # print(f"[UPDATE] Đã diệt địch. Còn: {current_enemy_count}")
                        self.last_enemy_count = current_enemy_count

                # # TRƯỜNG HỢP B: KHÔNG CÓ QUÁI (Threat < 100 hoặc = 0)
                # else:
                #     if self.is_in_combat:
                #         self.safe_timer += 1
                #         # Chờ khoảng 1.5 giây (75 loops) để chắc chắn sạch quái
                #         if self.safe_timer > 75: 
                #             print("[COMBAT END] An toàn.")
                #             self.voice.speak('Quét sạch kẻ thù. Loot đồ lẹ đi rồi mình đi tiếp!') 
                #             self.is_in_combat = False
                #             self.safe_timer = 0
                #             self.last_enemy_count = 0
                
                    # 3. Địch chết bớt (Số lượng giảm)
                    elif current_enemy_count < self.last_enemy_count:
                        # Chỉ cập nhật mốc, im lặng cho đại ca tập trung bem tiếp
                        self.last_enemy_count = current_enemy_count

                # TRƯỜNG HỢP B: QUÉT SẠCH CHIẾN TRƯỜNG
                else:
                    if self.is_in_combat:
                        self.safe_timer += 1
                        # Đợi 1.5 giây xác nhận quái chết hẳn
                        if self.safe_timer > 75: 
                            msg = "An toàn rồi."
                            print("[COMBAT END] An toàn.")
                            self.voice.speak(msg) 
                            
                            self.is_in_combat = False
                            self.safe_timer = 0
                            self.last_enemy_count = 0

                # --- LOGIC 2: HÀNH ĐỘNG BEM (Giữ nguyên) ---
                if self.is_in_combat and threat > 0:
                    if self.radar and self.radar.is_target_detected():
                        if not self.is_pressing:
                            pydirectinput.mouseDown(button='left')
                            self.is_pressing = True
                    else:
                        if self.is_pressing:
                            pydirectinput.mouseUp(button='left')
                            self.is_pressing = False
                else:
                    if self.is_pressing:
                        pydirectinput.mouseUp(button='left')
                        self.is_pressing = False

                # --- LOGIC 3: BƠM MÁU ---
                if hp < threshold:
                    if current_time - last_potion_time > 0.8:
                        pydirectinput.press('space')
                        last_potion_time = current_time
                        if current_time - self.last_speak_time > 3.0:
                            self.voice.speak('Cấp cứu, bơm máu.')
                            self.last_speak_time = current_time

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
                # winsound.Beep(1000 if self.is_running else 500, 200)
                # status = "ON" if self.is_running else "OFF"
                # self.voice.speak('Tao mở máy rồi mày sẵn sàng chưa?')
                # print(f"\n[SYSTEM] Trạng thái Bot: {status}")
                winsound.Beep(1000 if self.is_running else 500, 200)
                if self.is_running:
                    self.voice.speak('Hệ thống bot đã bật.')
                else:
                    self.voice.speak('Bot nghỉ ngơi tí đây.')
                time.sleep(0.4)

            if keyboard.is_pressed('esc'):
                self.exit_event.set()
                print("\n[SYSTEM] Đang thoát...")

            time.sleep(0.1)

if __name__ == "__main__":
    bot = SacredBot()
    bot.run()
