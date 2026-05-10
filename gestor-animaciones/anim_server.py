"""
anim_server.py - Gestor local de animaciones Codigo Soberana
Ubicacion: C:\Videos_Josue\gestor-animaciones\anim_server.py
Correr: py -3.11 anim_server.py
Abrir:  http://localhost:5050
"""
from flask import Flask, request, jsonify, send_from_directory, send_file
import subprocess, os, threading, uuid, sys, re

ESTE_DIR   = os.path.dirname(os.path.abspath(__file__))
JOSUE_DIR  = os.path.dirname(ESTE_DIR)
CAPTURE_JS = os.path.join(JOSUE_DIR, "capture_animation.js")
CHROME     = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SALIDA_MP4 = os.path.join(JOSUE_DIR, "workshop-animaciones", "animaciones")
UPLOAD_TMP = os.path.join(JOSUE_DIR, "tmp_anim_uploads")
SRT_OUT    = os.path.join(JOSUE_DIR, "subtitulos")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

sys.path.insert(0, JOSUE_DIR)
os.chdir(JOSUE_DIR)
os.makedirs(SALIDA_MP4, exist_ok=True)
os.makedirs(UPLOAD_TMP, exist_ok=True)
os.makedirs(SRT_OUT,    exist_ok=True)

app = Flask(__name__, static_folder=os.path.join(ESTE_DIR, "anim_templates"), static_url_path="")
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024

jobs = {}

# ── Calcular duracion desde HTML ─────────────────────────────────
def calcular_duracion(c):
    # 1. DURACION_MS explicita
    m = re.search(r'const\s+DURACION_MS\s*=\s*(\d+)', c)
    if m: return int(m.group(1)) + 1500

    # 2. Fade out total con setTimeout grande al final
    fade_m = re.search(r'Fade out total[\s\S]{0,300}},\s*(\d{5,})\s*\)', c)
    if fade_m: return int(fade_m.group(1)) + 700 + 1500

    # 3. Slides con dur:
    durs = re.findall(r'dur\s*:\s*(\d+)', c)
    if durs:
        total = sum(int(d) for d in durs)
        t = re.search(r'const\s+TRANS\s*=\s*(\d+)', c)
        return total + (len(durs) * (int(t.group(1)) if t else 380)) + 1500

    # 4. Escritura letra a letra
    dm  = re.search(r'DELAY_INICIO\s*=\s*(\d+)', c)
    vm  = re.search(r'VELOCIDAD\s*=\s*(\d+)', c)
    vis = re.search(r'DURACION_VISIBLE\s*=\s*(\d+)', c)
    tx  = re.search(r'const texto\s*=\s*["\']([^"\']+)["\']', c)
    if dm and vm and vis and tx:
        return int(dm.group(1)) + len(tx.group(1)) * int(vm.group(1)) + int(vis.group(1)) + 700 + 1500

    # 5. Patron },N) buscar el mayor timeout
    tos2 = [int(x) for x in re.findall(r'},\s*(\d{4,})\s*\)', c)]
    if tos2: return max(tos2) + 1500

    # 6. Fallback
    tos = [int(x) for x in re.findall(r'setTimeout\([^,]+,\s*(\d{4,})\)', c)]
    return (max(tos) + 2000) if tos else 10000

def limpiar_nombre(nombre):
    """Quita sufijos tipo ' (1).html' que Windows agrega a duplicados"""
    m = re.match(r'^(.+?) \(\d+\)(\.html)$', nombre)
    if m:
        return m.group(1) + m.group(2)
    return nombre

# ── API: recibir HTMLs arrastrados ───────────────────────────────
@app.route("/api/cargar-htmls", methods=["POST"])
def cargar_htmls():
    archivos = request.files.getlist("htmls")
    resultado = []
    for f in archivos:
        if not f.filename.endswith(".html"):
            continue
        contenido = f.read().decode("utf-8", errors="ignore")
        dur = calcular_duracion(contenido)
        nombre = limpiar_nombre(f.filename)
        ruta = os.path.join(UPLOAD_TMP, nombre)
        with open(ruta, "w", encoding="utf-8") as fout:
            fout.write(contenido)
        mp4 = os.path.join(SALIDA_MP4, nombre.replace(".html", ".mp4"))
        resultado.append({
            "nombre":     nombre,
            "duracion_s": round(dur / 1000, 1),
            "tiene_mp4":  os.path.exists(mp4)
        })
    return jsonify(resultado)

