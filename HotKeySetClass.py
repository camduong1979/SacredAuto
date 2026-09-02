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

    def reload_config(self, config):
        """[NEW 2026-09-01] Nạp nóng cấu hình mới từ sacred_config.json khi bật bot."""
        self.cfg = config or {}
        self.combos = self.cfg.get('combos', [])
        self._key_states = {}
        print(f"[HOTKEY] Đã nạp lại {len(self.combos)} bộ combo.")

    def release_all_inputs(self):
        """[NEW 2026-08-16] Xả toàn bộ phím và chuột để tạo Clean State,
        tránh xung đột khi người chơi đang đè giữ chuột/phím di chuyển hoặc đánh thường.
        """
        pydirectinput.mouseUp(button='left')
        pydirectinput.mouseUp(button='right')
        pydirectinput.keyUp('shift')

    def press_key(self, key):
        """[NEW 2026-09-01] Public API: Nhấn phím trực tiếp bằng direct input chuẩn"""
        pydirectinput.press(key)

    def _press_key(self, key):
        """Nhấn phím trực tiếp bằng direct input chuẩn"""
        self.press_key(key)

    def execute_step(self, step):
        """[NEW 2026-08-30] Thực thi 1 bước hành động đơn lẻ (dùng cho Step-by-Step Guarded Execution)."""
        action = step.get('action', 'press')
        key    = step.get('key', '')
        wait   = step.get('wait', 0.05)

        if action == 'press':
            self.press_key(key)
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

        if wait > 0:
            time.sleep(wait)

    def _run_sequence(self, sequence):
        """[NEW 2026-08-30] Thực thi chuỗi hành động của combo trên một Clean State bằng execute_step."""
        # 1. Giải phóng sạch mọi nút đang bị giữ
        self.release_all_inputs()
        time.sleep(0.01)

        # 2. Thực thi từng bước hành động
        for step in sequence:
            self.execute_step(step)

    def execute_sequence(self, sequence):
        """[NEW 2026-08-11] Public API: Thực thi chuỗi hành động bất kỳ (cho Auto Buff System)"""
        self._run_sequence(sequence)

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
        """[NEW 2026-09-01] Kiểm tra phím người dùng — rising edge & falling edge detection.
        on_trigger: callback tùy chọn để thông báo tên combo vừa kích hoạt cho HUD.
        """
        if not self.cfg.get('enabled', True):
            return

        for combo in self.combos:
            trigger_key = str(combo.get('trigger_key', '')).strip().lower()

            if not trigger_key or trigger_key in ['none', 'null', 'false', '']:
                continue

            is_down  = keyboard.is_pressed(trigger_key)
            was_down = self._key_states.get(trigger_key, False)

            # 1. Rising edge: kích hoạt khi phím vừa được nhấn xuống
            if is_down and not was_down:
                if on_trigger:
                    on_trigger(combo['name'])
                self._run_sequence(combo.get('sequence', []))

            # 2. Falling edge: kích hoạt khi nhả phím (hỗ trợ hold combo Z/X)
            elif not is_down and was_down:
                on_release = combo.get('on_release', [])
                if on_release:
                    for step in on_release:
                        self.execute_step(step)

            self._key_states[trigger_key] = is_down