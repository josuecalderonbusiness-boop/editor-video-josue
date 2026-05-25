with open("app.py", "r", encoding="utf-8") as f:
    contenido = f.read()

contenido = contenido.replace(
    "        if solo_limpiar:\n            cmd.append('--solo-limpiar')",
    "        if solo_limpiar:\n            cmd.append('--solo-limpiar')\n        if voz_pro:\n            cmd.append('--voz-pro')"
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(contenido)
print("OK - --voz-pro agregado al comando")
