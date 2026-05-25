#!/usr/bin/env python3
# ============================================================
#   EDITOR DE VIDEO PERSONAL — JOSUÉ CALDERÓN  v4.0
#   Sistema automático: silencio + subtítulos + exportación
#   Código Soberana · 2026
#
#   USO:
#   py -3.11 editor_josue_v4.py reel video.mp4
#   py -3.11 editor_josue_v4.py reel video.mp4 --fuente bebas
#   py -3.11 editor_josue_v4.py reel video.mp4 --guion guion.txt
#   py -3.11 editor_josue_v4.py reel video.mp4 --fuente montserrat
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
        "bold":   ["BebasNeue-Regular.ttf"],   # Bebas solo tiene un weight
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
    """
    Dado un nombre corto ('montserrat', 'bebas', etc.) y si es bold,
    devuelve la ruta completa al .ttf que existe en este PC.
    Si no encuentra ninguna, devuelve None (PIL usará la fuente por defecto).
    """
    nombre_fuente = nombre_fuente.lower()
    if nombre_fuente not in FUENTES_MAPA:
        nombre_fuente = FUENTE_DEFECTO

    tipo = "bold" if bold else "normal"
    opciones = FUENTES_MAPA[nombre_fuente][tipo]

    for opcion in opciones:
        # Ruta absoluta directa
        if os.path.isabs(opcion) and os.path.exists(opcion):
            return opcion
        # En carpeta de usuario (sin admin)
        ruta_user = os.path.join(FUENTES_DIR, opcion)
        if os.path.exists(ruta_user):
            return ruta_user
        # En carpeta de sistema
        ruta_sys = os.path.join("C:/Windows/Fonts", opcion)
        if os.path.exists(ruta_sys):
            return ruta_sys

    return None


def cargar_fuente_pil(nombre_fuente, tam, bold=False):
    """Carga una fuente PIL dado el nombre corto y tamaño."""
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

    # Fallback: intentar Arial
    for fallback in ["C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
                     "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"]:
        try:
            from PIL import ImageFont
            return ImageFont.truetype(fallback, tam)
        except Exception:
            continue

    # Último recurso
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

    dv       = 0.02
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
#  word_timestamps=True → tiempo exacto por palabra
# ─────────────────────────────────────────
def transcribir(audio, carpeta):
    print("\n💬 Transcribiendo con Whisper (timestamps por palabra)...")
    import whisper
    modelo = whisper.load_model("medium")
    result  = modelo.transcribe(audio, language="es", word_timestamps=True)

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
            # Fallback si no hay words (no debería pasar)
            palabras.append((seg["start"], seg["end"], seg["text"].strip()))

    # Escribir SRT con tiempo exacto por palabra
    with open(srt, "w", encoding="utf-8") as f:
        for i, (ini, fin, palabra) in enumerate(palabras, 1):
            f.write(f"{i}\n")
            f.write(f"{segundos_a_srt(ini)} --> {segundos_a_srt(fin)}\n")
            f.write(f"{palabra}\n\n")

    print(f"✅ Subtítulos: {srt} ({len(palabras)} palabras)")
    return srt


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


def fragmentar_srt(entradas, max_palabras=3):
    chunks = []
    for inicio, fin, texto in entradas:
        palabras   = texto.split()
        if not palabras:
            continue
        duracion    = fin - inicio
        por_palabra = duracion / len(palabras)
        i = 0
        while i < len(palabras):
            grupo   = palabras[i:i + max_palabras]
            t_ini   = inicio + i * por_palabra
            t_fin   = t_ini + len(grupo) * por_palabra
            chunks.append((t_ini, t_fin, " ".join(grupo)))
            i += max_palabras
    return chunks


