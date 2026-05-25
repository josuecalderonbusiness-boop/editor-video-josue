/**
 * diagnostico_railway.js
 * ─────────────────────────────────────────────────────────────
 * Verifica si Railway puede renderizar HTML con animaciones CSS/GSAP
 * como MP4 usando Puppeteer + SwiftShader (software renderer).
 *
 * USO LOCAL (Windows):
 *   node diagnostico_railway.js
 *
 * USO EN RAILWAY — agregar ruta temporal en app.py:
 *   @app.route('/diagnostico-render')
 *   def diagnostico_render():
 *       import subprocess
 *       r = subprocess.run(['node', 'diagnostico_railway.js'],
 *                          capture_output=True, text=True, timeout=60)
 *       return r.stdout + r.stderr
 * ─────────────────────────────────────────────────────────────
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// ─── HTML de prueba con animación CSS pura (sin GSAP, sin red) ───
const HTML_TEST = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1080px; height: 1920px; overflow: hidden;
    background: #0F0A0B;
    display: flex; align-items: center; justify-content: center;
    flex-direction: column; gap: 40px;
  }
  .box {
    width: 300px; height: 300px;
    background: linear-gradient(135deg, #6B1A2A, #B8892A);
    border-radius: 16px;
    animation: spin 2s linear infinite;
  }
  .text {
    font-family: sans-serif;
    font-size: 64px;
    color: #F9F3E8;
    animation: pulse 1s ease-in-out infinite alternate;
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
  @keyframes pulse {
    from { opacity: 0.4; transform: scale(0.95); }
    to   { opacity: 1.0; transform: scale(1.05); }
  }
</style>
</head>
<body>
  <div class="box"></div>
  <div class="text">Código Soberana</div>
</body>
</html>`;

// ─── Configuraciones a probar (de más compatible a más exigente) ───
const CONFIGS = [
  {
    nombre: "SwiftShader (software GL)",
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--use-gl=swiftshader',
      '--use-software-gl',
      '--ignore-gpu-blocklist',
      '--disable-web-security',
    ]
  },
  {
    nombre: "Angle (GLES backend)",
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--use-gl=angle',
      '--use-angle=swiftshader',
      '--ignore-gpu-blocklist',
      '--disable-web-security',
    ]
  },
  {
    nombre: "Modo headless puro (sin GL)",
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--headless=new',
      '--virtual-time-budget=5000',
      '--disable-web-security',
    ]
  },
];

// ─── Resultado acumulado ───
const resultados = [];

function log(msg) {
  const linea = `[${new Date().toISOString().slice(11,19)}] ${msg}`;
  console.log(linea);
  resultados.push(linea);
}

// ─── Test 1: Screenshot (verifica que el HTML se renderiza) ───────
async function testScreenshot(browser, htmlPath) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920 });

  await page.goto(`file://${htmlPath}`, { waitUntil: 'load', timeout: 15000 });
  await new Promise(r => setTimeout(r, 800)); // esperar animación

  const screenshotPath = path.join(__dirname, `tmp_diag_screenshot.png`);
  await page.screenshot({ path: screenshotPath, fullPage: false });
  await page.close();

  const tamano = fs.existsSync(screenshotPath) ? fs.statSync(screenshotPath).size : 0;
  fs.existsSync(screenshotPath) && fs.unlinkSync(screenshotPath);

  return tamano;
}

// ─── Test 2: Grabación de video (el test real) ────────────────────
async function testGrabacion(browser, htmlPath, outputPath) {
  let PuppeteerScreenRecorder;
  try {
    ({ PuppeteerScreenRecorder } = require('puppeteer-screen-recorder'));
  } catch (e) {
    return { ok: false, error: 'puppeteer-screen-recorder no instalado: ' + e.message };
  }

  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920 });

  const recorder = new PuppeteerScreenRecorder(page, {
    fps: 30,
    videoFrame: { width: 1080, height: 1920 },
    videoCrf: 23,
    videoCodec: 'libx264',
    videoPreset: 'ultrafast',
  });

  await page.goto(`file://${htmlPath}`, { waitUntil: 'load', timeout: 15000 });
  await new Promise(r => setTimeout(r, 500));

  await recorder.start(outputPath);
  await new Promise(r => setTimeout(r, 3000)); // grabar 3 segundos
  await recorder.stop();
  await page.close();

  const tamano = fs.existsSync(outputPath) ? fs.statSync(outputPath).size : 0;
  return { ok: tamano > 50000, tamano };
}

// ─── Runner principal ─────────────────────────────────────────────
async function main() {
  log('══════════════════════════════════════════');
  log('  DIAGNÓSTICO RAILWAY — Render HTML → MP4');
  log('══════════════════════════════════════════');
  log(`Node.js: ${process.version}`);
  log(`Plataforma: ${process.platform} ${process.arch}`);
  log(`Chromium: ${process.env.PUPPETEER_EXECUTABLE_PATH || 'default'}`);
  log('');

  // Escribir HTML de prueba a disco
  const htmlPath = path.join(__dirname, 'tmp_diag_test.html');
  fs.writeFileSync(htmlPath, HTML_TEST, 'utf8');
  log(`HTML de prueba escrito: ${htmlPath}`);
  log('');

  let configuracionGanadora = null;

  for (const config of CONFIGS) {
    log(`─── Probando: ${config.nombre} ───`);

    let browser;
    try {
      browser = await puppeteer.launch({
        headless: 'new',
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
        args: config.args,
        timeout: 20000,
      });
      log(`  ✓ Browser abrió`);
    } catch (e) {
      log(`  ✗ Browser no abrió: ${e.message}`);
      continue;
    }

    // Test 1: Screenshot
    let tamanoScreenshot = 0;
    try {
      tamanoScreenshot = await testScreenshot(browser, htmlPath);
      if (tamanoScreenshot > 5000) {
        log(`  ✓ Screenshot OK (${(tamanoScreenshot/1024).toFixed(1)}KB) — HTML se renderiza`);
      } else {
        log(`  ✗ Screenshot muy pequeño (${tamanoScreenshot}B) — posible pantalla negra`);
      }
    } catch (e) {
      log(`  ✗ Screenshot falló: ${e.message}`);
    }

    // Test 2: Grabación de video
    const mp4Path = path.join(__dirname, `tmp_diag_output.mp4`);
    let resultadoVideo = { ok: false, tamano: 0 };
    try {
      resultadoVideo = await testGrabacion(browser, htmlPath, mp4Path);
      if (resultadoVideo.ok) {
        log(`  ✓ VIDEO OK (${(resultadoVideo.tamano/1024).toFixed(1)}KB) ← ESTA CONFIGURACIÓN FUNCIONA`);
        configuracionGanadora = config;
      } else {
        log(`  ✗ Video vacío o muy pequeño (${resultadoVideo.tamano}B)`);
      }
    } catch (e) {
      log(`  ✗ Grabación falló: ${e.message}`);
    }

    // Limpiar MP4 de prueba
    fs.existsSync(mp4Path) && fs.unlinkSync(mp4Path);

    await browser.close();
    log('');

    if (configuracionGanadora) break; // ya encontramos una que funciona
  }

  // Limpiar HTML de prueba
  fs.existsSync(htmlPath) && fs.unlinkSync(htmlPath);

  // ─── Resultado final ───
  log('══════════════════════════════════════════');
  if (configuracionGanadora) {
    log(`✅ FUNCIONA: "${configuracionGanadora.nombre}"`);
    log('');
    log('FLAGS a usar en capture_animation.js:');
    configuracionGanadora.args.forEach(a => log(`  "${a}",`));
  } else {
    log('❌ NINGUNA CONFIGURACIÓN FUNCIONÓ');
    log('');
    log('Opciones:');
    log('  1. Remotion (renderiza React → MP4 sin browser)');
    log('  2. Browserless.io ($35/mes, garantizado headless)');
    log('  3. Reescribir animaciones en Remotion/React');
  }
  log('══════════════════════════════════════════');

  // Guardar resultado en archivo para leerlo desde Python
  const resumenPath = path.join(__dirname, 'diagnostico_resultado.txt');
  fs.writeFileSync(resumenPath, resultados.join('\n'), 'utf8');
  log(`\nResultado guardado en: ${resumenPath}`);
}

main().catch(e => {
  console.error('Error fatal:', e.message);
  process.exit(1);
});
