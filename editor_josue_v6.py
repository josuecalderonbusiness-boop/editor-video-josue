#!/usr/bin/env python3
# ============================================================
#   EDITOR DE VIDEO PERSONAL — JOSUÉ CALDERÓN  v6.0
#   Sistema automático: silencio + subtítulos + exportación
#   + Limpieza de errores con IA (Claude API)
#   + Detección de patrón "repito / me equivoqué"
#   + Fade de audio en cortes (transiciones suaves)
#   + Log detallado de todos los cortes aplicados
#   Código Soberana · 2026
#
#   USO:
#   py -3.11 editor_josue_v6.py reel video.mp4
#   py -3.11 editor_josue_v6.py reel video.mp4 --fuente bebas
#   py -3.11 editor_josue_v6.py reel video.mp4 --guion guion.txt
#   py -3.11 editor_josue_v6.py reel video.mp4 --fuente montserrat --guion guion.txt
#
#   FUENTES DISPONIBLES:
#   montserrat  → moderna, versátil (defecto)
#   bebas       → impacto, todo caps, muy limpia
#   anton       → máximo impacto, agresiva
#   oswald      → condensada, fuerte
#   outfit      → limpia y suave
#   playfair    → elegante, serif
#   inter       → la más legible
#   arial       → clásica de Windows
# ============================================================

import subprocess
import sys
import os
import re
import json
import shutil
import argparse
import datetime

# Imports globales moviepy 2.x y numpy
try:
    import numpy as np
    from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip, VideoClip
    _MOVIEPY_OK = True
except Exception:
    _MOVIEPY_OK = False
    np = None

# ─────────────────────────────────────────
#  ⚠️  TU API KEY DE CLAUDE — PONLA AQUÍ
#  Consíguela en: https://console.anthropic.com
# ─────────────────────────────────────────
CLAUDE_API_KEY = "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"   

# ─────────────────────────────────────────
#  PALABRAS CLAVE QUE INDICAN REPETICIÓN
#  El hablante dice estas palabras cuando
#  se equivoca y va a repetir la línea.
# ─────────────────────────────────────────
PALABRAS_REPETICION = [
    "repito", "perdón", "perdon", "espera", "un momento",
    "me equivoqué", "me equivoque", "de nuevo", "otra vez",
    "voy de nuevo", "vamos de nuevo", "empiezo de nuevo",
    "lo repito", "no", "esperen", "corte", "corten",
    "mejor dicho", "o sea", "quiero decir",
]

# ─────────────────────────────────────────
#  MAPA DE FUENTES
# ─────────────────────────────────────────
FUENTES_DIR = os.path.join(os.path.expanduser("~"),
              "AppData", "Local", "Microsoft", "Windows", "Fonts")

FUENTES_MAPA = {
    "montserrat": {
        "normal": ["Montserrat-Regular.ttf", "Montserrat-SemiBold.ttf"],
        "bold":   ["Montserrat-Bold.ttf", "Montserrat-ExtraBold.ttf", "Montserrat-Black.ttf"],
    },
    "bebas": {
        "normal": ["BebasNeue-Regular.ttf"],
        "bold":   ["BebasNeue-Regular.ttf"],
    },
    "anton": {
        "normal": ["Anton-Regular.ttf"],
        "bold":   ["Anton-Regular.ttf"],
    },
    "oswald": {
        "normal": ["Oswald-Regular.ttf", "Oswald-SemiBold.ttf"],
        "bold":   ["Oswald-Bold.ttf", "Oswald-SemiBold.ttf"],
    },
    "outfit": {
        "normal": ["Outfit-Regular.ttf", "Outfit-SemiBold.ttf"],
        "bold":   ["Outfit-Bold.ttf", "Outfit-Black.ttf"],
    },
    "playfair": {
        "normal": ["PlayfairDisplay-Regular.ttf"],
        "bold":   ["PlayfairDisplay-Bold.ttf", "PlayfairDisplay-ExtraBold.ttf"],
    },
    "inter": {
        "normal": ["Inter-Regular.ttf", "Inter-SemiBold.ttf"],
        "bold":   ["Inter-Bold.ttf"],
    },
    "arial": {
        "normal": ["arial.ttf",   "C:/Windows/Fonts/arial.ttf",   "calibri.ttf"],
        "bold":   ["arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf", "calibrib.ttf"],
    },
}

FUENTE_DEFECTO = "montserrat"

# ─────────────────────────────────────────
#  CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────
CONFIG = {
    "silencio_minimo": 0.5,
    "umbral_db":       -40,
    "resolucion":      "1080:1920",
    "fps":             30,
    "idioma_whisper":  "es",
    "fade_audio_ms":   80,       # milisegundos de fade in/out en cada corte
    "margen_corte":    0.08,     # segundos de colchón antes/después de cada segmento
}

CARPETA_INPUT  = "input"
CARPETA_OUTPUT = "output"
CARPETA_SUBS   = "subtitulos"
CARPETA_LOGS   = "logs"


