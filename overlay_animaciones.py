import subprocess, os, shutil, sys, json

ENV_DISPLAY = os.getenv("DISPLAY", ":99")
CHROME = os.getenv("PUPPETEER_EXECUTABLE_PATH", "/usr/bin/chromium")

def capturar_animacion(html_path, duracion, salida_mp4):
    print(f"   Capturando {os.path.basename(html_path)} ({duracion}s)...")
    html_abs = os.path.abspath(html_path).replace("\\", "/")
    fps = 30

    script_js = f"""
const puppeteer = require('puppeteer');
const {{ PuppeteerScreenRecorder }} = require('puppeteer-screen-recorder');
(async () => {{
  const browser = await puppeteer.launch({{
    executablePath: '{CHROME}',
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-gpu','--use-gl=swiftshader','--use-software-gl','--ignore-gpu-blocklist','--disable-web-security','--window-size=1080,1920'],
    defaultViewport: {{ width: 1280, height: 720 }}
  }});
  const page = await browser.newPage();
  const recorder = new PuppeteerScreenRecorder(page, {{
    fps: {fps},
    videoFrame: {{ width: 1280, height: 720 }},
    aspectRatio: '16:9',
    recordDurationLimit: {duracion + 2},
  }});
  await recorder.start('{salida_mp4.replace(os.sep, "/")}');
  await page.goto('file:///{html_abs}', {{ waitUntil: 'networkidle0', timeout: 15000 }});
  await new Promise(r => setTimeout(r, {duracion * 1000}));
  await recorder.stop();
  await browser.close();
  console.log('OK');
}})().catch(e => {{ console.error('ERROR:', e.message); process.exit(1); }});
"""
    js_path = f"tmp_cap_{os.path.basename(html_path)}.js"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(script_js)

    env = os.environ.copy()
    env["DISPLAY"] = ENV_DISPLAY
    r = subprocess.run(["node", js_path], capture_output=True, text=True, env=env)
    if os.path.exists(js_path):
        os.remove(js_path)
    if r.returncode != 0:
        print(f"   Error: {r.stderr[-300:]}")
        return False
    if not os.path.exists(salida_mp4) or os.path.getsize(salida_mp4) < 1000:
        print(f"   Error: archivo vacio")
        return False
    return True


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
    return r.returncode == 0


def aplicar_animaciones(video_entrada, timings_json, html_folder, video_salida):
    print(f"\nAplicando animaciones a: {video_entrada}")
    with open(timings_json, "r", encoding="utf-8") as f:
        timings = json.load(f)
    print(f"   {len(timings)} animaciones")

    # Capturar
    print("\n--- Capturando ---")
    caps = {}
    for t in timings:
        html_path = os.path.join(html_folder, t["html"])
        if not os.path.exists(html_path):
            print(f"   FALTA: {html_path}")
            continue
        # Si el MP4 ya existe (descargado desde Drive), usarlo directamente
        mp4_prerender = os.path.join(html_folder, os.path.splitext(t["html"])[0] + ".mp4")
        if os.path.exists(mp4_prerender):
            print(f"   Usando MP4 pre-renderizado: {mp4_prerender}")
            caps[t["html"]] = mp4_prerender
        elif capturar_animacion(html_path, t["duration"], f"tmp_anim_{os.path.splitext(t['html'])[0]}.mp4"):
            mp4_tmp = f"tmp_anim_{os.path.splitext(t['html'])[0]}.mp4"
            caps[t["html"]] = mp4_tmp
        else:
            print(f"   Omitiendo {t['html']}")

    if not caps:
        shutil.copy2(video_entrada, video_salida)
        return False

    # Overlay
    print("\n--- Overlays ---")
    video_actual = video_entrada
    for i, t in enumerate(timings):
        if t["html"] not in caps:
            continue
        tmp_out = f"tmp_overlay_{i}.mp4"
        print(f"[{i+1}/{len(timings)}] {t['html']} en {t['start']}s...")
        ok = overlay_animacion(video_actual, caps[t["html"]], t["start"], t["duration"], tmp_out)
        if ok:
            if video_actual != video_entrada and os.path.exists(video_actual):
                os.remove(video_actual)
            video_actual = tmp_out

    shutil.copy2(video_actual, video_salida)
    if video_actual != video_entrada and os.path.exists(video_actual):
        os.remove(video_actual)
    for mp4 in caps.values():
        if os.path.exists(mp4):
            os.remove(mp4)

    print(f"\nListo: {video_salida}")
    return True


# Compatibilidad con llamada antigua (sin JSON)
TIMINGS_DEFAULT = [
    {"html": "anim_an1.html", "start": 25,  "duration": 33},
    {"html": "anim_an2.html", "start": 128, "duration": 30},
    {"html": "anim_an3.html", "start": 254, "duration": 42},
    {"html": "anim_an4.html", "start": 335, "duration": 14},
    {"html": "anim_an5.html", "start": 389, "duration": 22},
    {"html": "anim_an6.html", "start": 458, "duration": 14},
    {"html": "anim_an7.html", "start": 745, "duration": 48},
]

def aplicar_todas_las_animaciones(video_entrada, video_salida, html_folder="workshop-animaciones/compositions"):
    tmp_json = "tmp_timings.json"
    with open(tmp_json, "w") as f:
        json.dump(TIMINGS_DEFAULT, f)
    ok = aplicar_animaciones(video_entrada, tmp_json, html_folder, video_salida)
    if os.path.exists(tmp_json):
        os.remove(tmp_json)
    return ok


if __name__ == "__main__":
    if len(sys.argv) == 3:
        ok = aplicar_todas_las_animaciones(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 5:
        ok = aplicar_animaciones(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Uso: py overlay_animaciones.py entrada.mp4 salida.mp4")
        print("     py overlay_animaciones.py entrada.mp4 timings.json carpeta_html salida.mp4")
        sys.exit(1)
    sys.exit(0 if ok else 1)
