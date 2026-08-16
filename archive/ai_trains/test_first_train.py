from ultralytics import YOLO
import cv2

# 1. Load bộ não vừa train xong
model = YOLO(r'D:\PyProject\SacredAuto\runs\detect\train6\weights\best.pt')

# 2. Đưa một tấm ảnh game mới (chưa từng train) vào xem nó đoán thế nào
results = model.predict(source='anh_game_moi.jpg', save=True, conf=0.5)

# 3. Hiển thị kết quả
for r in results:
    im_array = r.plot()  # Vẽ khung lên ảnh
    cv2.imshow('AI nhin Sacred', im_array)
    cv2.waitKey(0)