with open('editor_josue_v7_clean.py', 'r', encoding='utf-8') as f:
    txt = f.read()

viejo = '''            print("   Re-codificando a MP4 compatible...")
            cmd_reenc = [
                "ffmpeg", "-y", "-i", video_para_procesar,
                "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k", archivo_final
            ]'''

nuevo = '''            print("   Copiando a MP4 compatible...")
            cmd_reenc = [
                "ffmpeg", "-y", "-i", video_para_procesar,
                "-c:v", "copy", "-c:a", "copy", archivo_final
            ]'''

if viejo in txt:
    txt = txt.replace(viejo, nuevo)
    print('Fix aplicado.')
else:
    print('No encontrado.')

with open('editor_josue_v7_clean.py', 'w', encoding='utf-8') as f:
    f.write(txt)