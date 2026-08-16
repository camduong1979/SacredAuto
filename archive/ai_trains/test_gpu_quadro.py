import torch
import numpy as np
from ultralytics import YOLO
import time

def check_nvidia_power():
    print("--- KIỂM TRA HỆ THỐNG NVIDIA ---")
    # 1. Kiểm tra Torch có thấy CUDA không
    cuda_available = torch.cuda.is_available()
    print(f"[1] CUDA Available: {cuda_available}")
    
    if not cuda_available:
        print("[!] LỖI: Torch chưa nhận GPU. Hãy cài lại: pip install torch --index-url https://download.pytorch.org/whl/cu121")
        return

    # 2. Thông tin Card màn hình
    device_name = torch.cuda.get_device_name(0)
    print(f"[2] Card đồ họa phát hiện: {device_name}")

    # 3. Chạy thử AI trên GPU
    print("[3] Đang nạp Model vào VRAM của Quadro...")
    try:
        model = YOLO('yolov8n.pt').to('cuda') # Ép model lên GPU
        
        # Tạo một ảnh giả lập để AI "nhai" thử
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        
        start_time = time.time()
        for _ in range(10): # Chạy 10 lần để tính trung bình
            model(dummy_img, device='cuda', verbose=False)
        
        end_time = time.time()
        avg_speed = (end_time - start_time) / 10
        print(f"[OK] AI đang hoạt động trên GPU!")
        print(f"[SPEED] Tốc độ xử lý trung bình: {avg_speed*1000:.2f}ms / khung hình")
        
    except Exception as e:
        print(f"[!] Lỗi khi nạp GPU: {e}")

if __name__ == "__main__":
    check_nvidia_power()