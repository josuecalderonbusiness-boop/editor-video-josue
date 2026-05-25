with open("editor_josue_v7_clean.py", "r", encoding="utf-8") as f:
    lineas = f.readlines()

# Eliminar la linea 1259 (indice 1258)
lineas_limpias = []
for i, linea in enumerate(lineas, 1):
    if i == 1259:
        print(f"Eliminando linea {i}: {linea.strip()}")
        continue
    lineas_limpias.append(linea)

with open("editor_josue_v7_clean.py", "w", encoding="utf-8") as f:
    f.writelines(lineas_limpias)
print("OK - linea duplicada eliminada")
