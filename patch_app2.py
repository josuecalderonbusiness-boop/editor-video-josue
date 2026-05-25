with open("app.py", "r", encoding="utf-8") as f:
    contenido = f.read()

# Eliminar duplicado
contenido = contenido.replace(
    "    voz_pro = request.form.get('voz_pro') == 'true'\n    voz_pro = request.form.get('voz_pro') == 'true'\n",
    "    voz_pro = request.form.get('voz_pro') == 'true'\n"
)

# Agregar --voz-pro al comando despues de --limpia-audio
contenido = contenido.replace(
    "    if limpia_audio:\n        cmd.append('--limpia-audio')",
    "    if limpia_audio:\n        cmd.append('--limpia-audio')\n    if voz_pro:\n        cmd.append('--voz-pro')"
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(contenido)
print("OK - app.py corregido")
