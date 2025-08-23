from belel_conversation import get_reply
from elevenlabs_speech import speak
from input_capture import capture_input

def start_loop():
    while True:
        query = capture_input()
        response = get_reply(query)
        speak(response)
