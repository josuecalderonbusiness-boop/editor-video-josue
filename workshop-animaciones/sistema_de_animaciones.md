ESPECIFICACIONES DE ANIMACIONES
## Código Soberana · Josué Calderón · 2026

---

## SISTEMA TÉCNICO

- **Resolución:** 1280x720 (render) → upscale 4K con ffmpeg
- **Renderizador:** Puppeteer + capture_animation.js
- **Ubicación compositions:** `C:\Videos_Josue\workshop-animaciones\compositions\leccion_1\`
- **Ubicación animaciones MP4:** `C:\Videos_Josue\workshop-animaciones\animaciones\leccion_1\`
- **Fix fuentes:** Todas las animaciones incluyen `document.fonts.ready` con delay 1500ms
- **Upscale:** `ffmpeg -i input.mp4 -vf scale=3840:2160:flags=lanczos -c:v libx264 -crf 16 -preset slow output_4k.mp4`

---

## REGLAS DE FONDO

| Tipo de animación | Fondo |
|---|---|
| Tapa toda la pantalla (pizarra, negro, vino) | Fondo sólido normal |
| Va sobre el video (INICIO_TEMA, franja, texto encima, credenciales, fotos) | **#00FF00** (green screen) |
| Fotos familiares hardcodeadas | Base64 embebido, fondo #00FF00 |

---

## PALETA DE COLORES

```css
--wine-deep:    #3D0C11
--wine-primary: #6B1A2A
--wine-medium:  #8B2D3F
--wine-pale:    #C97080
--gold-primary: #E8C870   /* dorado cálido luminoso — APROBADO */
--gold-medium:  #D4A843
--cream-warm:   #F9F3E8
--charcoal:     #0F0A0B
--green-screen: #00FF00
```

## TIPOGRAFÍAS

- **Playfair Display** 900 — títulos principales, frases memorables (sin cursiva)
- **Playfair Display** 400 italic — línea secundaria de frases
- **Cormorant Garamond** italic — firmas, labels elegantes, pizarra
- **Inter** 300/400 — labels UI, referencias de lección

---

## TIPOS DE ANIMACIÓN APROBADOS

### FRASE_MEMORABLE
- Fondo: negro sólido `#000`
- Comillas: carácter `"` (U+201C) en Playfair Display 900, color `#E8C870`, tamaño 130-140px
- Glow comillas: pulsa entre dorado suave y dorado brillante
- Línea 1: Playfair Display 900, ~72px, blanco con glow intenso (4 capas)
- Línea 2: Playfair Display 400 italic, ~58px, crema suave
- Línea especial (si hay 3): Playfair Display 700 italic, color `#E8C870` con glow dorado
- Animación palabras: aparecen desde blur + translateY, una por una
- Línea dorada: crece de izq a derecha con chispa que la recorre
- Firma: Cormorant Garamond italic, `#E8C870`, ~34px
- Glow fondo: radial borgoña pulsante izquierda
- Fade in/out: toda la escena

### INICIO_LECCION
- Fondo: gradiente `#0F0A0B → #2D0810 → #6B1A2A`
- Silueta número: Playfair Display 900, ~600px, solo outline borgoña semitransparente
- Texto: flash intermitente que revela (animación `flashReveal`)
- Entra: slide desde derecha → izquierda
- Sale: slide hacia izquierda
- Línea accent dorada izquierda que crece

### INICIO_TEMA (fondo verde)
- Fondo: `#00FF00`
- Banda semitransparente oscura que se expande desde la izquierda
- Barra dorada izquierda con glow
- Referencia lección arriba: Inter 300, dorado, letra espaciada
- Título: Cormorant Garamond italic, ~62px, escritura letra a letra con cursor parpadeante dorado
- Fade out al terminar

### DATO_INTERNO — Pizarra
- Fondo: `#EDE3CE` con cuadrícula beige
- Borde izquierdo: gradiente borgoña
- Borde superior: gradiente dorado
- Título: Playfair Display 700, borgoña oscuro, subrayado dorado
- Items: Cormorant Garamond italic, ~28-30px, con checks SVG dorado/borgoña dibujándose
- Frase final: ocupa toda la pantalla con fadeIn

### DATO_INTERNO — Overlay transparente (fondo verde)
- Fondo: `#00FF00`
- Banda oscura semitransparente que se desliza
- Texto: Cormorant Garamond italic grande
- Va sobre el video — chroma key en Railway

### DATO_INTERNO — Franja noticias (fondo verde)
- Fondo: `#00FF00`
- Franja en la parte inferior (110px alto)
- Banda superior: tag "Código Soberana" + subtítulo
- Banda principal: texto que se desplaza horizontalmente
- Tag izquierdo en borgoña, punto dorado parpadeante

### DATO_INTERNO — Fotos/Credenciales (fondo verde)
- Fondo: `#00FF00`
- Cards con foto hardcodeada en base64
- `object-fit:cover; object-position:center 20%` (fotos verticales)
- Altura imagen: 180px
- Línea dorada que crece en cada card
- Aparición: slideIn desde el lado correspondiente

---

## ANIMACIONES LECCIÓN 1 COMPLETAS

