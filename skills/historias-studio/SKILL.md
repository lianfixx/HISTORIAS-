---
name: historias-studio
description: "Crear secuencias de historias de Instagram (1080x1920) para los espacios de Emi (personal, MILLA, Castorena, PAN/Acción Juvenil), cada uno por separado: preguntar el brief, proponer guion, elegir fotos reales, imitar el look de una referencia de Pinterest, dibujar las láminas y entregarlas en Drive. Usar al pedir historias, stories, una secuencia o carrusel de historias, al mandar una referencia de Pinterest, al revisar el nicho de la semana o al corregir láminas ya hechas. No es para videos (eso es Vox Studio) ni para carruseles del feed."
metadata:
  version: "0.2.1"
  release_date: "2026-11-10"
  language: "es-MX"
---

# Historias Studio

**Candidato**: el motor dibuja y está probado, pero ninguna secuencia tiene todavía aprobación de Emi. Emi decide; la IA pregunta, propone, dibuja y documenta.

Funciona con cualquier IA que pueda leer este repositorio y ejecutar Python 3.10+ con Pillow (`pip install -r requirements.txt`). Sin terminal, la IA puede hacer el brief y el guion y dejar el `plan.json` para que otra lo dibuje: ver [portabilidad](references/portabilidad.md). Desde el ZIP de la skill, el motor está en `scripts/historias.py` y las secuencias se crean en `producciones/` de la carpeta de trabajo.

```bash
H="python3 skills/historias-studio/scripts/historias.py"   # desde la raíz del repositorio
```

## Espacios separados

Los mismos cuatro de Vox Studio: `personal`, `milla`, `castorena`, `pan`. Cada uno vive en `espacios/<espacio>/` (perfil, marca, nicho, aprendizajes, ideas, referencias) y no se mezcla. Las secuencias y las fotos son privadas: van en `producciones/<espacio>/<tema>/`, fuera de git, y se entregan en Drive. Antes de trabajar un espacio, leer su `MARCA.md` y su `desde-vox.md`: Castorena y PAN tienen límites (visto bueno del despacho; no hablar a nombre del partido ni usar su logotipo sin autorización).

## 1. Antes de proponer nada

1. `$H vox` si el repositorio de Vox está a la mano (`VOX_REPO` o carpeta hermana `VIDEOS-IA-SKILL-MILLA`). Trae marca y lecciones de video como copia de solo lectura. Si avisa de una diferencia, se le pregunta a Emi cuál vale.
2. `$H aprendizajes --espacio E`. Son reglas vigentes, no sugerencias.
3. `$H nicho --espacio E`. Si avisa que lleva más de 7 días, proponer a Emi la [revisión semanal](references/nicho.md) antes de seguir.

## 2. Preguntar a Emi (siempre, en un solo mensaje)

Nunca se supone lo que se puede preguntar. Para cada secuencia nueva, y saltando solo lo que Emi ya dijo en esa conversación:

1. ¿Para qué espacio es?
2. ¿De qué va y por qué hoy? (qué pasó, qué anuncia, qué quiere contar)
3. ¿Qué quiere lograr? (que respondan, que escriban por DM, que vayan a un enlace, que lo conozcan mejor, que se rían, vender)
4. ¿A quién le habla esta vez?
5. ¿Qué quiere que haga la gente al final, exactamente?
6. ¿Cuál es su postura o qué siente al respecto? ¿Hay una frase que diría tal cual?
7. ¿Qué fotos o videos tiene de esto? ¿Sale alguien más? ¿Se puede publicar su cara?
8. ¿Cuántas láminas quiere, o lo decide la IA?
9. ¿Hay una referencia (Pinterest) para el look? Si no, ¿sigue el estilo del espacio?
10. ¿Fecha, hora, lugar, precio, enlace o @ que deban aparecer? (los datos duros no se inventan)
11. ¿Algo que no deba decirse o mostrarse?
12. ¿Cuándo se publica y quién lo sube?

Las respuestas se guardan en `brief` del plan, con las palabras de Emi en `brief.respuestas_emi`. El validador rechaza un plan sin ellas.

## 3. Proponer el guion

Elegir una [estructura](references/estructuras.md) según el objetivo y decirle a Emi cuál y por qué. Presentar el guion lámina por lámina en texto llano (no JSON): qué se ve, qué dice, qué sticker lleva. Ofrecer una o dos alternativas de gancho. Proponer con libertad (un formato distinto, un remate, una foto mejor), marcándolo como propuesta.

Cómo se escribe, para que suene a Emi y no a máquina: [voz](references/voz.md). En corto: primera persona, como le escribiría a un amigo; una idea por lámina; hasta 30 palabras (28 en `milla` y `pan`, 24 en `castorena`); nada de «descubre», «al siguiente nivel», «¿sabías que…?»; sin rayas largas. Los emojis no se dibujan (las tipografías no los tienen y el validador los rechaza): si Emi quiere uno, lo pone en Instagram y se anota en `nota_publicacion`.

**No se dibuja en limpio hasta que Emi aprueba el guion.** Entonces `guion_aprobado: true`. Para enseñarle cómo va quedando antes de eso: `$H render DIR --borrador`.

## 4. Fotos

