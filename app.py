from flask import Flask, render_template, request, jsonify, send_file, Response
import subprocess
import os
import threading
import uuid
import json
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

jobs = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/procesar', methods=['POST'])
def procesar():
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {'status': 'subiendo', 'progress': 0, 'log': [], 'output': None}

    video = request.files.get('video')
    guion = request.files.get('guion')
    tipo = request.form.get('tipo', 'reel')
    subtitulos = request.form.get('subtitulos') == 'true'
    limpia_audio = request.form.get('limpia_audio') == 'true'
    voz_pro = request.form.get('voz_pro') == 'true'
    solo_limpiar = request.form.get('solo_limpiar') == 'true'
    animaciones = request.form.get('animaciones') == 'true'
    sin_silencios = request.form.get('sin_silencios') == 'true'

    if not video:
        return jsonify({'error': 'No se subio video'}), 400

    video_path = os.path.join(UPLOAD_FOLDER, f'{job_id}_{video.filename}')
    video.save(video_path)

    guion_path = None
    if guion and guion.filename:
        guion_path = os.path.join(UPLOAD_FOLDER, f'{job_id}_guion.txt')
        guion.save(guion_path)

    cortes = request.files.get('cortes')
    cortes_path = None
    if cortes and cortes.filename:
        cortes_path = os.path.join(UPLOAD_FOLDER, f'{job_id}_cortes.txt')
        cortes.save(cortes_path)

    def correr_editor():
        jobs[job_id]['status'] = 'procesando'
        cmd = ['python', 'editor_josue_v7_clean.py', 'reel',
               os.path.basename(video_path),
               ]
        if guion_path:
            cmd += ['--guion', os.path.basename(guion_path)]
        if subtitulos:
            cmd.append('--subtitulos')
        if limpia_audio:
            cmd.append('--limpia-audio')
        if solo_limpiar:
            cmd.append('--solo-limpiar')
        if voz_pro:
            cmd.append('--voz-pro')
        if cortes_path:
            cmd += ['--cortes', os.path.basename(cortes_path)]
        if sin_silencios:
            cmd.append('--sin-silencios')

        os.makedirs('input', exist_ok=True)
        os.rename(video_path, os.path.join('input', os.path.basename(video_path)))
        if guion_path:
            os.rename(guion_path, os.path.join('input', os.path.basename(guion_path)))
        if cortes_path:
            os.rename(cortes_path, os.path.join('input', os.path.basename(cortes_path)))

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            if 'Descargando desde Drive' in line and jobs[job_id]['log'] and 'Descargando desde Drive' in jobs[job_id]['log'][-1]:
                jobs[job_id]['log'][-1] = line
            else:
                jobs[job_id]['log'].append(line)
                jobs[job_id]['status'] = (
                    'descargando' if 'Descargando' in line else
                    'procesando' if any(x in line for x in ['Eliminando', 'Transcribiendo', 'GPT-4o', 'Aplicando']) else
                    'subiendo' if 'Subiendo' in line else
                    jobs[job_id]['status']
                )
        proc.wait()

        nombre_base = os.path.splitext(os.path.basename(video_path))[0]
        archivo_output = None
        for f in os.listdir('output'):
            if nombre_base in f:
                archivo_output = f
                break

        # Aplicar animaciones si se pidió
        if animaciones and archivo_output and proc.returncode == 0:
            jobs[job_id]['log'].append('Aplicando animaciones...')
            ruta_input_anim  = os.path.join('output', archivo_output)
            nombre_con_anim  = archivo_output.replace('.mp4', '_anim.mp4')
            ruta_output_anim = os.path.join('output', nombre_con_anim)
            cmd_anim = ['python', 'overlay_animaciones.py', ruta_input_anim, ruta_output_anim]
            proc_anim = subprocess.Popen(cmd_anim, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in proc_anim.stdout:
                line = line.strip()
                if line:
                    jobs[job_id]['log'].append(line)
            proc_anim.wait()
            if proc_anim.returncode == 0 and os.path.exists(ruta_output_anim):
                archivo_output = nombre_con_anim
                jobs[job_id]['log'].append('Animaciones aplicadas.')
            else:
                jobs[job_id]['log'].append('Error al aplicar animaciones, se entrega video sin animaciones.')

        jobs[job_id]['output'] = archivo_output
        jobs[job_id]['status'] = 'listo' if proc.returncode == 0 else 'error'

    t = threading.Thread(target=correr_editor)
    t.daemon = True
    t.start()
    return jsonify({'job_id': job_id})


@app.route('/procesar-drive', methods=['POST'])
def procesar_drive():
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {'status': 'iniciando', 'progress': 0, 'log': [], 'output': None, 'drive_link': None}

    data = request.json
    drive_file_id = data.get('drive_file_id', '').strip()
    guion_texto   = data.get('guion', '').strip()
    tipo          = data.get('tipo', 'reel')
    subtitulos    = data.get('subtitulos', False)
    limpia_audio  = data.get('limpia_audio', False)
    solo_limpiar  = data.get('solo_limpiar', True)
    voz_pro       = data.get('voz_pro', False)
    animaciones   = data.get('animaciones', False)
    sin_silencios = data.get('sin_silencios', False)

    if not drive_file_id:
        return jsonify({'error': 'Falta el ID del archivo de Drive'}), 400

    carpeta_output_id = os.getenv('DRIVE_OUTPUT_FOLDER_ID', '')

    def correr_editor_drive():
        try:
            from drive_utils import descargar_archivo, subir_archivo

            # 1. Descargar video desde Drive
            nombre_video = f'drive_{job_id}.mp4'
            video_local  = os.path.join('input', nombre_video)
            os.makedirs('input', exist_ok=True)

            jobs[job_id]['status'] = 'descargando'
            jobs[job_id]['log'].append('Descargando video desde Google Drive...')
            from drive_utils import get_drive_service
            from googleapiclient.http import MediaIoBaseDownload
            service = get_drive_service()
            request = service.files().get_media(fileId=drive_file_id)
            with open(video_local, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request, chunksize=50*1024*1024)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    pct = int(status.progress() * 100)
                    jobs[job_id]['log'][-1] = f'Descargando desde Drive... {pct}%'
                    pct = int(status.progress() * 100)
                    jobs[job_id]['log'].append(f'Descargando desde Drive... {pct}%')
            jobs[job_id]['log'].append(f'Descarga completa.')
            jobs[job_id]['log'].append('Descarga completa. Iniciando procesamiento...')

            # 2. Guardar guion si viene
            guion_nombre = None
            if guion_texto:
                guion_nombre = f'guion_{job_id}.txt'
                with open(os.path.join('input', guion_nombre), 'w', encoding='utf-8') as f:
                    f.write(guion_texto)

            # 3. Correr editor
            jobs[job_id]['status'] = 'procesando'
            cmd = ['python', 'editor_josue_v7_clean.py', 'reel',
                   nombre_video, ]
            if guion_nombre:
                cmd += ['--guion', guion_nombre]
            if subtitulos:
                cmd.append('--subtitulos')
            if limpia_audio:
                cmd.append('--limpia-audio')
            if solo_limpiar:
                cmd.append('--solo-limpiar')
            if voz_pro:
                cmd.append('--voz-pro')
            if sin_silencios:
                cmd.append('--sin-silencios')

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                line = line.strip()
                if line:
                    jobs[job_id]['log'].append(line)
            proc.wait()

            if proc.returncode != 0:
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['log'].append('Error en el procesamiento.')
                return

            # 4. Buscar archivo de output
            nombre_base = os.path.splitext(nombre_video)[0]
            archivo_output = None
            for f in os.listdir('output'):
                if nombre_base in f:
                    archivo_output = f
                    break

            if not archivo_output:
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['log'].append('No se encontro el archivo de salida.')
                return

            # 5. Aplicar animaciones si se pidió
            if animaciones and archivo_output:
                jobs[job_id]['log'].append('Aplicando animaciones...')
                ruta_input_anim  = os.path.join('output', archivo_output)
                nombre_con_anim  = archivo_output.replace('.mp4', '_anim.mp4')
                ruta_output_anim = os.path.join('output', nombre_con_anim)

                # Descargar MP4 de animaciones desde Drive si viene animaciones_data
                animaciones_data = data.get('animaciones_data')
                timings_json_path = None
                if animaciones_data:
                    jobs[job_id]['log'].append('Descargando MP4 de animaciones desde Drive...')
                    os.makedirs('tmp_animaciones', exist_ok=True)
                    timings_local = []
                    for anim in animaciones_data:
                        mp4_local = os.path.join('tmp_animaciones', anim['archivo'])
                        try:
                            descargar_archivo(anim['drive_id'], mp4_local)
                            timings_local.append({
                                'html': anim['archivo'],
                                'start': anim['start'],
                                'duration': anim['duration']
                            })
                            jobs[job_id]['log'].append(f"  OK: {anim['archivo']}")
                        except Exception as e:
                            jobs[job_id]['log'].append(f"  Error descargando {anim['archivo']}: {e}")
                    timings_json_path = 'tmp_timings_drive.json'
                    import json as _json
                    with open(timings_json_path, 'w') as f:
                        _json.dump(timings_local, f)

                if timings_json_path:
                    cmd_anim = ['python', 'overlay_animaciones.py',
                                ruta_input_anim, timings_json_path,
                                'tmp_animaciones', ruta_output_anim]
                else:
                    cmd_anim = ['python', 'overlay_animaciones.py',
                                ruta_input_anim, ruta_output_anim]

                proc_anim = subprocess.Popen(cmd_anim, stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, text=True)
                for line in proc_anim.stdout:
                    line = line.strip()
                    if line:
                        jobs[job_id]['log'].append(line)
                proc_anim.wait()
                if proc_anim.returncode == 0 and os.path.exists(ruta_output_anim):
                    archivo_output = nombre_con_anim
                    jobs[job_id]['log'].append('Animaciones aplicadas.')

                # Limpiar temporales
                import shutil as _shutil
                if os.path.exists('tmp_animaciones'):
                    _shutil.rmtree('tmp_animaciones')
                if timings_json_path and os.path.exists(timings_json_path):
                    os.remove(timings_json_path)

            # 6. Subir resultado a Drive
            jobs[job_id]['status'] = 'subiendo'
            jobs[job_id]['log'].append('Subiendo video procesado a Google Drive...')
            ruta_output = os.path.join('output', archivo_output)
            _, link = subir_archivo(ruta_output, f'procesado_{job_id}.mp4', carpeta_output_id)

            jobs[job_id]['status'] = 'listo'
            jobs[job_id]['output'] = archivo_output
            jobs[job_id]['drive_link'] = link
            jobs[job_id]['log'].append(f'Listo. Video en Drive: {link}')

        except Exception as e:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['log'].append(f'Error: {str(e)}')

    t = threading.Thread(target=correr_editor_drive)
    t.daemon = True
    t.start()
    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job no encontrado'}), 404
    return jsonify(job)

@app.route('/descargar/<job_id>')
def descargar(job_id):
    job = jobs.get(job_id)
    if not job or not job.get('output'):
        return jsonify({'error': 'No hay output'}), 404
    path = os.path.join('output', job['output'])
    return send_file(path, as_attachment=True)

@app.route('/diagnostico-render')
def diagnostico_render():
    import subprocess
    try:
        r = subprocess.run(
            ['node', 'diagnostico_railway.js'],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        output = r.stdout + ('\n\nSTDERR:\n' + r.stderr if r.stderr else '')
        return f'<pre style="background:#111;color:#eee;padding:20px;font-family:monospace;font-size:13px">{output}</pre>'
    except subprocess.TimeoutExpired:
        return '<pre>TIMEOUT</pre>', 500
    except Exception as e:
        return f'<pre>ERROR: {e}</pre>', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