### TEMA 1 — ¿Qué es el Código Soberana?
| Archivo | Tipo | Segundo | Duración | Fondo |
|---------|------|---------|----------|-------|
| anim_l1_an1.html | FRASE_MEMORABLE | 0:00 | 8s | Negro |
| anim_l1_an2.html | INICIO_LECCION | 0:01 | 4s | Vino/negro |
| anim_l1_an3.html | DATO_INTERNO pizarra | 0:25 | 25s | Beige |
| anim_l1_an4.html | DATO_INTERNO negación NO ES | 1:03 | 28s | Negro |
| anim_l1_an5.html | DATO_INTERNO matrimonio sueños | 1:57 | 5s | **Verde** |
| anim_l1_an6.html | DATO_INTERNO logo Código Soberana | 2:07 | 16s | **Verde** |

### TEMA 2 — ¿Quién soy y por qué puedo hablar de esto?
| Archivo | Tipo | Segundo | Duración | Fondo |
|---------|------|---------|----------|-------|
| anim_l1_an7.html | INICIO_TEMA | 2:26 | 4s | **Verde** |
| anim_l1_an8.html | DATO_INTERNO credenciales + fotos | 2:29 | 25s | **Verde** |
| anim_l1_an9.html | DATO_INTERNO "analfabeto emocional" | 3:01 | 5s | **Verde** |
| anim_l1_an10.html | DATO_INTERNO video Gemini tormenta | 4:35 | 13s | Beige (video) |
| anim_l1_an11.html | DATO_INTERNO fotos 20 años | 5:00 | 22s | **Verde** |
| anim_l1_an12.html | DATO_INTERNO camino 1→2→3 + logo | 8:23 | 18s | Negro |

**Nota an10:** requiere archivo `tormenta.mp4` (generado con Gemini Veo 3) en la misma carpeta.

**Fotos hardcodeadas en an8 y an11:**
- foto_familia.jpg — familia en restaurante
- foto_predicando.png — Iglesia Cristiana Unida 2007
- foto_negocio1.jpg, foto_negocio2.jpg, foto_negocio3.jpg — emprendimiento
- foto_matrimonio.jpg — boda
- foto_piscina.jpg — con hijo en piscina
- foto_delgado.jpg — Josué a los 37

### TEMA 3 — El problema que nadie está nombrando
| Archivo | Tipo | Segundo | Duración | Fondo |
|---------|------|---------|----------|-------|
| anim_l1_an13.html | INICIO_TEMA | 7:58 | 4s | **Verde** |
| anim_l1_an14.html | FRASE_MEMORABLE | 8:00 | 7s | Negro |
| anim_l1_an15.html | DATO_INTERNO pizarra 2 columnas | 8:55 | 25s | Beige |
| anim_l1_an16.html | DATO_INTERNO pizarra 2 columnas | 9:22 | 20s | Beige |
| anim_l1_an17.html | DATO_INTERNO pizarra bullets | 9:45 | 20s | Beige |
| anim_l1_an18.html | FRASE_MEMORABLE franja noticias | 8:43 | 9s | **Verde** |
| anim_l1_an19.html | FRASE_MEMORABLE 3 líneas | final | 10s | Negro |

### TEMA 4 — ¿Qué es el Código Soberana?
| Archivo | Tipo | Segundo | Duración | Fondo |
|---------|------|---------|----------|-------|
| anim_l1_an20.html | INICIO_TEMA | ~9:26 | 4s | **Verde** |
| anim_l1_an21.html | FRASE_MEMORABLE (título solo → palabras) | ~9:28 | 14s | Negro |
| anim_l1_an22.html | FRASE_MEMORABLE 3 líneas | ~9:45 | 10s | Negro |
| anim_l1_an23.html | DATO_INTERNO mockup PWA celular | ~9:50 | 15s | **Verde** |

---

## FLUJO DE RENDERIZADO

```powershell
# 1. Renderizar HTML → MP4
cd C:\Videos_Josue
node capture_animation.js compositions\leccion_1\tema_X\anim_l1_anXX.html animaciones\leccion_1\anim_l1_anXX.mp4 DURACION_MS

# 2. Upscale a 4K
cd C:\Videos_Josue\workshop-animaciones\animaciones\leccion_1
ffmpeg -i anim_l1_anXX.mp4 -vf scale=3840:2160:flags=lanczos -c:v libx264 -crf 16 -preset slow anim_l1_anXX_4k.mp4 -y

# 3. Subir a Drive
cd C:\Videos_Josue
py -3.11 subir_l1_temaX.py

# 4. Push JSON a GitHub
git add animaciones_l1_temaX.json
git commit -m "animaciones l1 temaX 4k"
git push
```

---

## NOTAS IMPORTANTES

1. **Fuentes en Puppeteer:** siempre incluir el bloque `document.fonts.ready` con 1500ms de delay
2. **Green screen → chroma key en Railway** para animaciones sobre video
3. **Fotos:** siempre hardcodear en base64, redimensionar a max 400px antes de embeber
4. **Gemini Veo 3:** para ilustraciones animadas complejas, generar video y embeber en HTML
5. **Duración render:** duración real + 1500ms del delay de fuentes
6. **Caracteres especiales:** descargar HTMLs desde Claude directamente, NO copiar con PowerShell (corrompe UTF-8)

---