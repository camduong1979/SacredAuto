import cv2
import numpy as np
import mss
import time
from ultralytics import YOLO

class YOLOManager:
    def __init__(self, config):
        self.cfg = config['ai_system']
        self.model = YOLO(self.cfg['model_path']).to('cuda')
        self.sct = None 
        self.size = self.cfg['scan_size']
        self.roi = {
            "top": self.cfg['center_y'] - (self.size // 2),
            "left": self.cfg['center_x'] - (self.size // 2),
            "width": self.size,
            "height": self.size
        }
        self.mid = self.size // 2
        self.safe_w = self.cfg['safe_box_w']
        self.safe_h = self.cfg['safe_box_h']

        # --- BIẾN QUẢN LÝ LOCK MỤC TIÊU ---
        self.locked_target = None       # Tọa độ (x, y) màn hình của mục tiêu đang lock
        self.lost_frames = 0            # Số frame liên tiếp bị mất dấu quái đang lock
        self.MAX_LOST_FRAMES = 5        # Mất dấu quá 5 frame (~0.1s) sẽ unlock
        self.TRACKING_RADIUS = 160      # Bán kính (pixel) tìm quái cũ (mở rộng để chịu camera cuộn)
        self.lock_start_time = 0        # Mốc thời gian bắt đầu lock
        self.MAX_LOCK_DURATION = 6.0    # Khóa tối đa 6 giây (tránh kẹt)
        self.ignored_targets = []       # Danh sách đen tạm thời các quái vừa bị Untrack

    def reset_lock(self):
        """Hủy khóa mục tiêu"""
        self.locked_target = None
        self.lost_frames = 0
        self.lock_start_time = 0

    def confirm_lock(self, target_pos):
        """Kích hoạt LOCK khi Radar xác nhận đúng là quái (có thanh máu)"""
        self.locked_target = target_pos
        self.lost_frames = 0
        self.lock_start_time = time.time()

    def ignore_current_target(self, duration=3.0):
        """Đưa mục tiêu hiện tại vào danh sách đen trong `duration` giây và hủy Lock"""
        if self.locked_target:
            self.ignored_targets.append({
                'pos': self.locked_target,
                'expire': time.time() + duration
            })
        self.reset_lock()

    def get_best_target(self, debug=False):
        """Quét quái và trả về tọa độ. Nếu debug=True sẽ hiển thị cửa sổ soi."""
        if self.sct is None:
            self.sct = mss.mss()

        try:
            sct_img = self.sct.grab(self.roi)
            img = np.array(sct_img)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            results = self.model(img, device='cuda', stream=True, conf=self.cfg['conf'], verbose=False)
            
            now = time.time()

            # 1. Dọn dẹp các quái đã hết hạn trong danh sách đen (Ignored targets)
            self.ignored_targets = [item for item in self.ignored_targets if now < item['expire']]

            valid_boxes = []

            # Vẽ Safe Box lên ảnh debug
            if debug:
                cv2.rectangle(img, (self.mid - self.safe_w//2, self.mid - self.safe_h//2), 
                              (self.mid + self.safe_w//2, self.mid + self.safe_h//2), (255, 255, 0), 1)

            for r in results:
                for box in r.boxes:
                    label = self.model.names[int(box.cls[0])]
                    conf = float(box.conf[0])
                    if label not in self.cfg['target_classes']: continue

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                    tx = x1 + self.roi['left'] + ((x2 - x1) // 2)
                    ty = y1 + self.roi['top'] + ((y2 - y1) // 2)

                    # Bỏ qua nếu mục tiêu này đang nằm trong Danh sách đen (Ignored Targets - bấm phím d)
                    is_ignored = False
                    for ig in self.ignored_targets:
                        ig_x, ig_y = ig['pos']
                        if ((tx - ig_x)**2 + (ty - ig_y)**2)**0.5 < 100:
                            is_ignored = True
                            break
                    if is_ignored: continue

                    # Kiểm tra Safe Box (Loại bỏ vị trí nhân vật)
                    is_self = (self.mid - self.safe_w//2 < mx < self.mid + self.safe_w//2) and \
                              (self.mid - self.safe_h//2 < my < self.mid + self.safe_h//2)

                    # NÂNG CẤP SAFE BOX: Nếu quái này khớp với quái đang LOCK (đang áp sát đánh cận chiến),
                    # Bỏ qua giới hạn Safe Box để không bị mất lock khi quái tiến sát vào người!
                    if is_self and self.locked_target:
                        lx, ly = self.locked_target
                        if ((tx - lx)**2 + (ty - ly)**2)**0.5 < self.TRACKING_RADIUS:
                            is_self = False

                    if debug:
                        color = (255, 255, 255) if is_self else (0, 0, 255)
                        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(img, f"{label} {conf:.2f}", (x1, y1-10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                    if is_self: continue

                    valid_boxes.append({'screen_pos': (tx, ty), 'roi_pos': (mx, my)})

            # 2. XỬ LÝ KHÓA MỤC TIÊU (TARGET LOCK & TRACKING LOGIC)
            target_to_return = None

            # Kiểm tra hết hạn lock (Timeout)
            if self.locked_target and (now - self.lock_start_time > self.MAX_LOCK_DURATION):
                self.reset_lock()

            if self.locked_target:
                # TRẠNG THÁI: TRACKING (Theo dấu mục tiêu đang lock trong bán kính TRACKING_RADIUS)
                lx, ly = self.locked_target
                best_match = None
                min_track_dist = 9999

                for b in valid_boxes:
                    tx, ty = b['screen_pos']
                    dist = ((tx - lx)**2 + (ty - ly)**2)**0.5
                    if dist < self.TRACKING_RADIUS and dist < min_track_dist:
                        min_track_dist = dist
                        best_match = (tx, ty)

                if best_match:
                    self.locked_target = best_match
                    self.lost_frames = 0
                    target_to_return = best_match
                else:
                    self.lost_frames += 1
                    if self.lost_frames > self.MAX_LOST_FRAMES:
                        self.reset_lock()
                    # KHẮC PHỤC KẸT CHUỘT: Khi không thấy quái ở frame hiện tại, KHÔNG trả về tọa độ cũ nữa!
                    # Trả về None để bot lập tức nhả chuột, tránh bị ghì chuột vào điểm khoảng không.
                    target_to_return = None
            else:
                # TRẠNG THÁI: SEARCHING (Chưa lock, tìm mục tiêu gần tâm màn hình nhất)
                min_dist = 9999
                for b in valid_boxes:
                    mx, my = b['roi_pos']
                    dist = ((mx - self.mid)**2 + (my - self.mid)**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        target_to_return = b['screen_pos']

            if debug:
                if self.locked_target:
                    lx_roi = self.locked_target[0] - self.roi['left']
                    ly_roi = self.locked_target[1] - self.roi['top']
                    cv2.circle(img, (lx_roi, ly_roi), 8, (0, 255, 0), -1)
                    cv2.putText(img, "LOCKED", (lx_roi-20, ly_roi-15), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("Sacred AI Debug", img)
                cv2.waitKey(1) # Cần thiết để OpenCV cập nhật cửa sổ

            return target_to_return
        except:
            self.sct = None
            return None
