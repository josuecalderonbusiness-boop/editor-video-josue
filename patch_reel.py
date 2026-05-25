with open("editor_josue_v7_clean.py", "r", encoding="utf-8") as f:
    contenido = f.read()

contenido = contenido.replace(
    'def editar_reel(nombre_archivo, fuente="montserrat", guion=None,\n                subtitulos=False, solo_limpiar=False, limpia_audio=False, color_workshop=False, cortes_manual=None):',
    'def editar_reel(nombre_archivo, fuente="montserrat", guion=None,\n                subtitulos=False, solo_limpiar=False, limpia_audio=False, color_workshop=False, cortes_manual=None, voz_pro=False):'
)

with open("editor_josue_v7_clean.py", "w", encoding="utf-8") as f:
    f.write(contenido)
print("OK - voz_pro agregado a editar_reel")
