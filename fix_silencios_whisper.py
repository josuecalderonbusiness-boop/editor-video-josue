with open('editor_josue_v7_clean.py', 'r', encoding='utf-8') as f:
    txt = f.read()

viejo = '''def eliminar_silencios(entrada, salida, log=None):
    print("\\nEliminando silencios...")
    umbral_db    = CONFIG["umbral_db"]
    silencio_min = CONFIG["silencio_minimo"]
    margen       = CONFIG["margen_corte"]

    # Detectar duracion total con ffprobe
    r_dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", entrada],
        capture_output=True, text=True
    )
    try:
        duracion_total = float(r_dur.stdout.strip())
    except Exception:
        duracion_total = 0.0

    # PASO A+B — detectar silencios DIRECTO del video (sin pasar por MP3)
    # Motivo: convertir a MP3 introduce delay que desplaza los timestamps
    print("   Detectando silencios directamente del video...")
    cmd_detect = [
        "ffmpeg", "-y", "-i", entrada,
        "-vn",
        "-af", f"silencedetect=noise={umbral_db}dB:d={silencio_min}",
        "-f", "null", "-"
    ]
    r = subprocess.run(cmd_detect, capture_output=True, text=True)
    stderr = r.stderr

    inicios = [float(x) for x in re.findall(r"silence_start: ([\\d.]+)", stderr)]
    fines   = [float(x) for x in re.findall(r"silence_end: ([\\d.]+)", stderr)]

    # Construir segmentos a MANTENER
    silencios = list(zip(inicios, fines))
    segmentos = []
    cursor    = 0.0
    for t_ini_s, t_fin_s in silencios:
        t_i = max(0.0, t_ini_s - margen)
        t_f = min(duracion_total, t_fin_s + margen)
        if cursor < t_i:
            segmentos.append((cursor, t_i))
            if log:
                log.registrar("SILENCIO", t_i, t_f, "pausa/silencio")
        cursor = t_f
    if cursor < duracion_total:
        segmentos.append((cursor, duracion_total))

    if not segmentos:
        print("   Sin segmentos de voz detectados.")
        shutil.copy2(entrada, salida)
        return

    tiempo_cortado = duracion_total - sum(f - i for i, f in segmentos)
    print(f"   Segmentos: {len(segmentos)} | Cortado: {tiempo_cortado:.1f}s")

    # PASO C — aplicar cortes al video original sin recodificar
    print("   Aplicando cortes al video original...")
    lista_tmp = "tmp_sil_concat.txt"
    clips_tmp = []
    with open(lista_tmp, "w", encoding="utf-8") as f:
        for idx, (t_s, t_e) in enumerate(segmentos):
            if t_e - t_s < 0.1:
                continue
            clip_tmp = f"tmp_sil_seg_{idx}.mp4"
            clips_tmp.append(clip_tmp)
            cmd_corte = [
                "ffmpeg", "-y",
                "-ss", str(t_s), "-to", str(t_e),
                "-i", entrada,
                "-c:v", "copy", "-c:a", "aac", "-af", "afade=t=in:st=0:d=0.05",
                "-avoid_negative_ts", "make_zero", clip_tmp
            ]
            subprocess.run(cmd_corte, capture_output=True, text=True)
            f.write(f"file \'{clip_tmp}\'\\n")

    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", lista_tmp, "-c:v", "copy", "-c:a", "aac", salida
    ]
    r2 = subprocess.run(cmd_concat, capture_output=True, text=True)

    if os.path.exists(lista_tmp):
        os.remove(lista_tmp)
    for c in clips_tmp:
        if os.path.exists(c):
            os.remove(c)

    if r2.returncode != 0:
        print(f"   Error FFmpeg concat: {r2.stderr[-200:]}")
        shutil.copy2(entrada, salida)
        return

    print("Silencios eliminados.")'''

nuevo = '''def eliminar_silencios(entrada, salida, log=None):
    """
    Elimina silencios usando timestamps de Whisper.
    Corta exactamente entre palabras — nunca en medio de una silaba.
    """
    print("\\nEliminando silencios con Whisper...")

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
                f.write(f"file \'{clip_tmp}\'\\n")

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

    print("Silencios eliminados con precision de palabra.")'''

if viejo in txt:
    txt = txt.replace(viejo, nuevo)
    print('Fix aplicado correctamente.')
else:
    print('ADVERTENCIA: No se encontro el bloque.')

with open('editor_josue_v7_clean.py', 'w', encoding='utf-8') as f:
    f.write(txt)