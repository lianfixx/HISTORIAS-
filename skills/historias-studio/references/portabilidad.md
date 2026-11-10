# Usar esta skill con cualquier IA

Todo es Markdown, JSON y un script de Python sin servicios propios de ninguna plataforma.

| IA | Cómo cargarla |
|---|---|
| Claude Code (terminal, web, escritorio) | Abrir este repositorio: `.claude/skills/historias-studio/` la carga sola. |
| Claude (claude.ai, app) | Subir `dist/historias-studio.zip` como skill (`python3 tools/empaquetar.py`), o pegar `SKILL.md` en las instrucciones de un proyecto. |
| Codex, Cursor y agentes que leen `AGENTS.md` | Abrir el repositorio; `AGENTS.md` y `.agents/skills/` apuntan aquí. |
| ChatGPT, Gemini, Grok y otras sin terminal | Pegar `SKILL.md` y los `references/` que hagan falta, más `espacios/<espacio>/`. |

## Con terminal

`pip install -r requirements.txt` y seguir `SKILL.md`. Para Kie hace falta `KIE_API_KEY` en el entorno (la misma de Vox). Sin ella todo funciona menos `fondo --execute`, `saldo` y `cierre`.

Desde el ZIP (fuera del repositorio) el motor es `python3 scripts/historias.py`, los espacios viajan dentro de la skill y las secuencias se crean en `producciones/` de la carpeta desde la que se ejecuta. `HISTORIAS_ESPACIOS` y `HISTORIAS_PRODUCCIONES` cambian esas rutas. Lo aprendido en una copia suelta no llega a GitHub: hay que pasarlo al repositorio.

Probado con Python 3.10 y Pillow 10.1 en Linux. En Windows y macOS no se ha ejecutado; todo el texto se lee y escribe en UTF-8.

## Sin terminal

La IA hace lo que no necesita ejecutar nada: brief, guion, elección de estructura, ficha de referencia a ojo y el `plan.json` completo según [plan.md](plan.md). Lo entrega a Emi como «plan listo para dibujar» y otra IA con terminal corre `validar` y `render`. No debe afirmar que validó ni que dibujó.

## Sin Drive o sin box

Sin conector de Drive, la IA deja la secuencia en `producciones/` y le dice a Emi qué subir y a qué carpeta. Sin box, pide a Emi la imagen o la captura en lugar del enlace.

## Lo que ninguna IA hace por su cuenta

Publicar en Instagram, iniciar sesión por Emi, gastar saldo sin `--execute`, inventar datos o respuestas de Emi, escribir claves en archivos o en el chat, ni escribir en el repositorio de Vox.
