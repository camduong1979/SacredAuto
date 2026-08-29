# 📜 CHANGELOG & ROLLBACK GUIDE: YOLO TARGETING & COMBAT RADAR LOCK

> **Ngày tạo:** 2026-08-21  
> **File ảnh hưởng:** `Sacred_yolo.py`, `YOLOManagerClass.py`  
> **Trạng thái:** Đã cập nhật & Hoàn tất  

---

## 1. Vấn đề phát hiện & Nguyên nhân (Root Cause Analysis)

### 📌 Hiện tượng thực tế:
- Khi bật chế độ YOLO (`Z`), YOLO chụp ảnh và nhận diện quái, di chuyển chuột đến mục tiêu.
- Khi chuột trỏ vào quái, **CombatRadar** đã nhận diện dải màu thanh máu (`is_target_detected() == True`) và tiến hành đè chuột tấn công (`mouseDown`).
- **Tuy nhiên:** YOLO vẫn liên tục nhảy quét mục tiêu ở mỗi frame (`~30-50 FPS`), dẫn đến tình trạng chuột bị giật, rung hoặc nhảy sang quái khác xung quanh ngay cả khi quái hiện tại chưa chết.

### 🔍 Nguyên nhân trong mã nguồn:
1. Trong `YOLOManagerClass.py`, hệ thống đã xây dựng sẵn 2 trạng thái:
   - **SEARCHING:** Quét toàn bộ quái và chọn con gần tâm màn hình nhất.
   - **TRACKING (LOCK):** Bám sát duy nhất 1 con quái trong bán kính `TRACKING_RADIUS` (160px).
   - Hàm `confirm_lock(target_pos)` có nhiệm vụ chuyển trạng thái từ **SEARCHING ➔ TRACKING**.
2. Trong `Sacred_yolo.py`, vòng lặp `yolo_worker` sau khi `radar.is_target_detected()` xác nhận đúng quái thì **chưa bao giờ gọi `self.ai_sys.confirm_lock(target_pos)`**.
3. Do `self.locked_target` luôn là `None`, `YOLOManager` bị kẹt vĩnh viễn ở trạng thái **SEARCHING**, liên tục tính lại khoảng cách tâm và nhảy mục tiêu ở mọi frame.

---

## 2. Chi tiết thay đổi (Changes Applied)

### File: `Sacred_yolo.py`

#### A. Khối Toggle X (Tắt YOLO) & Guard State
- **Bổ sung:** Khi bấm `X` tắt YOLO hoặc khi Bot bị tạm dừng, gọi `self.ai_sys.reset_lock()` để giải phóng mục tiêu bị khóa.

#### B. Khối Xử lý YOLO Detect + Radar Confirm (`yolo_worker`)
- **Bổ sung:** Khi `self.radar.is_target_detected() == True` ➔ Gọi `self.ai_sys.confirm_lock(target_pos)` để kích hoạt chế độ **TRACKING**.
- **Bổ sung:** Khi Radar không còn phát hiện thanh máu (quái chết/chạy mất) hoặc khi mất target ➔ Gọi `self.ai_sys.reset_lock()` và nhả chuột `mouseUp`.

---

## 3. So sánh Code Trước & Sau (Before / After)

```python
# ==============================================================================
# BEFORE (CODE CŨ)
# ==============================================================================
try:
    target_pos = self.ai_sys.get_best_target(debug=True)

    if target_pos:
        tx, ty = target_pos
        pydirectinput.moveTo(tx, ty, _pause=False)

        if self.radar.is_target_detected():     # Thanh HP xác nhận → BEM
            if not self.is_pressing:
                pydirectinput.mouseDown(button='left')
                self.is_pressing = True
        else:                                   # Radar fail → nhả tay
            if self.is_pressing:
                pydirectinput.mouseUp(button='left')
                self.is_pressing = False
    else:                                       # Mất target → nhả tay
        if self.is_pressing:
            pydirectinput.mouseUp(button='left')
            self.is_pressing = False

except Exception as e:
    print(f"\n[YOLO ERROR] {e}")
    if self.is_pressing:
        pydirectinput.mouseUp(button='left')
        self.is_pressing = False
```

```python
# ==============================================================================
# AFTER (CODE MỚI ĐÃ CẬP NHẬT)
# ==============================================================================
try:
    target_pos = self.ai_sys.get_best_target(debug=True)

    if target_pos:
        tx, ty = target_pos
        pydirectinput.moveTo(tx, ty, _pause=False)

        if self.radar.is_target_detected():     # Thanh HP xác nhận → BEM & KHÓA MỤC TIÊU
            self.ai_sys.confirm_lock(target_pos) # Kích hoạt trạng thái TRACKING trong YOLO
            if not self.is_pressing:
                pydirectinput.mouseDown(button='left')
                self.is_pressing = True
        else:                                   # Radar fail (quái chết / mất máu) → Hủy khóa & nhả tay
            self.ai_sys.reset_lock()
            if self.is_pressing:
                pydirectinput.mouseUp(button='left')
                self.is_pressing = False
    else:                                       # Mất target → Hủy khóa & nhả tay
        self.ai_sys.reset_lock()
        if self.is_pressing:
            pydirectinput.mouseUp(button='left')
            self.is_pressing = False

except Exception as e:
    print(f"\n[YOLO ERROR] {e}")
    if self.ai_sys:
        self.ai_sys.reset_lock()
    if self.is_pressing:
        pydirectinput.mouseUp(button='left')
        self.is_pressing = False
```

---

## 4. Hướng dẫn hoàn tác (Rollback Instructions)

Nếu bạn muốn quay lại trạng thái code ban đầu vì bất kỳ lý do gì:

1. Mở file `Sacred_yolo.py`.
2. Tìm đến khối comment:
   ```python
   # --- OLD CODE (REPLACED) ---
   # ...
   # ---------------------------
   ```
3. Xóa khối code mới nằm ngay dưới và bỏ comment (`# `) cho khối code cũ.
4. Lưu file và khởi động lại bot.