# ─────────────────────────────────────────
#  LOG DE EDICIÓN
# ─────────────────────────────────────────
class LogEdicion:
    """Registra todos los cortes aplicados al video para revisión posterior."""

    def __init__(self, nombre_video):
        self.nombre_video = nombre_video
        self.inicio       = datetime.datetime.now()
        self.entradas     = []

    def registrar(self, tipo, t_ini, t_fin, detalle=""):
        self.entradas.append({
            "tipo":   tipo,
            "inicio": round(t_ini, 3),
            "fin":    round(t_fin, 3),
            "dur":    round(t_fin - t_ini, 3),
            "detalle": detalle,
        })

    def guardar(self):
        os.makedirs(CARPETA_LOGS, exist_ok=True)
        ts    = self.inicio.strftime("%Y%m%d_%H%M%S")
        base  = os.path.splitext(self.nombre_video)[0]
        ruta  = os.path.join(CARPETA_LOGS, f"{base}_log_{ts}.txt")

        total_cortado = sum(e["dur"] for e in self.entradas)

        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"LOG DE EDICIÓN — {self.nombre_video}\n")
            f.write(f"Fecha : {self.inicio.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Cortes: {len(self.entradas)}\n")
            f.write(f"Tiempo cortado total: {total_cortado:.1f}s\n")
            f.write("=" * 60 + "\n\n")

            for i, e in enumerate(self.entradas, 1):
                f.write(f"[{i:03d}] {e['tipo']}\n")
                f.write(f"      {e['inicio']:.2f}s → {e['fin']:.2f}s  "
                        f"(duración: {e['dur']:.2f}s)\n")
                if e["detalle"]:
                    f.write(f"      Palabras: \"{e['detalle']}\"\n")
                f.write("\n")

        print(f"\n📋 Log guardado: {ruta}")
        print(f"   Total cortado: {total_cortado:.1f}s en {len(self.entradas)} corte(s)")
        return ruta


# ─────────────────────────────────────────
#  RESOLVER RUTA DE FUENTE
# ─────────────────────────────────────────
def resolver_fuente(nombre_fuente, bold=False):
    nombre_fuente = nombre_fuente.lower()
    if nombre_fuente not in FUENTES_MAPA:
        nombre_fuente = FUENTE_DEFECTO

    tipo     = "bold" if bold else "normal"
    opciones = FUENTES_MAPA[nombre_fuente][tipo]

    for opcion in opciones:
        if os.path.isabs(opcion) and os.path.exists(opcion):
            return opcion
        ruta_user = os.path.join(FUENTES_DIR, opcion)
        if os.path.exists(ruta_user):
            return ruta_user
        ruta_sys = os.path.join("C:/Windows/Fonts", opcion)
        if os.path.exists(ruta_sys):
            return ruta_sys
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

    for fallback in (["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf"]
                     if bold else
                     ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf"]):
        try:
            return ImageFont.truetype(fallback, tam)
        except Exception:
            continue

    from PIL import ImageFont
    return ImageFont.load_default()


# ─────────────────────────────────────────
#  VERIFICAR DEPENDENCIAS
# ─────────────────────────────────────────
def verificar_dependencias():
    if shutil.which("ffmpeg") is None:
        print("\n❌ Falta FFmpeg. Instala con: winget install ffmpeg")
        sys.exit(1)
    try:
        import whisper as _w
    except ImportError:
        print("\n❌ Falta whisper. Instala con:")
        print("   py -3.11 -m pip install openai-whisper")
        sys.exit(1)
    if not _MOVIEPY_OK:
        print("\n❌ Faltan librerías. Instala con:")
        print("   py -3.11 -m pip install moviepy numpy pillow")
        sys.exit(1)
    try:
        from PIL import Image
    except ImportError:
        print("\n❌ Falta pillow. Instala con:")
        print("   py -3.11 -m pip install pillow")
        sys.exit(1)
    print("✅ Dependencias verificadas.")


def crear_carpetas():
    for carpeta in [CARPETA_INPUT, CARPETA_OUTPUT, CARPETA_SUBS, CARPETA_LOGS]:
        os.makedirs(carpeta, exist_ok=True)
    print("✅ Carpetas listas.")


# ─────────────────────────────────────────
#  PASO 1 — ELIMINAR SILENCIOS
# ─────────────────────────────────────────
def eliminar_silencios(entrada, salida, log: LogEdicion = None):
    print("\n🔇 Eliminando silencios...")

    umbral_db    = CONFIG["umbral_db"]
    silencio_min = CONFIG["silencio_minimo"]
    margen       = CONFIG["margen_corte"]

    clip      = VideoFileClip(entrada)
    audio     = clip.audio
    fps_audio = audio.fps
    muestras  = audio.to_soundarray(fps=fps_audio)

    if muestras.ndim > 1:
        muestras = muestras.mean(axis=1)

    ventana  = int(fps_audio * 0.02)
    n_vent   = len(muestras) // ventana
    volumen  = []
    for i in range(n_vent):
        chunk = muestras[i * ventana:(i + 1) * ventana]
        rms   = np.sqrt(np.mean(chunk ** 2))
        db    = 20 * np.log10(rms + 1e-10)
        volumen.append(db)

    dv        = 0.02
    tiene_voz = [v > umbral_db for v in volumen]

    segmentos = []
    en_voz    = False
    inicio    = 0
    for i, voz in enumerate(tiene_voz):
        t = i * dv
        if voz and not en_voz:
            inicio = t
            en_voz = True
        elif not voz and en_voz:
            fin = t
            if (fin - inicio) > 0.1:
                segmentos.append((inicio, fin))
            en_voz = False
    if en_voz:
        segmentos.append((inicio, clip.duration))

    unidos = []
    for seg in segmentos:
        if unidos and (seg[0] - unidos[-1][1]) < silencio_min:
            unidos[-1] = (unidos[-1][0], seg[1])
        else:
            unidos.append(list(seg))

    if not unidos:
        print("⚠️  Sin voz detectada. Usando video original.")
        clip.write_videofile(salida, codec="libx264", audio_codec="aac",
                             logger=None, fps=CONFIG["fps"])
        clip.close()
        return

    # Registrar silencios cortados en el log
    if log:
        cursor = 0.0
        for ini, fin in unidos:
            t_i = max(0, ini - margen)
            if cursor < t_i:
                log.registrar("SILENCIO", cursor, t_i, "pausa/silencio")
            cursor = min(clip.duration, fin + margen)

    tiempo_cortado = clip.duration - sum(f - i for i, f in unidos)
    print(f"   Segmentos: {len(unidos)} | Cortado: {tiempo_cortado:.1f}s")

    clips_voz = []
    for ini, fin in unidos:
        t_i = max(0, ini - margen)
        t_f = min(clip.duration, fin + margen)
        clips_voz.append(clip.subclipped(t_i, t_f))

    video_final = concatenate_videoclips(clips_voz)
    video_final.write_videofile(salida, codec="libx264", audio_codec="aac",
                                fps=CONFIG["fps"], logger=None)
    clip.close()
    video_final.close()
    print("✅ Silencios eliminados.")


# ─────────────────────────────────────────
#  PASO 2 — CONVERTIR A 9:16
# ─────────────────────────────────────────
def convertir_916(entrada, salida):
    print("\n📐 Convirtiendo a 9:16...")
    res    = CONFIG["resolucion"]
    filtro = (f"scale={res}:force_original_aspect_ratio=decrease,"
              f"pad={res}:(ow-iw)/2:(oh-ih)/2:color=black")
    cmd = ["ffmpeg", "-y", "-i", entrada,
           "-vf", filtro, "-r", str(CONFIG["fps"]),
           "-c:v", "libx264", "-c:a", "aac", salida]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"❌ Error: {r.stderr}")
        sys.exit(1)
    print("✅ Convertido a 9:16.")


