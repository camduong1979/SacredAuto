import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')

# Giả sử Microsoft An nằm ở index cuối cùng sau khi bạn sửa Registry
for voice in voices:
    if "An" in voice.name:
        engine.setProperty('voice', voice.id)
        break

engine.say("Xin chào, tôi là An. Tôi có thể nói 5 tiếng Việt rất tốt.")
engine.runAndWait()