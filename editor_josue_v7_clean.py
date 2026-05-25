#!/usr/bin/env python3
# ============================================================
#   EDITOR DE VIDEO PERSONAL — JOSUÉ CALDERÓN  v7.0
#   Sistema automático: silencio + limpieza con IA + exportación
#
#   IA: OpenAI Whisper API (transcripción) + GPT-4o (detección errores)
#   Sin Whisper local — todo corre en la nube
#
#   USO:
#   py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt
#   py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --subtitulos
#   py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --solo-limpiar
#   py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --limpia-audio
# ============================================================

import subprocess
import sys
import os
import re
import json
import shutil
import argparse
import datetime
try:
    from cortes_precisos import calcular_cortes_precisos
    _CORTES_PRECISOS_OK = True
except ImportError:
    _CORTES_PRECISOS_OK = False

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import numpy as np
    from moviepy import VideoFileClip, concatenate_videoclips, VideoClip
    _MOVIEPY_OK = True
except Exception:
    _MOVIEPY_OK = False
    np = None

# ─────────────────────────────────────────
#  API KEYS — se leen desde .env
# ─────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")   # ← pon tu key en .env
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")   # ← opcional

# ─────────────────────────────────────────
#  MAPA DE FUENTES
# ─────────────────────────────────────────
FUENTES_DIR = os.path.join(os.path.expanduser("~"),
              "AppData", "Local", "Microsoft", "Windows", "Fonts")

FUENTES_MAPA = {
    "montserrat": {
        "normal": ["Montserrat-Regular.ttf", "Montserrat-SemiBold.ttf"],
        "bold":   ["Montserrat-Bold.ttf", "Montserrat-ExtraBold.ttf"],
    },
    "bebas":   {"normal": ["BebasNeue-Regular.ttf"],   "bold": ["BebasNeue-Regular.ttf"]},
    "anton":   {"normal": ["Anton-Regular.ttf"],        "bold": ["Anton-Regular.ttf"]},
    "oswald":  {"normal": ["Oswald-Regular.ttf"],       "bold": ["Oswald-Bold.ttf"]},
    "outfit":  {"normal": ["Outfit-Regular.ttf"],       "bold": ["Outfit-Bold.ttf"]},
    "inter":   {"normal": ["Inter-Regular.ttf"],        "bold": ["Inter-Bold.ttf"]},
    "arial":   {"normal": ["arial.ttf", "C:/Windows/Fonts/arial.ttf"],
                "bold":   ["arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf"]},
}

FUENTE_DEFECTO = "montserrat"

CONFIG = {
    "silencio_minimo": 1.5,
    "umbral_db":       -28,
    "resolucion":      "1080:1920",
    "fps":             30,
    "fade_audio_ms":   80,
    "margen_corte":    0.18,
}

CARPETA_INPUT  = "input"
CARPETA_OUTPUT = "output"
CARPETA_SUBS   = "subtitulos"
CARPETA_LOGS   = "logs"


# ─────────────────────────────────────────
#  LOG
# ─────────────────────────────────────────
class LogEdicion:
    def __init__(self, nombre_video):
        self.nombre_video = nombre_video
        self.inicio       = datetime.datetime.now()
        self.entradas     = []

    def registrar(self, tipo, t_ini, t_fin, detalle=""):
        self.entradas.append({
            "tipo": tipo, "inicio": round(t_ini, 3),
            "fin": round(t_fin, 3), "dur": round(t_fin - t_ini, 3),
            "detalle": detalle,
        })

    def guardar(self):
        os.makedirs(CARPETA_LOGS, exist_ok=True)
        ts   = self.inicio.strftime("%Y%m%d_%H%M%S")
        base = os.path.splitext(self.nombre_video)[0]
        ruta = os.path.join(CARPETA_LOGS, f"{base}_log_{ts}.txt")
        total = sum(e["dur"] for e in self.entradas)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"LOG DE EDICION - {self.nombre_video}\n")
            f.write(f"Fecha : {self.inicio.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Cortes: {len(self.entradas)} | Total cortado: {total:.1f}s\n")
            f.write("=" * 60 + "\n\n")
            for i, e in enumerate(self.entradas, 1):
                f.write(f"[{i:03d}] {e['tipo']}\n")
                f.write(f"      {e['inicio']:.2f}s -> {e['fin']:.2f}s ({e['dur']:.2f}s)\n")
                if e["detalle"]:
                    f.write(f"      {e['detalle']}\n")
                f.write("\n")
        print(f"\nLog guardado: {ruta}")
        print(f"   Total cortado: {total:.1f}s en {len(self.entradas)} corte(s)")
        return ruta


# ─────────────────────────────────────────
#  FUENTES
# ─────────────────────────────────────────
def resolver_fuente(nombre_fuente, bold=False):
    nombre_fuente = nombre_fuente.lower()
    if nombre_fuente not in FUENTES_MAPA:
        nombre_fuente = FUENTE_DEFECTO
    tipo = "bold" if bold else "normal"
    for opcion in FUENTES_MAPA[nombre_fuente][tipo]:
        if os.path.isabs(opcion) and os.path.exists(opcion):
            return opcion
        for base in [FUENTES_DIR, "C:/Windows/Fonts"]:
            ruta = os.path.join(base, opcion)
            if os.path.exists(ruta):
                return ruta
    return None


def cargar_fuente_pil(nombre_fuente, tam, bold=False):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    ruta = resolver_fuente(nombre_fuente, bold)
    if ruta:
        try:
            return ImageFont.truetype(ruta, tam)
        except Exception:
            pass
    for fb in (["C:/Windows/Fonts/arialbd.ttf"] if bold else ["C:/Windows/Fonts/arial.ttf"]):
        try:
            return ImageFont.truetype(fb, tam)
        except Exception:
            pass
    from PIL import ImageFont
    return ImageFont.load_default()


# ─────────────────────────────────────────
#  VERIFICAR DEPENDENCIAS
# ─────────────────────────────────────────
def verificar_dependencias():
    if shutil.which("ffmpeg") is None:
        print("Error: Falta FFmpeg.")
        sys.exit(1)
    if not _MOVIEPY_OK:
        print("Error: Falta moviepy/numpy.")
        sys.exit(1)
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: Falta openai. Instala con: py -3.11 -m pip install openai")
        sys.exit(1)
    print("Dependencias verificadas.")


def crear_carpetas():
    for c in [CARPETA_INPUT, CARPETA_OUTPUT, CARPETA_SUBS, CARPETA_LOGS]:
        os.makedirs(c, exist_ok=True)
    print("Carpetas listas.")


