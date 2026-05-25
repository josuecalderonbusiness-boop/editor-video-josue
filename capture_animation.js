const puppeteer = require('puppeteer');
const { PuppeteerScreenRecorder } = require('puppeteer-screen-recorder');
const path = require('path');

async function capturarAnimacion(htmlPath, outputPath, duracionMs) {
  let browser;
  
  // Timeout de seguridad — mata todo si tarda mas de duracion + 30 segundos
  const timeoutSeguridad = setTimeout(() => {
    console.error('TIMEOUT DE SEGURIDAD — cerrando browser');
    if (browser) browser.close().catch(() => {});
    process.exit(1);
  }, duracionMs + 30000);

  try {
    browser = await puppeteer.launch({
      headless: 'new',
      executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--use-gl=swiftshader',
        '--use-software-gl',
        '--ignore-gpu-blocklist',
        '--disable-web-security',
        '--allow-file-access-from-files',
      ],
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });

    const fileUrl = htmlPath.startsWith('http')
      ? htmlPath
      : `file://${path.resolve(htmlPath)}`;

    await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 500));

    const recorder = new PuppeteerScreenRecorder(page, {
      fps: 30,
      videoFrame: { width: 1280, height: 720 },
      videoCrf: 18,
      videoCodec: 'libx264',
      videoPreset: 'ultrafast',
      autopad: { color: 'black' },
    });

    await recorder.start(outputPath);
    await new Promise(r => setTimeout(r, duracionMs));
    await recorder.stop();
    await browser.close();
    
    clearTimeout(timeoutSeguridad);
    console.log(`OK: ${outputPath}`);
  } catch (err) {
    clearTimeout(timeoutSeguridad);
    if (browser) await browser.close().catch(() => {});
    console.error('ERROR:', err.message);
    process.exit(1);
  }
}

const [,, htmlPath, outputPath, duracionMs] = process.argv;
capturarAnimacion(htmlPath, outputPath, parseInt(duracionMs || '5000'));
