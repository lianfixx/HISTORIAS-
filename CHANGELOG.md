# Cambios

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