# ─────────────────────────────────────────
#  PROXY — comprime video para analisis rapido
# ─────────────────────────────────────────
def crear_proxy(entrada, proxy):
    print("   Creando proxy 720p para analisis...")
    cmd = [
        "ffmpeg", "-y", "-i", entrada,
        "-vf", "scale=1280:720",
        "-c:v", "libx264", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        "-preset", "ultrafast", proxy
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"   Error creando proxy: {r.stderr[-200:]}")
        return False
    tam = os.path.getsize(proxy) / (1024*1024)
    print(f"   Proxy listo: {tam:.0f}MB")
    return True


def aplicar_cortes_a_original(original, segmentos, salida):
    """Aplica los timestamps del proxy al video original en alta calidad."""
    lista_tmp = "tmp_orig_concat.txt"
    clips_tmp = []
    with open(lista_tmp, "w", encoding="utf-8") as f:
        for idx, (t_s, t_e) in enumerate(segmentos):
            if t_e - t_s < 0.1:
                continue
            clip_tmp = f"tmp_orig_seg_{idx}.mp4"
            clips_tmp.append(clip_tmp)
            cmd_corte = [
                "ffmpeg", "-y",
                "-ss", str(t_s), "-to", str(t_e),
                "-i", original,
                "-c:v", "copy", "-c:a", "aac",
                "-avoid_negative_ts", "make_zero", clip_tmp
            ]
            subprocess.run(cmd_corte, capture_output=True, text=True)
            f.write(f"file '{clip_tmp}'\n")

    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", lista_tmp, "-c", "copy", salida
    ]
    r = subprocess.run(cmd_concat, capture_output=True, text=True)

    if os.path.exists(lista_tmp):
        os.remove(lista_tmp)
    for c in clips_tmp:
        if os.path.exists(c):
            os.remove(c)

    return r.returncode == 0


# ─────────────────────────────────────────
#  PASO 1 — ELIMINAR SILENCIOS (audio-first)
# ─────────────────────────────────────────
def eliminar_silencios(entrada, salida, log=None):
    """
    Elimina silencios usando timestamps de Whisper.
    Corta exactamente entre palabras — nunca en medio de una silaba.
    """
    print("\nEliminando silencios con Whisper...")

    # Detectar duracion total
    r_dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", entrada],
        capture_output=True, text=True
    )
    try:
        duracion_total = float(r_dur.stdout.strip())
    except Exception:
        duracion_total = 0.0

    # Extraer audio para Whisper
    print("   Extrayendo audio para Whisper...")
    tmp_audio = "tmp_sil_whisper.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", entrada, "-vn", "-acodec", "mp3", "-ab", "128k", tmp_audio],
        capture_output=True, text=True
    )

    # Transcribir con Whisper para obtener timestamps de palabras
    print("   Transcribiendo con Whisper para detectar palabras...")
    audio_words = transcribir_con_openai(tmp_audio)

    if os.path.exists(tmp_audio):
        os.remove(tmp_audio)

    if not audio_words:
        print("   Whisper no devolvio palabras — copiando video sin cambios.")
        shutil.copy2(entrada, salida)
        return

    # Construir segmentos a MANTENER basados en timestamps de palabras
    # Un silencio = gap entre fin de palabra N y inicio de palabra N+1
    silencio_min = CONFIG["silencio_minimo"]
    segmentos = []
    silencios_cortados = 0

    for i in range(len(audio_words)):
        w = audio_words[i]
        # Inicio del segmento: inicio de esta palabra
        seg_ini = w["t_ini"]
        # Fin del segmento: fin de esta palabra
        seg_fin = w["t_fin"]

        # Extender hasta la siguiente palabra si el gap es menor al silencio minimo
        if i + 1 < len(audio_words):
            siguiente = audio_words[i + 1]
            gap = siguiente["t_ini"] - w["t_fin"]
            if gap < silencio_min:
                # Gap pequeno — incluir en este segmento
                continue
            else:
                # Gap grande — es un silencio a cortar
                silencios_cortados += 1
                if log:
                    log.registrar("SILENCIO", w["t_fin"], siguiente["t_ini"],
                                  f"gap entre '{w['orig']}' y '{siguiente['orig']}'")

    # Reconstruir segmentos correctamente
    segmentos = []
    i = 0
    while i < len(audio_words):
        seg_ini = audio_words[i]["t_ini"]
        seg_fin = audio_words[i]["t_fin"]

        # Extender segmento mientras el gap con la siguiente sea menor al minimo
        while i + 1 < len(audio_words):
            gap = audio_words[i + 1]["t_ini"] - audio_words[i]["t_fin"]
            if gap < silencio_min:
                i += 1
                seg_fin = audio_words[i]["t_fin"]
            else:
                break
        segmentos.append((seg_ini, seg_fin))
        i += 1

    if not segmentos:
        print("   Sin segmentos detectados.")
        shutil.copy2(entrada, salida)
        return

    tiempo_voz   = sum(f - i for i, f in segmentos)
    tiempo_cortado = duracion_total - tiempo_voz
    print(f"   Palabras: {len(audio_words)} | Segmentos: {len(segmentos)} | Cortado: {tiempo_cortado:.1f}s")

    # Aplicar cortes con recodificacion para cortes frame-perfect
    print("   Aplicando cortes precisos...")
    lista_tmp = "tmp_sil_concat.txt"
    clips_tmp = []
    with open(lista_tmp, "w", encoding="utf-8") as f:
        for idx, (t_s, t_e) in enumerate(segmentos):
            dur = t_e - t_s
            if dur < 0.1:
                continue
            clip_tmp = f"tmp_sil_seg_{idx}.mp4"
            clips_tmp.append(clip_tmp)
            fade_d = min(0.05, dur / 4)
            cmd_corte = [
                "ffmpeg", "-y",
                "-ss", str(max(0, t_s - 0.05)),
                "-to", str(t_e + 0.05),
                "-i", entrada,
                "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                "-af", f"afade=t=in:st=0:d={fade_d},afade=t=out:st={max(0,dur-fade_d):.3f}:d={fade_d}",
                "-c:a", "aac",
                "-avoid_negative_ts", "make_zero", clip_tmp
            ]
            r = subprocess.run(cmd_corte, capture_output=True, text=True)
            if r.returncode == 0:
                f.write(f"file '{clip_tmp}'\n")

    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", lista_tmp, "-c", "copy", salida
    ]
    r2 = subprocess.run(cmd_concat, capture_output=True, text=True)

    if os.path.exists(lista_tmp):
        os.remove(lista_tmp)
    for c in clips_tmp:
        if os.path.exists(c):
            os.remove(c)

    if r2.returncode != 0:
        print(f"   Error concat: {r2.stderr[-200:]}")
        shutil.copy2(entrada, salida)
        return

    print("Silencios eliminados con precision de palabra.")


