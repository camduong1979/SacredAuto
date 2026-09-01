import time
import mss
import numpy as np


class BuffScheduler:
    """
    [NEW 2026-09-01] Bộ điều phối Buff tự động độc lập (SOLID - Single Responsibility).
    Vai trò:
      - Quản lý danh sách buff với timer interval độc lập cho từng skill (không bị chồng nghẽn).
      - Hỗ trợ phân nhánh 'only_in_combat': chỉ buff khi trong giao tranh hoặc buff tự do.
      - Quy trình thi triển an toàn:
          Gate Timer -> Chọn phím buff (Select) -> Kiểm tra sẵn sàng (Ready Check)
          -> Click chuột phải (Cast) -> Trả về phím chính (Restore) -> Cập nhật Timer.
      - Loại bỏ hoàn toàn Post-Cast Verification gây delay/nhiễu.
    """

    def __init__(self, buff_config: dict, hotkey_sys, cooldown_hook=None, combat_state=None):
        self.cfg = buff_config or {}
        self.enabled = self.cfg.get('enabled', False)
        self.hotkey_sys = hotkey_sys
        self.cooldown_hook = cooldown_hook
        self.combat_state = combat_state
        self.sct = None  # Lazy init trong thread worker

        # [NEW 2026-09-01] Global Cooldown (GCD) & Deferral Parameters
        self.stagger_delay = self.cfg.get('stagger_delay_ms', 800) / 1000.0
        self.defer_delay = self.cfg.get('defer_delay_ms', 300) / 1000.0
        self.max_wait_timeout = self.cfg.get('max_wait_timeout_s', 5.0)
        self.last_successful_cast_time = 0.0

        self.buffs = self._init_buffs(self.cfg.get('buffs', []))
        print(f"[BUFF SCHEDULER] {'BẬT' if self.enabled else 'TẮT'} — Đã nạp {len(self.buffs)} loại buff (GCD Stagger: {self.stagger_delay*1000:.0f}ms).")

    # --- OLD CODE (REPLACED: _init_buffs cũ thiếu state deferral và pending timer) ---
    # def _init_buffs(self, raw_buffs: list) -> list:
    #     buffs = []
    #     for b in raw_buffs:
    #         buff_id = b.get('id', 'unknown')
    #         mode = b.get('mode', 'visual' if 'co' in buff_id else 'memory')
    #         buffs.append({
    #             'id': buff_id,
    #             'name': b.get('name', 'Buff'),
    #             'enabled': b.get('enabled', False),
    #             'only_in_combat': b.get('only_in_combat', True),
    #             'mode': mode,
    #             'interval': b.get('interval', 30),
    #             'max_retries': b.get('max_retries', 3),
    #             'use_memory': b.get('use_memory', (mode == 'memory')),
    #             'sentinel_enabled': b.get('sentinel_enabled', (mode == 'visual')),
    #             'sentinel_x': b.get('sentinel_x', 0),
    #             'sentinel_y': b.get('sentinel_y', 0),
    #             'tolerance_rgb': b.get('tolerance_rgb', 1),
    #             'min_brightness': b.get('min_brightness', 14),
    #             'max_brightness': b.get('max_brightness', 177),
    #             'sequence': b.get('sequence', []),
    #             'last_cast_time': 0.0,
    #             'retry_count': 0
    #         })
    #     return buffs
    # ----------------------------------------------------------------------------------

    def _init_buffs(self, raw_buffs: list) -> list:
        buffs = []
        for b in raw_buffs:
            buff_id = b.get('id', 'unknown')
            mode = b.get('mode', 'visual' if 'co' in buff_id else 'memory')
            buffs.append({
                'id': buff_id,
                'name': b.get('name', 'Buff'),
                'enabled': b.get('enabled', False),
                'only_in_combat': b.get('only_in_combat', True),  # Mặc định chỉ buff khi có quái
                'mode': mode,  # 'visual' hoặc 'memory'
                'interval': b.get('interval', 30),
                'max_retries': b.get('max_retries', 3),
                'use_memory': b.get('use_memory', (mode == 'memory')),
                'sentinel_enabled': b.get('sentinel_enabled', (mode == 'visual')),
                'sentinel_x': b.get('sentinel_x', 0),
                'sentinel_y': b.get('sentinel_y', 0),
                'tolerance_rgb': b.get('tolerance_rgb', 1),
                'min_brightness': b.get('min_brightness', 14),
                'max_brightness': b.get('max_brightness', 177),
                'sequence': b.get('sequence', []),
                'last_cast_time': 0.0,
                'retry_count': 0,
                'state': 'IDLE',            # 'IDLE' hoặc 'PENDING_RETRY'
                'pending_since': 0.0,       # Thời điểm bắt đầu rơi vào PENDING_RETRY
                'next_eval_time': 0.0       # Mốc thời gian được phép kiểm tra lại
            })
        return buffs

    # --- OLD CODE (REPLACED: reset_all_timers cũ chỉ reset last_cast_time và retry_count) ---
    # def reset_all_timers(self):
    #     """Reset toàn bộ mốc thời gian và retry khi bật bot."""
    #     for b in self.buffs:
    #         b['last_cast_time'] = 0.0
    #         b['retry_count'] = 0
    # ---------------------------------------------------------------------------------------

    def reset_all_timers(self):
        """[NEW 2026-09-01] Reset toàn bộ mốc thời gian, GCD Stagger và trạng thái Deferral khi bật bot."""
        self.last_successful_cast_time = 0.0
        for b in self.buffs:
            b['last_cast_time'] = 0.0
            b['retry_count'] = 0
            b['state'] = 'IDLE'
            b['pending_since'] = 0.0
            b['next_eval_time'] = 0.0

    def reload_config(self, buff_config: dict):
        """[NEW 2026-09-01] Nạp nóng cấu hình mới từ sacred_config.json khi bật bot."""
        self.cfg = buff_config or {}
        self.enabled = self.cfg.get('enabled', False)
        self.stagger_delay = self.cfg.get('stagger_delay_ms', 800) / 1000.0
        self.defer_delay = self.cfg.get('defer_delay_ms', 300) / 1000.0
        self.max_wait_timeout = self.cfg.get('max_wait_timeout_s', 5.0)
        self.buffs = self._init_buffs(self.cfg.get('buffs', []))
        self.reset_all_timers()
        print(f"[BUFF SCHEDULER] Đã nạp lại cấu hình ({len(self.buffs)} buffs, Stagger: {self.stagger_delay*1000:.0f}ms).")

    def is_buff_ready(self, buff) -> bool:
        """
        Kiểm tra trạng thái sẵn sàng của skill:
        1. Mode 'memory': Đọc Cooldown Memory Hook (00562B13).
           - Cooldown <= 0.001 -> Sẵn sàng (True)
           - Cooldown > 0.001 -> Đang hồi chiêu (False)
        2. Mode 'visual': Soi màu RGB pixel icon (Visual Sentinel).
           - Thoát khỏi phổ xám đen -> Sẵn sàng (True)
           - Rơi vào phổ xám đen -> Đang hồi chiêu / casting (False)
        """
        mode = buff.get('mode', 'memory' if buff.get('use_memory', False) else 'visual')

        # 1. KIỂM TRA BẰNG MEMORY COOLDOWN HOOK
        if mode == 'memory' or buff.get('use_memory', False):
            if self.cooldown_hook and getattr(self.cooldown_hook, 'is_hooked', False):
                cd_val = self.cooldown_hook.get_cooldown()
                if cd_val is not None:
                    return cd_val <= 0.001
            # Fallback nếu hook chưa sẵn sàng
            if not buff.get('sentinel_enabled', False):
                return True

        # 2. KIỂM TRA BẰNG VISUAL SENTINEL
        if not buff.get('sentinel_enabled', True):
            return True

        x = buff.get('sentinel_x', 0)
        y = buff.get('sentinel_y', 0)
        if x <= 0 or y <= 0:
            return True

        try:
            if self.sct is None:
                self.sct = mss.mss()

            bbox = {'top': y, 'left': x, 'width': 1, 'height': 1}
            img = np.array(self.sct.grab(bbox))
            pixel = img[0, 0]
            b_val, g_val, r_val = int(pixel[0]), int(pixel[1]), int(pixel[2])

            tol = buff.get('tolerance_rgb', 1)
            min_b = buff.get('min_brightness', 14)
            max_b = buff.get('max_brightness', 177)

            is_equal_rgb = (abs(r_val - g_val) <= tol) and (abs(g_val - b_val) <= tol) and (abs(r_val - b_val) <= tol)
            avg_brightness = (r_val + g_val + b_val) / 3.0
            is_dark_range = min_b <= avg_brightness <= max_b
            is_casting = is_equal_rgb and is_dark_range

            return not is_casting
        except Exception:
            self.sct = None
            return True

    # --- OLD CODE (REPLACED: tick v1.0 thiếu GCD Stagger, Deferral Queue và làm block loop) ---
    # def tick(self, is_in_combat: bool, on_event=None):
    #     """
    #     Gọi mỗi 20ms từ action_worker.
    #     on_event(str): callback nhận thông điệp HUD khi thi triển buff.
    #     """
    #     if not self.enabled:
    #         return
    #
    #     now = time.time()
    #
    #     for buff in self.buffs:
    #         if not buff.get('enabled', False):
    #             continue
    #
    #         # GATE 1: Combat Gatekeeper
    #         if buff.get('only_in_combat', True) and not is_in_combat:
    #             continue
    #
    #         # GATE 2: Interval Timer Gatekeeper
    #         if (now - buff['last_cast_time']) < buff.get('interval', 30):
    #             continue
    #
    #         sequence = buff.get('sequence', [])
    #         if not sequence:
    #             continue
    #
    #         buff_name = buff.get('name', 'Buff')
    #
    #         # Nếu sequence là dạng chuẩn 3 bước: [select_step, cast_step, restore_steps...]
    #         if len(sequence) >= 3:
    #             select_step = sequence[0]
    #             cast_step = sequence[1]
    #             restore_steps = sequence[2:]
    #
    #             # BƯỚC 1: Chọn phím skill buff (Select)
    #             self.hotkey_sys.execute_step(select_step)
    #             time.sleep(0.04)  # Nghỉ ngắn để game cập nhật state
    #
    #             # BƯỚC 2: Kiểm tra sẵn sàng (Pre-Cast Ready Check)
    #             if not self.is_buff_ready(buff):
    #                 # Skill chưa sẵn sàng -> Trả về phím chính ngay, không click chuột
    #                 for step in restore_steps:
    #                     self.hotkey_sys.execute_step(step)
    #
    #                 buff['retry_count'] += 1
    #                 max_retries = buff.get('max_retries', 3)
    #                 if buff['retry_count'] >= max_retries:
    #                     buff['last_cast_time'] = now  # Bỏ qua chu kỳ này
    #                     buff['retry_count'] = 0
    #                     if on_event:
    #                         on_event(f"Buff {buff_name}: Missed")
    #                 continue
    #
    #             # BƯỚC 3: Thi triển skill (Cast)
    #             self.hotkey_sys.execute_step(cast_step)
    #
    #             # BƯỚC 4: Khôi phục về phím chính (Restore)
    #             for step in restore_steps:
    #                 self.hotkey_sys.execute_step(step)
    #
    #             # BƯỚC 5: Cập nhật hoàn tất
    #             buff['last_cast_time'] = now
    #             buff['retry_count'] = 0
    #             if on_event:
    #                 on_event(f"Buff {buff_name}: OK")
    #
    #         else:
    #             # Fallback cho sequence tự do
    #             self.hotkey_sys.execute_sequence(sequence)
    #             buff['last_cast_time'] = now
    #             buff['retry_count'] = 0
    #             if on_event:
    #                 on_event(f"Buff {buff_name}: OK")
    # -------------------------------------------------------------------------------------------

    def tick(self, is_in_combat: bool, on_event=None):
        """
        [NEW 2026-09-01] Vòng lặp điều phối Buff tự động với GCD Stagger & Deferral Logic.
        Được gọi độc lập từ buff_worker (50ms).
        on_event(str): callback nhận thông điệp HUD khi thi triển buff.
        """
        if not self.enabled:
            return

        now = time.time()

        # GATE 0: Global Cooldown (GCD) Stagger Gatekeeper
        # Tránh thi triển 2 buff quá sát nhau làm xung đột animation và cooldown game
        if (now - self.last_successful_cast_time) < self.stagger_delay:
            return

        for buff in self.buffs:
            if not buff.get('enabled', False):
                continue

            buff_name = buff.get('name', 'Buff')

            # GATE 1: Combat Gatekeeper
            if buff.get('only_in_combat', True) and not is_in_combat:
                if buff['state'] == 'PENDING_RETRY':
                    buff['state'] = 'IDLE'
                    buff['pending_since'] = 0.0
                    buff['next_eval_time'] = 0.0
                continue

            # GATE 2: Interval Timer & Deferral State Gatekeeper
            if buff['state'] == 'PENDING_RETRY':
                # Đang chờ re-check do bận animation/cooldown
                if now < buff['next_eval_time']:
                    continue

                # Nếu chờ quá thời gian tối đa -> Xác nhận Missed thực sự
                if (now - buff['pending_since']) > self.max_wait_timeout:
                    buff['state'] = 'IDLE'
                    buff['pending_since'] = 0.0
                    buff['next_eval_time'] = 0.0
                    buff['last_cast_time'] = now
                    buff['retry_count'] = 0
                    if on_event:
                        on_event(f"Buff {buff_name}: Missed")
                    continue
            else:
                # Trạng thái bình thường: kiểm tra chu kỳ interval
                if (now - buff['last_cast_time']) < buff.get('interval', 30):
                    continue

            sequence = buff.get('sequence', [])
            if not sequence:
                continue

            # [NEW 2026-09-01] PRE-BUFF CLEAN STATE: Đánh dấu is_buffing và xả toàn bộ phím/chuột
            if self.combat_state:
                self.combat_state.is_buffing = True
            self.hotkey_sys.release_all_inputs()
            time.sleep(0.02)

            # Nếu sequence là dạng chuẩn 3 bước: [select_step, cast_step, restore_steps...]
            if len(sequence) >= 3:
                select_step = sequence[0]
                cast_step = sequence[1]
                restore_steps = sequence[2:]

                # BƯỚC 1: Chọn phím skill buff (Select)
                self.hotkey_sys.execute_step(select_step)
                time.sleep(0.04)  # Nghỉ ngắn để game cập nhật state

                # BƯỚC 2: Kiểm tra sẵn sàng (Pre-Cast Ready Check)
                if not self.is_buff_ready(buff):
                    # Skill chưa sẵn sàng -> Trả về phím chính ngay, không click chuột
                    for step in restore_steps:
                        self.hotkey_sys.execute_step(step)

                    # Kết thúc lượt can thiệp Buff để trả quyền điều khiển lại cho targeting_worker
                    if self.combat_state:
                        self.combat_state.is_buffing = False

                    # Chuyển sang trạng thái PENDING_RETRY với defer_delay
                    if buff['state'] != 'PENDING_RETRY':
                        buff['state'] = 'PENDING_RETRY'
                        buff['pending_since'] = now

                    buff['next_eval_time'] = now + self.defer_delay
                    buff['retry_count'] += 1
                    continue

                # BƯỚC 3: Thi triển skill (Cast)
                self.hotkey_sys.execute_step(cast_step)

                # BƯỚC 4: Khôi phục về phím chính (Restore)
                for step in restore_steps:
                    self.hotkey_sys.execute_step(step)

                # BƯỚC 5: Cập nhật hoàn tất & Kích hoạt GCD Stagger
                buff['last_cast_time'] = now
                buff['state'] = 'IDLE'
                buff['pending_since'] = 0.0
                buff['next_eval_time'] = 0.0
                buff['retry_count'] = 0
                self.last_successful_cast_time = now

                # Kết thúc lượt Buff thành công
                if self.combat_state:
                    self.combat_state.is_buffing = False

                if on_event:
                    on_event(f"Buff {buff_name}: OK")

                # Thoát vòng lặp ngay sau khi thi triển 1 buff để kích hoạt GCD Stagger
                break

            else:
                # Fallback cho sequence tự do
                self.hotkey_sys.execute_sequence(sequence)
                buff['last_cast_time'] = now
                buff['state'] = 'IDLE'
                buff['pending_since'] = 0.0
                buff['next_eval_time'] = 0.0
                buff['retry_count'] = 0
                self.last_successful_cast_time = now

                if self.combat_state:
                    self.combat_state.is_buffing = False

                if on_event:
                    on_event(f"Buff {buff_name}: OK")
                break
