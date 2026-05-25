with open("app.py", "r", encoding="utf-8") as f:
    contenido = f.read()

contenido = contenido.replace(
    "    solo_limpiar  = data.get('solo_limpiar', True)\n    if not drive_file_id:",
    "    solo_limpiar  = data.get('solo_limpiar', True)\n    voz_pro       = data.get('voz_pro', False)\n    if not drive_file_id:"
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(contenido)
print("OK - voz_pro agregado a procesar-drive")
