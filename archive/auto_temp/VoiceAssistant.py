# # # import pyttsx3
# # # import threading

# # # class VoiceAssistant:
# # #     def __init__(self):
# # #         # Khởi tạo engine TTS
# # #         self.engine = pyttsx3.init()
        
# # #         # Cấu hình giọng nói
# # #         voices = self.engine.getProperty('voices')
# # #         # Thường voices[1] là giọng nữ, voices[0] là giọng nam
# # #         # Bạn có thể loop qua voices để tìm giọng tiếng Việt nếu Windows có cài
# # #         self.engine.setProperty('voice', voices[1].id) 
# # #         self.engine.setProperty('rate', 180) # Tốc độ nói (vừa phải)

# # #     def _say(self, text):
# # #         """Hàm nội bộ để thực hiện việc nói"""
# # #         try:
# # #             self.engine.say(text)
# # #             self.engine.runAndWait()
# # #         except Exception as e:
# # #             print(f"[VOICE ERROR] {e}")

# # #     def speak(self, text):
# # #         """Hàm công khai: Gọi hàm này để nói mà không gây lag Bot"""
# # #         threading.Thread(target=self._say, args=(text,), daemon=True).start()

# # # # --- Đoạn code Test nhanh ---
# # # if __name__ == "__main__":
# # #     va = VoiceAssistant()
# # #     print("Đang test âm thanh...")
# # #     va.speak("có địch ddđ")
# # #     # Giữ chương trình chạy đủ lâu để nghe thấy tiếng
# # #     import time
# # #     time.sleep(2)
# # import pyttsx3
# # import threading
# # import queue
# # import time

# # class VoiceAssistant:
# #     def __init__(self):
# #         self.msg_queue = queue.Queue()
# #         # Luồng xử lý âm thanh duy nhất chạy ngầm
# #         self.worker_thread = threading.Thread(target=self._voice_worker, daemon=True)
# #         self.worker_thread.start()

# #     def _voice_worker(self):
# #         """Hàm này chạy trong luồng riêng, chỉ lấy tin từ queue ra nói"""
# #         # Engine PHẢI khởi tạo bên trong luồng này
# #         engine = pyttsx3.init()
        
# #         # Cấu hình giọng nói
# #         voices = engine.getProperty('voices')
# #         if len(voices) > 1:
# #             engine.setProperty('voice', voices[1].id) # Thường là giọng nữ
# #         engine.setProperty('rate', 180)

# #         while True:
# #             try:
# #                 # Đợi có tin nhắn mới trong queue (chặn luồng cho đến khi có tin)
# #                 text = self.msg_queue.get()
# #                 if text:
# #                     engine.say(text)
# #                     engine.runAndWait() # Vòng lặp này sẽ kết thúc xong mới lấy tin tiếp theo
# #                 self.msg_queue.task_done()
# #             except Exception as e:
# #                 print(f"[VOICE ERROR] {e}")
# #                 time.sleep(1)

# #     def speak(self, text):
# #         """Hàm gọi từ Bot: Cực nhẹ, chỉ thêm text vào hàng đợi"""
# #         # Tránh việc nhồi quá nhiều tin nhắn giống hệt nhau vào hàng đợi
# #         # Nếu queue đang quá dài (> 3 tin), tạm thời không nhận thêm tin mới để tránh nói 'đè'
# #         if self.msg_queue.qsize() < 3:
# #             self.msg_queue.put(text)

# # # --- Test nhanh ---
# # if __name__ == "__main__":
# #     va = VoiceAssistant()
# #     print("Đang test âm thanh (không gây crash)...")
# #     va.speak("Phát hiện mục tiêu")
# #     va.speak("Đang bơm máu")
# #     time.sleep(5)
# import pyttsx3
# import threading
# import queue
# import time
# import pythoncom # THƯ VIỆN QUAN TRỌNG NHẤT ĐỂ FIX LỖI

# class VoiceAssistant:
#     def __init__(self):
#         self.msg_queue = queue.Queue()
#         # Luồng xử lý âm thanh duy nhất chạy ngầm
#         self.worker_thread = threading.Thread(target=self._voice_worker, daemon=True)
#         self.worker_thread.start()

