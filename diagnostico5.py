import subprocess, json, urllib.request

with open('editor_josue_v7.py', encoding='utf-8') as f:
    c = f.read()

OPENAI_KEY = c.split('OPENAI_API_KEY = "')[1].split('"')[0]
CLAUDE_KEY = c.split('CLAUDE_API_KEY = "')[1].split('"')[0]

guion = open('input/reel_prueba.txt', encoding='utf-8').read()

# Transcribir
print("Transcribiendo con OpenAI...")
cmd = ['curl', '-s', 'https://api.openai.com/v1/audio/transcriptions',
    '-H', f'Authorization: Bearer {OPENAI_KEY}',
    '-F', 'file=@input/reel_prueba.mp4',
    '-F', 'model=whisper-1', '-F', 'language=es',
    '-F', 'response_format=verbose_json',
    '-F', 'timestamp_granularities[]=word']
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
data = json.loads(r.stdout)
words = data.get('words', [])
print(f"Palabras: {len(words)}")

lineas = [f"  {w['start']:.2f}s  {w['word']}" for w in words]
transcripcion_str = "\n".join(lineas)

# Preguntar a Claude
print("\nConsultando Claude...")
prompt = f"""Eres editor de video. Compara este guion con la transcripcion y dime que cortar.

GUION:
{guion}

TRANSCRIPCION:
{transcripcion_str}

Responde solo JSON: {{"cortes": [{{"inicio": 0.0, "fin": 0.0, "descripcion": ""}}]}}
Si no hay cortes: {{"cortes": []}}"""

payload = json.dumps({
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 1000,
    "messages": [{"role": "user", "content": prompt}]
}).encode('utf-8')

req = urllib.request.Request(
    'https://api.anthropic.com/v1/messages',
    data=payload,
    headers={
        'Content-Type': 'application/json',
        'x-api-key': CLAUDE_KEY,
        'anthropic-version': '2023-06-01'
    }
)

with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read())
    respuesta = result['content'][0]['text']

print(f"\nRespuesta de Claude:\n{respuesta}")

print("Payload size:", len(payload), "bytes")
print("Prompt preview:", prompt[:200])