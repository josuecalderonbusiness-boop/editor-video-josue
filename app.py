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

# Estado de los jobs
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
        return jsonify({'error': 'No se subió video'}), 400

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
               '--tipo', tipo]
        if guion_path:
            cmd += ['--guion', os.path.basename(guion_path)]
        if subtitulos:
            cmd.append('--subtitulos')
        if limpia_audio:
            cmd.append('--limpia-audio')
        if solo_limpiar:
            cmd.append('--solo-limpiar')

        # Copiar archivos a input/
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

        # Buscar output
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
