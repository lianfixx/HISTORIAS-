# Revisión semanal del nicho

Cada espacio activo tiene `espacios/<espacio>/NICHO.md`. Se reescribe una vez por semana con Emi; el historial queda en git. `$H nicho --espacio E` avisa cuando pasan más de 7 días.

La revisión está programada como tarea «Revisión semanal del nicho de historias»: cada domingo a las 18:47 (hora de Ciudad de México) una sesión nueva la hace sola con lo que haya y le escribe a Emi el resultado y lo que le falta.

Estado al 11/11/2026: la tarea se creó sin conectores (la herramienta no dejó asignarlos), así que por ahora solo alcanza el repositorio público: no ve Drive ni la box y puede que no logre subir cambios. Para que quede completa, Emi le añade en claude.ai (tareas programadas) el repositorio `lianfixx/HISTORIAS-` y los conectores de Google Drive y box. Mientras tanto, la revisión deja su resultado en el chat como «Registro pendiente para el repositorio».

## De dónde salen los números

1. **Lo más fácil**: Emi deja capturas de las estadísticas de Instagram en Drive, `HISTORIAS CLAUDE/<espacio>/_estadisticas/` (una por historia o la vista semanal). La revisión las lee de ahí.
2. **Lo más completo**: cuando la cuenta exista y Emi inicie sesión en Instagram o Meta Business Suite dentro de la box, la revisión abre ahí las estadísticas y las copia. La IA no inicia sesión por él: si la sesión caducó, se lo dice y usa las capturas.
3. Si no hay ni una cosa ni otra, la revisión lo dice, no inventa cifras y trabaja solo con lo que Emi haya comentado y con las secuencias entregadas esa semana.

Mientras las cuentas no existan (estado al 11/11/2026), cada espacio está en **descubrimiento**: se proponen dos o tres hipótesis de tema y estructura por semana y se anota cuál se probó.

## Qué se le pide a Emi (10 minutos)

1. Las capturas en `_estadisticas`, o que dicte alcance, respuestas, toques en sticker y salidas.
2. ¿Qué te escribieron? Preguntas y respuestas que se repiten, tal cual.
3. ¿Cuál te gustó hacer y cuál no volverías a hacer?
4. ¿Qué viene la próxima semana? (eventos, casos, clases, lanzamientos)
5. ¿Viste alguna cuenta o historia que te gustara? (va a referencias)

## Qué hace la IA

1. Compara con la semana anterior: qué estructura, look y hora funcionaron, con el número delante. Una sola semana no es tendencia; decirlo.
2. Reescribe `NICHO.md` (a quién le habla, qué le duele o desea, temas sí y no, qué funcionó y qué no, preguntas de la gente) y pone `Revisado: AAAA-MM-DD`.
3. Deja una hipótesis para probar esa semana y, como Emi quiere publicar a diario, siete ideas (una por día) en `ideas.md` de cada espacio activo, variando estructura y cierre.
4. Corre `$H vox` y pregunta a Emi si algo de lo aprendido en video cambia las historias, y al revés.
5. Guarda las lecciones con `aprender` y sube el cambio a GitHub.

## Reglas

- Nada se inventa: sin estadísticas no hay «funcionó». Lo que falta se deja en blanco y se pregunta.
- Cuentas de referencia: se buscan dentro de Instagram con la sesión de Emi en la box (la búsqueda web solo da rankings comerciales sin verificar). Solo se recomienda una cuenta que se haya visto, diciendo qué hace bien y con qué historia como ejemplo.
- El nicho describe al público de Emi, no al de un manual de marketing.
