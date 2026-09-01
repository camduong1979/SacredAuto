import time
import pydirectinput


class CombatStateManager:
    """
    [NEW 2026-09-01] Quản lý trạng thái chiến đấu tập trung.
    Vai trò:
      - Theo dõi threat để xác định is_in_combat
      - Đếm safe timer (3s mặc định) trước khi tuyên bố Clear
      - Lưu shared flags: target_detected, target_locked_id
        (được cập nhật bởi targeting_worker, đọc bởi action_worker)
    """

    def __init__(self, voice, safe_timeout: float = 3.0):
        self.voice       = voice
        self.safe_timeout = safe_timeout

        self.is_in_combat    = False
        self.safe_start_time = 0.0

        # Shared flags — targeting_worker ghi, action_worker và sensor_worker đọc
        self.target_detected   = False
        self.target_locked_id  = 0
        self.is_buffing        = False  # [NEW 2026-09-01] Cờ đánh dấu đang thi triển Buff (Clean State)

    # ------------------------------------------------------------------ #
    #  TICK — gọi mỗi 20ms từ BotEngine.action_worker()                   #
    # ------------------------------------------------------------------ #
    def tick(self, threat: int) -> dict:
        """
        Cập nhật trạng thái chiến đấu dựa trên threat level hiện tại.

        Returns:
            dict: {
                'combat_started': bool  — vừa chuyển vào COMBAT lần đầu,
                'cleared'       : bool  — vừa chuyển ra SAFE sau safe_timeout
            }
        """
        events = {'combat_started': False, 'cleared': False}
        now = time.time()

        if threat > 0:
            # Đang có quái: reset đồng hồ Safe, vào combat nếu chưa vào
            self.safe_start_time = 0.0
            if not self.is_in_combat:
                self.is_in_combat = True
                events['combat_started'] = True
                self.voice.speak('Có quái.')
        else:
            # Không có quái: bắt đầu / tiếp tục đếm Safe timer
            if self.is_in_combat:
                if self.safe_start_time == 0.0:
                    self.safe_start_time = now
                elif now - self.safe_start_time > self.safe_timeout:
                    # Đủ thời gian Safe → tuyên bố Clear
                    self.is_in_combat    = False
                    self.safe_start_time = 0.0
                    self.release_target()
                    pydirectinput.mouseUp(button='left')   # Nhả chuột trái nếu đang giữ
                    events['cleared'] = True
                    self.voice.speak('Clear.')

        return events

    # ------------------------------------------------------------------ #
    #  RELEASE TARGET                                                      #
    # ------------------------------------------------------------------ #
    def release_target(self):
        """
        Nhả cờ target_detected và target_locked_id về trạng thái rỗng.
        Gọi bởi:
          - targeting_worker: khi locked_id rời khỏi monster_ids (quái chết)
          - tick(): khi Safe timer hết (Clear)
        """
        self.target_detected  = False
        self.target_locked_id = 0
