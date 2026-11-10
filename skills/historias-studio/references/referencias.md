# Imitar una referencia de Pinterest

Emi manda una imagen y dice qué le gusta de ella. Se imita el look (luz, color, grano, tipografía, composición, ánimo), adaptado a su marca y a su foto. No se copia la obra.

## Pasos

1. **Guardar** la imagen en Drive, `HISTORIAS CLAUDE/<espacio>/_referencias/`. Si llega como enlace de Pinterest y la nube no lo abre, abrirlo desde la box.
2. **Preguntar** si no lo dijo: ¿qué te gusta de esta? (el color, la letra, el acomodo, el ánimo) y ¿es para una secuencia o queda como estilo del espacio?
3. **Medir**: `$H referencia IMG --espacio E --nombre N` crea `espacios/E/referencias/N.json` con medidas, paleta y un filtro de partida.
4. **Mirar** la imagen y completar la ficha a ojo:
   - `tipografia`: familia más cercana de las disponibles (`titular` del espacio, `serif`, `cuerpo`, `nota`, `etiqueta`), mayúsculas o no, tamaño relativo, color, si lleva caja.
   - `composicion`: dónde va el texto, cuánto aire, alineación, si hay giro, cuántos elementos.
   - `espiritu`: en una frase, qué transmite (domingo lento, apunte de libreta, revista, urgente).
   - `notas_emi`: lo que él dijo, literal.
5. **Borrador** con una foto de Emi y ese filtro: `$H render DIR --borrador`.
6. **Comparar**: `$H comparar REF DIR/out/01.png`. Cada número es la diferencia entre la lámina y la referencia:

   | Medida | Si sale positiva | Corregir |
   |---|---|---|
   | `luz` | más clara | bajar `brillo` o subir `velo` |
   | `negros` | negros más lavados | bajar `desvanecido` |
   | `saturacion` | más color | bajar `saturacion` |
   | `calidez` | más cálida | bajar `calidez` |
   | `grano` | más grano | bajar `grano` |
   | `vineta` | esquinas más oscuras | bajar `vineta` |

   Repetir hasta que ninguna pase de ±0.05 (±0.005 en `grano`), y entonces mirar las dos juntas: los números acercan, el ojo decide. La foto de fondo pesa en las medidas; comparar con una foto parecida a la de la referencia.
7. **Enseñar** a Emi referencia y lámina lado a lado. Lo que diga se guarda con `aprender` y, si aprueba, el filtro queda en la ficha y puede pasar a ser el del espacio.

## Límites

- Lo que no existe en el motor (una tipografía, un marco, un recorte, una textura) se dice y se programa con su prueba; no se finge con algo parecido sin avisar.
- No se usan las fotos, ilustraciones, textos ni marcas de la referencia. Tampoco tipografías de pago: se busca la equivalente libre y se añade a `fuentes/` con su licencia.
- Si la referencia es la obra reconocible de alguien, se toma la idea general, no su firma.
