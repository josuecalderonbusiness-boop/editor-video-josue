"""
subir_l1_tema1.py
"""
import os
import json
from drive_utils import get_drive_service, subir_archivo

CARPETA_ANIMACIONES = r"workshop-animaciones\animaciones\leccion_1"
CARPETA_DRIVE_ID = "17rMZDn6K1zD7lzvZXOKOAF1pnJroznz3"

TIMINGS = [
    {"html": "anim_l1_an1.html", "archivo": "anim_l1_an1_4k.mp4", "start": 0,   "duration": 8},
    {"html": "anim_l1_an2.html", "archivo": "anim_l1_an2_4k.mp4", "start": 1,   "duration": 4},
    {"html": "anim_l1_an3.html", "archivo": "anim_l1_an3_4k.mp4", "start": 25,  "duration": 25},
    {"html": "anim_l1_an4.html", "archivo": "anim_l1_an4_4k.mp4", "start": 63,  "duration": 28},
    {"html": "anim_l1_an5.html", "archivo": "anim_l1_an5_4k.mp4", "start": 117, "duration": 5},
    {"html": "anim_l1_an6.html", "archivo": "anim_l1_an6_4k.mp4", "start": 127, "duration": 16},
]

def subir_animaciones():
    print("Subiendo animaciones 4K Lección 1 - Tema 1 a Google Drive...")
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

    timings_drive = []
    for t in TIMINGS:
        if t["archivo"] in ids:
            timings_drive.append({
                "archivo": t["archivo"],
                "drive_id": ids[t["archivo"]],
                "start": t["start"],
                "duration": t["duration"]
            })

    json_nombre = "animaciones_l1_tema1.json"
    with open(json_nombre, "w") as f:
        json.dump(timings_drive, f, indent=2)

    print(f"\nListo. {json_nombre} generado con {len(timings_drive)} animaciones.")

if __name__ == "__main__":
    subir_animaciones()
