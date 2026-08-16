# # import cv2
# # import numpy as np
# # import mss
# # import pydirectinput
# # import keyboard
# # from ultralytics import YOLO
# # import time

# # # --- CẤU HÌNH ---
# # CX, CY = 958, 542
# # SIZE = 400
# # ROI = {"top": CY - (SIZE//2), "left": CX - (SIZE//2), "width": SIZE, "height": SIZE}

# # # VÙNG AN TOÀN (Không tự click vào mình - Khoảng 60x60 px ở giữa ROI)
# # SAFE_ZONE_SIZE = 60 

# # TARGET_CLASSES = ['person', 'dog', 'sheep', 'bird', 'cat', 'horse']

# # def run_final_test():
# #     # Ép sử dụng GPU 1 (Quadro)
# #     model = YOLO('yolov8n.pt').to('cuda')
# #     sct = mss.mss()
    
# #     print(f"--- DEBUG AI FINAL (GPU: QUADRO T2000) ---")
# #     print("AI sẽ bỏ qua bản thân nhân vật ở giữa màn hình.")

# #     while True:
# #         if cv2.waitKey(1) & 0xFF == ord('q'): break

# #         if keyboard.is_pressed('shift'):
# #             sct_img = sct.grab(ROI)
# #             img = np.array(sct_img)
# #             img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# #             results = model(img, device='cuda', stream=True, conf=0.4, verbose=False)

# #             for r in results:
# #                 for box in r.boxes:
# #                     class_id = int(box.cls[0])
# #                     label = model.names[class_id]

# #                     if label not in TARGET_CLASSES: continue

# #                     # Tọa độ local trong vùng ROI
# #                     x1, y1, x2, y2 = map(int, box.xyxy[0])
# #                     mid_x = (x1 + x2) // 2
# #                     mid_y = (y1 + y2) // 2

# #                     # KIỂM TRA VÙNG AN TOÀN:
# #                     # Tâm của ROI là (200, 200). Nếu quái nằm quá gần tâm -> Bỏ qua
# #                     dist_to_center = np.sqrt((mid_x - 200)**2 + (mid_y - 200)**2)
# #                     if dist_to_center < (SAFE_ZONE_SIZE // 2):
# #                         # Vẽ vòng tròn trắng đánh dấu bản thân để debug
# #                         cv2.circle(img, (mid_x, mid_y), 30, (255, 255, 255), 2)
# #                         continue

# #                     # Nếu vượt qua các lớp lọc -> Xác định tọa độ Global
# #                     target_x = x1 + ROI['left'] + ((x2 - x1) // 2)
# #                     target_y = y1 + ROI['top'] + ((y2 - y1) // 2)

# #                     # Vẽ mục tiêu thực sự (Màu đỏ)
# #                     cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
# #                     pydirectinput.moveTo(target_x, target_y, _pause=False)
# #                     break 
            
# #             cv2.imshow("Final Filter Test", img)
# #         else:
# #             time.sleep(0.05)

# #     cv2.destroyAllWindows()

# # if __name__ == "__main__":
# #     run_final_test()
# import cv2
# import numpy as np
# import mss
# import pydirectinput
# import keyboard
# import time
# from ultralytics import YOLO

# # --- CẤU HÌNH TÂM MÀN HÌNH CỦA BẠN ---
# CX, CY = 958, 542
# SIZE = 400
# ROI = {"top": CY - (SIZE//2), "left": CX - (SIZE//2), "width": SIZE, "height": SIZE}

# # Vùng an toàn để không tự click vào mình
# SAFE_ZONE_SIZE = 80 
# TARGET_CLASSES = ['person', 'dog', 'sheep', 'bird', 'cat', 'horse']

# def run_final_debug():
#     # Load model vào GPU 1 (Quadro T2000)
#     model = YOLO('yolov8n.pt').to('cuda')
#     sct = mss.mss()
    
#     print(f"--- DEBUG AI VIEW (GPU: {model.device}) ---")
#     print("Cửa sổ Preview sẽ luôn hiện. Giữ SHIFT để Bot chiếm quyền chuột.")

#     while True:
#         # 1. Luôn luôn chụp màn hình để hiện Preview
#         sct_img = sct.grab(ROI)
#         img = np.array(sct_img)
#         img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

#         # Vẽ tâm màn hình (Dấu cộng) để xác nhận Center CX, CY
#         cv2.line(img, (200, 190), (200, 210), (255, 255, 255), 1)
#         cv2.line(img, (190, 200), (210, 200), (255, 255, 255), 1)
#         # Vẽ vòng tròn an toàn (Safe Zone)
#         cv2.circle(img, (200, 200), SAFE_ZONE_SIZE // 2, (255, 255, 0), 1)

#         # 2. Chỉ xử lý Logic AI và Chuột khi giữ SHIFT
#         if keyboard.is_pressed('shift'):
#             results = model(img, device='cuda', stream=True, conf=0.4, verbose=False)

#             for r in results:
#                 for box in r.boxes:
#                     class_id = int(box.cls[0])
#                     label = model.names[class_id]

#                     if label not in TARGET_CLASSES: continue

#                     x1, y1, x2, y2 = map(int, box.xyxy[0])
#                     mid_x = (x1 + x2) // 2
#                     mid_y = (y1 + y2) // 2

#                     # Kiểm tra khoảng cách tới tâm (200, 200 trong ROI)
#                     dist = np.sqrt((mid_x - 200)**2 + (mid_y - 200)**2)
                    