# ─────────────────────────────────────────
#  PASO 3 — EXTRAER AUDIO
# ─────────────────────────────────────────
def extraer_audio(video, audio):
    print("\n🎙️  Extrayendo audio...")
    cmd = ["ffmpeg", "-y", "-i", video, "-vn",
           "-acodec", "mp3", "-ab", "192k", audio]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"❌ Error: {r.stderr}")
        sys.exit(1)
    print("✅ Audio extraído.")


# ─────────────────────────────────────────
#  PASO 4 — TRANSCRIBIR CON WHISPER
# ─────────────────────────────────────────
def transcribir(audio, carpeta, modelo_whisper=None):
    print("\n💬 Transcribiendo con Whisper (timestamps por palabra)...")
    import whisper

    if modelo_whisper is None:
        modelo_whisper = whisper.load_model("medium")

    result = modelo_whisper.transcribe(audio, language="es", word_timestamps=True)

    nombre_base = os.path.splitext(os.path.basename(audio))[0]
    srt         = os.path.join(carpeta, nombre_base + ".srt")

    palabras = []
    for seg in result["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                palabra = w["word"].strip()
                if palabra:
                    palabras.append((w["start"], w["end"], palabra))
        else:
            palabras.append((seg["start"], seg["end"], seg["text"].strip()))

    with open(srt, "w", encoding="utf-8") as f:
        for i, (ini, fin, palabra) in enumerate(palabras, 1):
            f.write(f"{i}\n")
            f.write(f"{segundos_a_srt(ini)} --> {segundos_a_srt(fin)}\n")
            f.write(f"{palabra}\n\n")

    print(f"✅ Subtítulos: {srt} ({len(palabras)} palabras)")
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
#  NUEVO: DETECCIÓN DE PATRÓN "REPITO"
#
#  Detecta el patrón:
#  [...frase equivocada...] → ["repito"/"perdón"/etc] → [...frase correcta...]
#
#  Corta desde el inicio de la frase equivocada
#  hasta el final de la palabra clave (inclusive).
#  Se queda con la versión correcta que viene después.
# ─────────────────────────────────────────
def detectar_patron_repeticion(audio_words):
    """
    Busca palabras clave de repetición en la transcripción y determina
    qué segmento cortar: desde donde empezó el error hasta después de la palabra clave.

    Retorna lista de (t_inicio_corte, t_fin_corte, descripcion)
    """
    if not audio_words:
        return []

    cortes = []

    for j, w in enumerate(audio_words):
        palabra_norm = re.sub(r"[¿?¡!.,;:\"\'\\-]", "", w["orig"].lower().strip())

        # Verificar si esta palabra es una señal de repetición
        es_senal = False
        senal_encontrada = ""

        # Verificar palabras individuales
        if palabra_norm in PALABRAS_REPETICION:
            es_senal = True
            senal_encontrada = palabra_norm

        # Verificar frases de 2 palabras
        if not es_senal and j > 0:
            dos_palabras = (re.sub(r"[¿?¡!.,;:\"\'\\-]", "",
                           audio_words[j-1]["orig"].lower().strip()) +
                           " " + palabra_norm)
            if dos_palabras in PALABRAS_REPETICION:
                es_senal = True
                senal_encontrada = dos_palabras
                j = j - 1  # El inicio es la palabra anterior

        if not es_senal:
            continue

        # ── Encontrar inicio del error ──
        # Retroceder para encontrar dónde empezó la frase equivocada.
        # Heurística: buscar hasta 15 palabras atrás o hasta un silencio largo (>0.4s)
        idx_inicio_error = j
        for k in range(j - 1, max(0, j - 15) - 1, -1):
            if k + 1 < len(audio_words):
                gap = audio_words[k + 1]["t_ini"] - audio_words[k]["t_fin"]
                if gap > 0.4:
                    # Hay un silencio largo antes: el error empieza después del silencio
                    idx_inicio_error = k + 1
                    break
            idx_inicio_error = k
        else:
            # Llegamos al límite sin encontrar silencio: usar el límite
            pass

        t_corte_ini = audio_words[idx_inicio_error]["t_ini"]
        t_corte_fin = w["t_fin"] + 0.1   # incluir la palabra clave + pequeño margen

        palabras_cortadas = " ".join(
            audio_words[k]["orig"]
            for k in range(idx_inicio_error, min(j + 1, len(audio_words)))
        )

        print(f"   🔄 Patrón '{senal_encontrada}' detectado: "
              f"[{palabras_cortadas}] "
              f"({t_corte_ini:.2f}s → {t_corte_fin:.2f}s)")

        cortes.append((t_corte_ini, t_corte_fin, palabras_cortadas))

    return cortes


# ─────────────────────────────────────────
#  NUEVO: APLICAR CORTES CON FADE DE AUDIO
#
#  En lugar de cortar "en seco", aplica un
#  fade-out antes del corte y fade-in después.
#  Resultado: transición suave e imperceptible.
# ─────────────────────────────────────────
def aplicar_cortes_con_fade(video_entrada, segmentos, video_salida):
    """
    Aplica cortes al video con fade de audio suave en cada unión.

    segmentos: lista de (t_inicio, t_fin) a MANTENER
    """
    if not segmentos:
        print("   ⚠️  Sin segmentos para mantener.")
        return False

    fade_ms  = CONFIG["fade_audio_ms"]
    fade_s   = fade_ms / 1000.0

    lista_tmp = "tmp_fade_concat.txt"
    clips_tmp = []

    print(f"   Aplicando fade de {fade_ms}ms en cada corte...")

    with open(lista_tmp, "w", encoding="utf-8") as f:
        for idx, (t_s, t_e) in enumerate(segmentos):
            clip_tmp = f"tmp_fade_seg_{idx}.mp4"
            clips_tmp.append(clip_tmp)

            duracion = t_e - t_s
            if duracion <= 0:
                continue

            # Fade in al inicio del segmento + fade out al final
            # afade: aplica fade al audio sin tocar el video
            filtro_audio = (
                f"afade=t=in:st=0:d={fade_s},"
                f"afade=t=out:st={max(0, duracion - fade_s):.3f}:d={fade_s}"
            )

            cmd_corte = [
                "ffmpeg", "-y",
                "-ss", str(t_s), "-to", str(t_e),
                "-i", video_entrada,
                "-c:v", "libx264",
                "-af", filtro_audio,
                "-c:a", "aac",
                "-avoid_negative_ts", "make_zero",
                clip_tmp
            ]
            r = subprocess.run(cmd_corte, capture_output=True, text=True)
            if r.returncode == 0:
                f.write(f"file '{clip_tmp}'\n")

    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", lista_tmp, "-c", "copy", video_salida
    ]
    r = subprocess.run(cmd_concat, capture_output=True, text=True)

    if os.path.exists(lista_tmp):
        os.remove(lista_tmp)
    for c in clips_tmp:
        if os.path.exists(c):
            os.remove(c)

    if r.returncode != 0:
        print(f"   ⚠️  Error FFmpeg: {r.stderr[-300:]}")
        return False

    print(f"   ✅ Video con cortes suaves: {video_salida}")
    return True


