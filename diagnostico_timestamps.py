#!/usr/bin/env python3
"""
Herramienta de diagnóstico — muestra transcripción con timestamps exactos
para entender qué está detectando Whisper.

USO:
py -3.11 diagnostico_timestamps.py video.mp4
"""
import sys
import subprocess
import os

def main():
    if len(sys.argv) < 2:
        print("USO: py -3.11 diagnostico_timestamps.py video.mp4")
        return

    video = sys.argv[1]
    if not os.path.exists(video):
        print(f"❌ No encuentro el archivo: {video}")
        return

    print("Cargando Whisper medium...")
    import whisper
    modelo = whisper.load_model("medium")

    # Extraer audio
    tmp = "tmp_diag.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", video, "-vn", "-acodec", "mp3", "-ab", "192k", tmp],
        capture_output=True
    )

    print("Transcribiendo con timestamps por palabra...")
    result = modelo.transcribe(tmp, language="es", word_timestamps=True)

    if os.path.exists(tmp):
        os.remove(tmp)

    print("\n" + "="*60)
    print("TRANSCRIPCIÓN CON TIMESTAMPS")
    print("="*60)
    for seg in result["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                p = w["word"].strip()
                if p:
                    print(f"  {w['start']:6.2f}s  {p}")
    print("="*60)

if __name__ == "__main__":
    main()
