# import json
# import winsound
# import keyboard
# import pymem
# import pymem.process
# import time
# from AutoPotionClass import AutoPotion
# from HotKeySetClass import HotKeySystem

# class SacredBot:
#     def __init__(self):
#         self.config_file = 'sacred_config.json'
#         self.config = self.load_config()
#         self.auto_sense_enabled = False
#         self.pm = None
#         self.module_addr = None
#         self.init_done = False

#     def load_config(self):
#         with open(self.config_file, 'r', encoding='utf-8') as f: 
#             return json.load(f)

#     def connect_game(self):
#         try:
#             p_name = self.config['global']['process_name']
#             self.pm = pymem.Pymem(p_name)
           
#             self.module_addr = pymem.process.module_from_name(self.pm.process_handle, p_name).lpBaseOfDll
            
#             # Khởi tạo module con
#             self.potion_sys = AutoPotion(self.config['potion_system'], self.pm, self.module_addr)
#             self.hotkey_sys = HotKeySystem(self.config.get('hotkey_system', {'enabled': False}))
            
#             print(f"\n-> [OK] Connected! Base: {hex(self.module_addr)}")
#             self.init_done = True
#             return True
#         except:
#             print('error')
#             return False

#     def run(self):
#         print("--- SACRED GOD BOT (MODULE VERSION) ---")
#         if not self.connect_game():
#             print("Đang chờ Sacred.exe...")

#         while True:
#             if not self.init_done:
#                 if self.connect_game(): pass
#                 else: 
#                     time.sleep(1)
#                     continue

#             # Phím V để Bật/Tắt Potion
#             if keyboard.is_pressed(self.config['global']['toggle_key']):
#                 self.auto_sense_enabled = not self.auto_sense_enabled
#                 print(f"\n[SYSTEM] Auto Potion: {'ON' if self.auto_sense_enabled else 'OFF'}")
#                 winsound.Beep(1000 if self.auto_sense_enabled else 500, 200)
#                 time.sleep(0.4)

#             # Combo Q luôn chạy
#             self.hotkey_sys.run_check()

#             # Potion chạy khi ON
#             if self.auto_sense_enabled:
#                 self.potion_sys.run_check()

#             if keyboard.is_pressed('esc'): break
#             time.sleep(0.02)

# if __name__ == "__main__":
#     bot = SacredBot()
#     bot.run()

import json
import time
import keyboard
import pymem
import pymem.process
import pydirectinput
import winsound

# Import các Class đã module hóa
from AutoPotionClass import AutoPotion
from DangerSystemClass import DangerSystem
from HotKeySetClass import HotKeySystem 

class SacredBot:
    def __init__(self):
        # Config giờ chỉ còn chứa mấy cái như % bơm máu, phím tắt...
        self.config = self.load_config()
        self.pm = None
        self.module_addr = None
        self.init_done = False
        
        self.is_running = False
        self.combat_mode = False
        self.last_combat_time = 0 
        self.last_potion_time = 0

    def load_config(self):
        with open('sacred_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def connect_game(self):
        try:
            p_name = "sacred.exe" # Hard-code tên process luôn cho chắc
            self.pm = pymem.Pymem(p_name)
            self.module_addr = pymem.process.module_from_name(self.pm.process_handle, p_name).lpBaseOfDll
            
            # Khởi tạo module (Không cần truyền config địa chỉ nữa)
            self.potion_sys = AutoPotion(self.pm, self.module_addr)
            self.danger_sys = DangerSystem(self.pm, self.module_addr)
            self.hotkey_sys = HotKeySystem(self.config.get('hotkey_system'))
            
            print(f"\n-> [SYSTEM] Đã kết nối! Base: {hex(self.module_addr)}")
            self.init_done = True
            return True
        except:
            return False

    def logic_combat(self):
        # 1. Quét máu
        hp_percent = self.potion_sys.get_hp_percent()
        if hp_percent is not None:
            # Lấy ngưỡng bơm từ file config (JSON chỉ còn giữ số liệu setting)
            threshold = self.config['potion_system']['threshold_percent']
            
            if hp_percent < threshold:
                if time.time() - self.last_potion_time > 0.5:
                    pydirectinput.press('space') # Hard-code phím Space hoặc lấy từ config
                    self.last_potion_time = time.time()
                    print(f"\n[CẤP CỨU] HP: {hp_percent:.1f}% -> BƠM!")
            else:
                 print(f"[FIGHT] HP: {hp_percent:.1f}% | Threat: ĐỊCH!      ", end='\r')

        # 2. Hotkey
        self.hotkey_sys.run_check()

    def run(self):
        print("--- SACRED GOD BOT: OPTIMIZED ---")
        print("Nhấn 'V' để Bật/Tắt.")
        
        while True:
            if not self.init_done:
                if not self.connect_game():
                    time.sleep(2)
                    continue

            if keyboard.is_pressed('v'):
                self.is_running = not self.is_running
                print(f"\n[SYSTEM] Bot: {'ON' if self.is_running else 'OFF'}")
                winsound.Beep(1000 if self.is_running else 500, 200)
                time.sleep(0.4)

            if self.is_running:
                # Đọc Danger
                threat = self.danger_sys.get_threat_level()
                
                if threat > 0:
                    self.combat_mode = True
                    self.last_combat_time = time.time()
                    self.logic_combat()
                    time.sleep(0.01) # Quét nhanh khi combat
                else:
                    # Logic chờ 2s sau combat
                    if self.combat_mode:
                        elapsed = time.time() - self.last_combat_time
                        print(f"[WAIT] Hết địch... {2.0 - elapsed:.1f}s     ", end='\r')
                        if elapsed > 2.0:
                            print("\n[RELAX] Về chế độ nghỉ.")
                            self.combat_mode = False
                        self.logic_combat() # Vẫn bơm máu lúc chờ
                    else:
                        # Nghỉ ngơi
                        self.hotkey_sys.run_check()
                        time.sleep(0.1)

            if keyboard.is_pressed('esc'): break

if __name__ == "__main__":
    bot = SacredBot()
    bot.run()