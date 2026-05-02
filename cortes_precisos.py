#!/usr/bin/env python3
# ============================================================
#   CORTES PRECISOS — Módulo de detección mejorada
#   Para editor_josue_v7_clean.py
#
#   Estrategia: usar silencios del audio como anclas naturales
#   para encontrar el inicio real de cada bloque fallido.
#
#   USO: importar y reemplazar detectar_errores_con_gpt4()
#   en editor_josue_v7_clean.py
# ============================================================

import subprocess
import re
import json
import os


# ─────────────────────────────────────────
#  PASO 1: Extraer mapa de silencios del audio
#  (ya lo tienes en el script, aquí lo reutilizamos con más detalle)
# ─────────────────────────────────────────
def extraer_mapa_silencios(audio_path, umbral_db=-25, silencio_min=0.3):
    """
    Devuelve lista de (t_inicio, t_fin) de cada silencio en el audio.
    Umbral más sensible que el de eliminación para encontrar pausas breves.
    """
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-af", f"silencedetect=noise={umbral_db}dB:d={silencio_min}",
        "-f", "null", "-"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    stderr = r.stderr

    inicios = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", stderr)]
    fines   = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", stderr)]

    silencios = list(zip(inicios, fines))
    print(f"   Mapa de silencios: {len(silencios)} pausas detectadas")
    return silencios


# ─────────────────────────────────────────
#  PASO 2: Anclar timestamp al silencio más cercano
# ─────────────────────────────────────────
def anclar_a_silencio_anterior(t_objetivo, silencios, ventana_busqueda=8.0):
    """
    Dado un timestamp t_objetivo (inicio tentativo de frase fallida),
    busca el silencio más cercano ANTES de ese punto dentro de la ventana.

    Esto resuelve el problema de desfase: en vez de retroceder 2s fijo,
    buscamos el corte natural (pausa real) más cercano.

    Retorna el t_fin del silencio encontrado (= inicio real del bloque fallido)
    o t_objetivo - 0.5 como fallback.
    """
    t_min = t_objetivo - ventana_busqueda
    candidatos = [
        sil for sil in silencios
        if sil[0] >= t_min and sil[1] <= t_objetivo
    ]

    if not candidatos:
        # No hay silencio cercano — retroceder 0.5s como mínimo seguro
        return max(0.0, t_objetivo - 0.5)

    # El silencio más cercano ANTES del punto de inicio
    sil_mas_cercano = max(candidatos, key=lambda s: s[1])
    print(f"      Ancla encontrada: silencio {sil_mas_cercano[0]:.2f}s-{sil_mas_cercano[1]:.2f}s → inicio corte: {sil_mas_cercano[1]:.2f}s")
    return sil_mas_cercano[1]


def anclar_fin_a_silencio(t_objetivo, silencios, ventana_busqueda=3.0):
    """
    Para el fin del corte (después del "repito"),
    busca el siguiente silencio para incluir la pausa completa.
    """
    candidatos = [
        sil for sil in silencios
        if sil[0] >= t_objetivo and sil[0] <= t_objetivo + ventana_busqueda
    ]

    if not candidatos:
        return t_objetivo + 0.3  # pequeño margen si no hay silencio

    sil_siguiente = min(candidatos, key=lambda s: s[0])
    return sil_siguiente[1]  # incluir el silencio completo


