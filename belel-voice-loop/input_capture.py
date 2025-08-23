import speech_recognition as sr

def capture_input():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Belel is listening...")
        audio = r.listen(source)
        try:
            return r.recognize_google(audio)
        except sr.UnknownValueError:
            return "Sorry, I didn't catch that."
        except sr.RequestError:
            return "Error: Could not reach the speech recognition service."