#     def _voice_worker(self):
#         """Hàm này chạy trong luồng riêng, quản lý Engine TTS"""
#         # QUAN TRỌNG: Khởi tạo COM cho luồng này để Windows cho phép dùng Engine nói
#         pythoncom.CoInitialize() 
        
#         # Khởi tạo Engine ngay trong luồng này
#         engine = pyttsx3.init()
        
#         # Cấu hình giọng
#         voices = engine.getProperty('voices')
#         if len(voices) > 1:
#             engine.setProperty('voice', voices[1].id) 
#         engine.setProperty('rate', 190)

#         print("[VOICE SYSTEM] Hệ thống giọng nói đã sẵn sàng.")

#         while True:
#             try:
#                 # Chờ lấy tin nhắn từ queue
#                 text = self.msg_queue.get()
#                 if text:
#                     # In debug để bạn chắc chắn là tin nhắn đã truyền được vào đây
#                     print(f"[VOICE DEBUG] Đang phát âm thanh: {text}")
#                     engine.say(text)
#                     engine.runAndWait()
#                 self.msg_queue.task_done()
#             except Exception as e:
#                 print(f"[VOICE ERROR] Lỗi trong luồng nói: {e}")
#                 time.sleep(1)

#     def speak(self, text):
#         """Hàm gọi từ Bot: Kiểm tra trước khi ném vào hàng đợi"""
#         # 1. Nếu hàng đợi đang quá tải (>2 câu), bỏ qua luôn
#         if self.msg_queue.qsize() > 2:
#             return

#         # 2. Kiểm tra xem câu này có đang được xếp hàng không (tránh nói lặp)
#         # Lưu ý: Với queue.Queue chuẩn không duyệt được, nhưng ta có thể check đơn giản:
#         self.msg_queue.put(text)
from gtts import gTTS
import pygame
import os
import threading
import time

class VoiceAssistant:
    def __init__(self):
        # Khởi tạo mixer của pygame với tần số chuẩn để tránh rè
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
        except Exception:
            pygame.mixer.init()
            
        self.cache_dir = "google_voice_cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        # Hàng đợi tin nhắn (để tránh nói chồng chéo)
        self.queue = []
        self.is_speaking = False
        
        # Chạy luồng xử lý riêng
        threading.Thread(target=self._worker, daemon=True).start()

    def _get_filename(self, text):
        """Tạo tên file không dấu để tránh lỗi Win"""
        # Ví dụ: "Có địch" -> "co_dich.mp3"
        safe_text = "".join([c if c.isalnum() else "_" for c in text])
        # Giới hạn độ dài tên file kẻo lỗi
        return os.path.join(self.cache_dir, f"{safe_text[:50]}.mp3")

    def _download_and_play(self, text):
        filename = self._get_filename(text)
        
        # BƯỚC 1: KIỂM TRA CACHE
        # Nếu chưa có file thì mới tải từ Google (chỉ tốn mạng lần đầu)
        if not os.path.exists(filename):
            print(f"[GOOGLE TTS] Đang tải giọng nói: '{text}'...")
            try:
                tts = gTTS(text=text, lang='vi')
                tts.save(filename)
            except Exception as e:
                print(f"[ERROR] Mất mạng hoặc lỗi API: {e}")
                return

        # BƯỚC 2: PHÁT NHẠC BẰNG PYGAME
        try:
            # Kiểm tra xem mixer có đang bận không
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            # Đợi phát xong (để không bị ngắt quãng nếu bot tắt)
            # while pygame.mixer.music.get_busy():
            #    time.sleep(0.1)
        except Exception as e:
            print(f"[PLAY ERROR] {e}")

    def _worker(self):
        while True:
            if self.queue:
                text = self.queue.pop(0)
                self._download_and_play(text)
            time.sleep(0.1)

    def speak(self, text):
        # Thêm vào hàng đợi, giới hạn tối đa 3 câu để không bị delay quá lâu
        if len(self.queue) < 3:
            self.queue.append(text)

# --- Test ---
if __name__ == "__main__":
    va = VoiceAssistant()
    print("Test tải và nói...")
    va.speak("Xin chào đại ca, em là trợ lý ảo")
    time.sleep(4) # Chờ tải lần đầu
    va.speak("Có địch tấn công")
    time.sleep(2)
    # Lần này sẽ nói ngay lập tức vì đã có file
    va.speak("Có địch tấn công") 
    time.sleep(5)