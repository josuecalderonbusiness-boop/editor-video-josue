import os
from drive_utils import get_drive_service, subir_archivo, crear_carpeta

CARPETA_LECCION1_ID = "1rfyZJzs-1JQ8DeckgNnoIRO-IpVTfzBD"
BASE = r"C:\Videos_Josue\workshop-animaciones\animaciones\leccion_1"

TEMAS = {
    "tema_2": [
        "anim_l1_an7.mp4",
        "anim_l1_an8.mp4",
        "anim_l1_an9.mp4",
        "anim_l1_an10.mp4",
        "anim_l1_an11.mp4",
        "anim_l1_an12.mp4",
    ],
    "tema_3": [
        "anim_l1_an13.mp4",
        "anim_l1_an14.mp4",
        "anim_l1_an15.mp4",
        "anim_l1_an16.mp4",
        "anim_l1_an17.mp4",
        "anim_l1_an18.mp4",
        "anim_l1_an19.mp4",
    ],
    "tema_4": [
        "anim_l1_an20.mp4",
        "anim_l1_an21.mp4",
        "anim_l1_an22.mp4",
        "anim_l1_an23.mp4",
    ],
}

def subir_animaciones():
    service = get_drive_service()
    for tema, archivos in TEMAS.items():
        print(f"\nCreando carpeta {tema} en Drive...")
        carpeta_id = crear_carpeta(service, tema, CARPETA_LECCION1_ID)
        print(f"  OK carpeta: {carpeta_id}")
        for archivo in archivos:
            ruta = os.path.join(BASE, tema, archivo)
            if not os.path.exists(ruta):
                print(f"  FALTA: {ruta}")
                continue
            print(f"  Subiendo {archivo}...")
            file_id, link = subir_archivo(ruta, archivo, carpeta_id)
            print(f"  OK: {link}")
    print("\nListo.")

if __name__ == "__main__":
    subir_animaciones()