# Análisis del video de origen

**«Creé una Máquina de Historias de Instagram con IA que Imprime Dinero»** · Santiago Muñoz (Horizontes IA, @sanmunoz.ia) · 29 min · https://youtu.be/pz6AIlkjWlc

Analizado el 10/11/2026 a partir de su transcripción automática completa y de su descripción. No se vieron los fotogramas: lo que aparece en pantalla se conoce solo por lo que él narra.

## Qué enseña

Un flujo en Claude Code para producir secuencias de historias sin abrir Canva:

1. **Una carpeta de fotos** propias (retratos, lugares, objetos).
2. **Una línea** con el tema del día.
3. **Claude como director**: pregunta lo que le falta (de qué va, a qué hora, cuántas láminas, quién es el invitado, su foto), propone el guion y espera aprobación.
4. **Composición con Pillow**: texto sobre la foto, 1080x1920.
5. **Fondos con IA** cuando no hay foto, vía Kie AI (Nano Banana 2, unos 0.04 USD por imagen).
6. **Empaquetarlo como skill** para invocarlo con una frase desde cualquier sesión.

## Lo que de verdad importa (y lo que adoptamos)

| Idea del video | Minuto | Cómo quedó aquí |
|---|---|---|
| Describir cada foto **una sola vez** con visión y guardar un catálogo (qué es, dónde hay espacio libre, dónde está la cara) | 14:23 | `historias.py catalogo` + `catalogo.json`; el validador rechaza fotos sin describir y el render se niega a tapar un rostro |
| La IA dirige, la persona decide: preguntar antes de generar y pedir aprobación del guion | 3:47 | Cuestionario fijo en la skill; el plan no pasa sin `brief.respuestas_emi` ni se dibuja en limpio sin `guion_aprobado` |
| Sin formato ganador de storytelling no funciona, por buenas que sean las imágenes | 0:28, 22:24 | `references/estructuras.md` por objetivo y `references/voz.md` |
| Híbrido: fotos reales primero, IA solo donde falta; el fondo generado nunca lleva texto | 19:36 | Regla de la skill; `fondo` añade «no text» a todo prompt |
| Generar los fondos en paralelo | 22:24 | Cada fondo tiene su archivo de estado, así que se pueden lanzar a la vez y reconsultar sin pagar de nuevo |
| Resaltar palabras clave con otro color o subrayado | 22:24 | `resaltar` en cada bloque |
| Varios formatos según el tipo de historia (anuncio, inspiración, venta) | 25:00 | Estructuras por objetivo y estilo por espacio |
| «Si ya tienes tu formato, dáselo y que lo imite» | 9:34 | `referencia`, `medir` y `comparar` para las imágenes de Pinterest |
| Mejorar a base de decirle qué no gustó | 22:24 | `aprender`: lecciones que no se borran y se leen antes de cada secuencia |

## Lo que no adoptamos, y por qué

- **Velo oscuro fijo y texto centrado en todas las láminas.** Es lo que hace que se vean hechas por plantilla. Aquí el texto va donde la foto está libre y el velo es por lámina.
- **Barra de progreso dibujada y sticker de respuesta falso.** Instagram ya pone la suya; un sticker pintado no se puede tocar. Se reserva el espacio y el sticker real se pone en la app.
- **Ilustraciones generadas sobrepuestas (el pájaro con fondo verde).** El propio video muestra que queda mal colocada. Se deja fuera hasta que Emi lo pida.
- **Modo «omitir permisos».** Aquí nada gasta sin `--execute` y nada se publica.
- **La clave pegada en el chat.** La clave de Kie llega por variable de entorno o por el proxy, nunca por texto.
- **Las cifras de resultados** (3,000 USD, 20,000 vistas) son afirmaciones suyas sin evidencia verificable; no son una promesa de esta skill.

## ¿Ya existe la skill en GitHub?

Sí, dos repositorios públicos del autor:

- `santmun/historias-ig-skill` (el del video): un comando `/historias-ig`, onboarding de 8 preguntas, 35 estructuras narrativas, `generate.py` con Pillow y Kie. Su `README` dice que el framework completo se entrega en su comunidad de pago.
- `santmun/instagram-stories-skill`: variante con fondos de pixel art, hecha a la medida de su marca.

Se leyó completo el primero y **no se instaló tal cual**, por cinco razones:

1. Es de una sola marca (`config.json` único); Emi necesita cuatro espacios separados.
2. Todas las láminas salen con la misma maqueta: foto oscurecida, texto centrado, barra de progreso, caja amarilla de «Responde PALABRA». Es justo el aspecto que Emi no quiere.
3. No tiene la protección de rostros que el video recomienda: `scan_fotos.py` solo lista archivos.
4. Guarda la clave de Kie en `config.json`.
5. No trae licencia, así que no se puede redistribuir su código ni su texto.

De ahí se tomaron ideas (el repertorio de estructuras por objetivo, el polling de Kie), reescritas. El contrato de Kie se copió del que ya estaba probado en Vox Studio.

## Lo que el video no resuelve y aquí sí

Varias marcas sin mezclarse, referencias de estilo medibles, revisión semanal del nicho, memoria de lecciones compartida con el sistema de video, entrega ordenada en Drive, frenos de gasto y de aprobación, pruebas automáticas y uso desde cualquier IA.
