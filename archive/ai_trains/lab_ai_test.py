import cv2
import numpy as np
import mss
import time
from ultralytics import YOLO

# --- CẤU HÌNH ---
# Dùng model mặc định trước để test code
MODEL_PATH = 'yolov8n.pt' 
# Tâm radar của bạn là 947, 790. Ta sẽ quét rộng ra xung quanh đó.
CENTER_X, CENTER_Y = 958, 542
WIDTH, HEIGHT = 800, 600 # Vùng quét 800x600 px
TOP = CENTER_Y - (HEIGHT // 2)
LEFT = CENTER_X - (WIDTH // 2)

REGION = {"top": TOP, "left": LEFT, "width": WIDTH, "height": HEIGHT}
# Vùng quét (Giống bước 2)
#REGION = {"top": 490, "left": 547, "width": 800, "height": 600} 

def run_ai_lab():
    # 1. Load Model
    print("Đang load YOLO... Chờ chút...")
    model = YOLO(MODEL_PATH)
    print("Load xong! Bắt đầu quét...")

    sct = mss.mss()
    
    # Biến tính FPS
    prev_time = 0
    
    while True:
        loop_start = time.time()
        
        # 2. Chụp ảnh
        sct_img = sct.grab(REGION)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) # Bắt buộc convert màu
        
        # 3. AI Nhận diện
        # conf=0.4: Độ tin cậy trên 40% mới lấy
        results = model(img, stream=True, conf=0.4, verbose=False)
        
        # 4. Vẽ khung lên ảnh để debug
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Lấy tọa độ
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Vẽ hình chữ nhật màu Xanh lá
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Hiển thị tên Class (Vd: person, horse...)
                cls = int(box.cls[0])
                label = f"{model.names[cls]} {float(box.conf):.2f}"
                cv2.putText(img, label, (x1, y1 - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 5. Tính FPS thực tế
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time)
        prev_time = curr_time
        
        cv2.putText(img, f"FPS: {int(fps)}", (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # 6. Show kết quả
        cv2.imshow("AI Debug Lab (Q to Quit)", img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_ai_lab()