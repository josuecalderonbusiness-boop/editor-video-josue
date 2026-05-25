with open("editor_josue_v7_clean.py", "r", encoding="utf-8") as f:
    contenido = f.read()

contenido = contenido.replace(
    "        # PASO 2.5: Voz profesional\n        if voz_pro:\n            tmp_voz = f'tmp_{nombre_base}_voz.mp4'\n            if aplicar_voz_pro(video_para_procesar, tmp_voz):\n                shutil.copy2(tmp_voz, video_para_procesar)\n                if os.path.exists(tmp_voz): os.remove(tmp_voz)",
    "        # PASO 2.5: Voz profesional\n        if voz_pro:\n            tmp_voz = f'tmp_{nombre_base}_voz.mp4'\n            print('Iniciando voz profesional...')\n            if aplicar_voz_pro(video_para_procesar, tmp_voz):\n                video_para_procesar = tmp_voz\n                print('Voz profesional aplicada correctamente.')"
)

with open("editor_josue_v7_clean.py", "w", encoding="utf-8") as f:
    f.write(contenido)
print("OK - voz_pro corregido")
