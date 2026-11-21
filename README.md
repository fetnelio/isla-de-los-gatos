# La Isla de los Gatos

Generador de videos verticales (IG / TikTok) que resuelven puzzles de lógica
del género **Star Battle de 1 estrella** (también conocido como *Queens*):
un gato por fila, por columna y por isla, y los gatos no se tocan, ni en diagonal.

La idea central: los tableros no se resuelven con backtracking, sino con una
**escalera de tácticas humanas**, y el registro de esas tácticas es el guion del relator.

## Escalera de tácticas

| Nivel | Táctica | Idea |
|---|---|---|
| 0 | Barrido | Gato puesto → X en su fila, columna, isla y 8 vecinas |
| 1 | Único lugar | A un grupo le queda una sola casilla → gato |
| 2 | Encierro en una línea | Isla metida en una línea (o línea metida en una isla) → X en el resto |
| 3 | Ataque común | Todas las candidatas de un grupo atacan una casilla → X (equivale a "si pongo un gato acá, el grupo B se queda sin lugar") |
| 4 | Encierro doble | 2 grupos encerrados en 2 líneas/islas |
| 5 | Encierro múltiple | k ≥ 3 grupos en k líneas/islas |
| 6 | Contradicción | Supongo un gato, se fuerzan gatos (nivel 1) y un grupo queda vacío → X |
| 7 | Contradicción larga | Igual, pero propagando con niveles 1–5 |

La dificultad de un tablero es la táctica más alta que necesita.

## Piezas

- `solver.py`: solver explicador; aplica siempre la táctica más baja y registra la evidencia de cada paso.
- `generador.py`: elige la solución, hace crecer las islas y hace búsqueda local hasta que el solver necesite exactamente el nivel pedido (con penalizaciones por islas deformes o desparejas).
- `guion.py`: convierte los pasos en guion: intro, "pausá y probá", pregunta + explicación la primera vez que aparece cada táctica, frases cortas en las repeticiones, cascada final y latiguillo de cierre.
- `voz.py`: voz del relator con [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) (por defecto `ef_dora`; también `em_alex`, `em_santa`, o voces Piper) y re-timing del guion según la voz. Marcas: `[miau]`, `[michi]`.
- `audio.py`: música de fondo, notas por gato (escala ascendente en la cascada), tics por X, campanita en las preguntas, voz encima con ducking.
- `render/index.html` + `render/grabar.js`: animación SVG y grabación cuadro a cuadro con Playwright + ffmpeg (MP4 1080×1920).
- `backtracking.py`: solver por fuerza bruta, solo para verificar unicidad.
- `calibracion/`: comparación con niveles comunitarios de Queens y estadísticas de los 667 niveles oficiales de LinkedIn (solo para calibrar; no se publican esos niveles).

## Uso

```bash
pip install -r requirements.txt     # además: ffmpeg, node + playwright
./descargar_voces.sh

# tablero generado: tamaño, táctica objetivo, semilla, número de episodio
./hacer_video.sh 8 4 5 2

# tablero existente
./hacer_video.sh episodios/ep3.txt 3

# otra voz / velocidad
VOZ=em_alex VOZ_VEL=1.1 ./hacer_video.sh episodios/ep1.txt 1
```

Formato de tablero: N líneas de N letras, cada letra es una isla.

## Elección de voz

Se midió la inteligibilidad transcribiendo con Whisper frases del guion
(¿se entienden "isla" y "gato"?): Piper `es_AR-daniela` 4/15, otras voces Piper 9–12/15,
**Kokoro (las 3 voces) 15/15**.

## Calibración (resumen)

- Niveles oficiales de LinkedIn (667): ~81% necesitan encierro k≥2 y ~16% contradicción.
- Niveles comunitarios (691 con solución única): el solver los resuelve todos sin backtracking.

## Pendientes

- Destacar más el momento en que un grupo queda vacío en la contradicción.
- Intro más corta a partir del segundo episodio.
- Más variantes de frases; archivo de episodios para generar en lote y cruzar con analítica.