# ─────────────────────────────────────────
#  PASO 2 — CONVERTIR A 9:16
# ─────────────────────────────────────────
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


def convertir_916(entrada, salida):
    print("\nConvirtiendo a 9:16...")
    res    = CONFIG["resolucion"]
    filtro = (f"scale={res}:force_original_aspect_ratio=decrease,"
              f"pad={res}:(ow-iw)/2:(oh-ih)/2:color=black")
    cmd = ["ffmpeg", "-y", "-i", entrada, "-vf", filtro,
           "-r", str(CONFIG["fps"]), "-c:v", "libx264", "-c:a", "aac", salida]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error: {r.stderr}")
        sys.exit(1)
    print("Convertido a 9:16.")


# ─────────────────────────────────────────
#  PASO 3 — EXTRAER AUDIO
# ─────────────────────────────────────────
def extraer_audio(video, audio, limpia_audio=False):
    print("\nExtrayendo audio...")
    if limpia_audio:
        filtro_audio = "afftdn=nf=-25,highpass=f=80,loudnorm"
        cmd = ["ffmpeg", "-y", "-i", video, "-vn",
               "-af", filtro_audio, "-acodec", "mp3", "-ab", "192k", audio]
    else:
        cmd = ["ffmpeg", "-y", "-i", video, "-vn",
               "-acodec", "mp3", "-ab", "192k", audio]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error: {r.stderr}")
        sys.exit(1)
    print("Audio extraido.")


# ─────────────────────────────────────────
#  TRANSCRIBIR CON OPENAI WHISPER API
# ─────────────────────────────────────────
def transcribir_con_openai(audio_path):
    """
    Transcribe audio usando OpenAI Whisper API en la nube.
    Retorna lista de palabras con timestamps exactos.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == "PEGA_TU_KEY_AQUI":
        print("   Advertencia: API key de OpenAI no configurada.")
        return []

    print("   Transcribiendo con OpenAI Whisper API...")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="es",
                response_format="verbose_json",
                timestamp_granularities=["word"],
                prompt="Transcribe literalmente todo lo que escuchas sin corregir nada. Si alguien dice 'repito' escribe 'repito'. Si alguien dice una palabra incompleta escribela incompleta. Si hay ruido o comentarios fuera de tema escribelos. No interpretes ni corrijas absolutamente nada.",
temperature=0.0
            )

        audio_words = []
        for w in (result.words or []):
            palabra = w.word.strip()
            if palabra:
                audio_words.append({
                    "t_ini": w.start,
                    "t_fin": w.end,
                    "orig":  palabra
                })

        print(f"   Transcripcion: {len(audio_words)} palabras detectadas")
        return audio_words

    except Exception as e:
        print(f"   Error OpenAI Whisper: {e}")
        return []


# ─────────────────────────────────────────
#  TRANSCRIBIR CON WHISPER LOCAL (subtítulos)
# ─────────────────────────────────────────
def transcribir_local(audio, carpeta):
    print("\nTranscribiendo para subtitulos...")
    try:
        import whisper
        modelo = whisper.load_model("medium")
        result  = modelo.transcribe(audio, language="es", word_timestamps=True)
    except ImportError:
        # Fallback a OpenAI API si no hay whisper local
        audio_words = transcribir_con_openai(audio)
        if not audio_words:
            return None, None
        nombre_base = os.path.splitext(os.path.basename(audio))[0]
        srt         = os.path.join(carpeta, nombre_base + ".srt")
        with open(srt, "w", encoding="utf-8") as f:
            for i, w in enumerate(audio_words, 1):
                f.write(f"{i}\n")
                f.write(f"{segundos_a_srt(w['t_ini'])} --> {segundos_a_srt(w['t_fin'])}\n")
                f.write(f"{w['orig']}\n\n")
        print(f"Subtitulos: {srt}")
        return srt, None

    nombre_base = os.path.splitext(os.path.basename(audio))[0]
    srt         = os.path.join(carpeta, nombre_base + ".srt")
    palabras    = []
    for seg in result["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                p = w["word"].strip()
                if p:
                    palabras.append((w["start"], w["end"], p))
        else:
            palabras.append((seg["start"], seg["end"], seg["text"].strip()))

    with open(srt, "w", encoding="utf-8") as f:
        for i, (ini, fin, p) in enumerate(palabras, 1):
            f.write(f"{i}\n")
            f.write(f"{segundos_a_srt(ini)} --> {segundos_a_srt(fin)}\n")
            f.write(f"{p}\n\n")

    print(f"Subtitulos: {srt} ({len(palabras)} palabras)")
    return srt, result


# ─────────────────────────────────────────
#  UTILIDADES SRT
# ─────────────────────────────────────────
def leer_srt(archivo_srt):
    with open(archivo_srt, "r", encoding="utf-8") as f:
        contenido = f.read()
    patron  = r"\d+\s+(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2},\d{3})\s+([\s\S]*?)(?=\n\n|\Z)"
    bloques = re.findall(patron, contenido.strip())
    entradas = []
    for inicio_str, fin_str, texto in bloques:
        texto_limpio = texto.replace("\n", " ").strip()
        entradas.append((tiempo_a_segundos(inicio_str),
                         tiempo_a_segundos(fin_str),
                         texto_limpio))
    return entradas


def tiempo_a_segundos(t):
    t = t.replace(",", ".")
    p = t.split(":")
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])


def segundos_a_srt(s):
    h  = int(s // 3600)
    m  = int((s % 3600) // 60)
    sg = s % 60
    ms = int((sg - int(sg)) * 1000)
    return f"{h:02d}:{m:02d}:{int(sg):02d},{ms:03d}"


# ─────────────────────────────────────────
#  DETECTAR ERRORES CON GPT-4o
# ─────────────────────────────────────────
def detectar_errores_con_gpt4_audio(audio_path, guion_texto):
    """
    Envia el audio directamente a GPT-4o para detectar errores del habla.
    GPT-4o escucha el audio real sin pasar por Whisper.
    """
    if not OPENAI_API_KEY:
        print("   Advertencia: API key de OpenAI no configurada.")
        return []

    print("   GPT-4o analizando audio directamente...")

    try:
        import base64
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        with open(audio_path, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode("utf-8")

        prompt_sistema = """Eres un editor de video profesional con 15 años de experiencia editando clases y workshops en español.

