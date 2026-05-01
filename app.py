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
    solo_limpiar = request.form.get('solo_limpiar') == 'true'

    if not video:
        return jsonify({'error': 'No se subio video'}), 400

    video_path = os.path.join(UPLOAD_FOLDER, f'{job_id}_{video.filename}')
    video.save(video_path)

    guion_path = None
    if guion and guion.filename:
        guion_path = os.path.join(UPLOAD_FOLDER, f'{job_id}_guion.txt')
        guion.save(guion_path)

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

        os.makedirs('input', exist_ok=True)
        os.rename(video_path, os.path.join('input', os.path.basename(video_path)))
        if guion_path:
            os.rename(guion_path, os.path.join('input', os.path.basename(guion_path)))

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            line = line.strip()
            if line:
                jobs[job_id]['log'].append(line)
        proc.wait()

        nombre_base = os.path.splitext(os.path.basename(video_path))[0]
        for f in os.listdir('output'):
            if nombre_base in f:
                jobs[job_id]['output'] = f
                break

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
            descargar_archivo(drive_file_id, video_local)
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

            # 5. Subir resultado a Drive
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
