import winsound
import time

def test_alerts():
    print("--- KIỂM TRA ÂM THANH BOT ---")
    
    print("\n1. Am thanh: PHÁT HIỆN QUÁI (High Tone)")
    # Tần số 1500Hz là mức báo động, 200ms là độ dài tiêu chuẩn
    winsound.Beep(1500, 200) 
    time.sleep(1)
    
    print("2. Am thanh: HẾT QUÁI / AN TOÀN (Low Tone)")
    # Tần số 500Hz nghe rất êm, báo hiệu bạn có thể nghỉ ngơi
    winsound.Beep(500, 150)
    time.sleep(1)
    
    print("3. Am thanh: BƠM MÁU CẤP CỨU")
    # Tiếng bíp ngắn và gắt để báo hiệu Bot vừa tự động dùng Space
    winsound.Beep(2000, 100)
    
    print("\n[OK] Kiem tra hoan tat. Loa cua ban van rat tot!")

if __name__ == "__main__":
    test_alerts()