Vas a escuchar el audio de un coach que tiene dislexia del habla. También tienes el guion de lo que debía decir.

Tu tarea es identificar EXACTAMENTE en qué segundos hay errores del habla que deben cortarse.

ERRORES QUE DEBES DETECTAR:
1. El coach dice "repito" — corta desde donde empezó la frase fallida hasta después del "repito". La segunda vez que dice la frase es la correcta.
2. Comentarios fuera de la clase — "silencio papi", "ay espera", "se me olvidó cronometrar", cualquier cosa dirigida a alguien en la sala.
3. Ruidos que no son voz — golpes, movimientos bruscos, sonidos extraños.
4. Tartamudeo — misma sílaba o palabra repetida.
5. Frases incompletas que quedaron colgadas sin terminar.

LO QUE NUNCA DEBES CORTAR:
- Contenido válido de la clase aunque esté parafraseado
- Introducciones de sección como "lección nueve"
- Pausas normales para pensar
- Si tienes duda — NO cortes

RESPONDE ÚNICAMENTE con JSON válido:
{"cortes": [{"inicio": 4.0, "fin": 18.2, "tipo": "repito", "descripcion": "frase fallida con repito"}]}

Si no hay nada que cortar: {"cortes": []}"""

        response = client.chat.completions.create(
            model="gpt-4o-audio-preview",
            modalities=["text"],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{prompt_sistema}\n\nGUION:\n{guion_texto}"
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_data,
                                "format": "mp3"
                            }
                        }
                    ]
                }
            ]
        )

        texto = response.choices[0].message.content.strip()
        if texto.startswith("```"):
            lineas_resp = [l for l in texto.split("\n") if not l.startswith("```")]
            texto = "\n".join(lineas_resp).strip()

        resultado = json.loads(texto)
        cortes_raw = resultado.get("cortes", [])

        if not cortes_raw:
            print("   GPT-4o audio: sin errores detectados.")
            return []

        cortes = []
        for c in cortes_raw:
            t_ini = float(c["inicio"])
            t_fin = float(c["fin"])
            dur = t_fin - t_ini
            tipo = c.get("tipo", "error")
            desc = c.get("descripcion", "")
            if dur >= 0.3:
                print(f"   [Corte] {desc} ({t_ini:.2f}s -> {t_fin:.2f}s, {dur:.1f}s)")
                cortes.append((t_ini, t_fin, desc))

        return cortes

    except json.JSONDecodeError as e:
        print(f"   Respuesta inesperada de GPT-4o: {e}")
        return []
    except Exception as e:
        print(f"   Error con GPT-4o audio: {e}")
        return []


def detectar_errores_con_gpt4(guion_texto, audio_words):
    """
    GPT-4o compara el guion vs transcripcion y devuelve rangos a cortar.
    Optimizado para dislexia del habla.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == "PEGA_TU_KEY_AQUI":
        print("   Advertencia: API key de OpenAI no configurada.")
        return []

    # Construir transcripcion con timestamps
    lineas = [f"  {w['t_ini']:.2f}s  {w['orig']}" for w in audio_words]
    transcripcion_str = "\n".join(lineas)

    prompt = f"""Eres un editor de video profesional con 15 años de experiencia editando clases y workshops. Te doy el guion y la transcripcion real de un coach con dislexia del habla.

Tu unica tarea: identificar los momentos del audio que suenan como errores del habla y marcarlos para cortar. El resultado debe sonar como si el coach hubiera grabado perfecto.

ERRORES QUE DEBES BUSCAR:

1. El coach dice "repito" — significa que se equivoco y va a repetir.
COMO CALCULAR EL CORTE EXACTO:
- Encuentra "repito" en los timestamps
- Mira las palabras que vienen DESPUES — esa es la version correcta
- Busca HACIA ATRAS hasta encontrar la primera palabra de esa version correcta
- El corte empieza 2 segundos ANTES de esa primera palabra — para incluir el silencio previo
- El corte termina en el timestamp de fin de "repito"

Ejemplo:
  4.0s  silencio
  6.3s  "Sales"       ← inicio frase fallida
  6.8s  "de"
  7.1s  "aqui"
  14.2s "repito"      ← señal
  16.0s "Sales"       ← inicio version correcta

Corte: desde 4.3s (2 segundos antes de 6.3s) hasta 15.9s (justo antes del segundo "Sales")
Esto incluye el silencio previo y toda la frase fallida.

2. Comentarios personales fuera de la clase — cosas que le dice a alguien en la sala, comentarios sobre el mismo, interrupciones. Ejemplos: "silencio papi", "ay espera", "se me olvido cronometrar", "perdon". Corta todo eso.

3. Palabras repetidas seguidas sin "repito" — tartamudeo. Conserva la ultima repeticion.

4. Palabras incompletas seguidas de la misma palabra completa.

LO QUE NUNCA DEBES CORTAR:
- Contenido de la clase aunque este parafraseado diferente al guion
- Introducciones como "leccion nueve", "dimension cuatro"
- Pausas normales
- Si tienes duda — NO cortes

Analiza la transcripcion como lo haria un editor humano inteligente que escucha el audio y decide que suena mal para el espectador final. Tu trabajo es limpiar el audio de un coach hispanohablante que tiene dislexia del habla.

Tienes dos insumos:
1. El GUION — lo que el coach tenía planeado decir
2. La TRANSCRIPCION con timestamps — lo que realmente dijo

Tu tarea NO es verificar que el audio coincida palabra por palabra con el guion. Tu tarea es identificar los errores del habla — los momentos donde el coach tropezó, se interrumpió, se repitió o dijo algo fuera de contexto — y marcarlos para cortar.

Usa el guion para ENTENDER el contenido y el contexto, no para comparar literalmente. El coach puede parafrasear, reordenar palabras, agregar ejemplos o hacer transiciones propias — todo eso es válido y NO se corta.

PIENSA COMO UN EDITOR HUMANO: si estuvieras viendo el video, ¿qué momentos sonarían raros, repetidos o fuera de lugar para el espectador? Eso es lo que cortas.

CONTEXTO IMPORTANTE:
- El guion es una GUIA de contenido, no un script palabra por palabra
- El creador puede introducir secciones con frases como "lección nueve", "punto uno", "ahora bien" — estas son válidas aunque no estén en el guion
- Las variaciones naturales de fraseo (decir "ustedes" en vez de "mujeres", reordenar palabras) NO se cortan
- Solo se corta lo que claramente interrumpe el flujo o es un error del habla

PATRON PRINCIPAL — LA PALABRA "REPITO":
Cuando el creador dice "repito", significa que cometió un error en la frase anterior y va a decirla correctamente. Se corta TODO desde el inicio de la frase fallida hasta la palabra "repito" inclusive.
Ejemplo:
  - "Sales de aquí con tres sistemas que la mayoría repito Sales de aquí con tres sistemas que la mayoría de mujeres"
  - Cortar: "Sales de aquí con tres sistemas que la mayoría repito"
  - Conservar: "Sales de aquí con tres sistemas que la mayoría de mujeres"
La palabra "repito" SIEMPRE es señal de corte — nunca se deja en el audio final.

Tu trabajo es revisar la transcripcion del audio y compararla con el guion original. Usa tu criterio como editor humano experto para identificar TODO lo que suena mal, raro, o que no corresponde al guion.

GUION ORIGINAL (lo que DEBIA decir):
{guion_texto}

TRANSCRIPCION DEL AUDIO con timestamps en segundos (lo que REALMENTE dijo):
{transcripcion_str}

QUE CORTAR — SOLO ERRORES DEL HABLA:

1. PATRON "REPITO" — el mas importante:
El coach usa "repito" como señal explicita de que va a volver a decir una frase correctamente.
COMO IDENTIFICAR EL CORTE:
- Encuentra "repito" en los timestamps
- Mira las palabras que vienen DESPUES del "repito" — esa es la version correcta
- Busca hacia ATRAS hasta encontrar donde empezo a decir ESA MISMA frase — cuando aparece la primera palabra de la version correcta por primera vez
- Corta desde ahi hasta el final de "repito" inclusive
- La version correcta que viene despues queda intacta

Ejemplo real:
  6.3s  "Sales"
  6.8s  "de"
  7.1s  "aqui"
  7.5s  "con"
  7.9s  "tres"
  8.3s  "repito"    ← señal
  9.0s  "Sales"     ← inicio version correcta
  9.5s  "de"
  9.8s  "aqui"
  10.2s "con"
  10.6s "tres"
  11.0s "sistemas"

Cortar: 6.3s → 9.0s (desde el primer "Sales" hasta antes del segundo "Sales")
Conservar: desde 9.0s en adelante

2. COMENTARIOS FUERA DEL CONTENIDO:
Frases que claramente no son parte de la clase — comentarios a alguien en la sala, interrupciones propias, observaciones personales.
Ejemplos tipicos: "silencio papi", "ay espera", "un momento", "perdon", "me equivoque", "ahi se me olvido cronometrar"
Cortar la frase completa incluyendo la pausa que genera.

3. TARTAMUDEO:
La misma silaba o palabra repetida 2 o mas veces seguidas.
Ejemplo: "y y y entonces" — cortar los primeros "y y", dejar el ultimo "y entonces"

4. PALABRA TRABADA:
Palabra incompleta seguida inmediatamente de la misma palabra completa, a menos de 1.5 segundos.
Ejemplo: "siste... sistemas" — cortar "siste..."

QUE NUNCA CORTAR:
- Contenido del guion aunque este parafraseado o con palabras diferentes
- Introducciones de seccion como "leccion nueve", "dimension cuatro", "punto siguiente"
- Transiciones propias del coach aunque no esten en el guion
- Pausas normales para pensar
- Cuando tengas duda — NO cortes. Es mejor dejar algo que no deberia estar que cortar algo valido.

REGLA DE ORO: Solo cortas errores del habla. Nunca cortas contenido.

RESPONDE UNICAMENTE con JSON valido, sin explicaciones, sin markdown:
{{"cortes": [{{"inicio": 34.80, "fin": 38.12, "tipo": "repito", "descripcion": "frase repetida con repito"}}]}}

Si no hay nada que cortar: {{"cortes": []}}"""

    try:
        from openai import OpenAI
        print("   GPT-4o analizando guion vs audio...")
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        texto = response.choices[0].message.content.strip()

        # Limpiar markdown si GPT lo agrega
        if texto.startswith("```"):
            lineas_resp = [l for l in texto.split("\n") if not l.startswith("```")]
            texto = "\n".join(lineas_resp).strip()

        resultado  = json.loads(texto)
        cortes_raw = resultado.get("cortes", [])

        if not cortes_raw:
            print("   GPT-4o: sin errores detectados.")
            return []

        cortes = []
        for c in cortes_raw:
            t_ini = float(c["inicio"])
            t_fin = float(c["fin"])
            tipo  = c.get("tipo", "error")
            desc  = c.get("descripcion", "")
            # Retroceder 2 segundos para incluir silencio y contexto previo
            if tipo in ["repito", "intento_fallido"]:
                t_ini = max(0, t_ini - 2.0)
            dur = t_fin - t_ini
            if dur >= 0.3:
                emoji = "Repeticion" if tipo == "intento_fallido" else "Corte"
                print(f"   [{emoji}] {desc} ({t_ini:.2f}s -> {t_fin:.2f}s, {dur:.1f}s)")
                cortes.append((t_ini, t_fin, desc))

        return cortes

    except json.JSONDecodeError as e:
        print(f"   Respuesta inesperada de GPT-4o: {e}")
        return []
    except Exception as e:
        print(f"   Error con GPT-4o: {e}")
        return []


