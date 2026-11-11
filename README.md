# Historias Studio

Método, motor y memoria para hacer las historias de Instagram de Emi con cualquier IA: la IA pregunta, propone y dibuja; Emi decide.

Estado: **0.3.0, candidato** (11/11/2026). El motor está probado; falta la primera secuencia real aprobada por Emi.

## Qué hay aquí

| Ruta | Qué es |
|---|---|
| `skills/historias-studio/SKILL.md` | El método completo. Empezar por aquí. |
| `skills/historias-studio/references/` | Plan, voz, estructuras, referencias de Pinterest, nicho semanal y portabilidad. |
| `skills/historias-studio/scripts/historias.py` | El motor (Python + Pillow). |
| `skills/historias-studio/fuentes/` | Tipografías libres (OFL) con su licencia. |
| `espacios/` | Los cuatro espacios: `personal`, `milla`, `castorena`, `pan`. |
| `docs/ANALISIS-VIDEO.md` | Análisis del video de origen y qué se tomó de él. |
| `docs/PREGUNTAS-INICIALES.md` | Lo que falta que Emi conteste. |
| `docs/DRIVE.md` | Carpetas de Drive y sus identificadores. |
| `AGENTS.md` | Reglas para cualquier IA que trabaje en el repositorio. |
| `CHANGELOG.md` | Qué cambió en cada versión. |

Lo privado no está en git: `producciones/` (secuencias) y `fotos/`. Las entregas viven en Drive, carpeta **HISTORIAS CLAUDE**.

## Uso rápido

```bash
pip install -r requirements.txt
H="python3 skills/historias-studio/scripts/historias.py"
$H espacios
$H proyecto producciones/personal/mi-tema --espacio personal
# llenar el brief y las láminas en producciones/personal/mi-tema/plan.json
$H render producciones/personal/mi-tema --borrador
$H animar producciones/personal/mi-tema --borrador   # opcional: MP4 por lámina (necesita ffmpeg)
```

El plan recién creado no se dibuja hasta tener el `brief` con las respuestas de Emi: es a propósito.

Decirle a la IA: «hazme unas historias para …». Ella sigue `SKILL.md`: lee lo aprendido, pregunta, propone el guion, espera aprobación, dibuja, revisa, entrega en Drive y guarda la lección.

## Relación con Vox Studio

Vox Studio (`lianfixx/VIDEOS-IA-SKILL-MILLA`) hace los videos; Historias Studio, las historias. Comparten espacios, marca y clave de Kie. `historias.py vox` trae de Vox las lecciones y avisa si la marca difiere. Cada uno conserva sus propias instrucciones y ninguno escribe en el repositorio del otro.

## Comprobar

```bash
python3 tools/verificar.py     # enlaces, versión, puentes, nada privado en git y las pruebas del motor (minuto y medio)
python3 tools/empaquetar.py    # dist/historias-studio.zip para subir la skill a otra IA
```

## Créditos y licencias

Idea de partida: Santiago Muñoz, Horizontes IA (video y `santmun/historias-ig-skill`). El código y los textos de este repositorio son propios. Tipografías Anton, Gelasio, Inter y Caveat bajo SIL Open Font License; sus licencias están junto a los archivos.