# ── API: renderizar ──────────────────────────────────────────────
@app.route("/api/renderizar", methods=["POST"])
def renderizar():
    data     = request.json
    archivos = data.get("archivos", [])
    escalar  = data.get("escalar_4k", False)
    job_id   = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "procesando", "log": [], "total": len(archivos), "ok": 0, "errores": []}

    def correr():
        os.makedirs(SALIDA_MP4, exist_ok=True)
        salida_4k = SALIDA_MP4 + "_4k"
        if escalar: os.makedirs(salida_4k, exist_ok=True)
        env = os.environ.copy()
        env["PUPPETEER_EXECUTABLE_PATH"] = CHROME
        for archivo in archivos:
            html = os.path.join(UPLOAD_TMP, archivo)
            mp4  = os.path.join(SALIDA_MP4, archivo.replace(".html", ".mp4"))
            if not os.path.exists(html):
                jobs[job_id]["log"].append(f"FALTA: {archivo}")
                jobs[job_id]["errores"].append(archivo); continue
            if archivo in duraciones_ms:
                dur = duraciones_ms[archivo]
            else:
                with open(html, "r", encoding="utf-8", errors="ignore") as fh:
                    dur = calcular_duracion(fh.read())
            jobs[job_id]["log"].append(f"Renderizando {archivo} ({round(dur/1000,1)}s)...")
            r = subprocess.run(["node", CAPTURE_JS, html, mp4, str(dur)], capture_output=True, text=True, env=env)
            if r.returncode == 0:
                jobs[job_id]["log"].append(f"OK: {archivo}")
                jobs[job_id]["ok"] += 1
                if escalar:
                    mp4_4k = os.path.join(salida_4k, archivo.replace(".html", ".mp4"))
                    jobs[job_id]["log"].append(f"Escalando 4K: {archivo}...")
                    r4k = subprocess.run(["ffmpeg","-y","-i",mp4,"-vf","scale=3840:2160:flags=lanczos","-c:v","libx264","-crf","16","-preset","slow","-c:a","copy",mp4_4k], capture_output=True, text=True)
                    jobs[job_id]["log"].append(f"4K OK: {archivo}" if r4k.returncode == 0 else f"Error 4K: {archivo}")
            else:
                jobs[job_id]["log"].append(f"ERROR: {archivo}")
                jobs[job_id]["errores"].append(archivo)
        jobs[job_id]["status"] = "listo"
        jobs[job_id]["log"].append(f"Terminado: {jobs[job_id]['ok']} de {len(archivos)}")

    threading.Thread(target=correr, daemon=True).start()
    return jsonify({"job_id": job_id})

# ── API: subir a Drive ───────────────────────────────────────────
@app.route("/api/subir", methods=["POST"])
def subir():
    data     = request.json
    archivos = data.get("archivos", [])
    drive_id = data.get("carpeta_drive_id", "")
    usar_4k  = data.get("usar_4k", False)
    job_id   = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "subiendo", "log": [], "total": len(archivos), "ok": 0, "errores": []}

    def correr():
        from drive_utils import get_drive_service, subir_archivo
        carpeta = SALIDA_MP4 + "_4k" if usar_4k else SALIDA_MP4
        try:
            service = get_drive_service()
            res = service.files().list(
                q=f"'{drive_id}' in parents and trashed=false",
                fields="files(name)"
            ).execute()
            ya_en_drive = {f["name"] for f in res.get("files", [])}
        except:
            ya_en_drive = set()
        for archivo in archivos:
            mp4  = archivo.replace(".html", ".mp4")
            ruta = os.path.join(carpeta, mp4)
            if not os.path.exists(ruta):
                jobs[job_id]["log"].append(f"FALTA MP4: {mp4}")
                jobs[job_id]["errores"].append(mp4); continue
            if mp4 in ya_en_drive:
                jobs[job_id]["log"].append(f"Ya existe en Drive: {mp4}")
                jobs[job_id]["ok"] += 1; continue
            jobs[job_id]["log"].append(f"Subiendo {mp4}...")
            try:
                _, link = subir_archivo(ruta, mp4, drive_id)
                jobs[job_id]["log"].append(f"OK: {mp4}")
                jobs[job_id]["ok"] += 1
                ya_en_drive.add(mp4)
            except Exception as e:
                jobs[job_id]["log"].append(f"ERROR {mp4}: {str(e)}")
                jobs[job_id]["errores"].append(mp4)
        jobs[job_id]["status"] = "listo"
        jobs[job_id]["log"].append(f"Subidos: {jobs[job_id]['ok']} de {len(archivos)}")

    threading.Thread(target=correr, daemon=True).start()
    return jsonify({"job_id": job_id})