# ─────────────────────────────────────────
#  APLICAR CORTES CON FADE DE AUDIO
# ─────────────────────────────────────────
def aplicar_cortes_con_fade(video_entrada, segmentos, video_salida):
    if not segmentos:
        print("   Sin segmentos para mantener.")
        return False

    fade_s    = CONFIG["fade_audio_ms"] / 1000.0
    lista_tmp = os.path.join(os.path.dirname(video_entrada) or ".", "tmp_fade_concat.txt")
    clips_tmp = []

    print(f"   Aplicando fade de {CONFIG['fade_audio_ms']}ms en cada corte...")

    with open(lista_tmp, "w", encoding="utf-8") as f:
        for idx, (t_s, t_e) in enumerate(segmentos):
            clip_tmp = f"tmp_fade_seg_{idx}.mp4"
            clips_tmp.append(clip_tmp)
            duracion = t_e - t_s
            if duracion <= 0:
                continue
            filtro_audio = (
                f"afade=t=in:st=0:d={fade_s},"
                f"afade=t=out:st={max(0, duracion - fade_s):.3f}:d={fade_s}"
            )
            cmd_corte = [
                "ffmpeg", "-y",
                "-ss", str(t_s), "-to", str(t_e),
                "-i", video_entrada,
                "-c:v", "libx264", "-af", filtro_audio, "-c:a", "aac",
                "-avoid_negative_ts", "make_zero", clip_tmp
            ]
            r = subprocess.run(cmd_corte, capture_output=True, text=True)
            if r.returncode == 0:
                f.write(f"file '{clip_tmp}'\n")

    cmd_concat = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                  "-i", lista_tmp, "-c", "copy", video_salida]
    r = subprocess.run(cmd_concat, capture_output=True, text=True)

    if os.path.exists(lista_tmp):
        os.remove(lista_tmp)
    for c in clips_tmp:
        if os.path.exists(c):
            os.remove(c)

    if r.returncode != 0:
        print(f"   Error FFmpeg: {r.stderr[-300:]}")
        return False

    print(f"   Video con cortes suaves listo.")
    return True


