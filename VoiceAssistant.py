from gtts import gTTS
import pygame
import os
import threading
import queue
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
            
        # Hàng đợi tin nhắn thread-safe (tối đa 3 câu để tránh delay dồn)
        self.msg_queue = queue.Queue(maxsize=3)
        
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
        except Exception as e:
            print(f"[PLAY ERROR] {e}")

    def _worker(self):
        while True:
            text = self.msg_queue.get()   # Block cho đến khi có item
            self._download_and_play(text)
            self.msg_queue.task_done()

    def speak(self, text):
        """Thêm vào hàng đợi, bỏ qua nếu đã đầy (tránh delay dồn)"""
        try:
            self.msg_queue.put_nowait(text)
        except queue.Full:
            pass


# --- Test ---
if __name__ == "__main__":
    va = VoiceAssistant()
    print("Test tải và nói...")
    va.speak("Xin chào đại ca, em là trợ lý ảo")
    time.sleep(4)  # Chờ tải lần đầu
    va.speak("Có địch tấn công")
    time.sleep(2)
    # Lần này sẽ nói ngay lập tức vì đã có file
    va.speak("Có địch tấn công")
    time.sleep(5)