import subprocess, os, shutil, sys

ANIMATIONS_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "workshop-animaciones", "compositions", "main-graphics.html")

TIMINGS = [
    { "id": "an1", "start": 25,  "duration": 33 },
    { "id": "an2", "start": 128, "duration": 30 },
    { "id": "an3", "start": 254, "duration": 42 },
    { "id": "an4", "start": 335, "duration": 14 },
    { "id": "an5", "start": 389, "duration": 22 },
    { "id": "an6", "start": 458, "duration": 14 },
    { "id": "an7", "start": 745, "duration": 48 },
]

def capturar_animacion(anim_id, duracion, salida_mp4):
    print(f"   Capturando {anim_id} ({duracion}s)...")
    html_path = ANIMATIONS_HTML.replace("\\", "/")
    script_js = f"""const puppeteer = require('puppeteer');
const {{ PuppeteerScreenRecorder }} = require('puppeteer-screen-recorder');
(async () => {{
  const browser = await puppeteer.launch({{
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files']
  }});
  const page = await browser.newPage();
  await page.setViewport({{ width: 1280, height: 720 }});
  const recorder = new PuppeteerScreenRecorder(page, {{
    fps: 30,
    videoFrame: {{ width: 1280, height: 720 }},
    aspectRatio: '16:9',
  }});
  await recorder.start('{salida_mp4}');
  await page.goto('file:///{html_path}');
  await page.evaluate((id) => {{
    window.showAnimation(id);
    if (id === 'an1') window.startAN1 && window.startAN1();
  }}, '{anim_id}');
  await new Promise(r => setTimeout(r, {duracion * 1000}));
  await recorder.stop();
  await browser.close();
  console.log('OK: {salida_mp4}');
}})().catch(e => {{ console.error(e); process.exit(1); }});
"""
    script_path = f"tmp_cap_{anim_id}.js"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_js)
    r = subprocess.run(["node", script_path], capture_output=True, text=True)
    if os.path.exists(script_path):
        os.remove(script_path)
    if r.returncode != 0:
        print(f"   Error: {r.stderr[-300:]}")
        return False
    return os.path.exists(salida_mp4)

def overlay_animacion(video_entrada, anim_mp4, t_inicio, duracion, video_salida):
    t_fin = t_inicio + duracion
    cmd = [
        "ffmpeg", "-y",
        "-i", video_entrada,
        "-i", anim_mp4,
        "-filter_complex",
        f"[1:v]setpts=PTS+{t_inicio}/TB[anim];[0:v][anim]overlay=0:0:enable='between(t,{t_inicio},{t_fin})'[v]",
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "copy",
        video_salida
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"   Error FFmpeg: {r.stderr[-300:]}")
    return r.returncode == 0

def aplicar_todas_las_animaciones(video_entrada, video_salida):
    print(f"\nAplicando animaciones a: {video_entrada}")

    # Paso 1 — capturar todas las animaciones
    print("\n--- Capturando animaciones ---")
    archivos_anim = {}
    for anim in TIMINGS:
        mp4 = f"tmp_anim_{anim['id']}.mp4"
        ok = capturar_animacion(anim["id"], anim["duration"], mp4)
        if ok:
            archivos_anim[anim["id"]] = mp4
        else:
            print(f"   ADVERTENCIA: {anim['id']} no se pudo capturar, se omite.")

    if not archivos_anim:
        print("No se capturó ninguna animación. Abortando.")
        return False

    # Paso 2 — overlay uno por uno
    print("\n--- Aplicando overlays ---")
    video_actual = video_entrada
    for i, anim in enumerate(TIMINGS):
        anim_id = anim["id"]
        if anim_id not in archivos_anim:
            continue
        tmp_out = f"tmp_overlay_{i}.mp4"
        print(f"\n[{i+1}/7] {anim_id} en segundo {anim['start']}...")
        ok = overlay_animacion(video_actual, archivos_anim[anim_id],
                               anim["start"], anim["duration"], tmp_out)
        if ok:
            if video_actual != video_entrada and os.path.exists(video_actual):
                os.remove(video_actual)
            video_actual = tmp_out
        else:
            print(f"   Saltando {anim_id}.")

    shutil.copy2(video_actual, video_salida)
    if video_actual != video_entrada and os.path.exists(video_actual):
        os.remove(video_actual)

    # Limpiar temporales
    for mp4 in archivos_anim.values():
        if os.path.exists(mp4):
            os.remove(mp4)

    print(f"\nListo: {video_salida}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: py overlay_animaciones.py entrada.mp4 salida.mp4")
        sys.exit(1)
    ok = aplicar_todas_las_animaciones(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)