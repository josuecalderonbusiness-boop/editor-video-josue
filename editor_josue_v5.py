#!/usr/bin/env python3
# ============================================================
#   EDITOR DE VIDEO PERSONAL — JOSUÉ CALDERÓN  v5.0
#   Sistema automático: silencio + subtítulos + exportación
#   + Limpieza de errores con IA (Gemini)
#   Código Soberana · 2026
#
#   USO:
#   py -3.11 editor_josue_v5.py reel video.mp4
#   py -3.11 editor_josue_v5.py reel video.mp4 --fuente bebas
#   py -3.11 editor_josue_v5.py reel video.mp4 --guion guion.txt
#   py -3.11 editor_josue_v5.py reel video.mp4 --fuente montserrat --guion guion.txt
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

# Imports globales moviepy 2.x y numpy
try:
    import numpy as np
    from moviepy import VideoFileClip, concatenate_videoclips, CompositeVideoClip, VideoClip
    _MOVIEPY_OK = True
except Exception:
    _MOVIEPY_OK = False
    np = None

# ─────────────────────────────────────────
#  ⚠️  TU API KEY DE GEMINI — PONLA AQUÍ
# ─────────────────────────────────────────
GEMINI_API_KEY = "PEGA_TU_KEY_AQUI"   # ← reemplaza esto

# ─────────────────────────────────────────
#  MAPA DE FUENTES
#  nombre_corto → rutas posibles en Windows
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
    "umbral_db":       "-40dB",
    "resolucion":      "1080:1920",
    "fps":             30,
    "idioma_whisper":  "Spanish",
}

CARPETA_INPUT  = "input"
CARPETA_OUTPUT = "output"
CARPETA_SUBS   = "subtitulos"


# ─────────────────────────────────────────
#  RESOLVER RUTA DE FUENTE
# ─────────────────────────────────────────
def resolver_fuente(nombre_fuente, bold=False):
    nombre_fuente = nombre_fuente.lower()
    if nombre_fuente not in FUENTES_MAPA:
        nombre_fuente = FUENTE_DEFECTO

    tipo    = "bold" if bold else "normal"
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

    for fallback in ["C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
                     "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"]:
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
    for carpeta in [CARPETA_INPUT, CARPETA_OUTPUT, CARPETA_SUBS]:
        os.makedirs(carpeta, exist_ok=True)
    print("✅ Carpetas listas.")


