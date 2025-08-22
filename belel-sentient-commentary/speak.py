import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def speak(text, voice="onyx", output_path="audio_out/belel.wav"):
    response = openai.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text
    )
    with open(output_path, "wb") as f:
        f.write(response.content)

if __name__ == "__main__":
    with open("prompts/welcome.txt") as file:
        text = file.read()
    speak(text)
