# SISTEMA EDITOR DE VIDEO — JOSUÉ CALDERÓN
## Especificación Técnica Completa

---

## DESCRIPCIÓN GENERAL

Sistema automatizado de edición de video que corre en Windows desde la terminal. Elimina silencios, detecta y corta errores del habla (incluyendo dislexia), genera subtítulos animados y prepara videos para redes sociales.

---

## UBICACIÓN EN PC

```
C:\Videos_Josue\
├── input\                    ← videos originales + guiones .txt
├── output\                   ← videos procesados
├── subtitulos\               ← archivos .srt generados
├── logs\                     ← registro de cada edición
├── fuentes\                  ← fuentes tipográficas
├── workshop-animaciones\     ← proyecto HyperFrames
├── editor_josue_v7_clean.py  ← script principal ACTIVO
├── editor_josue_v4.py        ← versión antigua
├── editor_josue_v5.py        ← versión antigua
├── editor_josue_v6.py        ← versión antigua
└── diagnostico_*.py          ← archivos de diagnóstico
```

---

## VERSIÓN ACTIVA

**`editor_josue_v7_clean.py`** — escrito desde cero, sin parches acumulados.

### Comando principal:
```bash
cd C:\Videos_Josue
py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --solo-limpiar
```

### Todos los modos disponibles:
```bash
# Limpiar errores sin convertir a 9:16 (más rápido para revisar)
py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --solo-limpiar

# Limpiar + convertir a 9:16
py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt

# Limpiar + convertir + subtítulos animados
py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --subtitulos

# Con limpieza de ruido de audio
py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --limpia-audio

# Todo junto
py -3.11 editor_josue_v7_clean.py reel video.mp4 --guion guion.txt --subtitulos --limpia-audio
```

---

## FLUJO DE PROCESAMIENTO

```
Video original (input/)
        ↓
PASO 1: Eliminar silencios
        Librería: MoviePy + NumPy
        Umbral: -40dB | Silencio mínimo: 0.5s
        Margen: 80ms fade antes/después
        ↓
PASO 2: Transcribir audio
        API: OpenAI Whisper API (whisper-1)
        Idioma: español
        Output: palabras con timestamps exactos
        ↓
PASO 3: Detectar errores con GPT-4o
        API: OpenAI GPT-4o
        Input: guión original + transcripción con timestamps
        Detecta: intentos fallidos, palabras trabadas, tartamudeo
        Output: lista de rangos (t_inicio, t_fin) a cortar
        ↓
PASO 4: Aplicar cortes con fade de audio
        Herramienta: FFmpeg
        Fade: 80ms en cada corte (entrada y salida)
        ↓
PASO 5 (opcional): Convertir a 9:16
        Resolución: 1080x1920
        FPS: 30
        ↓
PASO 6 (opcional): Subtítulos animados
        Estilo: ESTILO 001 — palabras que aparecen por grupos de 3
        Fuente: Montserrat (o la elegida)
        Animación: slide-in desde abajo con easing
        ↓
Video final (output/)
```

---

## APIs Y COSTOS

### OpenAI (platform.openai.com)
- **Whisper API** — transcripción de audio
  - Modelo: `whisper-1`
  - Costo: ~$0.006 por minuto de audio
  - Video de 10 min ≈ $0.06
- **GPT-4o** — detección de errores
  - Costo: ~$0.03-0.08 por video
  - **Total por video de 10 min ≈ $0.10**
  - $5 USD ≈ 50 videos procesados

### Anthropic Claude API (platform.claude.com)
- **Estado actual**: PENDIENTE — requiere $40 acumulados para Tier 1
- **Saldo actual**: $5.00 USD cargados
- **Uso futuro**: reemplazar GPT-4o cuando se alcance Tier 1
- Key guardada en el archivo como `CLAUDE_API_KEY`

---

## DEPENDENCIAS INSTALADAS