# ─────────────────────────────────────────
#  PASO 1 — ELIMINAR SILENCIOS
# ─────────────────────────────────────────
def eliminar_silencios(entrada, salida):
    print("\n🔇 Eliminando silencios...")

    umbral_db    = -40
    silencio_min = CONFIG["silencio_minimo"]
    margen       = 0.08

    clip      = VideoFileClip(entrada)
    audio     = clip.audio
    fps_audio = audio.fps
    muestras  = audio.to_soundarray(fps=fps_audio)

    if muestras.ndim > 1:
        muestras = muestras.mean(axis=1)

    ventana   = int(fps_audio * 0.02)
    n_vent    = len(muestras) // ventana
    volumen   = []
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

    print(f"   Segmentos: {len(unidos)} | Cortado: "
          f"{clip.duration - sum(f-i for i,f in unidos):.1f}s")

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
#  Devuelve (ruta_srt, resultado_whisper)
#  para reutilizar en el análisis con IA
# ─────────────────────────────────────────
def transcribir(audio, carpeta, modelo_whisper=None):
    print("\n💬 Transcribiendo con Whisper (timestamps por palabra)...")
    import whisper

    # Reutilizar modelo si ya está cargado (evita cargar 2 veces)
    if modelo_whisper is None:
        modelo_whisper = whisper.load_model("medium")

    result = modelo_whisper.transcribe(audio, language="es", word_timestamps=True)

    nombre_base = os.path.splitext(os.path.basename(audio))[0]
    srt         = os.path.join(carpeta, nombre_base + ".srt")

    # Extraer palabras con sus tiempos exactos
    palabras = []
    for seg in result["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                palabra = w["word"].strip()
                if palabra:
                    palabras.append((w["start"], w["end"], palabra))
        else:
            palabras.append((seg["start"], seg["end"], seg["text"].strip()))

    # Escribir SRT con tiempo exacto por palabra
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
#  ESTILO 001 — con fuente elegible
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

        if len(palabras) >= 2:
            l1 = " ".join(palabras[:2])
        else:
            l1 = palabras[0]
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
#  ALINEACIÓN GUIÓN vs TRANSCRIPCIÓN
#  Algoritmo Python puro — sin IA
#
#  Lógica:
#  1. Normalizar guión y transcripción
#  2. Alinear palabra por palabra con LCS
#     (Longest Common Subsequence)
#  3. Todo lo que está en la transcripción
#     pero NO en el guión = ERROR → cortar
#  4. FFmpeg aplica los cortes
# ─────────────────────────────────────────

def _normalizar(texto):
    """Limpia texto para comparar: minúsculas, sin puntuación."""
    texto = texto.lower()
    texto = re.sub(r"[¿?¡!.,;:\"\'\\-]", " ", texto)
    return [w for w in texto.split() if w]


def _similares(a, b):
    """
    True si dos palabras son iguales o muy parecidas.
    Maneja errores de dislexia: 'vivms' ≈ 'vivimos', 'consesjos' ≈ 'consejos'
    """
    if a == b:
        return True
    # Prefijo largo: 'vivim' coincide con 'vivimos'
    largo = min(len(a), len(b))
    if largo >= 4 and (a.startswith(b[:4]) or b.startswith(a[:4])):
        return True
    # Distancia de edición ≤ 2 para palabras largas
    if abs(len(a) - len(b)) <= 2 and largo >= 5:
        difs = sum(1 for x, y in zip(a, b) if x != y)
        difs += abs(len(a) - len(b))
        if difs <= 2:
            return True
    return False


def _lcs_alineacion(guion_palabras, audio_words):
    """
    Alinea guión vs transcripción usando LCS (Longest Common Subsequence).
    Devuelve lista de índices: para cada palabra del audio,
    el índice en el guión al que corresponde, o -1 si es error.

    Usa programación dinámica O(n*m) — funciona bien para reels cortos.
    """
    n = len(guion_palabras)
    m = len(audio_words)

    audio_norm = [_normalizar(w["orig"]) for w in audio_words]
    audio_norm = [n[0] if n else "" for n in audio_norm]

    # Tabla DP
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if _similares(guion_palabras[i-1], audio_norm[j-1]):
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])

    # Reconstruir alineación
    alineacion = [-1] * m  # -1 = no está en el guión = error
    i, j = n, m
    while i > 0 and j > 0:
        if _similares(guion_palabras[i-1], audio_norm[j-1]):
            alineacion[j-1] = i - 1  # palabra j del audio → posición i del guión
            i -= 1
            j -= 1
        elif dp[i-1][j] >= dp[i][j-1]:
            i -= 1
        else:
            j -= 1

    return alineacion


