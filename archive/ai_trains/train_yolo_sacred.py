from ultralytics import YOLO

if __name__ == '__main__':
    # 1. Load model gốc (nano - cực nhẹ cho máy)
    model = YOLO('yolov8n.pt') 

    # 2. Bắt đầu train
    model.train(
        data=r'D:\PyProject\SacredAuto\ai_trains\First_train\data.yaml', # Đường dẫn tuyệt đối đến file yaml
        epochs=100,      # Số vòng lặp (với 24 ảnh, 100 epoch là ổn)
        imgsz=640,       # Kích thước ảnh chuẩn
        device=0,        # Nếu không có card NVIDIA, hãy đổi 0 thành 'cpu'
        workers=2        # Số luồng xử lý (máy yếu nên để 2)
    )