# ─────────────────────────────────────────
#  LIMPIAR ERRORES CON GUION
# ─────────────────────────────────────────
def limpiar_errores_con_guion(video_entrada, guion_txt, video_salida,
                               log=None, limpia_audio=False):
    print("\nAnalizando guion vs grabacion con GPT-4o...")

    with open(guion_txt, "r", encoding="utf-8") as f:
        guion_texto = f.read()
    print(f"   Guion cargado: {len(guion_texto.split())} palabras")

    tmp_audio = "tmp_guion_check.mp3"
    extraer_audio(video_entrada, tmp_audio, limpia_audio=limpia_audio)

    # Transcribir con Whisper API
    audio_words = transcribir_con_openai(tmp_audio)

    # Detectar cortes con motor preciso (ancla de silencios)
    if _CORTES_PRECISOS_OK and audio_words:
        print("   Usando motor de cortes precisos...")
        cortes = calcular_cortes_precisos(
            guion_texto, audio_words, tmp_audio, OPENAI_API_KEY
        )
    else:
        print("   Fallback: GPT-4o audio directo...")
        cortes = detectar_errores_con_gpt4_audio(tmp_audio, guion_texto)

    if os.path.exists(tmp_audio):
        os.remove(tmp_audio)

    if not cortes:
        print("   Sin errores detectados - video limpio.")
        return video_entrada

    # Registrar en log
    if log:
        for t_ini, t_fin, desc in cortes:
            log.registrar("ERROR_IA", t_ini, t_fin, desc)

    print(f"\n   Total cortes: {len(cortes)}")

    # Ordenar y fusionar cortes
    cortes.sort(key=lambda x: x[0])
    cortes_limpios = []
    for c in cortes:
        if cortes_limpios and c[0] < cortes_limpios[-1][1]:
            cortes_limpios[-1] = (cortes_limpios[-1][0],
                                  max(c[1], cortes_limpios[-1][1]),
                                  cortes_limpios[-1][2])
        else:
            cortes_limpios.append(list(c))

    # Calcular segmentos a MANTENER
    duracion_total = audio_words[-1]["t_fin"] + 0.5
    segmentos      = []
    cursor         = 0.0
    for t_ini_c, t_fin_c, _ in cortes_limpios:
        if cursor < t_ini_c:
            segmentos.append((cursor, t_ini_c))
        cursor = t_fin_c
    if cursor < duracion_total:
        segmentos.append((cursor, duracion_total))

    if not segmentos:
        print("   No quedaron segmentos.")
        return video_entrada

    exito = aplicar_cortes_con_fade(video_entrada, segmentos, video_salida)
    if not exito:
        print("   Fade falló, aplicando cortes sin fade...")
        exito = aplicar_cortes_a_original(video_entrada, segmentos, video_salida)
    return video_salida if exito else video_entrada


# ─────────────────────────────────────────
#  SUBTITULOS — ESTILO 001
# ─────────────────────────────────────────
def quemar_estilo_001(video, srt, salida, fuente="montserrat"):
    print(f"\nAplicando subtitulos - fuente: {fuente.upper()}...")

    from PIL import Image, ImageDraw

    palabras_srt = leer_srt(srt)
    chunks_raw   = []
    i = 0
    while i < len(palabras_srt):
        grupo    = palabras_srt[i:i+3]
        t_ini    = grupo[0][0]
        t_fin    = grupo[-1][1]
        palabras = [p[2] for p in grupo]
        t_pals   = [p[0] for p in grupo]
        chunks_raw.append((t_ini, t_fin, palabras, t_pals))
        i += 3

    clip = VideoFileClip(video)
    W, H = clip.w, clip.h
    fps  = clip.fps

    TAM_NORMAL       = 68
    TAM_GRANDE       = 96
    COLOR            = (255, 255, 255, 255)
    PECHO_Y          = int(H * 0.62)
    DURACION_ENTRADA = 0.12

    fn = cargar_fuente_pil(fuente, TAM_NORMAL, bold=False)
    fb = cargar_fuente_pil(fuente, TAM_GRANDE, bold=True)

    eventos = []
    for t_ini, t_fin, palabras, t_pals in chunks_raw:
        if not palabras:
            continue
        img_tmp = Image.new("RGB", (W, H))
        d_tmp   = ImageDraw.Draw(img_tmp)

        def medir(txt, fuente_pil):
            bb = d_tmp.textbbox((0, 0), txt, font=fuente_pil)
            return bb[2] - bb[0], bb[3] - bb[1]

        l1     = " ".join(palabras[:2]) if len(palabras) >= 2 else palabras[0]
        w1, h1 = medir(l1, fn)
        l2, w2, h2 = None, 0, 0
        if len(palabras) >= 3:
            l2     = palabras[2]
            w2, h2 = medir(l2, fb)

        eventos.append({
            "ini": t_ini, "fin": t_fin,
            "palabras": palabras, "t_palabra": t_pals,
            "linea1": l1, "w1": w1, "h1": h1,
            "linea2": l2, "w2": w2, "h2": h2,
        })

    def slide_offset(t, t_ap, altura):
        elapsed = t - t_ap
        if elapsed < 0:
            return altura + 20
        if elapsed >= DURACION_ENTRADA:
            return 0
        p = elapsed / DURACION_ENTRADA
        p = 1 - (1 - p) ** 2
        return int((1 - p) * (altura + 20))

    def hacer_frame(t):
        frame = clip.get_frame(t)
        img   = Image.fromarray(frame).convert("RGBA")
        chunk = next((ev for ev in eventos if ev["ini"] <= t < ev["fin"]), None)
        if chunk is None:
            return np.array(img.convert("RGB"))

        draw     = ImageDraw.Draw(img)
        palabras = chunk["palabras"]
        t_pal    = chunk["t_palabra"]
        gap      = 8
        y_base_l2 = PECHO_Y
        y_base_l1 = y_base_l2 - chunk["h2"] - gap - chunk["h1"]

        if t >= t_pal[0]:
            if len(palabras) >= 2 and t >= t_pal[1]:
                off = slide_offset(t, t_pal[1], chunk["h1"])
                x1  = (W - chunk["w1"]) // 2
                draw.text((x1, y_base_l1 - off), chunk["linea1"], font=fn, fill=COLOR)
            else:
                img_m = Image.new("RGB", (10, 10))
                dm    = ImageDraw.Draw(img_m)
                bb    = dm.textbbox((0, 0), palabras[0], font=fn)
                w_p1  = bb[2] - bb[0]
                off   = slide_offset(t, t_pal[0], chunk["h1"])
                x1    = (W - w_p1) // 2
                draw.text((x1, y_base_l1 - off), palabras[0], font=fn, fill=COLOR)

        if chunk["linea2"] and len(t_pal) >= 3 and t >= t_pal[2]:
            off = slide_offset(t, t_pal[2], chunk["h2"])
            x2  = (W - chunk["w2"]) // 2
            draw.text((x2, y_base_l2 - chunk["h2"] - off),
                      chunk["linea2"], font=fb, fill=COLOR)

        return np.array(img.convert("RGB"))

    print("   Renderizando frame a frame...")
    clip_final = VideoClip(hacer_frame, duration=clip.duration)
    clip_final = clip_final.with_audio(clip.audio)
    clip_final.write_videofile(salida, fps=fps,
                               codec="libx264", audio_codec="aac", logger=None)
    clip.close()
    print("Subtitulos aplicados.")