# ─────────────────────────────────────────
#  PASO 3: GPT-4o con transcripción mejorada + anclaje posterior
# ─────────────────────────────────────────
def detectar_errores_preciso(guion_texto, audio_words, audio_path, openai_api_key):
    """
    Versión mejorada de detectar_errores_con_gpt4().

    Diferencias clave:
    1. GPT-4o solo necesita encontrar la palabra "repito" — no tiene que
       calcular el inicio exacto. Eso lo hace anclar_a_silencio_anterior().
    2. El prompt es más simple y directo → menos errores de GPT.
    3. Los timestamps se ajustan con el mapa de silencios real del audio.
    """
    if not openai_api_key:
        print("   Error: API key de OpenAI no configurada.")
        return []

    # Construir transcripción con timestamps
    lineas = [f"  {w['t_ini']:.2f}s  {w['orig']}" for w in audio_words]
    transcripcion_str = "\n".join(lineas)

    # ── PROMPT SIMPLIFICADO ──
    # La clave: pedirle a GPT-4o solo LO QUE ES BUENO en IA (identificar
    # el "repito" y la versión correcta), no lo que es malo (calcular timestamps exactos).
    prompt = f"""Eres un editor de video profesional. Analiza esta transcripción de un coach con dislexia del habla.

TAREA PRINCIPAL — PATRÓN "REPITO":
El coach usa la palabra "repito" como señal de que va a repetir una frase que dijo mal.
Debes encontrar EXACTAMENTE:
1. El timestamp de la palabra "repito"
2. La primera palabra de la versión CORRECTA — es la que viene INMEDIATAMENTE después del "repito". Busca en los timestamps la primera palabra con contenido real después del "repito".
3. El inicio aproximado de la frase fallida — busca hacia atrás desde el "repito" hasta encontrar la misma primera palabra que aparece en la versión correcta.

EJEMPLO REAL de cómo calcularlo:
Transcripción:
  6.3s  Sales
  6.8s  de
  7.1s  aqui
  7.5s  con
  8.3s  repito       ← señal
  9.0s  Sales        ← primera palabra versión correcta
  9.5s  de
  9.8s  aqui

Resultado correcto:
  t_inicio_aprox: 6.3  (timestamp del primer "Sales" — misma palabra que empieza la versión correcta)
  t_repito: 8.3
  t_version_correcta: 9.0  (timestamp del segundo "Sales")

REGLA CRÍTICA para t_version_correcta:
Es el timestamp de la PRIMERA PALABRA con contenido real después del "repito".
Ignora palabras vacías como "y", "o", "a", "de" si la frase correcta empieza con una palabra de contenido.
Si después del "repito" hay una pausa y luego empieza la frase — el timestamp es el de esa primera palabra real.

REGLA EXTRA — cuando hay un comentario ANTES del repito:
A veces el coach hace un comentario personal ("ah espera", "cronometrar") y luego dice "repito" o simplemente empieza la frase correcta sin decir "repito".
En ese caso el comentario y el repito son DOS cortes separados:
- Corte 1 tipo "comentario": desde el inicio del comentario hasta el fin del comentario
- Corte 2 tipo "repito": desde el inicio de la frase fallida (ANTES del comentario) hasta el inicio de la versión correcta

Ejemplo:
  6.3s  Sales         ← inicio frase fallida
  14.5s silencio papi ← comentario
  16.9s Repito        ← señal
  18.1s Sales         ← inicio versión correcta

Resultado:
  corte repito: t_inicio_aprox=6.3, t_repito=16.9, t_version_correcta=18.1
  (el comentario queda incluido dentro del corte repito — NO es un corte separado)

REGLA EXTRA — comentario seguido inmediatamente de otro repito:
A veces después de un comentario personal el coach dice otra frase fallida y luego "repito".
En ese caso son DOS cortes separados:
- Corte 1 tipo "comentario": desde inicio del comentario hasta fin del comentario
- Corte 2 tipo "repito": desde inicio de la frase fallida (después del comentario) hasta inicio de versión correcta

Ejemplo:
  25.4s  Ah espera     ← inicio comentario
  29.0s  Cronometrar   ← fin comentario
  31.3s  El sistema no ← inicio frase fallida
  32.7s  repito        ← señal
  33.4s  El primero    ← inicio versión correcta

Resultado:
  corte comentario: t_inicio_aprox=25.4, t_fin=31.2
  corte repito: t_inicio_aprox=31.3, t_repito=32.7, t_version_correcta=33.4

OTROS ERRORES A DETECTAR:
- Comentarios personales fuera de la clase: "silencio papi", "ay espera", "un momento", "perdon", "espera que yo quería cronometrar" — cualquier cosa dirigida a alguien en la sala o a sí mismo. Para estos usa t_inicio_aprox y t_fin.
- Tartamudeo: misma sílaba o palabra repetida 2+ veces seguidas. Para estos usa t_inicio_aprox y t_fin.

REGLA ABSOLUTA — LA PALABRA "REPITO" SIEMPRE ES UN CORTE:
Si ves la palabra "repito" en la transcripción, SIEMPRE hay un corte ahí sin excepción.
No importa si la frase fallida suena casi correcta o similar al guion.
No importa si la frase está casi completa.
El coach usa "repito" únicamente cuando quiere que se corte — es una señal explícita.

NUNCA CORTES:
- Contenido de la clase aunque esté parafraseado diferente al guión
- Pausas normales para pensar
- Si tienes duda — NO cortes. Es mejor dejar algo que cortar contenido válido.

GUION (solo para entender el contenido — NO comparar palabra por palabra):
{guion_texto}

TRANSCRIPCION CON TIMESTAMPS:
{transcripcion_str}

Responde SOLO con JSON válido, sin explicaciones ni markdown:
{{"cortes": [
  {{"tipo": "repito", "t_inicio_aprox": 6.3, "t_repito": 8.3, "t_version_correcta": 9.0, "descripcion": "frase repetida — Sales de aqui con..."}},
  {{"tipo": "comentario", "t_inicio_aprox": 25.1, "t_fin": 34.2, "descripcion": "ay espera cronometrar"}},
  {{"tipo": "tartamudeo", "t_inicio_aprox": 45.0, "t_fin": 45.8, "descripcion": "y y y entonces"}}
]}}

Si no hay nada que cortar: {{"cortes": []}}"""

    try:
        from openai import OpenAI
        print("   GPT-4o analizando transcripción...")
        client = OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4000,
            temperature=0.0,  # máxima consistencia
            messages=[{"role": "user", "content": prompt}]
        )
        texto = response.choices[0].message.content.strip()

        # Limpiar markdown si GPT lo agrega
        if "```" in texto:
            lineas_resp = [l for l in texto.split("\n") if not l.startswith("```")]
            texto = "\n".join(lineas_resp).strip()

        resultado  = json.loads(texto)
        cortes_raw = resultado.get("cortes", [])

        if not cortes_raw:
            print("   GPT-4o: sin errores detectados.")
            return []

        print(f"   GPT-4o detectó {len(cortes_raw)} corte(s) candidatos")
        return cortes_raw

    except json.JSONDecodeError as e:
        print(f"   Respuesta inesperada de GPT-4o: {e}")
        print(f"   Respuesta cruda: {texto[:300]}")
        return []
    except Exception as e:
        print(f"   Error con GPT-4o: {e}")
        return []