Primero fotos reales de Emi; un fondo generado solo cuando no hay foto que sirva y el espacio lo admite (`fondos_ia`). Las fotos de una secuencia van en `producciones/<espacio>/<tema>/fotos/` (bajarlas de Drive: `HISTORIAS CLAUDE/<espacio>/_fotos/`).

`$H catalogo DIR/fotos` mide cada foto (zona más lisa, luz por tercios) y crea `catalogo.json`. Quien pueda **ver** la foto completa una sola vez `descripcion`, `cuando_usar`, `personas`, `permiso`, `foco` (`[x, y]` de 0 a 1: qué parte conservar al recortar) y `rostro` (caja `[x0, y0, x1, y1]` de 0 a 1 sobre la foto, o `null`). Ni el validador ni el render dejan poner texto o un sticker sobre un rostro, y una foto sin describir no pasa. HEIC no se lee: convertir antes a JPG. Si una foto se quita de la carpeta, su ficha se conserva marcada `ausente`.

## 5. Look y referencias de Pinterest

Cuando Emi mande una imagen de referencia: [referencias](references/referencias.md). En corto: `$H referencia IMG --espacio E --nombre N` mide luz, color, grano, viñeta y paleta y propone un filtro; la IA completa a ojo tipografía, composición y espíritu en la ficha; el plan la usa con `"estilo": {"referencia": "N"}`; se dibuja un borrador y `$H comparar REF out/01.png` dice cuánto falta. Se imita el look, no se copia la obra: ni sus fotos, ni su texto, ni marcas ajenas.

Filtros listos: `natural`, `calido`, `pelicula`, `crema`, `editorial_bn`, `noche`, `sobrio`, `ninguno`, o un objeto con `calidez`, `desvanecido`, `contraste`, `saturacion`, `brillo`, `grano`, `vineta`, `bn`, `desenfoque`, `tinte` y `tinte_fuerza` (rangos en [plan](references/plan.md)).

## 6. Dibujar

```bash
D=producciones/personal/TEMA
$H proyecto $D --espacio personal     # carpetas, plan de ejemplo y saldo inicial
$H catalogo $D/fotos
$H validar $D/plan.json --borrador    # las mismas comprobaciones que el render; si pasa, se dibuja
$H fondo --espacio personal --prompt-file $D/prompts/02.txt --out $D/fondos/02.png --estado $D/estados/02.json --execute   # solo si hace falta
$H render $D                          # out/01.png… + out/hoja.png + out/LEEME.md
$H cierre $D                          # créditos de Kie gastados y restantes
```

Campos del plan: [plan](references/plan.md). El borrador también exige el `brief` completo: primero se pregunta, luego se dibuja. Sin `--execute` nada gasta saldo, y `fondo` se niega en los espacios que no admiten imágenes generadas. La clave de Kie es la misma de Vox (`KIE_API_KEY`, o la que inyecta el proxy en la nube); nunca se escribe en un archivo ni en el chat.

Los stickers de Instagram (encuesta, pregunta, enlace, quiz, deslizador, cuenta regresiva) no se dibujan: se reserva su espacio y `out/LEEME.md` le dice a Emi cuál poner y dónde. Un sticker falso se nota y no funciona.

## 7. Revisar antes de entregar

Mirar `out/hoja.png` (todas las láminas con la zona segura en cian, el rostro en amarillo y el sticker en rosa) y cada PNG a tamaño real: texto legible en un teléfono, nada cortado, nada sobre una cara, la secuencia se entiende sin sonido y en orden. Corregir y volver a dibujar. Lo que una IA no puede juzgar (si suena a él, si el chiste funciona) se le pregunta a Emi con las imágenes delante.

## 8. Entregar en Drive

Carpeta `HISTORIAS CLAUDE` (id `1ltJlzCOw7LpQzFKXpzGkdEhbc9qTINHr`) → `<espacio>/` → una subcarpeta por secuencia, `AAAA-MM-DD tema`, con las láminas numeradas, `hoja.png`, `LEEME.md` y `plan.json`. Dar a Emi el enlace, la tabla de `cierre` y los avisos del validador. No publicar en Instagram: lo sube Emi.

## 9. Aprender (obligatorio)

Después de cada entrega y de cada comentario de Emi: `$H aprender "qué pasó y qué regla queda"` (con `--espacio E` si es de una sola marca). Las lecciones no se borran. Si la lección también sirve a los videos, decírselo a Emi como «propuesta para Vox»; este repositorio no escribe en el de Vox, y Vox no escribe aquí. Si la lección cambia el motor, hacer el cambio con su prueba y anotarlo en `CHANGELOG.md`.

Cada semana: [revisión del nicho](references/nicho.md) por espacio activo.

## Herramientas

- **Drive**: fotos, referencias y entregas.
- **box** (la computadora en la nube de Emi): para lo que la nube de la IA no alcanza, como abrir Pinterest o Instagram con su sesión o bajar un video. No se inicia sesión ni se publica por él.
- **Kie**: fondos, solo con `--execute` y avisando el costo (4 créditos por imagen con `nano-banana-2-lite`, medido en Vox el 10/11/2026).
- **GitHub** (`lianfixx/HISTORIAS-`): todo cambio de método queda aquí, con `CHANGELOG.md` al día.

## Terminado

`validar` sin errores, `render` final, hoja revisada, entrega en Drive con enlace, tabla de saldos, lecciones guardadas, repositorio actualizado y visto bueno de Emi.
