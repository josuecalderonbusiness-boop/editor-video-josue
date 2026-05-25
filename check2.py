with open("editor_josue_v7_clean.py", "r", encoding="utf-8") as f:
    lineas = f.readlines()

for i, l in enumerate(lineas):
    if "# PASO 2.5: Voz profesional" in l:
        print(f"PASO 2.5 en linea {i+1}")
    if "elif guion:" in l:
        print(f"elif guion en linea {i+1}")
    if "else:" in l and i > 1150 and i < 1200:
        print(f"else en linea {i+1}: {l.strip()}")
