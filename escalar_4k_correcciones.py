"""
escalar_4k_correcciones.py
Escala los MP4 de correcciones de 1280x720 a 3840x2160 (4K)
Uso: py -3.11 escalar_4k_correcciones.py
"""
import os
import subprocess

BASE        = r"C:\Videos_Josue\workshop-animaciones\animaciones\leccion_1\correcciones"
SALIDA_4K   = r"C:\Videos_Josue\workshop-animaciones\animaciones\leccion_1\correcciones_4k"

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

def escalar():
    os.makedirs(SALIDA_4K, exist_ok=True)

    ok      = 0
    errores = []

    print("Escalando correcciones a 4K...")
    print("")

    for archivo in ARCHIVOS:
        entrada = os.path.join(BASE, archivo)
        salida  = os.path.join(SALIDA_4K, archivo)

        if not os.path.exists(entrada):
            print(f"FALTA: {archivo}")
            errores.append(archivo)
            continue

        tam_mb = os.path.getsize(entrada) / (1024 * 1024)
        print(f"Escalando {archivo} ({tam_mb:.1f} MB)...")

        cmd = [
            "ffmpeg", "-y",
            "-i", entrada,
            "-vf", "scale=3840:2160:flags=lanczos",
            "-c:v", "libx264",
            "-crf", "16",
            "-preset", "slow",
            "-c:a", "copy",
            salida
        ]

        r = subprocess.run(cmd, capture_output=True, text=True)

        if r.returncode == 0:
            tam_out = os.path.getsize(salida) / (1024 * 1024)
            print(f"OK: {archivo} -> {tam_out:.1f} MB")
            ok += 1
        else:
            print(f"ERROR en {archivo}:")
            print(r.stderr[-400:])
            errores.append(archivo)

        print("")

    print(f"Terminado: {ok} de {len(ARCHIVOS)} escalados")
    print(f"Carpeta salida: {SALIDA_4K}")

    if errores:
        print("Errores en:")
        for e in errores:
            print(f"  - {e}")

if __name__ == "__main__":
    escalar()