def detectar_errores_por_alineacion(guion_texto, audio_words):
    """
    Compara guión vs transcripción y devuelve lista de (t_inicio, t_fin) a cortar.

    Regla principal: solo cortar bloques de 3 o más palabras consecutivas
    que no aparecen en el guión. Palabras sueltas son variaciones normales
    del habla (muletillas, artículos extra, etc.) y NO se cortan.

    Además filtra por duración mínima de 0.8s para evitar micro-cortes.
    """
    guion_palabras = _normalizar(guion_texto)

    if not guion_palabras or not audio_words:
        return []

    print(f"   Guión: {len(guion_palabras)} palabras")
    print(f"   Audio: {len(audio_words)} palabras detectadas")

    alineacion = _lcs_alineacion(guion_palabras, audio_words)

    # ── Agrupar palabras del audio por estado: en guión o fuera ──
    # Primero identificamos todos los bloques de palabras fuera del guión
    bloques_error = []   # lista de listas de índices consecutivos con alineacion == -1
    bloque_actual = []

    for j, g_idx in enumerate(alineacion):
        if g_idx == -1:
            bloque_actual.append(j)
        else:
            if bloque_actual:
                bloques_error.append(bloque_actual)
                bloque_actual = []
    if bloque_actual:
        bloques_error.append(bloque_actual)

    # ── Filtrar: solo bloques de 3+ palabras consecutivas ──
    MINIMO_PALABRAS = 3     # menos de esto = variación normal, no error
    MINIMO_SEGUNDOS = 0.8   # menos de esto = demasiado corto para cortar

    cortes = []
    for bloque in bloques_error:
        if len(bloque) < MINIMO_PALABRAS:
            continue  # 1-2 palabras sueltas: ignorar

        # ── Calcular inicio del corte ──
        # Usar el FIN de la palabra anterior al bloque (ultima palabra valida del guion)
        # para no comernos palabras validas que Whisper pego al error.
        idx_primero = bloque[0]
        if idx_primero > 0:
            t_ini = audio_words[idx_primero - 1]["t_fin"]
        else:
            t_ini = audio_words[idx_primero]["t_ini"]

        t_fin = audio_words[bloque[-1]]["t_fin"]
        dur   = t_fin - t_ini

        if dur < MINIMO_SEGUNDOS:
            continue  # muy corto: ignorar

        palabras_error = [audio_words[k]["orig"] for k in bloque]
        print(f"   ✂️  Error: [{' '.join(palabras_error)}] "
              f"({t_ini:.2f}s → {t_fin:.2f}s, {dur:.1f}s)")
        cortes.append((t_ini, t_fin))

    if not cortes:
        print("   ✅ Sin errores significativos — video limpio.")

    return cortes


