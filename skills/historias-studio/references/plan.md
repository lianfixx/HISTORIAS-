# El plan (`plan.json`)

```json
{
  "titulo": "Por qué falté al gym",
  "espacio": "personal",
  "fecha": "2026-11-12",
  "brief": {
    "objetivo": "que respondan y conversar por DM",
    "publico": "gente que entrena y se siente culpable al descansar",
    "accion": "contestar la caja de pregunta",
    "respuestas_emi": "lo que Emi contestó, con sus palabras",
    "sin_cierre": false
  },
  "estructura": "Error propio",
  "estilo": {"filtro": "calido", "referencia": "cafe-domingo"},
  "guion_aprobado": true,
  "laminas": [
    {
      "fondo": {"tipo": "foto", "archivo": "gym-espejo.jpg", "foco": [0.5, 0.3]},
      "filtro": "pelicula",
      "velo": 0.18,
      "bloques": [
        {"texto": "Hoy no fui al gym", "estilo": "titular", "pos": "arriba", "resaltar": ["gym"]},
        {"texto": "y no pasó nada", "estilo": "nota", "pos": "abajo", "giro": -3}
      ],
      "sticker": {"tipo": "pregunta", "pos": "abajo", "texto": "¿Tú cuántos días descansas?"},
      "nota_publicacion": "poner la canción que traía ese día"
    }
  ]
}
```

## Lámina

| Campo | Valores | Notas |
|---|---|---|
| `fondo.tipo` | `foto`, `ia`, `color` | `foto` busca en `fotos/`; `ia` en `fondos/`; `color` usa un color del espacio (`papel`, `tinta`, `acento`, `apoyo`) o un `#RRGGBB` |
| `fondo.foco` | `[x, y]` de 0 a 1 | qué parte de la foto se conserva al recortar a 9:16 |
| `filtro` | nombre u objeto | si falta, vale `estilo.filtro` y luego el del espacio |
| `velo` | 0 a 0.85 | oscurece la foto para que el texto se lea (0.18 por defecto) |
| `bloques` | lista | texto, de arriba hacia abajo dentro de su `pos` |
| `sticker` | `encuesta`, `pregunta`, `enlace`, `quiz`, `deslizador`, `cuenta_regresiva`, `mencion`, `ubicacion` | solo reserva el espacio |
| `nota_publicacion` | texto | instrucción para Emi al subirla (música, mención, enlace) |

## Bloque de texto

| Campo | Valores |
|---|---|
| `texto` | lo que se lee; `\n` fuerza un salto |
| `estilo` | `titular` (tipografía del espacio), `cuerpo` (Inter), `serif` (Gelasio), `nota` (Caveat, letra a mano), `etiqueta` (texto sobre caja, como el de Instagram) |
| `pos` | `arriba`, `centro`, `abajo` |
| `alinear` | `izq`, `centro`, `der` |
| `resaltar` | palabras que van en el color de acento (subrayadas en `nota` y `etiqueta`) |
| `color`, `fondo`, `color_resalte` | color del espacio o `#RRGGBB` (`fondo` solo en `etiqueta`) |
| `tam`, `ancho`, `giro` | cuerpo en px, ancho máximo en px, grados |

Si el texto no cabe, la letra se reduce sola hasta un 60 %; más allá, error: hay que acortar. Todo el texto queda dentro de la zona segura (x 90–990, y 270–1540).
