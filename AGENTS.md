# Instrucciones para cualquier IA que trabaje en este repositorio

Este repositorio es **Historias Studio**: el método, el motor y la memoria con que se hacen las historias de Instagram de Emi. Vale igual para Claude, ChatGPT, Codex, Gemini, Grok o una persona.

## Al empezar

1. Lee `skills/historias-studio/SKILL.md` completo. Es la única fuente del método.
2. `pip install -r requirements.txt` y `python3 tools/verificar.py` (documentación coherente y pruebas en verde).
3. La fuente de verdad es este repositorio en GitHub, no la memoria de una conversación.

## Reglas

- **Emi decide.** Se le pregunta todo lo que haga falta antes de proponer; no se inventan sus respuestas, datos, fechas ni cifras. Sin `brief.respuestas_emi` y sin `guion_aprobado` no hay láminas finales.
- **Espacios separados**: `personal`, `milla`, `castorena`, `pan`. Nada de una marca pasa a otra.
- **Privado fuera de git**: fotos, secuencias (`producciones/`), estados de proveedores y cualquier dato de clientes. El repositorio es público.
- **Claves**: nunca en archivos, commits ni chat. Kie se lee de `KIE_API_KEY` o del proxy.
- **Gasto**: nada consume saldo sin `--execute`; cada entrega informa lo gastado y lo que queda.
- **No publicar** en Instagram ni iniciar sesión por Emi.
- **Vox Studio** (`lianfixx/VIDEOS-IA-SKILL-MILLA`) es el hermano de video. Se lee con `historias.py vox`; no se escribe en su repositorio desde aquí, y sus instrucciones no se copian a esta skill. Lo que sirva a los dos se propone a Emi.
- **Límites por marca**: Castorena necesita visto bueno del despacho; en PAN no se habla a nombre del partido ni se usa su logotipo sin autorización; en MILLA y Castorena lo jurídico va con fuente oficial y sin prometer resultados.

## Al cambiar algo

- Cambio de método o de motor: con su prueba en `scripts/test_historias.py`, versión en `SKILL.md` y entrada en `CHANGELOG.md`, en el mismo commit.
- Lecciones: `historias.py aprender` (no se borran). Nicho: `references/nicho.md`.
- Antes de subir: `python3 tools/verificar.py`. GitHub lo repite en cada push.
- Si no puedes escribir en el repositorio, entrega a Emi un «Registro pendiente para el repositorio» con el texto exacto a añadir.