# ─────────────────────────────────────────
#  VOZ PROFESIONAL — calibrada para boya + Sony ZVE10
# ─────────────────────────────────────────
def aplicar_voz_pro(entrada, salida):
    print("\nAplicando procesamiento de voz profesional...")
    filtro = (
        "equalizer=f=60:width_type=o:width=2:g=4,"
        "equalizer=f=80:width_type=o:width=2:g=7,"
        "equalizer=f=150:width_type=o:width=2:g=5,"
        "equalizer=f=300:width_type=o:width=1:g=3,"
        "equalizer=f=2000:width_type=o:width=1:g=-4,"
        "equalizer=f=5000:width_type=o:width=2:g=-6,"
        "equalizer=f=8000:width_type=o:width=2:g=-7,"
        "acompressor=threshold=-20dB:ratio=3:attack=10:release=150:makeup=4,"
        "loudnorm=I=-14:TP=-1.5:LRA=11"
    )
    cmd = ["ffmpeg", "-y", "-i", entrada, "-af", filtro, "-c:v", "copy", salida]
    import subprocess
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error voz pro: {r.stderr[-200:]}")
        return False
    print("Voz profesional aplicada.")
    return True

# ─────────────────────────────────────────
#  FLUJO PRINCIPAL
# ─────────────────────────────────────────
def editar_reel(nombre_archivo, fuente="montserrat", guion=None,
                subtitulos=False, solo_limpiar=False, limpia_audio=False, color_workshop=False, cortes_manual=None, voz_pro=False, sin_silencios=False):

    print(f"\n{'='*55}")
    print(f"  EDITOR JOSUE v7.0 (OpenAI Whisper + GPT-4o)")
    print(f"  EDITANDO: {nombre_archivo}")
    if guion:        print(f"  Guion: {guion}")
    if subtitulos:   print(f"  Subtitulos: activados")
    if solo_limpiar: print(f"  Modo: solo limpiar")
    if limpia_audio: print(f"  Limpieza de ruido: activada")
    print(f"{'='*55}\n")

    ruta_entrada = os.path.join(CARPETA_INPUT, nombre_archivo)
    if not os.path.exists(ruta_entrada):
        print(f"Error: No encontre: {ruta_entrada}")
        sys.exit(1)

    nombre_base   = os.path.splitext(nombre_archivo)[0]
    tmp_proxy     = f"tmp_{nombre_base}_proxy.mp4"
    tmp_sin_sil   = f"tmp_{nombre_base}_sin_sil.mp4"
    tmp_limpio    = f"tmp_{nombre_base}_limpio.mp4"
    tmp_916       = f"tmp_{nombre_base}_916.mp4"
    tmp_audio     = f"tmp_{nombre_base}.mp3"
    sufijo        = fuente if subtitulos else "limpio"
    archivo_final = os.path.join(CARPETA_OUTPUT, f"{nombre_base}_{sufijo}.mp4")

    # Detectar si el video es grande (>500MB) para usar proxy
    tam_mb = os.path.getsize(ruta_entrada) / (1024 * 1024)
    usar_proxy = False  # desactivado � audio-first es mas eficiente
    if usar_proxy:
        print(f"   Video grande ({tam_mb:.0f}MB) — usando proxy workflow")

    log = LogEdicion(nombre_archivo)

    try:
        # PASO 1: Eliminar silencios
        if sin_silencios:
            print("\nSaltando eliminacion de silencios (video ya editado).")
            shutil.copy2(ruta_entrada, tmp_sin_sil)
        elif usar_proxy:
            crear_proxy(ruta_entrada, tmp_proxy)
            eliminar_silencios(tmp_proxy, tmp_sin_sil, log=log)
        else:
            eliminar_silencios(ruta_entrada, tmp_sin_sil, log=log)

        # PASO 2: Cortes manuales o GPT-4o
        if cortes_manual and os.path.exists(cortes_manual):
            print(f"\nAplicando cortes manuales desde {cortes_manual}...")
            segmentos_corte = []
            with open(cortes_manual, "r", encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if not linea or linea.startswith("#"):
                        continue
                    partes = linea.split("-")
                    if len(partes) == 2:
                        t_ini = float(partes[0])
                        t_fin = float(partes[1])
                        segmentos_corte.append((t_ini, t_fin, "corte manual"))
            if segmentos_corte:
                # Anclar cada corte manual al silencio más cercano
                from cortes_precisos import extraer_mapa_silencios, anclar_a_silencio_anterior, anclar_fin_a_silencio
                tmp_audio_cortes = "tmp_cortes_manual.mp3"
                extraer_audio(tmp_sin_sil, tmp_audio_cortes)
                silencios = extraer_mapa_silencios(tmp_audio_cortes)
                if os.path.exists(tmp_audio_cortes):
                    os.remove(tmp_audio_cortes)
                cortes_anclados = []
                for t_i, t_f, desc in segmentos_corte:
                    t_i_ancla = anclar_a_silencio_anterior(t_i, silencios, ventana_busqueda=3.0)
                    t_f_ancla = anclar_a_silencio_anterior(t_f, silencios, ventana_busqueda=3.0)
                    print(f"   [manual] {t_i}s-{t_f}s → ancla: {t_i_ancla:.2f}s-{t_f_ancla:.2f}s")
                    cortes_anclados.append((t_i_ancla, t_f_ancla))
                cortes_ordenados = sorted(cortes_anclados)
                segmentos_mantener = []
                cursor = 0.0
                for t_i, t_f in cortes_ordenados:
                    if cursor < t_i:
                        segmentos_mantener.append((cursor, t_i))
                    cursor = t_f
                segmentos_mantener.append((cursor, 99999.0))
                exito = aplicar_cortes_con_fade(tmp_sin_sil, segmentos_mantener, tmp_limpio)
                video_para_procesar = tmp_limpio if exito else tmp_sin_sil
            else:
                video_para_procesar = tmp_sin_sil

        elif guion:
            ruta_guion = guion
            if not os.path.exists(ruta_guion):
                ruta_guion_alt = os.path.join(CARPETA_INPUT, guion)
                if os.path.exists(ruta_guion_alt):
                    ruta_guion = ruta_guion_alt

            if not os.path.exists(ruta_guion):
                print(f"Guion no encontrado: {guion}")
                video_para_procesar = tmp_sin_sil
            else:
                video_para_procesar = limpiar_errores_con_guion(
                    tmp_sin_sil, ruta_guion, tmp_limpio,
                    log=log, limpia_audio=limpia_audio
                )
        else:
            video_para_procesar = tmp_sin_sil

        # PASO 2.5: Voz profesional
        if voz_pro:
            tmp_voz = f'tmp_{nombre_base}_voz.mp4'
            print('Iniciando voz profesional...')
            if aplicar_voz_pro(video_para_procesar, tmp_voz):
                video_para_procesar = tmp_voz
                print('Voz profesional aplicada correctamente.')

        # PASO 3: Convertir o guardar
        if solo_limpiar:
            if color_workshop:
                tmp_color = f"tmp_{nombre_base}_color.mp4"
                aplicar_color_workshop(video_para_procesar, tmp_color)
                video_para_procesar = tmp_color
            # Re-codificar siempre a MP4 compatible (H264+AAC)
            print("   Copiando a MP4 compatible...")
            cmd_reenc = [
                "ffmpeg", "-y", "-i", video_para_procesar,
                "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "192k", archivo_final
            ]
            r_reenc = subprocess.run(cmd_reenc, capture_output=True, text=True)
            if r_reenc.returncode != 0:
                print(f"   Error re-codificando: {r_reenc.stderr[-200:]}")
                shutil.copy2(video_para_procesar, archivo_final)
            if color_workshop and os.path.exists(f"tmp_{nombre_base}_color.mp4"):
                os.remove(f"tmp_{nombre_base}_color.mp4")
            print(f"\nVideo limpio guardado: {archivo_final}")
        else:
            convertir_916(video_para_procesar, tmp_916)
            if subtitulos:
                extraer_audio(tmp_916, tmp_audio)
                archivo_srt, _ = transcribir_local(tmp_audio, CARPETA_SUBS)
                if archivo_srt:
                    quemar_estilo_001(tmp_916, archivo_srt, archivo_final, fuente)
                else:
                    shutil.copy2(tmp_916, archivo_final)
            else:
                shutil.copy2(tmp_916, archivo_final)

        log.guardar()

        print(f"\n{'='*55}")
        print(f"  LISTO! v7.0")
        print(f"  {archivo_final}")
        if guion:        print(f"  Errores limpiados con GPT-4o")
        if subtitulos:   print(f"  Subtitulos aplicados")
        if limpia_audio: print(f"  Audio limpiado")
        if color_workshop: print(f"  Color workshop: activado")
        print(f"{'='*55}\n")

    finally:
        for tmp in [tmp_proxy, tmp_sin_sil, tmp_limpio, tmp_916, tmp_audio]:
            if os.path.exists(tmp):
                os.remove(tmp)


# ─────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Editor de Video Josue v7.0 - OpenAI Whisper + GPT-4o",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
EJEMPLOS:
  py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --solo-limpiar
  py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt
  py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --subtitulos
  py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --limpia-audio
        """
    )
    parser.add_argument("modo", choices=["reel", "subtitulos"])
    parser.add_argument("archivo", nargs="?", default=None)
    parser.add_argument("--fuente",
        choices=["montserrat","bebas","anton","oswald","outfit","inter","arial"],
        default=FUENTE_DEFECTO)
    parser.add_argument("--guion",        default=None)
    parser.add_argument("--subtitulos",   action="store_true")
    parser.add_argument("--solo-limpiar", action="store_true")
    parser.add_argument("--limpia-audio", action="store_true")
    parser.add_argument("--voz-pro", action="store_true", help="Voz profesional estilo podcast")
    parser.add_argument("--color-workshop", action="store_true")
    parser.add_argument("--cortes", default=None)
    parser.add_argument("--sin-silencios", action="store_true", help="No eliminar silencios (video ya editado)")

    args = parser.parse_args()

    if args.archivo is None:
        print("Error: necesitas indicar el nombre del video.")
        sys.exit(1)

    verificar_dependencias()
    crear_carpetas()

    if args.modo == "reel":
        editar_reel(
            args.archivo, args.fuente,
            guion=args.guion,
            subtitulos=args.subtitulos,
            solo_limpiar=args.solo_limpiar,
            limpia_audio=args.limpia_audio,
            voz_pro=getattr(args, "voz_pro", False),
            color_workshop=getattr(args, "color_workshop", False),
            cortes_manual=args.cortes,
            sin_silencios=getattr(args, "sin_silencios", False)
        )


if __name__ == "__main__":
    main()





