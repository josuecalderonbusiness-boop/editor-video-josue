"""
subir_animaciones.py
Sube los MP4 de animaciones a una carpeta de Drive
y genera el JSON de timings para Railway.

Uso: py -3.11 subir_animaciones.py
"""
import os
import json
from drive_utils import get_drive_service, subir_archivo

CARPETA_ANIMACIONES = "animaciones"
CARPETA_DRIVE_ID = "1S4eeLmBmKaFTRskIjcVYdzg3iYzBXlAM"  # videos-procesados-editor

TIMINGS = [
    {"html": "anim_an1.html", "archivo": "anim_an1.mp4", "start": 25,  "duration": 33},
    {"html": "anim_an2.html", "archivo": "anim_an2.mp4", "start": 128, "duration": 30},
    {"html": "anim_an3.html", "archivo": "anim_an3.mp4", "start": 254, "duration": 42},
    {"html": "anim_an4.html", "archivo": "anim_an4.mp4", "start": 335, "duration": 14},
    {"html": "anim_an5.html", "archivo": "anim_an5.mp4", "start": 389, "duration": 22},
    {"html": "anim_an6.html", "archivo": "anim_an6.mp4", "start": 458, "duration": 14},
    {"html": "anim_an7.html", "archivo": "anim_an7.mp4", "start": 745, "duration": 48},
]

def subir_animaciones():
    print("Subiendo animaciones a Google Drive...")
    ids = {}
    for t in TIMINGS:
        ruta = os.path.join(CARPETA_ANIMACIONES, t["archivo"])
        if not os.path.exists(ruta):
            print(f"  FALTA: {ruta}")
            continue
        print(f"  Subiendo {t['archivo']}...")
        file_id, link = subir_archivo(ruta, t["archivo"], CARPETA_DRIVE_ID)
        ids[t["archivo"]] = file_id
        print(f"  OK: {link}")

    # Generar JSON con IDs de Drive para Railway
    timings_drive = []
    for t in TIMINGS:
        if t["archivo"] in ids:
            timings_drive.append({
                "archivo": t["archivo"],
                "drive_id": ids[t["archivo"]],
                "start": t["start"],
                "duration": t["duration"]
            })

    with open("animaciones_drive.json", "w") as f:
        json.dump(timings_drive, f, indent=2)

    print(f"\nListo. animaciones_drive.json generado con {len(timings_drive)} animaciones.")
    print("Sube ese archivo a GitHub para que Railway lo use.")

if __name__ == "__main__":
    subir_animaciones()