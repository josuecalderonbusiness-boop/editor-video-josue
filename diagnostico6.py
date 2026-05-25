from openai import OpenAI
import json

with open('editor_josue_v7.py', encoding='utf-8') as f:
    c = f.read()

OPENAI_KEY = c.split('OPENAI_API_KEY = "')[1].split('"')[0]

client = OpenAI(api_key=OPENAI_KEY)

print("Transcribiendo con OpenAI...")
with open('input/reel_prueba.mp4', 'rb') as f:
    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        language="es",
        response_format="verbose_json",
        timestamp_granularities=["word"]
    )

words = result.words
print(f"Palabras: {len(words)}")

print("\nToda la transcripción con timestamps:")
for w in words:
    print(f"  {w.start:.2f}s : {w.word}")