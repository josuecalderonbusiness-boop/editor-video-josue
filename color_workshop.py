def aplicar_color_workshop(entrada, salida):
    print("\nAplicando correccion de color profesional...")
    filtro = (
        "eq=brightness=-0.03:contrast=1.08:saturation=0.88,"
        "curves=r='0/0 0.22/0.18 0.75/0.72 1/1':"
               "g='0/0 0.22/0.21 0.75/0.73 1/0.97':"
               "b='0/0 0.22/0.20 0.75/0.70 1/0.94',"
        "unsharp=3:3:0.4:3:3:0.0"
    )
    cmd = [
        "ffmpeg", "-y", "-i", entrada,
        "-vf", filtro,
        "-c:v", "libx264", "-crf", "18", "-preset", "slow",
        "-c:a", "copy", salida
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error correccion color: {r.stderr[-200:]}")
        return False
    print("Correccion de color aplicada.")
    return True