#                     if dist < (SAFE_ZONE_SIZE // 2):
#                         # Đây là chính mình (WoodElf)
#                         cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 1)
#                         continue

#                     # Mục tiêu hợp lệ (Vẽ màu đỏ)
#                     cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
#                     cv2.putText(img, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

#                     # Điều khiển chuột
#                     target_x = x1 + ROI['left'] + ((x2 - x1) // 2)
#                     target_y = y1 + ROI['top'] + ((y2 - y1) // 2)
#                     pydirectinput.moveTo(target_x, target_y, _pause=False)
#                     break 

#         # 3. LUÔN HIỂN THỊ CỬA SỔ (Để debug liên tục)
#         cv2.imshow("Sacred AI - ROI Monitor", img)
        
#         # Thoát khi nhấn Q
#         if cv2.waitKey(1) & 0xFF == ord('q'):
#             break

#     cv2.destroyAllWindows()

# if __name__ == "__main__":
#     run_final_debug()
# v3
import cv2
import numpy as np
import mss
import pydirectinput
import keyboard
import time
from ultralytics import YOLO

# --- TỌA ĐỘ CHUẨN CỦA BẠN ---
CX, CY = 958, 550
SIZE = 600
ROI = {"top": CY - (SIZE//2), "left": CX - (SIZE//2), "width": SIZE, "height": SIZE}

# --- CẤU HÌNH VÙNG AN TOÀN HÌNH HỘP (SAFE BOX) ---
# Điều chỉnh rộng/cao để vừa khít nhân vật của bạn trong cửa sổ Preview
SAFE_W = 100  # Độ rộng che nhân vật
SAFE_H = 180  # Độ cao che nhân vật (nhân vật đứng nên cao hơn rộng)

TARGET_CLASSES = ['creep', 'scopes','person', 'dog', 'sheep', 'bird', 'cat', 'horse']

def run_ai_v3():
    model = YOLO(r'D:\PyProject\SacredAuto\runs\detect\train6\weights\best.pt').to('cuda') # Chạy trên GPU 1 (Quadro)
    sct = mss.mss()
    
    print(f"--- AI MONITOR V3 (ANTI-SELF TARGETING) ---")
    print("Sử dụng Safe Box để loại bỏ hoàn toàn việc nhận diện nhầm chính mình.")

    while True:
        sct_img = sct.grab(ROI)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # 1. Vẽ Vùng An Toàn (Safe Box) màu vàng để bạn căn chỉnh
        mid = SIZE // 2
        x_safe1, y_safe1 = mid - (SAFE_W // 2), mid - (SAFE_H // 2)
        x_safe2, y_safe2 = mid + (SAFE_W // 2), mid + (SAFE_H // 2)
        cv2.rectangle(img, (x_safe1, y_safe1), (x_safe2, y_safe2), (0, 255, 255), 2)
        cv2.putText(img, "SAFE ZONE", (x_safe1, y_safe1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        # 2. Logic AI
        if keyboard.is_pressed('shift'):
            results = model(img, device='cuda', stream=True, conf=0.4, verbose=False)

            # for r in results:
            #     for box in r.boxes:
            #         class_id = int(box.cls[0])
            #         label = model.names[class_id]
            #         if label not in TARGET_CLASSES: continue

            #         x1, y1, x2, y2 = map(int, box.xyxy[0])
            #         mx, my = (x1 + x2) // 2, (y1 + y2) // 2

            #         # THUẬT TOÁN LỌC: Nếu TÂM của đối tượng nằm trong SAFE BOX -> Bỏ qua
            #         if (x_safe1 < mx < x_safe2) and (y_safe1 < my < y_safe2):
            #             # Vẽ khung trắng cho chính mình để debug
            #             cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 1)
            #             continue

            #         # Nếu là mục tiêu hợp lệ (Nằm ngoài Safe Box)
            #         cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    
            #         tx = x1 + ROI['left'] + ((x2 - x1) // 2)
            #         ty = y1 + ROI['top'] + ((y2 - y1) // 2)
                    
            #         pydirectinput.moveTo(tx, ty, _pause=False)
            #         break 
            for r in results:
                for box in r.boxes:
                    class_id = int(box.cls[0])
                    label = model.names[class_id]
                    conf = float(box.conf[0]) # Lấy độ tự tin của AI
                    
                    if label not in TARGET_CLASSES: continue

                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                    
                    # Chuẩn bị nội dung chữ hiển thị (Ví dụ: "creep 85%")
                    display_text = f"{label} {conf:.2f}"

                    # THUẬT TOÁN LỌC: Nếu TÂM của đối tượng nằm trong SAFE BOX -> Bỏ qua
                    if (x_safe1 < mx < x_safe2) and (y_safe1 < my < y_safe2):
                        # Vẽ khung trắng và hiện tên cho chính mình (để debug)
                        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 1)
                        cv2.putText(img, f"SELF: {display_text}", (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        continue

                    # Nếu là mục tiêu hợp lệ (Nằm ngoài Safe Box)
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    
                    # --- HIỂN THỊ TÊN VÀ ĐỘ TỰ TIN LÊN MÀN HÌNH ---
                    cv2.putText(img, display_text, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
                    tx = x1 + ROI['left'] + ((x2 - x1) // 2)
                    ty = y1 + ROI['top'] + ((y2 - y1) // 2)
                    
                    pydirectinput.moveTo(tx, ty, _pause=False)
                    break

        cv2.imshow("Sacred AI - Safe Box Monitor", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_ai_v3()