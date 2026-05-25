with open("app.py", "r", encoding="utf-8") as f:
    contenido = f.read()

contenido = contenido.replace(
    "            if solo_limpiar:\n                cmd.append('--solo-limpiar')\n            proc = subprocess.Popen(cmd",
    "            if solo_limpiar:\n                cmd.append('--solo-limpiar')\n            if voz_pro:\n                cmd.append('--voz-pro')\n            proc = subprocess.Popen(cmd"
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(contenido)
print("OK - --voz-pro agregado a procesar-drive")