def detectar_errores_con_gemini(guion_texto, audio_words):
    """
    Usa Gemini para comparar el guion contra la transcripcion con timestamps
    y devuelve los rangos de tiempo exactos que hay que cortar.

    Le damos a Gemini:
    1. El guion original
    2. La transcripcion palabra por palabra con timestamps
    Y le pedimos que nos diga que rangos de tiempo NO corresponden al guion.
    """
    # Intentar importar Gemini
    try:
        import google.generativeai as genai
    except ImportError:
        print("   ⚠️  google-generativeai no instalado. Usando algoritmo local.")
        return detectar_errores_por_alineacion(guion_texto, audio_words)

    if not GEMINI_API_KEY or GEMINI_API_KEY == "PEGA_TU_KEY_AQUI":
        print("   ⚠️  API key de Gemini no configurada. Usando algoritmo local.")
        return detectar_errores_por_alineacion(guion_texto, audio_words)

    # Construir lista de transcripcion con timestamps
    lineas_transcripcion = []
    for w in audio_words:
        lineas_transcripcion.append(f"  {w['t_ini']:.2f}s  {w['orig']}")
    transcripcion_str = "\n".join(lineas_transcripcion)

    prompt = f"""Eres un editor de video. Tu tarea es encontrar errores en una grabacion comparandola contra un guion.

GUION ORIGINAL:
{guion_texto}

TRANSCRIPCION DEL AUDIO (cada palabra con su tiempo en segundos):
{transcripcion_str}

INSTRUCCIONES:
1. Compara la transcripcion contra el guion palabra por palabra
2. Identifica bloques de palabras en la transcripcion que NO corresponden al guion
   - Pueden ser frases repetidas, palabras trabadas, frases dichas de mas, equivocaciones
   - Ignora diferencias menores: acentos, signos de puntuacion, articulos extra sueltos
   - Solo marca bloques de 3 o mas palabras consecutivas que claramente no estan en el guion
3. Para cada error encontrado, indica el tiempo de inicio y fin en segundos

RESPONDE UNICAMENTE con un JSON valido, sin explicaciones, sin markdown, solo el JSON:
{{
  "cortes": [
    {{"inicio": 20.5, "fin": 38.2, "palabras": "y si eres de los que te la pasas consumiendo"}},
    {{"inicio": 60.9, "fin": 62.0, "palabras": "que te llama"}}
  ]
}}

Si no hay errores, responde:
{{"cortes": []}}
"""

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        print("   Consultando Gemini IA...")
        response = model.generate_content(prompt)
        texto = response.text.strip()

        # Limpiar markdown si Gemini lo agrega
        if texto.startswith("```"):
            lineas = texto.split("\n")
            lineas = [l for l in lineas if not l.startswith("```")]
            texto = "\n".join(lineas).strip()

        data = json.loads(texto)
        cortes_raw = data.get("cortes", [])

        if not cortes_raw:
            print("   ✅ Gemini: sin errores detectados.")
            return []

        cortes = []
        for c in cortes_raw:
            t_ini = float(c["inicio"])
            t_fin = float(c["fin"])
            dur = t_fin - t_ini
            if dur >= 0.5:
                palabras = c.get("palabras", "")
                print(f"   ✂️  Error: [{palabras}] ({t_ini:.2f}s → {t_fin:.2f}s, {dur:.1f}s)")
                cortes.append((t_ini, t_fin))

        return cortes

    except json.JSONDecodeError as e:
        print(f"   ⚠️  Gemini respondio algo inesperado: {e}")
        print(f"   Respuesta raw: {texto[:200]}")
        print("   Usando algoritmo local como respaldo...")
        return detectar_errores_por_alineacion(guion_texto, audio_words)
    except Exception as e:
        print(f"   ⚠️  Error con Gemini: {e}")
        print("   Usando algoritmo local como respaldo...")
        return detectar_errores_por_alineacion(guion_texto, audio_words)



def limpiar_errores_con_guion(video_entrada, guion_txt, video_salida, modelo_whisper=None):
    """
    Detecta y corta errores de dislexia usando Gemini IA.
    """
    import whisper

    print("\n📋 Analizando guión vs grabación con IA...")

    # Leer guión
    with open(guion_txt, "r", encoding="utf-8") as f:
        guion_texto = f.read()

    # Extraer audio temporal
    tmp_audio = "tmp_guion_check.mp3"
    cmd = ["ffmpeg", "-y", "-i", video_entrada,
           "-vn", "-acodec", "mp3", "-ab", "192k", tmp_audio]
    subprocess.run(cmd, capture_output=True, text=True)

    # Transcribir — reutilizar modelo si ya está cargado
    print("   Transcribiendo audio...")
    if modelo_whisper is None:
        modelo_whisper = whisper.load_model("medium")

    result = modelo_whisper.transcribe(tmp_audio, language="es", word_timestamps=True)

    if os.path.exists(tmp_audio):
        os.remove(tmp_audio)

    # Extraer palabras con timestamps
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

    # Mostrar transcripción completa
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

    # ── Detectar errores con Gemini IA ──
    cortes = detectar_errores_con_gemini(guion_texto, audio_words)

    if not cortes:
        print("   ✅ Sin errores detectados — video limpio.")
        return video_entrada, modelo_whisper

    # Aplicar cortes con FFmpeg
    duracion_total = audio_words[-1]["t_fin"] + 0.5
    cortes.sort(key=lambda x: x[0])

    # Fusionar cortes solapados
    cortes_limpios = []
    for c in cortes:
        if cortes_limpios and c[0] < cortes_limpios[-1][1]:
            cortes_limpios[-1][1] = max(c[1], cortes_limpios[-1][1])
        else:
            cortes_limpios.append(list(c))

    # Segmentos a MANTENER
    segmentos = []
    cursor = 0.0
    for t_ini_c, t_fin_c in cortes_limpios:
        if cursor < t_ini_c:
            segmentos.append((cursor, t_ini_c))
        cursor = t_fin_c
    if cursor < duracion_total:
        segmentos.append((cursor, duracion_total))

    if not segmentos:
        print("   ⚠️  No quedaron segmentos.")
        return video_entrada, modelo_whisper

    print(f"\n   Aplicando {len(cortes_limpios)} corte(s)...")

    lista_tmp = "tmp_concat_list.txt"
    clips_tmp  = []
    with open(lista_tmp, "w", encoding="utf-8") as f:
        for idx, (t_s, t_e) in enumerate(segmentos):
            clip_tmp = f"tmp_segmento_{idx}.mp4"
            clips_tmp.append(clip_tmp)
            cmd_corte = [
                "ffmpeg", "-y",
                "-ss", str(t_s), "-to", str(t_e),
                "-i", video_entrada,
                "-c:v", "libx264", "-c:a", "aac",
                "-avoid_negative_ts", "make_zero",
                clip_tmp
            ]
            subprocess.run(cmd_corte, capture_output=True, text=True)
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
        print(f"   ⚠️  Error FFmpeg: {r.stderr[-200:]}")
        return video_entrada, modelo_whisper

    print(f"   ✅ Video limpio: {video_salida}")
    return video_salida, modelo_whisper