# ─────────────────────────────────────────
#  NORMALIZAR TEXTO
# ─────────────────────────────────────────
def _normalizar(texto):
    texto = texto.lower()
    texto = re.sub(r"[¿?¡!.,;:\"\'\\-]", " ", texto)
    return [w for w in texto.split() if w]


def _similares(a, b):
    if a == b:
        return True
    largo = min(len(a), len(b))
    if largo >= 4 and (a.startswith(b[:4]) or b.startswith(a[:4])):
        return True
    if abs(len(a) - len(b)) <= 2 and largo >= 5:
        difs = sum(1 for x, y in zip(a, b) if x != y)
        difs += abs(len(a) - len(b))
        if difs <= 2:
            return True
    return False


def _lcs_alineacion(guion_palabras, audio_words):
    n = len(guion_palabras)
    m = len(audio_words)

    audio_norm = [_normalizar(w["orig"]) for w in audio_words]
    audio_norm = [n[0] if n else "" for n in audio_norm]

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if _similares(guion_palabras[i-1], audio_norm[j-1]):
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    alineacion = [-1] * m
    i, j = n, m
    while i > 0 and j > 0:
        if _similares(guion_palabras[i-1], audio_norm[j-1]):
            alineacion[j-1] = i - 1
            i -= 1
            j -= 1
        elif dp[i-1][j] >= dp[i][j-1]:
            i -= 1
        else:
            j -= 1

    return alineacion


def detectar_errores_por_alineacion(guion_texto, audio_words):
    guion_palabras = _normalizar(guion_texto)

    if not guion_palabras or not audio_words:
        return []

    print(f"   Guión: {len(guion_palabras)} palabras")
    print(f"   Audio: {len(audio_words)} palabras detectadas")

    alineacion = _lcs_alineacion(guion_palabras, audio_words)

    bloques_error  = []
    bloque_actual  = []

    for j, g_idx in enumerate(alineacion):
        if g_idx == -1:
            bloque_actual.append(j)
        else:
            if bloque_actual:
                bloques_error.append(bloque_actual)
                bloque_actual = []
    if bloque_actual:
        bloques_error.append(bloque_actual)

    MINIMO_PALABRAS = 3
    MINIMO_SEGUNDOS = 0.8

    cortes = []
    for bloque in bloques_error:
        if len(bloque) < MINIMO_PALABRAS:
            continue

        idx_primero = bloque[0]
        if idx_primero > 0:
            t_ini = audio_words[idx_primero - 1]["t_fin"]
        else:
            t_ini = audio_words[idx_primero]["t_ini"]

        t_fin = audio_words[bloque[-1]]["t_fin"]
        dur   = t_fin - t_ini

        if dur < MINIMO_SEGUNDOS:
            continue

        palabras_error = [audio_words[k]["orig"] for k in bloque]
        print(f"   ✂️  Error (LCS): [{' '.join(palabras_error)}] "
              f"({t_ini:.2f}s → {t_fin:.2f}s, {dur:.1f}s)")
        cortes.append((t_ini, t_fin))

    if not cortes:
        print("   ✅ Sin errores significativos — video limpio.")

    return cortes


