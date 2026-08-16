import keyboard
import pydirectinput
import time
# ================= MODULE 5: HỆ THỐNG HOTKEY (MACRO) =================
class HotKeySystem:
    def __init__(self, config):
        self.cfg = config
        self.combos = config.get('combos', [])
        # --- KHỞI TẠO BIẾN TRẠNG THÁI ---
        #self.d_pressing = False # Quan trọng: Khai báo để không bị lỗi AttributeError
        print(f"[HOTKEY] Đã load {len(self.combos)} bộ combo.")

    def run_check(self):
        if not self.cfg['enabled']: return
        # # --- XỬ LÝ RIÊNG PHÍM D (HOLD TO MOUSE DOWN) ---
        # if keyboard.is_pressed('d'):
        #     if not self.d_pressing:
        #         pydirectinput.mouseDown(button='left')
        #         self.d_pressing = True
        #         print("[MACRO] Đang đè chuột trái (D hold)")
        # else:
        #     if self.d_pressing:
        #         pydirectinput.mouseUp(button='left')
        #         self.d_pressing = False
        #         print("[MACRO] Đã nhả chuột trái (D release)")

        for combo in self.combos:
            # Kiểm tra xem phím kích hoạt có được nhấn không
            if keyboard.is_pressed(combo['trigger_key']):
                print(f"[MACRO] Kích hoạt: {combo['name']}")
                
                # Thực hiện chuỗi hành động
                for step in combo['sequence']:
                    action = step.get('action', 'press')
                    key = step['key']
                    wait = step.get('wait', 0.05)

                    if action == 'press':
                        pydirectinput.press(key)
                    elif action == 'click_right':
                        pydirectinput.click(button='right')
                    elif action == 'click_left':
                        pydirectinput.click(button='left')
                    
                    time.sleep(wait)
                
                # Chống lặp (Chờ người dùng thả phím ra mới cho bấm tiếp)
                while keyboard.is_pressed(combo['trigger_key']):
                    time.sleep(0.05)