# ─────────────────────────────────────────
#  PASO 4: Combinar todo — función principal
# ─────────────────────────────────────────
def calcular_cortes_precisos(guion_texto, audio_words, audio_path, openai_api_key):
    """
    Función principal. Reemplaza detectar_errores_con_gpt4() en el script.

    Flujo:
    1. Extraer mapa de silencios del audio (FFmpeg, sin costo)
    2. GPT-4o identifica QUÉ cortar (con prompt simplificado)
    3. Para cada corte, anclar timestamps al silencio más cercano
    4. Devolver lista de (t_inicio, t_fin, descripcion) lista para aplicar

    Retorna: lista de tuplas (t_ini, t_fin, descripcion)
    """
    print("\n   [CORTES PRECISOS] Iniciando análisis...")

    # 1. Mapa de silencios
    silencios = extraer_mapa_silencios(audio_path)

    # 2. GPT-4o identifica cortes
    cortes_raw = detectar_errores_preciso(guion_texto, audio_words, audio_path, openai_api_key)

    if not cortes_raw:
        return []

    # 3. Ajustar cada corte con el mapa de silencios
    cortes_finales = []

    for c in cortes_raw:
        tipo = c.get("tipo", "error")
        desc = c.get("descripcion", "")

        if tipo == "repito":
            # GPT nos da: t_inicio_aprox, t_repito, t_version_correcta
            t_inicio_aprox    = float(c.get("t_inicio_aprox", 0))
            t_version_correcta = float(c.get("t_version_correcta", c.get("t_fin", t_inicio_aprox + 5)))

            # El FIN del corte = justo antes de la versión correcta (GPT lo calculó bien)
            t_fin_corte = t_version_correcta - 0.1  # 100ms de margen

            # El INICIO del corte = silencio más cercano antes del inicio aprox
            # Esto es lo que GPT-4o hacía mal — ahora lo calcula FFmpeg
            t_inicio_corte = anclar_a_silencio_anterior(
                t_inicio_aprox,
                silencios,
                ventana_busqueda=8.0  # buscar hasta 8s antes
            )

            duracion = t_fin_corte - t_inicio_corte
            if duracion >= 0.5:
                print(f"   [repito] {desc}")
                print(f"      inicio_aprox GPT: {t_inicio_aprox:.2f}s → inicio_ancla: {t_inicio_corte:.2f}s → fin: {t_fin_corte:.2f}s ({duracion:.1f}s)")
                cortes_finales.append((t_inicio_corte, t_fin_corte, desc))
            else:
                print(f"   [repito] DESCARTADO (duración {duracion:.1f}s muy corta): {desc}")

        elif tipo in ["comentario", "tartamudeo", "error"]:
            # Para estos tipos GPT ya da t_inicio_aprox y t_fin directamente
            t_inicio_aprox = float(c.get("t_inicio_aprox", 0))
            t_fin          = float(c.get("t_fin", t_inicio_aprox + 2))

            # Igual: anclar inicio al silencio más cercano
            t_inicio_corte = anclar_a_silencio_anterior(
                t_inicio_aprox,
                silencios,
                ventana_busqueda=3.0  # ventana más corta para comentarios
            )
            # Anclar fin al siguiente silencio para incluir pausa
            t_fin_corte = anclar_fin_a_silencio(t_fin, silencios, ventana_busqueda=2.0)

            duracion = t_fin_corte - t_inicio_corte
            if duracion >= 0.3:
                print(f"   [{tipo}] {desc}")
                print(f"      {t_inicio_corte:.2f}s → {t_fin_corte:.2f}s ({duracion:.1f}s)")
                cortes_finales.append((t_inicio_corte, t_fin_corte, desc))

    print(f"\n   Total cortes precisos: {len(cortes_finales)}")
    return cortes_finales


