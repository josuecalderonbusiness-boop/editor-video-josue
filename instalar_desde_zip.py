#!/usr/bin/env python3
# ============================================================
#   INSTALAR FUENTES DESDE ZIPs DESCARGADOS
#   py -3.11 instalar_desde_zip.py
#
#   Pon todos los ZIPs de Google Fonts en:
#   C:\Videos_Josue\fuentes\
#   y corre este script
# ============================================================

import os, zipfile, shutil

CARPETA_ZIPS  = r"C:\Videos_Josue\fuentes"
CARPETA_FONTS = os.path.join(os.path.expanduser("~"),
                "AppData","Local","Microsoft","Windows","Fonts")

def main():
    print("=" * 50)
    print("  INSTALADOR DE FUENTES DESDE ZIPs")
    print("=" * 50)

    os.makedirs(CARPETA_FONTS, exist_ok=True)

    if not os.path.exists(CARPETA_ZIPS):
        print(f"\n  ❌ No existe la carpeta:")
        print(f"     {CARPETA_ZIPS}")
        print(f"\n  Créala y pon los ZIPs ahí.")
        input("\n  Enter para cerrar...")
        return

    zips = [f for f in os.listdir(CARPETA_ZIPS) if f.endswith(".zip")]
    if not zips:
        print(f"\n  ❌ No hay archivos ZIP en:")
        print(f"     {CARPETA_ZIPS}")
        input("\n  Enter para cerrar...")
        return

    print(f"\n  ZIPs encontrados: {len(zips)}")
    print()

    total_ok = 0
    total_skip = 0

    for zip_nombre in sorted(zips):
        zip_path = os.path.join(CARPETA_ZIPS, zip_nombre)
        print(f"  📦 {zip_nombre}")
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                ttfs = [n for n in z.namelist()
                        if n.endswith(".ttf") and "/" not in n.replace("static/","")]

                # aceptar static/ también
                if not ttfs:
                    ttfs = [n for n in z.namelist() if n.endswith(".ttf")]

                for ttf_path in ttfs:
                    nombre = os.path.basename(ttf_path)
                    destino = os.path.join(CARPETA_FONTS, nombre)
                    if os.path.exists(destino):
                        print(f"     ya existe: {nombre}")
                        total_skip += 1
                        continue
                    data = z.read(ttf_path)
                    with open(destino, "wb") as f:
                        f.write(data)
                    print(f"     ✅ {nombre}")
                    total_ok += 1
        except Exception as e:
            print(f"     ❌ Error: {e}")

    # Registrar en Windows
    try:
        import winreg
        clave = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
            0, winreg.KEY_SET_VALUE
        )
        for nombre in os.listdir(CARPETA_FONTS):
            if nombre.endswith(".ttf"):
                ruta = os.path.join(CARPETA_FONTS, nombre)
                winreg.SetValueEx(clave, nombre, 0, winreg.REG_SZ, ruta)
        winreg.CloseKey(clave)
        print("\n  ✅ Registradas en Windows")
    except Exception as e:
        print(f"\n  ⚠️  Registro: {e}")

    print()
    print("=" * 50)
    print(f"  ✅ Instaladas: {total_ok}")
    print(f"  ℹ️  Ya existían: {total_skip}")
    print()
    print("  Ahora puedes usar:")
    print("  --fuente montserrat / bebas / playfair")
    print("  --fuente outfit / oswald / anton / inter")
    print("=" * 50)
    input("\n  Presiona Enter para cerrar...")

if __name__ == "__main__":
    main()
