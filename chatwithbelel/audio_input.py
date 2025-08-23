import whisper
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from responder import get_belel_reply
from voice_player import generate_voice

model = whisper.load_model("base")

@app.post("/chatwithbelel/audio")
async def audio_input(file: UploadFile = File(...)):
    path = f"temp/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    
    result = model.transcribe(path)
    text = result['text']
    reply = get_belel_reply(text)
    voice = generate_voice(reply)

    return JSONResponse({
        "transcript": text,
        "response": reply,
        "voice": voice
    })