def cortar_por_notas(video_entrada, notas_txt, video_salida):
    """
    Lee un archivo de notas con rangos de tiempo a cortar y aplica los cortes.

    Formato del archivo de notas (un rango por linea):
        34-40
        61-62.5
        # esto es un comentario y se ignora

    Los tiempos pueden ser segundos enteros o decimales.
    """
    print(f"\n✂️  Leyendo notas de corte: {notas_txt}")

    cortes = []
    with open(notas_txt, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            # Aceptar formatos: "34-40" o "34.5-40.2" o "34 - 40"
            partes = re.split(r"[-–]", linea)
            if len(partes) != 2:
                print(f"   ⚠️  Linea ignorada (formato incorrecto): {linea}")
                continue
            try:
                t_ini = float(partes[0].strip())
                t_fin = float(partes[1].strip())
                if t_fin <= t_ini:
                    print(f"   ⚠️  Rango invalido ignorado: {linea}")
                    continue
                cortes.append((t_ini, t_fin))
                print(f"   ✂️  Corte: {t_ini:.1f}s → {t_fin:.1f}s  ({t_fin-t_ini:.1f}s)")
            except ValueError:
                print(f"   ⚠️  No pude leer los tiempos: {linea}")
                continue

    if not cortes:
        print("   ℹ️  Sin cortes definidos — video sin cambios.")
        return video_entrada

    # Obtener duracion total del video
    cmd_dur = ["ffprobe", "-v", "error", "-show_entries",
               "format=duration", "-of", "csv=p=0", video_entrada]
    r = subprocess.run(cmd_dur, capture_output=True, text=True)
    try:
        duracion_total = float(r.stdout.strip())
    except Exception:
        duracion_total = cortes[-1][1] + 5.0

    # Ordenar y fusionar cortes solapados
    cortes.sort(key=lambda x: x[0])
    cortes_limpios = []
    for c in cortes:
        if cortes_limpios and c[0] < cortes_limpios[-1][1]:
            cortes_limpios[-1] = (cortes_limpios[-1][0], max(c[1], cortes_limpios[-1][1]))
        else:
            cortes_limpios.append(c)

    # Segmentos a MANTENER
    segmentos = []
    cursor = 0.0
    for t_ini_c, t_fin_c in cortes_limpios:
        if cursor < t_ini_c:
            segmentos.append((cursor, t_ini_c))
        cursor = t_fin_c
    if cursor < duracion_total:
        segmentos.append((cursor, duracion_total))

    if not segmentos:
        print("   ⚠️  No quedaron segmentos.")
        return video_entrada

    print(f"\n   Aplicando {len(cortes_limpios)} corte(s)...")

    lista_tmp  = "tmp_notas_concat.txt"
    clips_tmp  = []
    with open(lista_tmp, "w", encoding="utf-8") as f:
        for idx, (t_s, t_e) in enumerate(segmentos):
            clip_tmp = f"tmp_notas_seg_{idx}.mp4"
            clips_tmp.append(clip_tmp)
            cmd_corte = [
                "ffmpeg", "-y",
                "-ss", str(t_s), "-to", str(t_e),
                "-i", video_entrada,
                "-c:v", "libx264", "-c:a", "aac",
                "-avoid_negative_ts", "make_zero",
                clip_tmp
            ]
            subprocess.run(cmd_corte, capture_output=True, text=True)
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
        print(f"   ⚠️  Error FFmpeg: {r.stderr[-200:]}")
        return video_entrada

    print(f"   ✅ Video cortado: {video_salida}")
    return video_salida



# ─────────────────────────────────────────
#  FLUJO COMPLETO — REEL
# ─────────────────────────────────────────
def editar_reel(nombre_archivo, fuente="montserrat", guion=None, cortes=None):
    print(f"\n{'='*55}")
    print(f"  EDITANDO: {nombre_archivo}")
    print(f"  Fuente: {fuente.upper()}")
    if guion:
        print(f"  Guión: {guion}")
    if cortes:
        print(f"  Cortes: {cortes}")
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

    modelo_whisper = None  # Se carga una sola vez y se reutiliza

    try:
        # ── PASO 1: Cortes manuales SOBRE EL VIDEO ORIGINAL ──
        # Importante: los tiempos del usuario corresponden al video original,
        # antes de quitar silencios. Por eso se aplican primero.
        if cortes:
            ruta_cortes = cortes
            if not os.path.exists(ruta_cortes):
                ruta_cortes_alt = os.path.join(CARPETA_INPUT, cortes)
                if os.path.exists(ruta_cortes_alt):
                    ruta_cortes = ruta_cortes_alt
            if not os.path.exists(ruta_cortes):
                print(f"⚠️  Archivo de cortes no encontrado: {cortes} — continuando sin cortes")
                video_tras_cortes = ruta_entrada
            else:
                video_tras_cortes = cortar_por_notas(ruta_entrada, ruta_cortes, tmp_limpio)
        else:
            video_tras_cortes = ruta_entrada

        # ── PASO 2: Eliminar silencios del video ya cortado ──
        eliminar_silencios(video_tras_cortes, tmp_sin_sil)

        if guion:
            if not os.path.exists(guion):
                print(f"⚠️  Guión no encontrado: {guion} — continuando sin limpieza")
                video_para_procesar = tmp_sin_sil
            else:
                # La función devuelve el modelo para reutilizarlo en transcribir()
                video_para_procesar, modelo_whisper = limpiar_errores_con_guion(
                    tmp_sin_sil, guion, tmp_limpio
                )
        else:
            video_para_procesar = tmp_sin_sil

        convertir_916(video_para_procesar, tmp_916)
        extraer_audio(tmp_916, tmp_audio)

        # Pasar el modelo ya cargado para no cargar Whisper 2 veces
        archivo_srt, _ = transcribir(tmp_audio, CARPETA_SUBS,
                                     modelo_whisper=modelo_whisper)

        quemar_estilo_001(tmp_916, archivo_srt, archivo_final, fuente)

        print(f"\n{'='*55}")
        print(f"  ✅ ¡LISTO!")
        print(f"  📁 {archivo_final}")
        if cortes:
            print(f"  ✂️  Cortes manuales aplicados")
        elif guion:
            print(f"  🧹 Errores limpiados con IA (Gemini)")
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
#  LISTAR FUENTES DISPONIBLES
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
        description="Editor de Video — Josué Calderón v5.0 (con IA Gemini)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
EJEMPLOS:
  # Reel completo con fuente por defecto (montserrat)
  py -3.11 editor_josue_v5.py reel video.mp4

  # Reel con fuente Bebas Neue (impacto, todo caps)
  py -3.11 editor_josue_v5.py reel video.mp4 --fuente bebas

  # Reel con limpieza de errores automática con IA
  py -3.11 editor_josue_v5.py reel video.mp4 --guion guion.txt

  # Reel completo: fuente + limpieza de errores
  py -3.11 editor_josue_v5.py reel video.mp4 --fuente montserrat --guion guion.txt

  # Reel con cortes manuales (archivo de notas)
  py -3.11 editor_josue_v5.py reel video.mp4 --cortes cortes.txt

  # Reel con cortes manuales + fuente
  py -3.11 editor_josue_v5.py reel video.mp4 --fuente bebas --cortes cortes.txt

  # Solo subtítulos
  py -3.11 editor_josue_v5.py subtitulos video.mp4 --fuente oswald

  # Cortar fragmento
  py -3.11 editor_josue_v5.py cortar video.mp4 --inicio 00:00:05 --fin 00:00:45

  # Ver qué fuentes tienes instaladas
  py -3.11 editor_josue_v5.py fuentes
        """
    )

    parser.add_argument(
        "modo",
        choices=["reel", "subtitulos", "cortar", "fuentes"],
        help=(
            "reel       → Edición completa (silencios + 9:16 + subtítulos)\n"
            "subtitulos → Solo agregar subtítulos\n"
            "cortar     → Cortar un fragmento\n"
            "fuentes    → Ver fuentes disponibles"
        )
    )
    parser.add_argument(
        "archivo",
        nargs="?",
        default=None,
        help="Nombre del video dentro de 'input/' (no requerido para 'fuentes')"
    )
    parser.add_argument(
        "--fuente",
        choices=["montserrat","bebas","anton","oswald","outfit",
                 "playfair","inter","arial"],
        default=FUENTE_DEFECTO,
        help=(
            "montserrat → moderna, versátil (DEFECTO)\n"
            "bebas      → impacto, todo caps\n"
            "anton      → máximo impacto\n"
            "oswald     → condensada, fuerte\n"
            "outfit     → limpia y suave\n"
            "playfair   → elegante, serif\n"
            "inter      → la más legible\n"
            "arial      → clásica de Windows"
        )
    )
    parser.add_argument("--inicio", default="00:00:00")
    parser.add_argument("--fin",    default="00:00:30")
    parser.add_argument(
        "--guion",
        default=None,
        help="Ruta al archivo .txt del guión para limpiar errores con IA\n"
             "Ejemplo: --guion C:\\Videos_Josue\\input\\guion.txt"
    )
    parser.add_argument(
        "--cortes",
        default=None,
        help="Archivo .txt con rangos de tiempo a cortar (un rango por linea)\n"
             "Formato: inicio-fin en segundos, ej: 34-40\n"
             "Ejemplo: --cortes cortes.txt"
    )

    args = parser.parse_args()

    if args.modo == "fuentes":
        listar_fuentes()
        return

    if args.archivo is None:
        print("❌ Necesitas indicar el nombre del video.")
        print("   Ejemplo: py -3.11 editor_josue_v5.py reel mi_video.mp4")
        sys.exit(1)

    verificar_dependencias()
    crear_carpetas()

    if args.modo == "reel":
        editar_reel(args.archivo, args.fuente, guion=args.guion, cortes=args.cortes)
    elif args.modo == "subtitulos":
        solo_subtitulos(args.archivo, args.fuente)
    elif args.modo == "cortar":
        cortar_clip(args.archivo, args.inicio, args.fin)


if __name__ == "__main__":
    main()
