import time
import pydirectinput


class PotionPump:
    """
    [NEW 2026-09-01] Tự động bơm máu khi HP dưới ngưỡng cấu hình.
    Tách khỏi action_worker để tái sử dụng ở mọi loại bot.

    Config keys dùng (từ section 'potion_system' trong sacred_config.json):
        threshold_percent (int)  — Ngưỡng % HP để kích hoạt bơm (mặc định 30)
        key              (str)  — Phím uống máu (mặc định 'space')
    """

    PUMP_COOLDOWN_SEC  = 0.8   # Thời gian chờ tối thiểu giữa 2 lần bơm (giây)
    VOICE_GUARD_SEC    = 3.0   # Thời gian chờ tối thiểu giữa 2 lần thông báo giọng nói

    def __init__(self, potion_config: dict, voice):
        self.threshold  = potion_config.get('threshold_percent', 30)
        self.key        = potion_config.get('key', 'space')
        self.voice      = voice
        self._last_pump  = 0.0
        self._last_speak = 0.0

    def reload_config(self, potion_config: dict):
        """[NEW 2026-09-01] Nạp nóng cấu hình mới từ sacred_config.json khi bật bot."""
        self.threshold = potion_config.get('threshold_percent', 30)
        self.key       = potion_config.get('key', 'space')

    # ------------------------------------------------------------------ #
    #  TICK — gọi mỗi 20ms từ BotEngine.action_worker()                   #
    # ------------------------------------------------------------------ #
    def tick(self, hp_percent: float) -> bool:
        """
        Kiểm tra HP và bơm máu nếu cần.

        Args:
            hp_percent: HP hiện tại (0–100)

        Returns:
            True nếu vừa bơm máu trong lần tick này, False nếu không.
        """
        now = time.time()

        if hp_percent < self.threshold and (now - self._last_pump) > self.PUMP_COOLDOWN_SEC:
            pydirectinput.press(self.key)
            self._last_pump = now

            # Thông báo giọng nói — chống spam
            if now - self._last_speak > self.VOICE_GUARD_SEC:
                self.voice.speak('Bơm máu!')
                self._last_speak = now

            return True

        return False