# ── API: generar SRT ─────────────────────────────────────────────
@app.route("/api/generar-srt", methods=["POST"])
def generar_srt():
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "procesando", "log": [], "srt_path": None, "srt_nombre": None}

    if request.is_json:
        data     = request.json
        drive_id = data.get("drive_id", "").strip()
        nombre   = data.get("nombre", "video_drive").strip()
        if not drive_id:
            return jsonify({"error": "Falta drive_id"}), 400
        video_path = os.path.join(UPLOAD_TMP, f"{job_id}_{nombre}.mp4")

        def correr():
            try:
                from drive_utils import get_drive_service
                from googleapiclient.http import MediaIoBaseDownload
                jobs[job_id]["log"].append("Descargando video desde Drive...")
                service = get_drive_service()
                req = service.files().get_media(fileId=drive_id)
                with open(video_path, "wb") as f:
                    downloader = MediaIoBaseDownload(f, req, chunksize=50*1024*1024)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        pct = int(status.progress() * 100)
                        jobs[job_id]["log"][-1] = f"Descargando desde Drive... {pct}%"
                jobs[job_id]["log"].append("Descarga completa.")
                _procesar_srt(job_id, video_path, nombre)
            except Exception as e:
                jobs[job_id]["log"].append(f"Error: {str(e)}")
                jobs[job_id]["status"] = "error"

        threading.Thread(target=correr, daemon=True).start()
        return jsonify({"job_id": job_id})

    if "video" not in request.files:
        return jsonify({"error": "No se subio video"}), 400
    video      = request.files["video"]
    video_path = os.path.join(UPLOAD_TMP, f"{job_id}_{video.filename}")
    video.save(video_path)

    def correr():
        _procesar_srt(job_id, video_path, video.filename)

    threading.Thread(target=correr, daemon=True).start()
    return jsonify({"job_id": job_id})


def _procesar_srt(job_id, video_path, nombre_original):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        jobs[job_id]["log"].append("Extrayendo audio...")
        audio_path = os.path.splitext(video_path)[0] + ".wav"
        r = subprocess.run(["ffmpeg","-y","-i",video_path,"-vn","-ar","16000","-ac","1","-f","wav",audio_path], capture_output=True, text=True)
        if r.returncode != 0:
            jobs[job_id]["log"].append("Error extrayendo audio")
            jobs[job_id]["status"] = "error"; return
        jobs[job_id]["log"].append("Transcribiendo con Whisper...")
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1", file=f, language="es",
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
        def seg_a_srt(s):
            h=int(s//3600); m=int((s%3600)//60); sec=int(s%60); ms=int((s-int(s))*1000)
            return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
        nombre_base = os.path.splitext(os.path.basename(nombre_original))[0]
        srt_path    = os.path.join(SRT_OUT, f"{job_id}_{nombre_base}.srt")
        words       = result.words if hasattr(result, 'words') and result.words else []
        if words:
            jobs[job_id]["log"].append(f"Generando SRT ({len(words)} palabras)...")
            with open(srt_path, "w", encoding="utf-8") as f:
                i=0; idx=1
                while i < len(words):
                    grupo=words[i:i+3]; ini=grupo[0].start; fin=grupo[-1].end
                    texto=" ".join(w.word for w in grupo)
                    f.write(f"{idx}\n{seg_a_srt(ini)} --> {seg_a_srt(fin)}\n{texto}\n\n")
                    i+=3; idx+=1
        else:
            segs = result.segments if hasattr(result, 'segments') and result.segments else []
            jobs[job_id]["log"].append(f"Generando SRT ({len(segs)} segmentos)...")
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, seg in enumerate(segs, 1):
                    f.write(f"{i}\n{seg_a_srt(seg.start)} --> {seg_a_srt(seg.end)}\n{seg.text.strip()}\n\n")
        jobs[job_id]["srt_path"]   = srt_path
        jobs[job_id]["srt_nombre"] = os.path.basename(srt_path)
        jobs[job_id]["status"]     = "listo"
        jobs[job_id]["log"].append(f"SRT generado: {os.path.basename(srt_path)}")
        if os.path.exists(audio_path): os.remove(audio_path)
        if os.path.exists(video_path): os.remove(video_path)
    except Exception as e:
        jobs[job_id]["log"].append(f"Error: {str(e)}")
        jobs[job_id]["status"] = "error"

# ── API: descargar SRT ───────────────────────────────────────────
@app.route("/api/descargar-srt/<job_id>")
def descargar_srt(job_id):
    job = jobs.get(job_id)
    if not job or not job.get("srt_path"):
        return jsonify({"error": "SRT no disponible"}), 404
    return send_file(job["srt_path"], as_attachment=True, download_name=job["srt_nombre"])

# ── API: status ──────────────────────────────────────────────────
@app.route("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job: return jsonify({"error": "Job no encontrado"}), 404
    return jsonify(job)

# ── Interfaz ─────────────────────────────────────────────────────
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(ESTE_DIR, "anim_templates"), "favicon.ico")

@app.route("/")
def index():
    return send_from_directory(os.path.join(ESTE_DIR, "anim_templates"), "index.html")

if __name__ == "__main__":
    print("")
    print("  Gestor de Animaciones — Codigo Soberana")
    print(f"  Salida MP4: {SALIDA_MP4}")
    print(f"  capture_animation.js: {CAPTURE_JS}")
    print("  Abre: http://localhost:5050")
    print("")
    app.run(host="0.0.0.0", port=5050, debug=False)
