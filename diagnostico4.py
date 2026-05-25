import subprocess, json, urllib.request

with open('editor_josue_v7.py', encoding='utf-8') as f:
    c = f.read()

OPENAI_KEY = c.split('OPENAI_API_KEY = "')[1].split('"')[0]
CLAUDE_KEY = c.split('CLAUDE_API_KEY = "')[1].split('"')[0]

# Transcribir con OpenAI
print("Transcribiendo...")
cmd = [
    'curl', '-s',
    'https://api.openai.com/v1/audio/transcriptions',
    '-H', f'Authorization: Bearer {OPENAI_KEY}',
    '-F', 'file=@input/reel_prueba.mp4',
    '-F', 'model=whisper-1',
    '-F', 'language=es',
    '-F', 'response_format=verbose_json',
    '-F', 'timestamp_granularities[]=word'
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
data = json.loads(r.stdout)
words = data.get('words', [])
print(f"Palabras: {len(words)}")

# Mostrar palabras del segundo 10 al 25 donde están los errores
print("\nPalabras 10s-25s:")
for w in words:
    if 0 <= w['start'] <= 70:
        print(f"  {w['start']:.2f}s : {w['word']}")