# ─────────────────────────────────────────
#  ESTILO 001 — con fuente elegible
#  Línea 1: palabras 1+2  |  Línea 2: palabra 3 (grande+bold)
#  Cada palabra entra con slide-up sincronizado a la voz
# ─────────────────────────────────────────
def quemar_estilo_001(video, srt, salida, fuente="montserrat"):
    print(f"\n📝 Aplicando ESTILO 001 — fuente: {fuente.upper()}...")

    from PIL import Image, ImageDraw

    # El SRT ya tiene 1 palabra por entrada con timestamps exactos de Whisper
    palabras_srt = leer_srt(srt)  # lista de (t_ini, t_fin, palabra)

    # Agrupar de 3 en 3 con sus timestamps reales
    chunks_raw = []
    i = 0
    while i < len(palabras_srt):
        grupo = palabras_srt[i:i+3]
        t_ini    = grupo[0][0]
        t_fin    = grupo[-1][1]
        palabras = [p[2] for p in grupo]
        t_pals   = [p[0] for p in grupo]  # timestamp exacto de cada palabra
        chunks_raw.append((t_ini, t_fin, palabras, t_pals))
        i += 3

    clip = VideoFileClip(video)
    W    = clip.w    # 1080
    H    = clip.h    # 1920
    fps  = clip.fps

    # ── Tamaños ──
    TAM_NORMAL       = 68
    TAM_GRANDE       = 96
    COLOR            = (255, 255, 255, 255)
    PECHO_Y          = int(H * 0.62)
    DURACION_ENTRADA = 0.12

    # ── Cargar fuentes ──
    fn = cargar_fuente_pil(fuente, TAM_NORMAL, bold=False)
    fb = cargar_fuente_pil(fuente, TAM_GRANDE, bold=True)

    print(f"   Fuente normal : {resolver_fuente(fuente, False) or 'fallback'}")
    print(f"   Fuente bold   : {resolver_fuente(fuente, True)  or 'fallback'}")

    # ── Precalcular métricas de cada chunk ──
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
            "t_palabra": t_pals,   # ← timestamps EXACTOS de Whisper
            "linea1": l1, "w1": w1, "h1": h1,
            "linea2": l2, "w2": w2, "h2": h2,
        })

    # ── Slide-up ──
    def slide_offset(t, t_ap, altura):
        elapsed = t - t_ap
        if elapsed < 0:
            return altura + 20
        if elapsed >= DURACION_ENTRADA:
            return 0
        p = elapsed / DURACION_ENTRADA
        p = 1 - (1 - p) ** 2   # ease-out
        return int((1 - p) * (altura + 20))

    # ── Dibujar frame ──
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

        # Línea 1
        if t >= t_pal[0]:
            if len(palabras) >= 2 and t >= t_pal[1]:
                off = slide_offset(t, t_pal[1], chunk["h1"])
                x1  = (W - chunk["w1"]) // 2
                draw.text((x1, y_base_l1 - off), chunk["linea1"],
                          font=fn, fill=COLOR)
            else:
                # Solo palabra 1
                img_m = Image.new("RGB", (10, 10))
                dm    = ImageDraw.Draw(img_m)
                bb    = dm.textbbox((0, 0), palabras[0], font=fn)
                w_p1  = bb[2] - bb[0]
                off   = slide_offset(t, t_pal[0], chunk["h1"])
                x1    = (W - w_p1) // 2
                draw.text((x1, y_base_l1 - off), palabras[0],
                          font=fn, fill=COLOR)

        # Línea 2
        if chunk["linea2"] and len(t_pal) >= 3 and t >= t_pal[2]:
            off = slide_offset(t, t_pal[2], chunk["h2"])
            x2  = (W - chunk["w2"]) // 2
            draw.text((x2, y_base_l2 - chunk["h2"] - off),
                      chunk["linea2"], font=fb, fill=COLOR)

        return np.array(img.convert("RGB"))

    # ── Renderizar ──
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
#  LIMPIEZA DE ERRORES CON GUIÓN — v3
#
#  Lógica basada en silencios + guión:
#
#  1. Detecta pausas en el audio (donde Josué se detuvo)
#  2. Después de cada pausa, verifica si lo que sigue
#     coincide con alguna parte del guión
#  3. Si coincide → busca hacia atrás qué parte del guión
#     terminó antes de la pausa
#  4. Lo que está entre el fin del guión anterior y el
#     inicio de la corrección = ERROR → cortar
#
#  Esto funciona aunque Whisper transcriba mal el error,
#  porque solo necesita transcribir bien la CORRECCIÓN.
# ─────────────────────────────────────────
def limpiar_errores_con_guion(video_entrada, guion_txt, video_salida):
    import whisper

    print("\n📋 Analizando guión vs grabación...")

    # ── Leer guión ──
    with open(guion_txt, "r", encoding="utf-8") as f:
        texto_guion = f.read()

    def normalizar(texto):
        texto = texto.lower()
        texto = re.sub(r"[¿?¡!.,;:\"\'\-\n\r]", " ", texto)
        return [w for w in texto.split() if w]

    palabras_guion = normalizar(texto_guion)

    # ── Transcribir ──
    print("   Transcribiendo audio...")
    tmp_audio = "tmp_guion_check.mp3"
    cmd = ["ffmpeg", "-y", "-i", video_entrada,
           "-vn", "-acodec", "mp3", "-ab", "192k", tmp_audio]
    subprocess.run(cmd, capture_output=True, text=True)

    modelo = whisper.load_model("medium")
    result  = modelo.transcribe(tmp_audio, language="es", word_timestamps=True)

    if os.path.exists(tmp_audio):
        os.remove(tmp_audio)

    # Extraer palabras con timestamps
    audio_words = []
    for seg in result["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                p = w["word"].strip()
                if p:
                    norm = normalizar(p)
                    audio_words.append({
                        "t_ini": w["start"],
                        "t_fin": w["end"],
                        "norm":  norm[0] if norm else p.lower(),
                        "orig":  p
                    })

    if not audio_words:
        print("   ⚠️  No se pudo transcribir.")
        return video_entrada

    # ── Mostrar transcripción para debug ──
    print("   Transcripción:")
    linea = "   "
    for w in audio_words:
        linea += w["orig"] + " "
        if len(linea) > 75:
            print(linea)
            linea = "   "
    if linea.strip():
        print(linea)
    print()

    # ── Detectar pausas ──
    # Una pausa es un gap de silencio entre dos palabras consecutivas
    PAUSA_MIN = 0.4   # mínimo para considerarse pausa real
    PAUSA_MAX = 8.0   # máximo — más de esto no es corrección

    pausas = []  # (índice_después_de_la_pausa, duración_pausa)
    for i in range(1, len(audio_words)):
        gap = audio_words[i]["t_ini"] - audio_words[i-1]["t_fin"]
        if PAUSA_MIN <= gap <= PAUSA_MAX:
            pausas.append((i, gap))

    print(f"   Pausas detectadas: {len(pausas)}")
    for idx_p, dur_p in pausas:
        print(f"   → pausa de {dur_p:.2f}s antes de '{audio_words[idx_p]['orig']}'")

    if not pausas:
        print("   ✅ Sin pausas — no hay errores que cortar.")
        return video_entrada

    # ── Para cada pausa: ¿lo que sigue está en el guión? ──
    # Buscar la posición en el guión de las N palabras que siguen a la pausa
    VENTANA_POST = 5   # palabras después de la pausa para identificar posición en guión
    VENTANA_GUION = 60 # cuánto buscar en el guión

    cortes = []

    # Mantener un cursor en el guión que solo avanza
    g_cursor = 0  # hasta dónde llegamos en el guión
    a_ultimo_ok = -1  # último índice del audio que coincidió con el guión

    for idx_pausa, dur_pausa in pausas:
        # Palabras después de la pausa
        post_pausa = [audio_words[j]["norm"]
                      for j in range(idx_pausa, min(idx_pausa + VENTANA_POST, len(audio_words)))]

        if not post_pausa:
            continue

        # Buscar estas palabras en el guión a partir de g_cursor
        mejor_g = None
        for g_start in range(g_cursor, min(g_cursor + VENTANA_GUION, len(palabras_guion))):
            coincidencias = 0
            for k, p in enumerate(post_pausa):
                if g_start + k < len(palabras_guion):
                    if _palabras_similares(p, palabras_guion[g_start + k]):
                        coincidencias += 1
            # Si al menos 3 de las primeras 5 palabras coinciden → es una corrección
            if coincidencias >= min(3, len(post_pausa)):
                mejor_g = g_start
                break

        if mejor_g is None:
            # La pausa no es una corrección — es pausa normal
            # Actualizar a_ultimo_ok avanzando el cursor del guión
            # con las palabras ANTES de esta pausa
            for j in range(max(0, a_ultimo_ok + 1), idx_pausa):
                p_a = audio_words[j]["norm"]
                if g_cursor < len(palabras_guion):
                    if _palabras_similares(p_a, palabras_guion[g_cursor]):
                        g_cursor += 1
                        a_ultimo_ok = j
            continue

        # ── Es una corrección ──
        # Buscar qué palabra del audio antes de la pausa
        # fue la última que coincidió con el guión
        # (el error empieza después de esa palabra)

        # Avanzar el cursor del guión con las palabras correctas antes de la pausa
        for j in range(max(0, a_ultimo_ok + 1), idx_pausa):
            p_a = audio_words[j]["norm"]
            if g_cursor < len(palabras_guion):
                if _palabras_similares(p_a, palabras_guion[g_cursor]):
                    g_cursor += 1
                    a_ultimo_ok = j

        # El error es todo lo que está entre a_ultimo_ok y idx_pausa
        idx_error_ini = a_ultimo_ok + 1
        idx_error_fin = idx_pausa  # primera palabra de la corrección

        if idx_error_ini < idx_error_fin:
            t_corte_ini = audio_words[idx_error_ini]["t_ini"]
            t_corte_fin = audio_words[idx_error_fin]["t_ini"]
            dur = t_corte_fin - t_corte_ini

            if 0.05 < dur <= PAUSA_MAX:
                palabras_error = [audio_words[j]["orig"]
                                  for j in range(idx_error_ini, idx_error_fin)]
                print(f"   ✂️  Cortar: [{' '.join(palabras_error)}] "
                      f"({t_corte_ini:.2f}s → {t_corte_fin:.2f}s, {dur:.1f}s)")
                cortes.append((t_corte_ini, t_corte_fin))

        # Actualizar cursor al inicio de la corrección
        a_ultimo_ok = idx_pausa - 1
        g_cursor = mejor_g

    if not cortes:
        print("   ✅ No se detectaron errores para cortar.")
        return video_entrada

    print(f"\n   Total cortes: {len(cortes)}")

    # ── Aplicar cortes con FFmpeg ──
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
        return video_entrada

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
        return video_entrada

    print(f"   ✅ Video limpio: {video_salida}")
    return video_salida

def _palabras_similares(a, b):
    """
    Compara dos palabras — True si son iguales o muy parecidas.
    Maneja errores de dislexia tipo 'hom' vs 'hombres' (prefijo).
    """
    if a == b:
        return True
    # Prefijo: una es inicio de la otra (error parcial de dislexia)
    if len(a) >= 3 and b.startswith(a):
        return True
    if len(b) >= 3 and a.startswith(b):
        return True
    # Distancia de edición simple para errores de 1-2 letras
    if abs(len(a) - len(b)) <= 2 and len(a) >= 4:
        difs = sum(1 for x, y in zip(a, b) if x != y)
        difs += abs(len(a) - len(b))
        if difs <= 2:
            return True
    return False


# ─────────────────────────────────────────
#  FLUJO COMPLETO — REEL
# ─────────────────────────────────────────
def editar_reel(nombre_archivo, fuente="montserrat", guion=None):
    print(f"\n{'='*55}")
    print(f"  EDITANDO: {nombre_archivo}")
    print(f"  Fuente: {fuente.upper()}")
    print(f"{'='*55}\n")

    ruta_entrada  = os.path.join(CARPETA_INPUT, nombre_archivo)
    if not os.path.exists(ruta_entrada):
        print(f"❌ No encontré: {ruta_entrada}")
        sys.exit(1)

    nombre_base        = os.path.splitext(nombre_archivo)[0]
    tmp_sin_sil        = f"tmp_{nombre_base}_sin_sil.mp4"
    tmp_limpio         = f"tmp_{nombre_base}_limpio.mp4"
    tmp_916            = f"tmp_{nombre_base}_916.mp4"
    tmp_audio          = f"tmp_{nombre_base}.mp3"
    archivo_final      = os.path.join(CARPETA_OUTPUT,
                                      f"{nombre_base}_{fuente}.mp4")
    try:
        eliminar_silencios(ruta_entrada, tmp_sin_sil)

        # Limpieza de errores con guion (opcional)
        if guion:
            if not os.path.exists(guion):
                print(f"⚠️  Guión no encontrado: {guion} — continuando sin limpieza")
                video_para_procesar = tmp_sin_sil
            else:
                video_para_procesar = limpiar_errores_con_guion(
                    tmp_sin_sil, guion, tmp_limpio
                )
        else:
            video_para_procesar = tmp_sin_sil

        convertir_916(video_para_procesar, tmp_916)
        extraer_audio(tmp_916, tmp_audio)
        archivo_srt = transcribir(tmp_audio, CARPETA_SUBS)
        quemar_estilo_001(tmp_916, archivo_srt, archivo_final, fuente)

        print(f"\n{'='*55}")
        print(f"  ✅ ¡LISTO!")
        print(f"  📁 {archivo_final}")
        if guion:
            print(f"  🧹 Errores de guión limpiados automáticamente")
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
        archivo_srt = transcribir(tmp_audio, CARPETA_SUBS)
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
        ruta = resolver_fuente(nombre, bold=False)
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
        description="Editor de Video — Josué Calderón v4.0",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
EJEMPLOS:
  # Reel completo con fuente por defecto (montserrat)
  py -3.11 editor_josue_v4.py reel video.mp4

  # Reel con fuente Bebas Neue (impacto, todo caps)
  py -3.11 editor_josue_v4.py reel video.mp4 --fuente bebas

  # Reel con Anton (máximo impacto)
  py -3.11 editor_josue_v4.py reel video.mp4 --fuente anton

  # Solo subtítulos con Oswald
  py -3.11 editor_josue_v4.py subtitulos video.mp4 --fuente oswald

  # Cortar fragmento
  py -3.11 editor_josue_v4.py cortar video.mp4 --inicio 00:00:05 --fin 00:00:45

  # Ver qué fuentes tienes instaladas
  py -3.11 editor_josue_v4.py fuentes
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
        help="Ruta al archivo .txt del guión para limpiar errores automáticamente\n"
             "Ejemplo: --guion C:\\Videos_Josue\\guion_reel1.txt"
    )

    args = parser.parse_args()

    if args.modo == "fuentes":
        listar_fuentes()
        return

    if args.archivo is None:
        print("❌ Necesitas indicar el nombre del video.")
        print("   Ejemplo: py -3.11 editor_josue_v4.py reel mi_video.mp4")
        sys.exit(1)

    verificar_dependencias()
    crear_carpetas()

    if args.modo == "reel":
        editar_reel(args.archivo, args.fuente, guion=args.guion)
    elif args.modo == "subtitulos":
        solo_subtitulos(args.archivo, args.fuente)
    elif args.modo == "cortar":
        cortar_clip(args.archivo, args.inicio, args.fin)


if __name__ == "__main__":
    main()
