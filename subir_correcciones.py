import os
from drive_utils import get_drive_service, subir_archivo

CARPETA_CORRECCIONES_ID = "1WwDw5l8qmaH9pmmEyaxwL2ec0qJdlAYQ"
BASE = r"C:\Videos_Josue\workshop-animaciones\animaciones\leccion_1\correcciones"

ARCHIVOS = [
    "anim_l1_an2_v2.mp4",
    "anim_l1_an3_v2.mp4",
    "anim_l1_an4_v3.mp4",
    "anim_l1_an7_v2.mp4",
    "anim_l1_an8_v2.mp4",
    "anim_l1_an12_v2.mp4",
    "anim_l1_an13_v2.mp4",
    "anim_l1_an15_v2.mp4",
    "anim_l1_an16_v2.mp4",
    "anim_l1_an17_v2.mp4",
    "anim_l1_an20_v2.mp4",
]

def subir_correcciones():
    service = get_drive_service()
    ok = 0
    errores = []

    print("Subiendo correcciones a Drive...")
    print("")

    for archivo in ARCHIVOS:
        ruta = os.path.join(BASE, archivo)
        if not os.path.exists(ruta):
            print(f"FALTA: {archivo}")
            errores.append(archivo)
            continue
        print(f"Subiendo {archivo}...")
        try:
            file_id, link = subir_archivo(ruta, archivo, CARPETA_CORRECCIONES_ID)
            print(f"OK: {link}")
            ok += 1
        except Exception as e:
            print(f"ERROR en {archivo}: {e}")
            errores.append(archivo)
        print("")

    print(f"Terminado: {ok} de {len(ARCHIVOS)} subidos")
    if errores:
        print("Errores en:")
        for e in errores:
            print(f"  - {e}")

if __name__ == "__main__":
    subir_correcciones()
