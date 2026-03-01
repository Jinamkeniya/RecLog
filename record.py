import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def stt(audio_path):
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f.read()),
            model="whisper-large-v3-turbo",
            response_format="text",
        )
    return transcription.strip()
