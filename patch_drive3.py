with open("app.py", "r", encoding="utf-8") as f:
    lineas = f.readlines()

# Insertar despues de linea 172 (--solo-limpiar)
lineas.insert(172, "            if voz_pro:\n")
lineas.insert(173, "                cmd.append('--voz-pro')\n")

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(lineas)
print("OK - voz-pro insertado en procesar-drive")
