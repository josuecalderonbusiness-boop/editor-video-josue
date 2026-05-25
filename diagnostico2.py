with open('editor_josue_v7.py', encoding='utf-8') as f:
    c = f.read()

key = c.split('OPENAI_API_KEY = "')[1].split('"')[0]
print('Key:', key[:20] + '...')
print('Funcion existe:', 'transcribir_con_openai_api' in c)
print('Se llama:', 'audio_words = transcribir_con_openai_api' in c)