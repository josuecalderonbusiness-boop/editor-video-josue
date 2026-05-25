import subprocess, json

with open('editor_josue_v7.py', encoding='utf-8') as f:
    contenido = f.read()

OPENAI_API_KEY = contenido.split('OPENAI_API_KEY = "')[1].split('"')[0]

cmd = [
    'curl', '-s',
    'https://api.openai.com/v1/audio/transcriptions',
    '-H', f'Authorization: Bearer {OPENAI_API_KEY}',
    '-F', 'file=@input/reel_prueba.mp4',
    '-F', 'model=whisper-1',
    '-F', 'language=es',
    '-F', 'response_format=verbose_json',
    '-F', 'timestamp_granularities[]=word'
]

r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
data = json.loads(r.stdout)
print(data.get('text', 'SIN TEXTO')) 

if "words" in data:
    print(f"\nPalabras con timestamps: {len(data['words'])}")
    for w in data['words'][:10]:
        print(f"  {w['start']:.2f}s - {w['end']:.2f}s : {w['word']}")
else:
    print("\nSIN timestamps por palabra — solo texto completo")
    print("Segmentos:", len(data.get('segments', [])))

print("\nEstructura de segments[0]:")
if data.get('segments'):
    seg = data['segments'][0]
    print(f"  Keys: {list(seg.keys())}")
    if 'words' in seg:
        print(f"  Palabras en segmento 0: {len(seg['words'])}")
        print(f"  Primera palabra: {seg['words'][0]}")