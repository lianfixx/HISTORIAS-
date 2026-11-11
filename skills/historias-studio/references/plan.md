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
| `fondo.tipo` | `foto`, `ia`, `color` | obligatorio si hay `fondo`; sin `fondo`, la lámina va en `papel` |
| `fondo.archivo` | nombre de archivo | para `foto` (está en `fotos/`) e `ia` (está en `fondos/`); sin subcarpetas ni `..` |
| `fondo.color` | `papel`, `tinta`, `acento`, `apoyo`, `blanco`, `negro` o `#RRGGBB` | para `color`; por defecto `papel` |
| `fondo.grano` | `true` / `false` | fibra de papel sobre el color liso (por defecto sí) |
| `fondo.foco` | `[x, y]` de 0 a 1 | qué parte de la foto se conserva al recortar a 9:16; si falta, vale el `foco` del catálogo |
| `filtro` | nombre u objeto | si falta: `estilo.filtro`, luego el de `estilo.referencia`, luego el del espacio. Solo actúa sobre `foto` e `ia` |
| `velo` | 0 a 0.85 | oscurece la foto para que el texto se lea (0.18 por defecto); no aplica a `color` |
| `bloques` | lista de objetos | texto, de arriba hacia abajo dentro de su `pos` |
| `sticker` | objeto `{"tipo", "pos", "alinear", "texto"}` | solo reserva el espacio. `tipo`: `encuesta`, `pregunta`, `enlace`, `quiz`, `deslizador`, `cuenta_regresiva`, `mencion`, `ubicacion`. `texto` es lo que Emi escribirá en el sticker |
| `nota_publicacion` | texto | instrucción para Emi al subirla (música, mención, emoji, enlace) |
| `duracion` | 2 a 15 | segundos de la versión animada (`animar`); 5 si no se dice |

`estructura` es informativa (qué estructura se eligió); el motor no la usa. `estilo.referencia` es el nombre de una ficha de `espacios/<espacio>/referencias/`.

## Filtro como objeto

| Clave | Rango | | Clave | Rango |
|---|---|---|---|---|
| `calidez` | −1 a 1 | | `grano` | 0 a 1 |
| `desvanecido` | 0 a 1 | | `vineta` | 0 a 1 |
| `contraste` | 0.3 a 2 | | `desenfoque` | 0 a 40 |
| `saturacion` | 0 a 2 | | `tinte` + `tinte_fuerza` | `#RRGGBB`, 0 a 1 |
| `brillo` | 0.3 a 2 | | `bn` | `true` / `false` |

## Bloque de texto

| Campo | Valores |
|---|---|
| `texto` | lo que se lee; `\n` fuerza un salto de línea (varios seguidos cuentan como uno). Sin emojis: se ponen en Instagram |
| `estilo` | `titular` (tipografía del espacio), `cuerpo` (Inter), `serif` (Gelasio), `nota` (Caveat, letra a mano), `etiqueta` (texto sobre caja, como el de Instagram) |
| `pos` | `arriba`, `centro`, `abajo` |
| `alinear` | `izq`, `centro`, `der` |
| `resaltar` | lista, por ejemplo `["gym", "no pasó"]`: van en el color de acento o, si no se leería, en el de apoyo; subrayadas en `nota` y `etiqueta` y cuando ningún color sirve. Una frase solo cuenta si sus palabras van seguidas |
| `color`, `fondo`, `color_resalte` | color del espacio, `blanco`, `negro` o `#RRGGBB` (`fondo` solo en `etiqueta`). Sin `color`, el motor elige el que se lea sobre el fondo |
| `tam` | cuerpo en px, de 20 a 400 |
| `ancho` | ancho máximo en px, de 200 a 900 |
| `giro` | grados, de −15 a 15 (`nota` gira −2.5 si no se dice) |

Si el texto no cabe, la letra se reduce sola hasta un 60 %; más allá, error: hay que acortar. La tinta real de cada bloque, ya girada, queda dentro de la zona segura (x 90–990, y 270–1540), a 30 px de los demás y fuera de cualquier rostro; lo comprueban igual `validar` y `render`.