# ─────────────────────────────────────────
#  NUEVO: DETECCIÓN CON CLAUDE API
#  Reemplaza Gemini — mejor en español,
#  más preciso para detectar repeticiones
# ─────────────────────────────────────────
def detectar_errores_con_claude(guion_texto, audio_words):
    """
    Usa Claude API para comparar guion vs transcripción con timestamps
    y devuelve los rangos de tiempo exactos que hay que cortar.
    """
    if not CLAUDE_API_KEY or CLAUDE_API_KEY == "PEGA_TU_KEY_AQUI":
        print("   ⚠️  API key de Claude no configurada. Usando algoritmo local.")
        return detectar_errores_por_alineacion(guion_texto, audio_words)

    try:
        import urllib.request
        import urllib.error
    except ImportError:
        print("   ⚠️  urllib no disponible. Usando algoritmo local.")
        return detectar_errores_por_alineacion(guion_texto, audio_words)

    # Construir transcripción con timestamps
    lineas = []
    for w in audio_words:
        lineas.append(f"  {w['t_ini']:.2f}s  {w['orig']}")
    transcripcion_str = "\n".join(lineas)

    prompt = f"""Eres un editor de video experto en español. Tu tarea es encontrar errores en una grabación comparándola contra un guión.

GUIÓN ORIGINAL:
{guion_texto}

TRANSCRIPCIÓN DEL AUDIO (cada palabra con su tiempo en segundos desde el inicio):
{transcripcion_str}

INSTRUCCIONES:
1. Compara la transcripción contra el guión palabra por palabra.
2. Identifica estos tipos de errores:
   a) REPETICIÓN: el hablante dice una frase, se equivoca, dice "repito"/"perdón"/"espera"/"de nuevo" y repite la frase. Cortar desde el inicio de la frase equivocada hasta DESPUÉS de la palabra clave (el inicio correcto queda intacto).
   b) FRASE EXTRA: bloques de 3+ palabras consecutivas que no están en el guión y no son variaciones naturales del habla.
   c) TARTAMUDEO: palabras o sílabas repetidas varias veces seguidas.
3. NO cortes: artículos o conjunciones sueltas, pequeñas variaciones naturales del habla, diferencias de puntuación o acentos.
4. Para cada error, indica el tiempo de inicio y fin EXACTO en segundos según los timestamps.

RESPONDE ÚNICAMENTE con JSON válido, sin explicaciones, sin markdown:
{{"cortes": [{{"inicio": 20.5, "fin": 38.2, "tipo": "repeticion", "palabras": "frase equivocada aqui repito"}}, {{"inicio": 60.9, "fin": 62.0, "tipo": "extra", "palabras": "palabras que sobran"}}]}}

Si no hay errores: {{"cortes": []}}"""

    payload = json.dumps({
        "model":      "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "messages":   [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    try:
        print("   🤖 Consultando Claude IA...")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data  = json.loads(resp.read().decode("utf-8"))
            texto = data["content"][0]["text"].strip()

        # Limpiar markdown si Claude lo agrega
        if texto.startswith("```"):
            lineas = texto.split("\n")
            lineas = [l for l in lineas if not l.startswith("```")]
            texto  = "\n".join(lineas).strip()

        resultado  = json.loads(texto)
        cortes_raw = resultado.get("cortes", [])

        if not cortes_raw:
            print("   ✅ Claude: sin errores detectados.")
            return []

        cortes = []
        for c in cortes_raw:
            t_ini = float(c["inicio"])
            t_fin = float(c["fin"])
            dur   = t_fin - t_ini
            tipo  = c.get("tipo", "error")
            pals  = c.get("palabras", "")
            if dur >= 0.5:
                emoji = "🔄" if tipo == "repeticion" else "✂️ "
                print(f"   {emoji} [{tipo}] [{pals}] "
                      f"({t_ini:.2f}s → {t_fin:.2f}s, {dur:.1f}s)")
                cortes.append((t_ini, t_fin, pals))

        return cortes

    except json.JSONDecodeError as e:
        print(f"   ⚠️  Claude respondió algo inesperado: {e}")
        print("   Usando algoritmo local como respaldo...")
        return [(t, f, "") for t, f in
                detectar_errores_por_alineacion(guion_texto, audio_words)]
    except Exception as e:
        print(f"   ⚠️  Error con Claude API: {e}")
        print("   Usando algoritmo local como respaldo...")
        return [(t, f, "") for t, f in
                detectar_errores_por_alineacion(guion_texto, audio_words)]


# ─────────────────────────────────────────
#  LIMPIAR ERRORES CON GUIÓN
#  Combina: patrón "repito" + Claude IA
# ─────────────────────────────────────────
def limpiar_errores_con_guion(video_entrada, guion_txt, video_salida,
                               modelo_whisper=None, log: LogEdicion = None):
    import whisper

    print("\n📋 Analizando guión vs grabación...")

    with open(guion_txt, "r", encoding="utf-8") as f:
        guion_texto = f.read()

    tmp_audio = "tmp_guion_check.mp3"
    cmd = ["ffmpeg", "-y", "-i", video_entrada,
           "-vn", "-acodec", "mp3", "-ab", "192k", tmp_audio]
    subprocess.run(cmd, capture_output=True, text=True)

    print("   Transcribiendo audio...")
    if modelo_whisper is None:
        modelo_whisper = whisper.load_model("medium")

    result = modelo_whisper.transcribe(tmp_audio, language="es", word_timestamps=True)

    if os.path.exists(tmp_audio):
        os.remove(tmp_audio)

    audio_words = []
    for seg in result["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                p = w["word"].strip()
                if p:
                    audio_words.append({
                        "t_ini": w["start"],
                        "t_fin": w["end"],
                        "orig":  p
                    })

    if not audio_words:
        print("   ⚠️  No se pudo transcribir.")
        return video_entrada, modelo_whisper

    # Mostrar transcripción
    print("   Transcripción detectada:")
    linea = "   "
    for w in audio_words:
        linea += w["orig"] + " "
        if len(linea) > 75:
            print(linea)
            linea = "   "
    if linea.strip():
        print(linea)
    print()

    # ── FASE 1: Detectar patrón "repito" / "perdón" ──
    print("   🔍 Fase 1: Buscando patrón 'repito/perdón/de nuevo'...")
    cortes_repeticion = detectar_patron_repeticion(audio_words)
    if not cortes_repeticion:
        print("   ✅ Sin patrones de repetición detectados.")

    # ── FASE 2: Detectar errores vs guión con Claude IA ──
    print("   🔍 Fase 2: Comparando contra guión con Claude IA...")
    cortes_ia = detectar_errores_con_claude(guion_texto, audio_words)

    # ── Unir todos los cortes ──
    todos_cortes = []
    for t_ini, t_fin, descripcion in cortes_repeticion:
        todos_cortes.append((t_ini, t_fin, f"[REPETICIÓN] {descripcion}"))
        if log:
            log.registrar("REPETICIÓN", t_ini, t_fin, descripcion)

    for item in cortes_ia:
        t_ini, t_fin = item[0], item[1]
        descripcion  = item[2] if len(item) > 2 else ""
        todos_cortes.append((t_ini, t_fin, f"[IA] {descripcion}"))
        if log:
            log.registrar("ERROR_IA", t_ini, t_fin, descripcion)

    if not todos_cortes:
        print("   ✅ Sin errores detectados — video limpio.")
        return video_entrada, modelo_whisper

    print(f"\n   Total cortes a aplicar: {len(todos_cortes)}")

    # ── Ordenar y fusionar cortes solapados ──
    todos_cortes.sort(key=lambda x: x[0])
    cortes_limpios = []
    for c in todos_cortes:
        if cortes_limpios and c[0] < cortes_limpios[-1][1]:
            cortes_limpios[-1] = (cortes_limpios[-1][0],
                                  max(c[1], cortes_limpios[-1][1]),
                                  cortes_limpios[-1][2] + " + " + c[2])
        else:
            cortes_limpios.append(list(c))

    # ── Calcular segmentos a MANTENER ──
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
        print("   ⚠️  No quedaron segmentos.")
        return video_entrada, modelo_whisper

    # ── Aplicar cortes CON FADE DE AUDIO ──
    print(f"\n   Aplicando {len(cortes_limpios)} corte(s) con fade de audio...")
    exito = aplicar_cortes_con_fade(video_entrada, segmentos, video_salida)

    if not exito:
        return video_entrada, modelo_whisper

    print(f"   ✅ Video limpio con transiciones suaves: {video_salida}")
    return video_salida, modelo_whisper


# ─────────────────────────────────────────
#  CORTES MANUALES POR ARCHIVO DE NOTAS
# ─────────────────────────────────────────
def cortar_por_notas(video_entrada, notas_txt, video_salida, log: LogEdicion = None):
    print(f"\n✂️  Leyendo notas de corte: {notas_txt}")

    cortes = []
    with open(notas_txt, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            partes = re.split(r"[-–]", linea)
            if len(partes) != 2:
                print(f"   ⚠️  Línea ignorada: {linea}")
                continue
            try:
                t_ini = float(partes[0].strip())
                t_fin = float(partes[1].strip())
                if t_fin <= t_ini:
                    continue
                cortes.append((t_ini, t_fin))
                print(f"   ✂️  Corte manual: {t_ini:.1f}s → {t_fin:.1f}s")
                if log:
                    log.registrar("MANUAL", t_ini, t_fin, f"linea: {linea}")
            except ValueError:
                continue

    if not cortes:
        print("   ℹ️  Sin cortes definidos.")
        return video_entrada

    cmd_dur = ["ffprobe", "-v", "error", "-show_entries",
               "format=duration", "-of", "csv=p=0", video_entrada]
    r = subprocess.run(cmd_dur, capture_output=True, text=True)
    try:
        duracion_total = float(r.stdout.strip())
    except Exception:
        duracion_total = cortes[-1][1] + 5.0

    cortes.sort(key=lambda x: x[0])
    cortes_limpios = []
    for c in cortes:
        if cortes_limpios and c[0] < cortes_limpios[-1][1]:
            cortes_limpios[-1] = (cortes_limpios[-1][0],
                                  max(c[1], cortes_limpios[-1][1]))
        else:
            cortes_limpios.append(c)

    segmentos = []
    cursor    = 0.0
    for t_ini_c, t_fin_c in cortes_limpios:
        if cursor < t_ini_c:
            segmentos.append((cursor, t_ini_c))
        cursor = t_fin_c
    if cursor < duracion_total:
        segmentos.append((cursor, duracion_total))

    exito = aplicar_cortes_con_fade(video_entrada, segmentos, video_salida)
    return video_salida if exito else video_entrada


# ─────────────────────────────────────────
#  ESTILO 001 — Subtítulos con fuente elegible
# ─────────────────────────────────────────
def quemar_estilo_001(video, srt, salida, fuente="montserrat"):
    print(f"\n📝 Aplicando ESTILO 001 — fuente: {fuente.upper()}...")

    from PIL import Image, ImageDraw

    palabras_srt = leer_srt(srt)

    chunks_raw = []
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
    W    = clip.w
    H    = clip.h
    fps  = clip.fps

    TAM_NORMAL       = 68
    TAM_GRANDE       = 96
    COLOR            = (255, 255, 255, 255)
    PECHO_Y          = int(H * 0.62)
    DURACION_ENTRADA = 0.12

    fn = cargar_fuente_pil(fuente, TAM_NORMAL, bold=False)
    fb = cargar_fuente_pil(fuente, TAM_GRANDE, bold=True)

    print(f"   Fuente normal : {resolver_fuente(fuente, False) or 'fallback'}")
    print(f"   Fuente bold   : {resolver_fuente(fuente, True)  or 'fallback'}")

    eventos = []
    for t_ini, t_fin, palabras, t_pals in chunks_raw:
        if not palabras:
            continue

        img_tmp = Image.new("RGB", (W, H))
        d_tmp   = ImageDraw.Draw(img_tmp)

        def medir(txt, fuente_pil):
            bb = d_tmp.textbbox((0, 0), txt, font=fuente_pil)
            return bb[2] - bb[0], bb[3] - bb[1]

        l1 = " ".join(palabras[:2]) if len(palabras) >= 2 else palabras[0]
        w1, h1 = medir(l1, fn)

        if len(palabras) >= 3:
            l2 = palabras[2]
            w2, h2 = medir(l2, fb)
        else:
            l2, w2, h2 = None, 0, 0

        eventos.append({
            "ini": t_ini, "fin": t_fin,
            "palabras": palabras,
            "t_palabra": t_pals,
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

        chunk = None
        for ev in eventos:
            if ev["ini"] <= t < ev["fin"]:
                chunk = ev
                break
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
                draw.text((x1, y_base_l1 - off), chunk["linea1"],
                          font=fn, fill=COLOR)
            else:
                img_m = Image.new("RGB", (10, 10))
                dm    = ImageDraw.Draw(img_m)
                bb    = dm.textbbox((0, 0), palabras[0], font=fn)
                w_p1  = bb[2] - bb[0]
                off   = slide_offset(t, t_pal[0], chunk["h1"])
                x1    = (W - w_p1) // 2
                draw.text((x1, y_base_l1 - off), palabras[0],
                          font=fn, fill=COLOR)

        if chunk["linea2"] and len(t_pal) >= 3 and t >= t_pal[2]:
            off = slide_offset(t, t_pal[2], chunk["h2"])
            x2  = (W - chunk["w2"]) // 2
            draw.text((x2, y_base_l2 - chunk["h2"] - off),
                      chunk["linea2"], font=fb, fill=COLOR)

        return np.array(img.convert("RGB"))

    print("   Renderizando frame a frame...")
    clip_final = VideoClip(hacer_frame, duration=clip.duration)
    clip_final = clip_final.with_audio(clip.audio)
    clip_final.write_videofile(
        salida, fps=fps,
        codec="libx264", audio_codec="aac",
        logger=None
    )
    clip.close()
    print("✅ ESTILO 001 aplicado.")


# ─────────────────────────────────────────
#  FLUJO COMPLETO — REEL v6
# ─────────────────────────────────────────
def editar_reel(nombre_archivo, fuente="montserrat", guion=None, cortes=None):
    print(f"\n{'='*55}")
    print(f"  EDITOR JOSUÉ v6.0")
    print(f"  EDITANDO: {nombre_archivo}")
    print(f"  Fuente: {fuente.upper()}")
    if guion:  print(f"  Guión: {guion}")
    if cortes: print(f"  Cortes: {cortes}")
    print(f"{'='*55}\n")

    ruta_entrada  = os.path.join(CARPETA_INPUT, nombre_archivo)
    if not os.path.exists(ruta_entrada):
        print(f"❌ No encontré: {ruta_entrada}")
        sys.exit(1)

    nombre_base   = os.path.splitext(nombre_archivo)[0]
    tmp_sin_sil   = f"tmp_{nombre_base}_sin_sil.mp4"
    tmp_limpio    = f"tmp_{nombre_base}_limpio.mp4"
    tmp_916       = f"tmp_{nombre_base}_916.mp4"
    tmp_audio     = f"tmp_{nombre_base}.mp3"
    archivo_final = os.path.join(CARPETA_OUTPUT,
                                 f"{nombre_base}_{fuente}.mp4")

    modelo_whisper = None
    log = LogEdicion(nombre_archivo)

    try:
        # ── PASO 1: Cortes manuales sobre el video original ──
        if cortes:
            ruta_cortes = cortes
            if not os.path.exists(ruta_cortes):
                ruta_cortes_alt = os.path.join(CARPETA_INPUT, cortes)
                if os.path.exists(ruta_cortes_alt):
                    ruta_cortes = ruta_cortes_alt
            if not os.path.exists(ruta_cortes):
                print(f"⚠️  Archivo de cortes no encontrado: {cortes}")
                video_tras_cortes = ruta_entrada
            else:
                video_tras_cortes = cortar_por_notas(
                    ruta_entrada, ruta_cortes, tmp_limpio, log=log)
        else:
            video_tras_cortes = ruta_entrada

        # ── PASO 2: Eliminar silencios ──
        eliminar_silencios(video_tras_cortes, tmp_sin_sil, log=log)

        # ── PASO 3: Limpiar errores con guión (Claude + patrón repito) ──
        if guion:
            ruta_guion = guion
            if not os.path.exists(ruta_guion):
                ruta_guion_alt = os.path.join(CARPETA_INPUT, guion)
                if os.path.exists(ruta_guion_alt):
                    ruta_guion = ruta_guion_alt

            if not os.path.exists(ruta_guion):
                print(f"⚠️  Guión no encontrado: {guion}")
                video_para_procesar = tmp_sin_sil
            else:
                video_para_procesar, modelo_whisper = limpiar_errores_con_guion(
                    tmp_sin_sil, ruta_guion, tmp_limpio,
                    modelo_whisper=modelo_whisper, log=log
                )
        else:
            video_para_procesar = tmp_sin_sil

        # ── PASO 4: Convertir a 9:16 ──
        convertir_916(video_para_procesar, tmp_916)

        # ── PASO 5: Extraer audio y transcribir ──
        extraer_audio(tmp_916, tmp_audio)
        archivo_srt, _ = transcribir(tmp_audio, CARPETA_SUBS,
                                     modelo_whisper=modelo_whisper)

        # ── PASO 6: Quemar subtítulos ──
        quemar_estilo_001(tmp_916, archivo_srt, archivo_final, fuente)

        # ── PASO 7: Guardar log ──
        log.guardar()

        print(f"\n{'='*55}")
        print(f"  ✅ ¡LISTO! v6.0")
        print(f"  📁 {archivo_final}")
        if cortes:  print(f"  ✂️  Cortes manuales aplicados (con fade)")
        if guion:   print(f"  🤖 Errores limpiados con Claude IA + patrón repito")
        print(f"  📋 Log guardado en: {CARPETA_LOGS}/")
        print(f"{'='*55}\n")

    finally:
        for tmp in [tmp_sin_sil, tmp_limpio, tmp_916, tmp_audio]:
            if os.path.exists(tmp):
                os.remove(tmp)


# ─────────────────────────────────────────
#  SOLO SUBTÍTULOS
# ─────────────────────────────────────────
def solo_subtitulos(nombre_archivo, fuente="montserrat"):
    print(f"\n{'='*55}")
    print(f"  SUBTÍTULOS: {nombre_archivo} — {fuente.upper()}")
    print(f"{'='*55}\n")

    ruta_entrada  = os.path.join(CARPETA_INPUT, nombre_archivo)
    nombre_base   = os.path.splitext(nombre_archivo)[0]
    tmp_audio     = f"tmp_{nombre_base}.mp3"
    archivo_final = os.path.join(CARPETA_OUTPUT,
                                 f"{nombre_base}_subs_{fuente}.mp4")
    try:
        extraer_audio(ruta_entrada, tmp_audio)
        archivo_srt, _ = transcribir(tmp_audio, CARPETA_SUBS)
        quemar_estilo_001(ruta_entrada, archivo_srt, archivo_final, fuente)
        print(f"\n✅ ¡Listo! → {archivo_final}\n")
    finally:
        if os.path.exists(tmp_audio):
            os.remove(tmp_audio)


# ─────────────────────────────────────────
#  CORTAR FRAGMENTO
# ─────────────────────────────────────────
def cortar_clip(nombre_archivo, inicio, fin):
    print(f"\n{'='*55}")
    print(f"  CORTANDO: {nombre_archivo} [{inicio} → {fin}]")
    print(f"{'='*55}\n")

    ruta_entrada  = os.path.join(CARPETA_INPUT, nombre_archivo)
    nombre_base   = os.path.splitext(nombre_archivo)[0]
    tag           = f"{inicio.replace(':','')}_{fin.replace(':','')}"
    archivo_final = os.path.join(CARPETA_OUTPUT,
                                 f"{nombre_base}_clip_{tag}.mp4")
    cmd = ["ffmpeg", "-y", "-i", ruta_entrada,
           "-ss", inicio, "-to", fin, "-c", "copy", archivo_final]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"❌ Error: {r.stderr}")
        sys.exit(1)
    print(f"✅ Clip guardado: {archivo_final}\n")


# ─────────────────────────────────────────
#  LISTAR FUENTES
# ─────────────────────────────────────────
def listar_fuentes():
    print("\n" + "=" * 50)
    print("  FUENTES DISPONIBLES EN ESTE PC")
    print("=" * 50)
    for nombre in FUENTES_MAPA:
        ruta      = resolver_fuente(nombre, bold=False)
        ruta_bold = resolver_fuente(nombre, bold=True)
        ok_n = "✅" if ruta else "❌"
        ok_b = "✅" if ruta_bold else "❌"
        print(f"  {nombre:<12} normal:{ok_n}  bold:{ok_b}")
        if ruta:
            print(f"             {os.path.basename(ruta)}")
    print("=" * 50)
    print()


# ─────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Editor de Video — Josué Calderón v6.0 (Claude IA + patrón repito + fade)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
EJEMPLOS:
  # Reel completo
  py -3.11 editor_josue_v6.py reel video.mp4

  # Con fuente Bebas
  py -3.11 editor_josue_v6.py reel video.mp4 --fuente bebas

  # Con limpieza de errores (Claude IA + detección de "repito")
  py -3.11 editor_josue_v6.py reel video.mp4 --guion guion.txt

  # Completo: fuente + guión
  py -3.11 editor_josue_v6.py reel video.mp4 --fuente montserrat --guion guion.txt

  # Con cortes manuales (con fade de audio)
  py -3.11 editor_josue_v6.py reel video.mp4 --cortes cortes.txt

  # Solo subtítulos
  py -3.11 editor_josue_v6.py subtitulos video.mp4 --fuente oswald

  # Cortar fragmento
  py -3.11 editor_josue_v6.py cortar video.mp4 --inicio 00:00:05 --fin 00:00:45

  # Ver fuentes instaladas
  py -3.11 editor_josue_v6.py fuentes

NOVEDADES v6.0:
  🔄 Detección automática del patrón "repito / perdón / de nuevo"
  🤖 Claude IA reemplaza a Gemini (más preciso en español)
  🎵 Fade de audio en todos los cortes (transiciones suaves)
  📋 Log detallado de cada corte en carpeta logs/
  🔑 Configura tu API key de Claude en CLAUDE_API_KEY
        """
    )

    parser.add_argument("modo",
        choices=["reel", "subtitulos", "cortar", "fuentes"])
    parser.add_argument("archivo", nargs="?", default=None)
    parser.add_argument("--fuente",
        choices=["montserrat","bebas","anton","oswald","outfit",
                 "playfair","inter","arial"],
        default=FUENTE_DEFECTO)
    parser.add_argument("--inicio", default="00:00:00")
    parser.add_argument("--fin",    default="00:00:30")
    parser.add_argument("--guion",  default=None,
        help="Ruta al guión .txt para limpiar errores con Claude IA")
    parser.add_argument("--cortes", default=None,
        help="Archivo .txt con rangos a cortar (formato: inicio-fin en segundos)")

    args = parser.parse_args()

    if args.modo == "fuentes":
        listar_fuentes()
        return

    if args.archivo is None:
        print("❌ Necesitas indicar el nombre del video.")
        print("   Ejemplo: py -3.11 editor_josue_v6.py reel mi_video.mp4")
        sys.exit(1)

    verificar_dependencias()
    crear_carpetas()

    if args.modo == "reel":
        editar_reel(args.archivo, args.fuente,
                    guion=args.guion, cortes=args.cortes)
    elif args.modo == "subtitulos":
        solo_subtitulos(args.archivo, args.fuente)
    elif args.modo == "cortar":
        cortar_clip(args.archivo, args.inicio, args.fin)


if __name__ == "__main__":
    main()
