import keyboard
import pydirectinput
import time

# ================= MODULE: HỆ THỐNG HOTKEY (MACRO) =================
class HotKeySystem:
    def __init__(self, config):
        self.cfg = config
        self.combos = config.get('combos', [])
        self._key_states = {}   # Trạng thái phím trước đó để detect rising edge
        print(f"[HOTKEY] Đã load {len(self.combos)} bộ combo.")

    # --- OLD CODE (REPLACED) ---
    # def _press_key(self, key):
    #     """Nhấn phím an toàn: keyUp trước để tránh stuck key"""
    #     pydirectinput.keyUp(key)
    #     pydirectinput.keyDown(key)
    #     time.sleep(0.03)
    #     pydirectinput.keyUp(key)
    #
    # def _run_sequence(self, sequence):
    #     """Thực thi chuỗi hành động của một combo"""
    #     for step in sequence:
    #         action = step.get('action', 'press')
    #         key    = step.get('key', '')
    #         wait   = step.get('wait', 0.1)
    #
    #         if action == 'press':
    #             self._press_key(key)
    #         # --- [CHANGELOG 2026-08-15] OLD: click_right và click_left hard-code time.sleep(0.08) ---
    #         # elif action == 'click_right':
    #         #     pydirectinput.mouseUp(button='right')
    #         #     pydirectinput.mouseDown(button='right')
    #         #     time.sleep(0.08)  # Tăng lên 0.08s để game Sacred nhận 100% tín hiệu click chuột
    #         #     pydirectinput.mouseUp(button='right')
    #         # elif action == 'click_left':
    #         #     pydirectinput.mouseUp(button='left')
    #         #     pydirectinput.mouseDown(button='left')
    #         #     time.sleep(0.08)  # Tăng lên 0.08s để tránh miss click chuột trái
    #         #     pydirectinput.mouseUp(button='left')
    #         # --- [END OLD] ---
    #
    #         # [NEW 2026-08-15] Hỗ trợ tham số hold tùy chỉnh (mặc định 0.20s Sweet Spot) và các action chuột mở rộng
    #         elif action == 'click_right':
    #             hold = step.get('hold', 0.20)  # Mặc định giữ chuột 0.20s (Sweet Spot) để engine Sacred nhận diện 100%
    #             pydirectinput.mouseUp(button='right')
    #             pydirectinput.mouseDown(button='right')
    #             time.sleep(hold)
    #             pydirectinput.mouseUp(button='right')
    #         elif action == 'click_left':
    #             hold = step.get('hold', 0.20)
    #             pydirectinput.mouseUp(button='left')
    #             pydirectinput.mouseDown(button='left')
    #             time.sleep(hold)
    #             pydirectinput.mouseUp(button='left')
    #         elif action in ['right_down', 'mouse_down_right']:
    #             pydirectinput.mouseDown(button='right')
    #         elif action in ['right_up', 'mouse_up_right']:
    #             pydirectinput.mouseUp(button='right')
    #         elif action in ['left_down', 'mouse_down_left']:
    #             pydirectinput.mouseDown(button='left')
    #         elif action in ['left_up', 'mouse_up_left']:
    #             pydirectinput.mouseUp(button='left')
    #         
    #         time.sleep(wait)
    # ---------------------------

    def release_all_inputs(self):
        """[NEW 2026-08-16] Xả toàn bộ phím và chuột để tạo Clean State,
        tránh xung đột khi người chơi đang đè giữ chuột/phím di chuyển hoặc đánh thường.
        """
        pydirectinput.mouseUp(button='left')
        pydirectinput.mouseUp(button='right')
        pydirectinput.keyUp('shift')

    def _press_key(self, key):
        """Nhấn phím trực tiếp bằng direct input chuẩn"""
        pydirectinput.press(key)

    def _run_sequence(self, sequence):
        """[NEW 2026-08-16] Thực thi chuỗi hành động của combo trên một Clean State.
        Mặc định dùng direct click/press, hỗ trợ hold tùy chỉnh nếu cần gồng chiêu.
        """
        # 1. Giải phóng sạch mọi nút đang bị giữ
        self.release_all_inputs()
        time.sleep(0.01)

        # 2. Thực thi chuỗi hành động
        for step in sequence:
            action = step.get('action', 'press')
            key    = step.get('key', '')
            wait   = step.get('wait', 0.05)

            if action == 'press':
                self._press_key(key)
            elif action == 'click_right':
                hold = step.get('hold', 0)
                if hold > 0:
                    pydirectinput.mouseDown(button='right')
                    time.sleep(hold)
                    pydirectinput.mouseUp(button='right')
                else:
                    pydirectinput.rightClick()
            elif action == 'click_left':
                hold = step.get('hold', 0)
                if hold > 0:
                    pydirectinput.mouseDown(button='left')
                    time.sleep(hold)
                    pydirectinput.mouseUp(button='left')
                else:
                    pydirectinput.click()
            elif action in ['right_down', 'mouse_down_right']:
                pydirectinput.mouseDown(button='right')
            elif action in ['right_up', 'mouse_up_right']:
                pydirectinput.mouseUp(button='right')
            elif action in ['left_down', 'mouse_down_left']:
                pydirectinput.mouseDown(button='left')
            elif action in ['left_up', 'mouse_up_left']:
                pydirectinput.mouseUp(button='left')
            
            time.sleep(wait)

    def execute_sequence(self, sequence):
        """[NEW 2026-08-11] Public API: Thực thi chuỗi hành động bất kỳ (cho Auto Buff System)"""
        self._run_sequence(sequence)

    # --- OLD CODE (REPLACED) ---
    # def run_combo(self, combo_name):
    #     """Kích hoạt combo theo tên trực tiếp từ bot"""
    #     if not self.cfg.get('enabled', True):
    #         return False
    #
    #     for combo in self.combos:
    #         if combo.get('name') == combo_name:
    #             print(f"[MACRO] Bot kích hoạt: {combo_name}")
    #             self._run_sequence(combo['sequence'])
    #             return True
    #
    #     print(f"[HOTKEY] Không tìm thấy combo: {combo_name}")
    #     return False
    #
    # def run_check(self):
    #     """Kiểm tra phím người dùng — dùng edge detection để không blocking action_worker"""
    #     if not self.cfg.get('enabled', True):
    #         return
    #
    #     for combo in self.combos:
    #         # Lấy trigger_key và chuyển về chữ thường để so sánh an toàn
    #         trigger_key = str(combo.get('trigger_key', '')).strip().lower()
    #
    #         # Bỏ qua nếu phím không hợp lệ
    #         if not trigger_key or trigger_key in ['none', 'null', 'false', '']:
    #             continue
    #
    #         is_down  = keyboard.is_pressed(trigger_key)
    #         was_down = self._key_states.get(trigger_key, False)
    #
    #         # Rising edge: chỉ kích hoạt 1 lần khi phím vừa được nhấn xuống
    #         if is_down and not was_down:
    #             print(f"[MACRO] Kích hoạt: {combo['name']}")
    #             self._run_sequence(combo['sequence'])
    #
    #         self._key_states[trigger_key] = is_down
    # ---------------------------

    def run_combo(self, combo_name):
        """Kích hoạt combo theo tên trực tiếp từ bot"""
        if not self.cfg.get('enabled', True):
            return False

        for combo in self.combos:
            if combo.get('name') == combo_name:
                self._run_sequence(combo['sequence'])
                return True
        return False

    def run_check(self, on_trigger=None):
        """Kiểm tra phím người dùng — dùng edge detection để không blocking action_worker.
        on_trigger: callback tùy chọn để thông báo tên combo vừa kích hoạt cho HUD.
        """
        if not self.cfg.get('enabled', True):
            return

        for combo in self.combos:
            # Lấy trigger_key và chuyển về chữ thường để so sánh an toàn
            trigger_key = str(combo.get('trigger_key', '')).strip().lower()

            # Bỏ qua nếu phím không hợp lệ
            if not trigger_key or trigger_key in ['none', 'null', 'false', '']:
                continue

            is_down  = keyboard.is_pressed(trigger_key)
            was_down = self._key_states.get(trigger_key, False)

            # Rising edge: chỉ kích hoạt 1 lần khi phím vừa được nhấn xuống
            if is_down and not was_down:
                if on_trigger:
                    on_trigger(combo['name'])
                self._run_sequence(combo['sequence'])

            self._key_states[trigger_key] = is_down