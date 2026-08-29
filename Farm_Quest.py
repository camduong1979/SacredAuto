import time
import keyboard
import pydirectinput

def main():
    print("=== FARM QUEST SCRIPT ===")
    print("Giữ hoặc nhấn phím 'n' để thực hiện: Ctrl+X -> Click Trái -> Enter")
    print("Nhấn 'Esc' hoặc 'Ctrl+C' để thoát chương trình.\n")

    pydirectinput.FAILSAFE = False

    try:
        while True:
            if keyboard.is_pressed('n'):
                pydirectinput.keyDown('ctrl')
                pydirectinput.press('x')
                pydirectinput.keyUp('ctrl')
                time.sleep(0.1)
                pydirectinput.click(button='left')
                time.sleep(0.1)
                pydirectinput.press('enter')
                time.sleep(0.4)

            if keyboard.is_pressed('esc'):
                print("Đã nhấn Esc. Thoát chương trình.")
                break

            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")

if __name__ == "__main__":
    main()