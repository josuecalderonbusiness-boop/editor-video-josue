# SESIÓN DE TRABAJO — 30 DE ABRIL 2026
## Sistema Editor Josué v7.0

---

## LO QUE HICIMOS HOY

### PASO 1 — Prompt GPT-4o mejorado (palabras trabadas)
- Reescribimos el punto 3 del prompt con ejemplos de patrones (palabras inventadas)
- Agregamos regla de proximidad: palabra rota y correcta deben estar a menos de 1.5s
- Separamos intentos fallidos de frase vs palabra trabada individual
- **Limitación encontrada:** Whisper autocorrige palabras trabadas antes de pasarlas a GPT-4o (ej: "vivims" → "Vivimos"). Pendiente resolver en el futuro.

### PASO 2 — GitHub
- Repo creado: `github.com/josuecalderonbusiness-boop/editor-video-josue` (privado)
- Configurado `.env` para que la API key no se suba al repo
- Script lee `OPENAI_API_KEY` desde variables de entorno con `python-dotenv`
- Flujo de commit: `git add`, `git commit`, `git push`

### PASO 3 — Mejoras al script

#### Flag `--tipo reel/workshop`
- `--tipo reel` → umbral silencio 0.5s (corte agresivo)
- `--tipo workshop` → umbral silencio 1.5s (pausas naturales)
- Se agrega automáticamente con PowerShell al descargar nuevo archivo

#### Eliminación de silencios: MoviePy → FFmpeg nativo
- **Problema:** MoviePy cargaba video de 6.6GB completo en RAM → 30+ min
- **Solución:** FFmpeg audio-first
  1. Extrae solo el audio (~50MB para 16 min) — 30 seg
  2. Detecta silencios en el audio liviano — 30 seg  
  3. Aplica cortes al video original sin recodificar (`-c:v copy`)
- **Resultado:** proceso de silencios en minutos en vez de horas

#### Proxy workflow (implementado pero no usado)
- Para videos >500MB se detectaba automáticamente
- Se descartó en favor del método audio-first que es más eficiente

### PASO 4 — Interfaz web + Railway

#### App Flask (`app.py`)
- Servidor web con rutas: `/`, `/procesar`, `/status/<job_id>`, `/descargar/<job_id>`
- Procesamiento en thread separado (no bloquea la UI)
- Polling cada 2 segundos para mostrar progreso en tiempo real

#### Interfaz (`templates/index.html`)
- Selector visual Reel / Workshop
- Upload de video y guion
- Opciones: Solo limpiar, Subtítulos, Limpiar audio, Convertir 9:16
- Log en tiempo real con colores por tipo de mensaje
- Botón de descarga cuando termina

#### Deploy en Railway
- URL activa: `web-production-d02ed.up.railway.app`
- Conectado al repo de GitHub (auto-deploy en cada push)
- Variable de entorno `OPENAI_API_KEY` configurada en Railway
- Costo estimado: $2-5/mes según uso

---

## ESTADO ACTUAL DEL SCRIPT

```
editor_josue_v7_clean.py — versión activa
├── Silencios: FFmpeg audio-first (rápido)
├── Transcripción: OpenAI Whisper API
├── Detección errores: GPT-4o con prompt mejorado
├── Cortes: FFmpeg con fade 80ms
├── Flags: --tipo reel/workshop, --guion, --subtitulos, --solo-limpiar, --limpia-audio
├── API key: desde .env (nunca en el código)
└── Web: Flask app en Railway
```

---

## COMANDOS ÚTILES

```bash
# Procesar reel
py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --solo-limpiar

# Procesar workshop
py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --tipo workshop --solo-limpiar --limpia-audio

# Subir cambios a GitHub
git add editor_josue_v7_clean.py
git commit -m "descripcion del cambio"
git push
```

---

## PENDIENTE PARA PRÓXIMAS SESIONES

1. **Verificar que Railway procesa el workshop_prueba.mp4** — estaba corriendo al cerrar la sesión
2. **HyperFrames** — animaciones de texto para workshop y reels
   - Definir fuentes
   - Definir estilo visual
   - Crear plantillas de animación
3. **Voz más grave** — flag `--voz-grave` con filtro de pitch en FFmpeg (pendiente)
4. **Palabras trabadas** — Whisper las autocorrige, buscar solución futura
5. **Interfaz web** — mejorar con barra de progreso real y estimado de tiempo

---

## ARQUITECTURA ACTUAL

```
iPhone/PC
    ↓ (sube video por web)
web-production-d02ed.up.railway.app
    ↓ (Flask app)
editor_josue_v7_clean.py
    ↓ (audio-first)
FFmpeg → detecta silencios
    ↓
OpenAI Whisper API → transcribe
    ↓
GPT-4o → detecta errores vs guion
    ↓
FFmpeg → aplica cortes con fade
    ↓ (descarga)
iPhone/PC
```

---

*Sesión: 30 de abril 2026*
*Desarrollado en colaboración con Claude (Anthropic)*
