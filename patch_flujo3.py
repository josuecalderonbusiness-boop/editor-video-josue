with open("editor_josue_v7_clean.py", "r", encoding="utf-8") as f:
    lineas = f.readlines()

# Eliminar el PASO 2.5 donde esta mal (lineas 1174-1181)
lineas_limpias = []
skip = False
for i, l in enumerate(lineas, 1):
    if "# PASO 2.5: Voz profesional" in l:
        skip = True
    if skip and "elif guion:" in l:
        skip = False
    if not skip:
        lineas_limpias.append(l)

# Insertar PASO 2.5 antes del PASO 3
resultado = []
for i, l in enumerate(lineas_limpias):
    if "# PASO 3: Convertir o guardar" in l:
        resultado.append("        # PASO 2.5: Voz profesional\n")
        resultado.append("        if voz_pro:\n")
        resultado.append("            tmp_voz = f'tmp_{nombre_base}_voz.mp4'\n")
        resultado.append("            if aplicar_voz_pro(video_para_procesar, tmp_voz):\n")
        resultado.append("                shutil.copy2(tmp_voz, video_para_procesar)\n")
        resultado.append("                if os.path.exists(tmp_voz): os.remove(tmp_voz)\n")
        resultado.append("\n")
    resultado.append(l)

with open("editor_josue_v7_clean.py", "w", encoding="utf-8") as f:
    f.writelines(resultado)
print("OK - PASO 2.5 movido al lugar correcto")
