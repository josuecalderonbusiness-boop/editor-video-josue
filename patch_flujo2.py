with open("editor_josue_v7_clean.py", "r", encoding="utf-8") as f:
    lineas = f.readlines()

# Insertar despues de la linea 1192 (else: video_para_procesar = tmp_sin_sil)
insertar = [
    "\n",
    "        # PASO 2.5: Voz profesional\n",
    "        if voz_pro:\n",
    "            tmp_voz = f'tmp_{nombre_base}_voz.mp4'\n",
    "            if aplicar_voz_pro(video_para_procesar, tmp_voz):\n",
    "                shutil.copy2(tmp_voz, video_para_procesar)\n",
    "                if os.path.exists(tmp_voz): os.remove(tmp_voz)\n",
    "\n"
]

# Buscar la linea exacta
for i, l in enumerate(lineas):
    if "video_para_procesar = tmp_sin_sil" in l and "else" in lineas[i-1]:
        print(f"Encontrado en linea {i+1}: {l.strip()}")
        lineas = lineas[:i+1] + insertar + lineas[i+1:]
        break

with open("editor_josue_v7_clean.py", "w", encoding="utf-8") as f:
    f.writelines(lineas)
print("OK - voz_pro insertado")