# ─────────────────────────────────────────
#  HERRAMIENTA DE DIAGNÓSTICO
#  Corre esto para ver los cortes ANTES de aplicarlos
# ─────────────────────────────────────────
def diagnosticar_cortes(audio_path, guion_path, openai_api_key):
    """
    Herramienta de diagnóstico independiente.
    Muestra qué cortaría el sistema sin tocar el video.

    Uso en CMD:
    py -3.11 cortes_precisos.py audio.mp3 guion.txt
    """
    print(f"\n{'='*55}")
    print(f"  DIAGNÓSTICO DE CORTES")
    print(f"  Audio: {audio_path}")
    print(f"  Guion: {guion_path}")
    print(f"{'='*55}")

    # Transcribir
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
        print("\n1. Transcribiendo con Whisper...")
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="es",
                response_format="verbose_json",
                timestamp_granularities=["word"],
                prompt="Transcribe literalmente. No corrijas nada. Si alguien dice repito escribe repito. Si dice una palabra incompleta escríbela incompleta.",
                temperature=0.0
            )
        audio_words = [
            {"t_ini": w.start, "t_fin": w.end, "orig": w.word.strip()}
            for w in (result.words or [])
            if w.word.strip()
        ]
        print(f"   {len(audio_words)} palabras transcritas")
    except Exception as e:
        print(f"   Error Whisper: {e}")
        return

    with open(guion_path, "r", encoding="utf-8") as f:
        guion_texto = f.read()

    cortes = calcular_cortes_precisos(guion_texto, audio_words, audio_path, openai_api_key)

    print(f"\n{'='*55}")
    print(f"  RESUMEN — {len(cortes)} corte(s) a aplicar:")
    for i, (t_ini, t_fin, desc) in enumerate(cortes, 1):
        dur = t_fin - t_ini
        print(f"  [{i}] {t_ini:.2f}s → {t_fin:.2f}s ({dur:.1f}s) — {desc}")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────
#  PUNTO DE ENTRADA (diagnóstico standalone)
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.getenv("OPENAI_API_KEY", "")

    if len(sys.argv) < 3:
        print("Uso: py -3.11 cortes_precisos.py audio.mp3 guion.txt")
        sys.exit(1)

    diagnosticar_cortes(sys.argv[1], sys.argv[2], api_key)