```
Python 3.11
FFmpeg 8.1
Node.js v24.14.1
npm 11.11.0

# Python packages:
moviepy
numpy
pillow
openai==2.33.0
anthropic (instalado, pendiente de activar)
whisper (instalado, solo para subtítulos locales)
```

---

## APIS KEYS EN EL ARCHIVO

En `editor_josue_v7_clean.py` líneas 20-21:
```python
OPENAI_API_KEY = "sk-proj-..."   # ← OpenAI — ACTIVA con $5
CLAUDE_API_KEY = "sk-ant-..."    # ← Anthropic — INACTIVA (Tier 1 requiere $40)
```

---

## PROBLEMA CONOCIDO — PENDIENTE

**Palabras trabadas no detectadas:**
GPT-4o detecta frases repetidas (intentos fallidos de varias palabras) pero NO detecta palabras individuales trabadas seguidas de la corrección. Ejemplo: "vivims → vivimos" no se detecta.

**Solución pendiente:** ajustar el prompt de GPT-4o para ser más agresivo con este patrón específico.

**Workaround actual:** usar el archivo manual de cortes:
```
# cortes.txt — formato: inicio-fin en segundos
21.0-22.5
45.3-46.1
```
```bash
py -3.11 editor_josue_v7_clean.py reel video.mp4 --cortes cortes.txt
```

---

## HYPERFRAMES — ANIMACIONES

### Ubicación:
```
C:\Videos_Josue\workshop-animaciones\
```

### Cómo correr:
```bash
cd C:\Videos_Josue\workshop-animaciones
npx hyperframes preview
```
Abre en: `http://localhost:3002`

### Plantilla activa: Kinetic Type
Archivo principal: `compositions/main-graphics.html`

### Cómo renderizar una animación:
```bash
npx hyperframes render compositions/main-graphics.html --output output/animacion.mp4
```

---

## FUENTES DISPONIBLES

| Nombre | Disponible | Uso recomendado |
|--------|-----------|-----------------|
| montserrat | ✅ | moderna, versátil (DEFECTO) |
| bebas | ✅ | impacto, todo caps |
| anton | ✅ | máximo impacto |
| oswald | ✅ | condensada, fuerte |
| outfit | ✅ | limpia y suave |
| inter | ✅ | la más legible |
| arial | ✅ | clásica Windows |

---

## CONTEXTO DEL CREADOR

- **Nombre:** Josué Calderón
- **Ubicación:** Villavicencio, Colombia
- **Contenido:** Workshop de desarrollo personal y productividad
- **Dislexia del habla:** el sistema está optimizado para este caso
- **Hardware:** PC con CPU, sin GPU dedicada (Whisper local es lento)
- **Preferencia:** herramientas gratuitas o de bajo costo

---

## ROADMAP PENDIENTE

### Próximas mejoras:
1. Ajustar prompt GPT-4o para detectar palabras trabadas individuales
2. Subir código a GitHub (repositorio privado)
3. Integrar HyperFrames al flujo de edición principal
4. Interfaz web local para no usar terminal
5. Acceso desde celular via túnel (ngrok/cloudflare)
6. Limpieza de ruido de audio mejorada
7. Activar Claude API cuando se alcance Tier 1 ($40)

### Futuro a largo plazo:
- App web completa accesible desde celular
- Deploy en Railway.app (~$5/mes) para correr sin PC encendida
- Generación automática de animaciones HyperFrames desde el guión

---

## HISTORIAL DE VERSIONES

| Versión | Cambio principal |
|---------|-----------------|
| v4 | Primera versión funcional |
| v5 | Integración Gemini API + subtítulos |
| v6 | Claude API + detección patrón "repito" + fade audio + logs |
| v7_clean | OpenAI Whisper API + GPT-4o + sin palabras clave + código limpio |

---

*Última actualización: 29 de abril 2026*
*Sistema desarrollado en colaboración con Claude (Anthropic)*
