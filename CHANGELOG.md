# Cambios

## 0.2.0 · 2026-11-10 · candidato

Auditoría independiente del motor: 24 hallazgos confirmados, todos corregidos, cada uno con su prueba.

- **Zona segura de verdad**: cada bloque se mide por su tinta real, ya girada. Antes un titular abajo sobresalía hasta 30 px y una nota girada hasta 74.
- **Rostros**: la colisión usa esa misma caja; cuenta también para stickers; un `rostro` mal escrito es error en vez de apagar la protección; ya no se rodea declarando la foto como fondo `ia`.
- **Validar y render son lo mismo** (`disposicion`): si `validar` pasa, se dibuja. El render arma todo en memoria y no deja `out/` a medias.
- Planes, catálogos, perfiles y estados mal formados dan un error en español, no una traza.
- Emojis y símbolos sin glifo se rechazan en vez de salir como rectángulos.
- Las frases prohibidas ya no se evaden con saltos de línea o espacios y no saltan dentro de otra palabra.
- El color del texto se elige según el fondo; texto invisible es error.
- `estilo.referencia` aplica el filtro de la ficha; `referencia` conserva lo escrito a mano y los filtros aprobados.
- `fondo` exige `--espacio`: respeta el veto de imágenes generadas y el estilo de imagen del espacio.
- Kie: respuestas inesperadas, estados corruptos y descargas que no son imagen se rechazan; no se siguen redirecciones a otro servidor; `KIE_API_KEY` vacía usa el marcador.
- El ZIP funciona fuera del repositorio (espacios dentro de la skill, `producciones/` en la carpeta de trabajo, `requirements.txt` incluido).
- Las lecciones generales de Vox ya se leen en `aprendizajes`; `vox --ruta` inválida es error; el plan nuevo toma el filtro del espacio.
- `resaltar`: frases como secuencia, ñ distinta de n, lista obligatoria.
- PNG con transparencia se rellenan con el papel del espacio; fotos rotas no impiden catalogar; una foto retirada conserva su ficha.
- El pie de entrega incluye el texto de cada lámina para copiar.
- 70 pruebas, entre ellas de píxeles (zona segura y rostro), del ZIP y de la línea de comandos.

Sin corregir, anotado: si el proceso muere justo después de crear una tarea en Kie y antes de guardar su estado, esa imagen se paga y se pierde; `cierre` atribuye a la secuencia lo que Vox gaste en el mismo intervalo; sin probar en Windows ni macOS.

## 0.1.0 · 2026-11-10 · candidato

Primera versión, a partir del video «Creé una Máquina de Historias de Instagram con IA» de Santiago Muñoz (análisis en `docs/ANALISIS-VIDEO.md`) y de las 15 indicaciones de Emi.

- Motor propio `historias.py` (Pillow): láminas 1080x1920 con zona segura, cinco estilos de texto, ocho filtros con grano y viñeta deterministas, recorte con punto de interés, protección de rostros, espacio reservado para stickers nativos, hoja de revisión y pie de entrega.
- Catálogo de fotos que se describe una sola vez (la idea central del video) y validador que rechaza fotos sin describir.
- Referencias de Pinterest medibles: `referencia`, `medir` y `comparar`.
- Los cuatro espacios de Vox Studio (`personal`, `milla`, `castorena`, `pan`) con su perfil, marca, nicho, aprendizajes, ideas y referencias; puente de solo lectura `historias.py vox`.
- Frenos: plan sin respuestas de Emi no pasa; sin `guion_aprobado` solo hay borrador; Kie no gasta sin `--execute`.
- Fondos con Kie usando la misma clave y el mismo contrato que Vox.
- 45 pruebas sin red; `tools/verificar.py` y revisión automática en GitHub.
- No se instaló `santmun/historias-ig-skill` tal cual: razones en `docs/ANALISIS-VIDEO.md`.

Pendiente de Emi: respuestas del cuestionario inicial (`docs/PREGUNTAS-INICIALES.md`), primera secuencia real y aprobación estética.
