import sys
import json
import time
import threading
import winsound
import keyboard

from VoiceAssistant import VoiceAssistant
from CombatStateManager import CombatStateManager
from PotionPump import PotionPump
from BuffScheduler import BuffScheduler


class BotEngine:
    """
    [NEW 2026-09-01] Core Backend Base Class cho toàn bộ hệ thống Bot (SOLID - Dependency Inversion & Open/Closed).
    Vai trò:
      - Quản lý vòng đời hệ thống (Lifecycle, Threads, Toggle, Exit).
      - Thread sensor_worker: Đọc Memory liên tục (HP, Threat, Monster IDs, Hover ID) -> shared_data.
      - Thread action_worker: Điều phối Combat State, Buff Scheduler, Potion Pump, HotKey System, Single-line HUD.
      - Tách biệt hoàn toàn phần Targeting để các Subclass (Melee Memory / YOLO AI) tự định nghĩa.
    """

    def __init__(self):
        self.config = self.load_config()
        self.voice = VoiceAssistant()

        # Quản lý kết nối & trạng thái
        self.pm = None
        self.module_addr = None
        self.game_connected = False
        self.is_running = False
        self.exit_event = threading.Event()
        self._data_lock = threading.Lock()

        # Shared data thread-safe
        self.shared_data = {
            'hp_percent': 100.0,
            'threat_level': 0,
            'monster_ids': set(),
            'hover_id': 0
        }

        # Sub-systems (Khởi tạo chi tiết trong connect_game của subclass)
        self.potion_sys = None
        self.danger_sys = None
        self.cooldown_hook = None
        self.hotkey_sys = None
        self.combat_state = None
        self.potion_pump = None
        self.buff_scheduler = None

        # HUD display state
        self.last_event_msg = "Sẵn sàng"
        self.last_hud_print_time = 0.0

    def load_config(self) -> dict:
        """Nạp file cấu hình sacred_config.json."""
        try:
            with open('sacred_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Không thể load config: {e}")
            return {}

    def print_hud(self, hp: float, threat: int, target_str: str = "None"):
        """In trạng thái trực tiếp trên 1 dòng duy nhất (Single-line Live HUD)."""
        now = time.time()
        if now - self.last_hud_print_time < 0.2:
            return
        self.last_hud_print_time = now

        clean_msg = self.last_event_msg.replace("\r", "").replace("\n", " ").strip()
        event_short = (clean_msg[:18] + "..") if len(clean_msg) > 20 else clean_msg

        hud_line = f"\rHP: {hp:5.1f}% | Target: {target_str:<12} | {event_short}\033[K"
        sys.stdout.write(hud_line)
        sys.stdout.flush()

    # ------------------------------------------------------------------ #
    #  ABSTRACT METHODS — Subclass bắt buộc phải override                #
    # ------------------------------------------------------------------ #
    def connect_game(self) -> bool:
        """Subclass kết nối pymem và khởi tạo các sub-systems."""
        raise NotImplementedError("Subclass phải implement connect_game()")

    def targeting_worker(self):
        """Subclass định nghĩa luồng nhận diện và khóa mục tiêu riêng."""
        raise NotImplementedError("Subclass phải implement targeting_worker()")

    # ------------------------------------------------------------------ #
    #  CORE WORKERS (Chạy nền độc lập)                                   #
    # ------------------------------------------------------------------ #
    def sensor_worker(self):
        """Luồng đọc Memory liên tục (50ms): HP, Threat, Monster IDs, Hover ID."""
        while not self.exit_event.is_set():
            if self.game_connected and self.is_running:
                try:
                    hp = self.potion_sys.get_hp_percent() if self.potion_sys else 100.0
                    threat = self.danger_sys.get_threat_level() if self.danger_sys else 0
                    monster_ids = self.danger_sys.get_monster_ids(max_monsters=15) if self.danger_sys else set()
                    hover_id = self.danger_sys.get_mouse_hover_id() if self.danger_sys else 0

                    with self._data_lock:
                        self.shared_data['hp_percent'] = hp if hp is not None else 100.0
                        self.shared_data['threat_level'] = threat
                        self.shared_data['monster_ids'] = monster_ids
                        self.shared_data['hover_id'] = hover_id
                except Exception as e:
                    print(f"\n[SENSOR ERROR] Mất kết nối game: {e}")
                    self.game_connected = False
            time.sleep(0.05)

    def action_worker(self):
        """Luồng thực thi chính (20ms): Combat State -> Buff Scheduler -> Potion Pump -> HotKey."""
        while not self.exit_event.is_set():
            if not (self.game_connected and self.is_running):
                time.sleep(0.1)
                continue

            with self._data_lock:
                hp = self.shared_data['hp_percent']
                threat = self.shared_data['threat_level']

            # 1. Cập nhật Trạng thái Chiến đấu (Combat State Manager)
            if self.combat_state:
                events = self.combat_state.tick(threat)
                if events.get('combat_started'):
                    self.last_event_msg = "Có quái"
                elif events.get('cleared'):
                    self.last_event_msg = "Clear"

            # --- OLD CODE (REPLACED: BuffScheduler chạy đồng bộ trong action_worker làm nghẽn Potion & Hotkey) ---
            # # 2. Điều phối Buff Tự động Độc lập (Buff Scheduler)
            # is_in_combat = self.combat_state.is_in_combat if self.combat_state else (threat > 0)
            # if self.buff_scheduler:
            #     self.buff_scheduler.tick(
            #         is_in_combat=is_in_combat,
            #         on_event=lambda msg: setattr(self, 'last_event_msg', msg)
            #     )
            # ------------------------------------------------------------------------------------------------------

            # 2. Tự động Bơm máu (Potion Pump - Phản hồi khẩn cấp tức thì)
            if self.potion_pump:
                if self.potion_pump.tick(hp):
                    self.last_event_msg = "Bom mau"

            # 3. Kiểm tra Hotkey Macro người dùng
            if self.hotkey_sys:
                self.hotkey_sys.run_check(
                    on_trigger=lambda name: setattr(self, 'last_event_msg', f"Combo: {name}")
                )

            # 4. Cập nhật Live HUD
            target_str = "None"
            if self.combat_state and self.combat_state.target_detected:
                target_str = f"LOCK:{self.combat_state.target_locked_id}"

            self.print_hud(hp, threat, target_str)

            time.sleep(0.02)

    def buff_worker(self):
        """
        [NEW 2026-09-01] Luồng Buff tự động chạy nền chuyên biệt (Dedicated Buff Thread).
        Tách rời hoàn toàn khỏi action_worker để đảm bảo PotionPump và HotKey phản hồi tức thì (non-blocking).
        Polling rate: 50ms.
        """
        while not self.exit_event.is_set():
            if not (self.game_connected and self.is_running):
                time.sleep(0.1)
                continue

            with self._data_lock:
                threat = self.shared_data['threat_level']

            is_in_combat = self.combat_state.is_in_combat if self.combat_state else (threat > 0)

            if self.buff_scheduler:
                self.buff_scheduler.tick(
                    is_in_combat=is_in_combat,
                    on_event=lambda msg: setattr(self, 'last_event_msg', msg)
                )

            time.sleep(0.05)

    def reload_all_configs(self):
        """[NEW 2026-09-01] Nạp lại sacred_config.json và đồng bộ sang tất cả các sub-systems khi bật Bot."""
        new_cfg = self.load_config()
        if not new_cfg:
            return
        self.config = new_cfg

        # 1. Hot-update HotKeySystem
        if self.hotkey_sys and hasattr(self.hotkey_sys, 'reload_config'):
            self.hotkey_sys.reload_config(self.config.get('hotkey_system', {}))

        # 2. Hot-update PotionPump
        if self.potion_pump and hasattr(self.potion_pump, 'reload_config'):
            self.potion_pump.reload_config(self.config.get('potion_system', {}))

        # 3. Hot-update BuffScheduler
        if self.buff_scheduler and hasattr(self.buff_scheduler, 'reload_config'):
            self.buff_scheduler.reload_config(self.config.get('auto_buff_system', {}))

    # ------------------------------------------------------------------ #
    #  RUN — Khởi chạy vòng lặp điều khiển chính                         #
    # ------------------------------------------------------------------ #
    def run(self):
        threads = [
            threading.Thread(target=self.sensor_worker, daemon=True, name="SensorWorker"),
            threading.Thread(target=self.action_worker, daemon=True, name="ActionWorker"),
            threading.Thread(target=self.buff_worker, daemon=True, name="BuffWorker"),
            threading.Thread(target=self.targeting_worker, daemon=True, name="TargetingWorker"),
        ]
        for t in threads:
            t.start()

        print("=== SACRED BOT ENGINE ACTIVE ===")
        try:
            while not self.exit_event.is_set():
                if not self.game_connected:
                    self.is_running = False
                    self.game_connected = self.connect_game()
                    if not self.game_connected:
                        time.sleep(2)
                        continue

                toggle_key = self.config.get('global', {}).get('toggle_key', 'd')
                if keyboard.is_pressed(toggle_key):
                    self.is_running = not self.is_running
                    winsound.Beep(1000 if self.is_running else 500, 200)

                    # --- OLD CODE (REPLACED: chỉ reset timers cũ, không nạp lại config) ---
                    # if self.is_running:
                    #     if self.buff_scheduler:
                    #         self.buff_scheduler.reset_all_timers()
                    #     self.last_event_msg = "Bot đã bật"
                    # -----------------------------------------------------------------------

                    if self.is_running:
                        # [NEW 2026-09-01] Tự động nạp nóng toàn bộ config mới nhất từ file JSON khi bật bot
                        self.reload_all_configs()
                        self.last_event_msg = "Bot đã bật"
                    else:
                        # Nhả target và phím khi tắt bot
                        if self.combat_state:
                            self.combat_state.release_target()
                        if self.hotkey_sys:
                            self.hotkey_sys.release_all_inputs()
                        self.last_event_msg = "Bot nghỉ ngơi"

                    status_msg = 'Bot đã bật.' if self.is_running else 'Bot nghỉ ngơi.'
                    self.voice.speak(status_msg)
                    time.sleep(0.4)  # Debounce

                if keyboard.is_pressed('esc'):
                    self.exit_event.set()
                time.sleep(0.1)

        finally:
            if self.cooldown_hook and getattr(self.cooldown_hook, 'is_hooked', False):
                self.cooldown_hook.uninstall()
            if self.hotkey_sys:
                self.hotkey_sys.release_all_inputs()
