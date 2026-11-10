#!/usr/bin/env python3
"""Historias Studio: secuencias de historias de Instagram (1080x1920) por espacio.

  espacios                                  lista los espacios y su estado
  aprendizajes [--espacio E]                reglas vigentes (leer antes de cada secuencia)
  aprender "texto" [--espacio E]            guarda una lección (no se borran)
  nicho --espacio E                         muestra el nicho y avisa si lleva más de 7 días sin revisarse
  vox [--ruta REPO_VOX]                     trae marca y aprendizajes de Vox Studio (solo lectura)
  proyecto DIR --espacio E                  crea producciones/<espacio>/<tema>/ con su plan de ejemplo
  catalogo DIR_FOTOS                        mide cada foto y deja catalogo.json para describirlas una sola vez
  medir IMAGEN                              métricas de look (luz, color, grano, viñeta, paleta)
  referencia IMAGEN --espacio E --nombre N  guarda una referencia (Pinterest) con el filtro que la imita
  comparar REFERENCIA IMAGEN                qué tan lejos queda una lámina de su referencia
  validar PLAN [--borrador]                 revisa el plan con las mismas reglas que el render, sin escribir nada
  fondo --espacio E --prompt-file F --out O --estado S   fondo con Kie (sin --execute no gasta)
  render DIR [--borrador]                   dibuja las láminas, la hoja de revisión y el pie de entrega
  saldo | cierre DIR                        créditos de Kie: lo que queda y lo gastado en la secuencia

La clave de Kie es la misma de Vox Studio: variable KIE_API_KEY o, en la nube, la que inyecta el proxy.
Nunca se escribe en archivos.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageStat

SKILL = Path(__file__).resolve().parent.parent
RAIZ = SKILL.parent.parent
FUENTES = SKILL / "fuentes"
W, H = 1080, 1920
# Zona segura de historias: arriba van la barra y el nombre de la cuenta; abajo, la caja de respuesta.
SEG_X0, SEG_X1, SEG_Y0, SEG_Y1 = 90, 990, 270, 1540
ANCHO_SEG = SEG_X1 - SEG_X0
MARCADOR = "proxy-injected"
KIE = "https://api.kie.ai/api/v1"
HOSTS_DESCARGA = {"tempfile.aiquickdraw.com", "file.aiquickdraw.com"}
# Mismo contrato que Vox Studio (docs.kie.ai, comprobado el 2026-11-10).
MODELOS_KIE = {
    "nano-banana-2-lite": {},
    "seedream/5-lite-text-to-image": {"quality": "basic", "output_format": "png"},
}
ESTILOS_FONDO = {
    "foto": "candid smartphone photograph, natural available light, true-to-life colors, slightly imperfect framing, unposed",
    "ilustracion": "hand-painted editorial illustration, gouache and ink texture, natural proportions, muted palette with one warm accent",
    "textura": "flat lay texture background, paper or fabric or wall, soft daylight, minimal, no objects in the center",
}
SIN_TEXTO = "vertical 9:16, no text, no letters, no logos, no watermark, calm uncluttered area where text can sit"
ARCHIVOS_FUENTE = {"Anton": "Anton-Regular.ttf", "Gelasio": "Gelasio.ttf", "Inter": "Inter.ttf", "Caveat": "Caveat.ttf"}
ESTILOS_BLOQUE = {
    #            fuente      peso  tam  interlinea
    "titular":  (None,       700,  118, 1.04),
    "cuerpo":   ("Inter",    600,   54, 1.28),
    "serif":    ("Gelasio",  500,   64, 1.22),
    "nota":     ("Caveat",   600,   82, 1.05),
    "etiqueta": ("Inter",    700,   54, 1.50),
}
POSICIONES = ("arriba", "centro", "abajo")
ALINEACIONES = ("izq", "centro", "der")
STICKERS = {  # espacio que ocupa cada sticker nativo de Instagram (se pone en la app, aquí solo se reserva)
    "encuesta": (640, 260), "pregunta": (720, 340), "enlace": (520, 130), "quiz": (720, 520),
    "deslizador": (720, 230), "cuenta_regresiva": (720, 300), "mencion": (460, 110), "ubicacion": (460, 110),
}
FILTROS = {
    "natural":      {"contraste": 1.03, "saturacion": 0.97, "grano": 0.05},
    "calido":       {"calidez": 0.28, "desvanecido": 0.10, "saturacion": 0.95, "grano": 0.07, "vineta": 0.14},
    "pelicula":     {"calidez": 0.16, "desvanecido": 0.20, "contraste": 0.94, "saturacion": 0.86, "grano": 0.16, "vineta": 0.22},
    "crema":        {"calidez": 0.20, "desvanecido": 0.26, "contraste": 0.90, "saturacion": 0.78, "brillo": 1.05, "grano": 0.06},
    "editorial_bn": {"bn": True, "contraste": 1.12, "grano": 0.12, "vineta": 0.18},
    "noche":        {"calidez": -0.12, "contraste": 1.08, "brillo": 0.88, "saturacion": 0.90, "grano": 0.14, "vineta": 0.30},
    "sobrio":       {"saturacion": 0.80, "contraste": 1.04, "desvanecido": 0.06, "grano": 0.03},
    "ninguno":      {},
}
RANGOS_FILTRO = {  # clave -> (mínimo, máximo)
    "calidez": (-1, 1), "desvanecido": (0, 1), "contraste": (0.3, 2), "saturacion": (0, 2), "brillo": (0.3, 2),
    "grano": (0, 1), "vineta": (0, 1), "desenfoque": (0, 40), "tinte_fuerza": (0, 1),
}
CLAVES_FILTRO = set(RANGOS_FILTRO) | {"bn", "tinte"}
# Giros que delatan texto de máquina. Son avisos: Emi decide.
FRASES_IA = [
    "en el mundo de hoy", "en la era digital", "sumérgete", "desbloquea", "descubre cómo", "lleva tu", "al siguiente nivel",
    "potencia tu", "no es solo", "no se trata solo", "¿sabías que", "en resumen", "en conclusión", "es importante destacar",
    "transforma tu", "eleva tu", "el secreto", "revoluciona", "imagina un mundo", "prepárate para", "sin lugar a dudas",
]
MAX_PALABRAS = 30
EXT_FOTO = {".jpg", ".jpeg", ".png", ".webp"}


class ErrorHistorias(Exception):
    pass


# ---------- utilidades ----------

def _leer_json(ruta: Path, que: str):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorHistorias(f"no existe {ruta}") from exc
    except (ValueError, OSError) as exc:
        raise ErrorHistorias(f"{que} ({ruta}) no se puede leer como JSON: {exc}") from exc


def _es_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _num(v, nombre: str, lo: float, hi: float) -> float:
    if not _es_num(v) or not lo <= v <= hi:
        raise ErrorHistorias(f"`{nombre}` debe ser un número entre {lo} y {hi} (llegó {v!r})")
    return float(v)


def _hex(c) -> tuple[int, int, int]:
    if not isinstance(c, str) or not re.fullmatch(r"#?[0-9a-fA-F]{6}", c):
        raise ErrorHistorias(f"color inválido: {c!r} (usa papel, tinta, acento, apoyo, blanco, negro o #RRGGBB)")
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def color(nombre, perfil: dict) -> tuple[int, int, int]:
    fijos = {"blanco": "#FFFFFF", "negro": "#111111"}
    if isinstance(nombre, str) and nombre in perfil["colores"]:
        return _hex(perfil["colores"][nombre])
    return _hex(fijos.get(nombre, nombre) if isinstance(nombre, str) else nombre)


def _luz(rgb) -> float:
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255


def _norm(p: str) -> str:
    """Minúsculas, sin acentos ni signos, conservando la ñ."""
    p = unicodedata.normalize("NFC", p.lower()).replace("ñ", "\0")
    p = "".join(c for c in unicodedata.normalize("NFD", p) if unicodedata.category(c) != "Mn")
    return "".join(c for c in p.replace("\0", "ñ") if c.isalnum())


def slug(texto: str) -> str:
    s = unicodedata.normalize("NFD", str(texto).lower())
    s = re.sub(r"[^a-z0-9]+", "-", "".join(c for c in s if unicodedata.category(c) != "Mn")).strip("-")
    return s[:60] or "historia"


def tam_imagen(ruta: Path) -> tuple[int, int]:
    """Tamaño ya enderezado según EXIF, sin cargar los píxeles."""
    try:
        with Image.open(ruta) as img:
            w, h = img.size
            return (h, w) if img.getexif().get(274) in (5, 6, 7, 8) else (w, h)
    except (OSError, ValueError) as exc:
        raise ErrorHistorias(f"{ruta.name} no es una imagen legible: {exc}") from exc


def abrir_imagen(ruta: Path, fondo=(255, 255, 255)) -> Image.Image:
    """Imagen enderezada y en RGB; lo transparente se rellena con `fondo`."""
    try:
        with Image.open(ruta) as cruda:
            img = ImageOps.exif_transpose(cruda)
            if img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info:
                img = img.convert("RGBA")
                base = Image.new("RGBA", img.size, (*fondo, 255))
                base.alpha_composite(img)
                img = base
            return img.convert("RGB")
    except FileNotFoundError as exc:
        raise ErrorHistorias(f"no existe la imagen {ruta}") from exc
    except (OSError, ValueError) as exc:
        raise ErrorHistorias(f"{ruta.name} no es una imagen legible: {exc}") from exc


# ---------- espacios y memoria ----------

def dir_espacios() -> Path:
    if os.environ.get("HISTORIAS_ESPACIOS"):
        return Path(os.environ["HISTORIAS_ESPACIOS"])
    # En el repositorio viven en la raíz; en el ZIP de la skill viajan dentro de ella.
    return RAIZ / "espacios" if (RAIZ / "espacios").is_dir() else SKILL / "espacios"


def dir_producciones() -> Path:
    if os.environ.get("HISTORIAS_PRODUCCIONES"):
        return Path(os.environ["HISTORIAS_PRODUCCIONES"])
    return (RAIZ if (RAIZ / "espacios").is_dir() else Path.cwd()) / "producciones"


def _revisar_perfil(nombre: str, pf) -> dict:
    if not isinstance(pf, dict) or not isinstance(pf.get("nombre"), str) or not isinstance(pf.get("colores"), dict):
        raise ErrorHistorias(f"espacios/{nombre}/perfil.json: faltan `nombre` o `colores`")
    for c in ("papel", "tinta", "acento", "apoyo"):
        try:
            _hex(pf["colores"].get(c))
        except ErrorHistorias as exc:
            raise ErrorHistorias(f"espacios/{nombre}/perfil.json: colores.{c}: {exc}") from exc
    pf.setdefault("titular", "Anton")
    pf.setdefault("filtro", "natural")
    if pf["titular"] not in ARCHIVOS_FUENTE:
        raise ErrorHistorias(f"espacios/{nombre}/perfil.json: tipografía desconocida {pf['titular']!r}")
    if pf["filtro"] not in FILTROS:
        raise ErrorHistorias(f"espacios/{nombre}/perfil.json: filtro desconocido {pf['filtro']!r}")
    if not isinstance(pf.get("frases_prohibidas", []), list) or not _es_num(pf.get("max_palabras", MAX_PALABRAS)):
        raise ErrorHistorias(f"espacios/{nombre}/perfil.json: `frases_prohibidas` debe ser lista y `max_palabras` número")
    return pf


def perfiles() -> dict:
    out = {f.parent.name: _revisar_perfil(f.parent.name, _leer_json(f, "el perfil")) for f in sorted(dir_espacios().glob("*/perfil.json"))}
    if not out:
        raise ErrorHistorias(f"no hay espacios en {dir_espacios()}")
    return out


def perfil_de(espacio) -> dict:
    todos = perfiles()
    if not isinstance(espacio, str) or espacio not in todos:
        raise ErrorHistorias(f"espacio desconocido: {espacio!r}. Existen: {', '.join(todos)}")
    return todos[espacio]


def archivo_aprendizajes(espacio: str = "") -> Path:
    if espacio:
        perfil_de(espacio)
        return dir_espacios() / espacio / "aprendizajes.md"
    return dir_espacios() / "APRENDIZAJES.md"


def leer_aprendizajes(espacio: str = "") -> str:
    """Lo propio de historias y, después, lo traído de Vox (copia de solo lectura)."""
    archivos = [archivo_aprendizajes("")]
    if espacio:
        archivos.append(archivo_aprendizajes(espacio))
    archivos.append(dir_espacios() / "DESDE-VOX.md")
    if espacio:
        archivos.append(dir_espacios() / espacio / "desde-vox.md")
    partes = [f.read_text(encoding="utf-8").strip() for f in archivos if f.exists()]
    return "\n\n".join(partes) or "Sin aprendizajes registrados."


def aprender(texto: str, espacio: str = "") -> Path:
    texto = " ".join(texto.split())
    if len(texto) < 12:
        raise ErrorHistorias("la lección es demasiado corta: di qué pasó y qué regla queda")
    f = archivo_aprendizajes(espacio)
    previo = f.read_text(encoding="utf-8") if f.exists() else f"# Aprendizajes · {espacio or 'todas las historias'}\n\n"
    f.write_text(previo.rstrip("\n") + f"\n- {dt.date.today().isoformat()} · {texto}\n", encoding="utf-8")
    return f


def estado_nicho(espacio: str, hoy: dt.date | None = None) -> tuple[str, int | None]:
    """Devuelve el texto del nicho y los días desde su última revisión (None si nunca se revisó o la fecha no vale)."""
    perfil_de(espacio)
    f = dir_espacios() / espacio / "NICHO.md"
    if not f.exists():
        return "", None
    texto = f.read_text(encoding="utf-8")
    m = re.search(r"Revisado:\s*(\d{4}-\d{2}-\d{2})", texto)
    try:
        dias = ((hoy or dt.date.today()) - dt.date.fromisoformat(m.group(1))).days if m else None
    except ValueError:
        dias = None
    return texto, dias if dias is None or dias >= 0 else None


# ---------- puente con Vox Studio (solo lectura) ----------

def ruta_vox(ruta: str = "") -> Path:
    if ruta:
        if not (Path(ruta) / "espacios").is_dir():
            raise ErrorHistorias(f"{ruta} no es el repositorio de Vox Studio (no tiene `espacios/`)")
        return Path(ruta)
    for c in (os.environ.get("VOX_REPO", ""), str(RAIZ.parent / "VIDEOS-IA-SKILL-MILLA")):
        if c and (Path(c) / "espacios").is_dir():
            return Path(c)
    raise ErrorHistorias("no encuentro el repositorio de Vox Studio: pasa --ruta o define VOX_REPO "
                         "(git clone https://github.com/lianfixx/VIDEOS-IA-SKILL-MILLA)")


def _solo_lecciones(texto: str) -> str:
    return "\n".join(l for l in texto.splitlines() if not l.startswith("# ")).strip() + "\n"


def sincronizar_vox(ruta: str = "") -> list[str]:
    """Copia de Vox lo que sirve a las historias (lecciones y marca) sin tocar sus instrucciones ni las nuestras.

    Deja `espacios/DESDE-VOX.md` y `espacios/<e>/desde-vox.md`, y avisa si los colores o el tono difieren.
    """
    vox = ruta_vox(ruta) / "espacios"
    avisos = []
    cab = (f"# Traído de Vox Studio\n\nCopia de solo lectura, actualizada el {dt.date.today().isoformat()} con `historias.py vox`. "
           "No editar aquí: lo de video se corrige en Vox; lo propio de historias va en `aprendizajes.md`.\n\n")
    general = vox / "APRENDIZAJES.md"
    if general.exists():
        (dir_espacios() / "DESDE-VOX.md").write_text(cab + _solo_lecciones(general.read_text(encoding="utf-8")), encoding="utf-8")
    mios = perfiles()
    for nombre, mio in mios.items():
        suyo_f = vox / nombre / "perfil.json"
        if not suyo_f.exists():
            avisos.append(f"{nombre}: Vox no tiene este espacio")
            continue
        suyo = _leer_json(suyo_f, "el perfil de Vox")
        for k in ("colores", "titular", "tono", "estilo_imagen"):
            if suyo.get(k) != mio.get(k):
                avisos.append(f"{nombre}: «{k}» difiere de Vox ({json.dumps(suyo.get(k), ensure_ascii=False)[:90]})")
        partes = [cab]
        for f in (vox / nombre / "aprendizajes.md", vox / nombre / "MARCA.md"):
            if f.exists():
                partes.append(f"## {f.name}\n\n" + _solo_lecciones(f.read_text(encoding="utf-8")) + "\n")
        (dir_espacios() / nombre / "desde-vox.md").write_text("\n".join(partes), encoding="utf-8")
    for nombre in sorted(p.parent.name for p in vox.glob("*/perfil.json")):
        if nombre not in mios:
            avisos.append(f"{nombre}: existe en Vox y no aquí; créalo con Emi si también quiere historias")
    return avisos


# ---------- tipografía ----------

def fuente(nombre: str, tam: int, peso: int = 600) -> ImageFont.FreeTypeFont:
    if nombre not in ARCHIVOS_FUENTE:
        raise ErrorHistorias(f"tipografía sin archivo: {nombre!r}. Disponibles: {', '.join(ARCHIVOS_FUENTE)}")
    f = ImageFont.truetype(str(FUENTES / ARCHIVOS_FUENTE[nombre]), int(tam))
    try:
        ejes = f.get_variation_axes()
    except (OSError, NotImplementedError):
        return f
    valores = []
    for e in ejes:
        n = e["name"].decode() if isinstance(e["name"], bytes) else e["name"]
        valores.append(min(e["maximum"], max(e["minimum"], peso if n == "Weight" else tam)))
    f.set_variation_by_axes(valores)
    return f


_SIN_GLIFO: dict[tuple[str, str], bool] = {}


def sin_glifo(familia: str, texto: str) -> list[str]:
    """Caracteres que la tipografía no tiene (emojis, flechas…): saldrían como un rectángulo vacío."""
    fnt = fuente(familia, 40)
    vacio = bytes(fnt.getmask("\U0010FFFE"))
    faltan = []
    for c in dict.fromkeys(texto):
        if c.isspace() or unicodedata.category(c) in ("Mn", "Cf", "Me"):
            continue
        if (familia, c) not in _SIN_GLIFO:
            _SIN_GLIFO[(familia, c)] = bytes(fnt.getmask(c)) == vacio
        if _SIN_GLIFO[(familia, c)]:
            faltan.append(c)
    return faltan


# ---------- filtros ----------

def revisar_filtro(f) -> dict:
    if not isinstance(f, dict):
        raise ErrorHistorias("el filtro debe ser un nombre o un objeto")
    sobran = set(f) - CLAVES_FILTRO
    if sobran:
        raise ErrorHistorias(f"claves de filtro desconocidas: {', '.join(sorted(sobran))}")
    for k, v in f.items():
        if k == "bn":
            if not isinstance(v, bool):
                raise ErrorHistorias("`bn` debe ser true o false")
        elif k == "tinte":
            _hex(v)
        else:
            _num(v, k, *RANGOS_FILTRO[k])
    return dict(f)


def aplicar_filtro(img: Image.Image, f: dict, semilla: int = 0) -> Image.Image:
    """Look de la lámina. Todo es determinista: la misma semilla da el mismo grano."""
    img = img.convert("RGB")
    if f.get("desenfoque"):
        img = img.filter(ImageFilter.GaussianBlur(float(f["desenfoque"])))
    if f.get("bn"):
        img = ImageOps.grayscale(img).convert("RGB")
    if f.get("brillo", 1) != 1:
        img = ImageEnhance.Brightness(img).enhance(float(f["brillo"]))
    if f.get("contraste", 1) != 1:
        img = ImageEnhance.Contrast(img).enhance(float(f["contraste"]))
    if f.get("saturacion", 1) != 1 and not f.get("bn"):
        img = ImageEnhance.Color(img).enhance(float(f["saturacion"]))
    cal = float(f.get("calidez", 0))
    if cal:
        r, g, b = img.split()
        r = r.point(lambda v: max(0, min(255, int(v * (1 + 0.16 * cal)))))
        b = b.point(lambda v: max(0, min(255, int(v * (1 - 0.16 * cal)))))
        img = Image.merge("RGB", (r, g, b))
    des = float(f.get("desvanecido", 0))
    if des:  # sube los negros, como una foto revelada o un filtro «fade»
        piso = int(70 * des)
        img = img.point(lambda v: piso + int(v * (255 - piso) / 255))
    if f.get("tinte"):
        capa = Image.new("RGB", img.size, _hex(f["tinte"]))
        img = Image.blend(img, ImageChops.soft_light(img, capa), float(f.get("tinte_fuerza", 0.5)))
    vin = float(f.get("vineta", 0))
    if vin:
        m = Image.new("L", (270, 480), 0)
        ImageDraw.Draw(m).ellipse([-40, -70, 310, 550], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(70)).resize(img.size)
        img = Image.composite(img, ImageEnhance.Brightness(img).enhance(1 - 0.75 * vin), m)
    gr = float(f.get("grano", 0))
    if gr:
        ruido = Image.frombytes("L", (540, 960), random.Random(f"grano{semilla}").randbytes(540 * 960))
        ruido = ruido.filter(ImageFilter.GaussianBlur(0.7)).resize(img.size, Image.BICUBIC)
        ruido = ImageOps.autocontrast(ruido).convert("RGB")
        img = Image.blend(img, ImageChops.overlay(img, ruido), min(0.9, gr * 1.8))
    return img


def ficha_referencia(espacio: str, nombre: str) -> Path:
    return dir_espacios() / espacio / "referencias" / f"{slug(nombre)}.json"


def filtro_de(plan: dict, lamina: dict, perfil: dict) -> dict:
    """Orden: el de la lámina, el de la secuencia, el de su referencia y, al final, el del espacio."""
    estilo = plan.get("estilo") or {}
    if "filtro" in lamina:
        eleccion = lamina["filtro"]
    elif estilo.get("filtro"):
        eleccion = estilo["filtro"]
    elif estilo.get("referencia"):
        f = ficha_referencia(plan["espacio"], estilo["referencia"])
        if not f.exists():
            raise ErrorHistorias(f"no existe la referencia «{estilo['referencia']}» ({f.name}) en este espacio")
        ficha = _leer_json(f, "la ficha de referencia")
        eleccion = ficha.get("filtro") if isinstance(ficha, dict) else None
    else:
        eleccion = perfil["filtro"]
    if isinstance(eleccion, str):
        if eleccion not in FILTROS:
            raise ErrorHistorias(f"filtro desconocido: {eleccion!r}. Existen: {', '.join(FILTROS)}")
        return dict(FILTROS[eleccion])
    return revisar_filtro(eleccion)


# ---------- medir y comparar looks (referencias de Pinterest) ----------

def medir(ruta: Path) -> dict:
    img = abrir_imagen(ruta)
    img.thumbnail((540, 960))
    gris = ImageOps.grayscale(img)
    hist = gris.histogram()
    total = sum(hist)

    def percentil(p: float) -> int:
        acum = 0
        for i, n in enumerate(hist):
            acum += n
            if acum >= total * p:
                return i
        return 255

    r, g, b = ImageStat.Stat(img).mean
    sat = ImageStat.Stat(img.convert("HSV")).mean[1] / 255
    grano = ImageStat.Stat(ImageChops.difference(gris, gris.filter(ImageFilter.GaussianBlur(2)))).mean[0] / 255
    w, h = gris.size
    cw, ch = max(1, w // 6), max(1, h // 6)
    centro = ImageStat.Stat(gris.crop((w // 4, h // 4, max(w // 4 + 1, 3 * w // 4), max(h // 4 + 1, 3 * h // 4)))).mean[0]
    esquinas = [gris.crop(c) for c in ((0, 0, cw, ch), (w - cw, 0, w, ch), (0, h - ch, cw, h), (w - cw, h - ch, w, h))]
    borde = sum(ImageStat.Stat(e).mean[0] for e in esquinas) / 4
    paleta_img = img.quantize(5, method=Image.Quantize.MEDIANCUT)
    pal = paleta_img.getpalette()
    paleta = ["#%02X%02X%02X" % tuple(pal[i * 3:i * 3 + 3]) for _, i in sorted(paleta_img.getcolors(), reverse=True)]
    return {
        "luz": round(ImageStat.Stat(gris).mean[0] / 255, 3), "negros": round(percentil(0.02) / 255, 3),
        "blancos": round(percentil(0.98) / 255, 3), "saturacion": round(sat, 3),
        "calidez": round((r - b) / 255, 3), "grano": round(grano, 4),
        "vineta": round(max(0.0, (centro - borde) / 255), 3), "paleta": list(dict.fromkeys(paleta)),
    }


def filtro_desde_medidas(m: dict) -> dict:
    """Punto de partida para imitar una referencia; se afina con `comparar` y con el ojo de Emi."""
    f: dict = {}
    if m["saturacion"] < 0.04:
        f["bn"] = True
    else:
        f["saturacion"] = round(min(1.3, max(0.55, 0.62 + m["saturacion"] * 1.1)), 2)
        f["calidez"] = round(min(0.6, max(-0.4, m["calidez"] * 2.2)), 2)
    if m["negros"] > 0.05:
        f["desvanecido"] = round(min(0.6, m["negros"] * 3.2), 2)
    f["contraste"] = round(min(1.2, max(0.82, 0.78 + (m["blancos"] - m["negros"]) * 0.3)), 2)
    if m["grano"] > 0.012:
        f["grano"] = round(min(0.4, (m["grano"] - 0.008) * 9), 2)
    if m["vineta"] > 0.05:
        f["vineta"] = round(min(0.5, m["vineta"] * 1.6), 2)
    return f


def comparar(ref: Path, img: Path) -> dict:
    a, b = medir(ref), medir(img)
    return {k: round(b[k] - a[k], 4) for k in ("luz", "negros", "blancos", "saturacion", "calidez", "grano", "vineta")}


def guardar_referencia(imagen: Path, espacio: str, nombre: str) -> tuple[Path, dict]:
    """Mide la referencia y guarda su ficha. Si ya existía, conserva lo que se escribió a mano."""
    perfil_de(espacio)
    m = medir(imagen)
    destino = ficha_referencia(espacio, nombre)
    previa = _leer_json(destino, "la ficha de referencia") if destino.exists() else {}
    if not isinstance(previa, dict):
        previa = {}
    ficha = {"nombre": nombre, "fecha": dt.date.today().isoformat(), "medidas": m, "filtro": filtro_desde_medidas(m),
             "filtro_aprobado": previa.get("filtro_aprobado") is True}
    if ficha["filtro_aprobado"] and isinstance(previa.get("filtro"), dict):
        ficha["filtro"] = previa["filtro"]  # un filtro que Emi ya aprobó no se pisa al volver a medir
    for campo in ("tipografia", "composicion", "espiritu", "notas_emi"):
        ficha[campo] = previa.get(campo, "")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino, ficha


# ---------- catálogo de fotos ----------

def _calma(gris: Image.Image, caja: tuple) -> float:
    """0 = zona lisa (buena para texto), 1 = zona con mucho detalle."""
    return round(min(1.0, ImageStat.Stat(gris.crop(caja).filter(ImageFilter.FIND_EDGES)).mean[0] / 40), 2)


def catalogar(carpeta: Path) -> dict:
    """Mide cada foto y conserva lo ya descrito. La descripción la escribe quien la ve (IA con visión o Emi), una vez."""
    if not carpeta.is_dir():
        raise ErrorHistorias(f"no existe la carpeta de fotos: {carpeta}")
    archivo = carpeta / "catalogo.json"
    previo = _leer_json(archivo, "el catálogo") if archivo.exists() else {}
    if not isinstance(previo, dict):
        raise ErrorHistorias(f"{archivo} debe ser un objeto JSON; corrígelo o bórralo para empezar de nuevo")
    cat, heic, ilegibles = {}, [], []
    for f in sorted(carpeta.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() in {".heic", ".heif"}:
            heic.append(f.name)
        if f.suffix.lower() not in EXT_FOTO:
            continue
        try:
            img = abrir_imagen(f)
        except ErrorHistorias:
            ilegibles.append(f.name)
            continue
        w, h = img.size
        gris = ImageOps.grayscale(img)
        gris.thumbnail((360, 640))
        gw, gh = gris.size
        t = max(1, gh // 3)
        cajas = {n: (0, i * t, gw, max(i * t + 1, (i + 1) * t)) for i, n in enumerate(POSICIONES)}
        zonas = {n: _calma(gris, c) for n, c in cajas.items()}
        ant = previo.get(f.name) if isinstance(previo.get(f.name), dict) else {}
        cat[f.name] = {
            "ancho": w, "alto": h, "vertical": h >= w, "detalle": zonas,
            "luz": {n: round(ImageStat.Stat(gris.crop(c)).mean[0] / 255, 2) for n, c in cajas.items()},
            "zona_calma": min(zonas, key=zonas.get),
            "descripcion": ant.get("descripcion", ""), "cuando_usar": ant.get("cuando_usar", ""),
            "rostro": ant.get("rostro"), "foco": ant.get("foco", [0.5, 0.5]),
            "personas": ant.get("personas", []), "permiso": ant.get("permiso", ""),
        }
    for nombre, ant in previo.items():  # una foto que ya no está conserva su ficha: describirla costó trabajo
        if nombre not in cat and isinstance(ant, dict) and ant.get("descripcion"):
            cat[nombre] = {**ant, "ausente": True}
    archivo.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    presentes = {n: d for n, d in cat.items() if not d.get("ausente")}
    return {"fotos": len(presentes), "sin_describir": [n for n, d in presentes.items() if not d["descripcion"]],
            "heic_sin_convertir": heic, "ilegibles": ilegibles}


def cargar_catalogo(base: Path) -> dict:
    f = base / "fotos" / "catalogo.json"
    if not f.exists():
        return {}
    cat = _leer_json(f, "el catálogo de fotos")
    if not isinstance(cat, dict) or not all(isinstance(v, dict) for v in cat.values()):
        raise ErrorHistorias(f"{f} debe ser un objeto con una ficha por foto; vuelve a correr `catalogo`")
    return cat


def _foco(v, donde: str) -> list:
    if not isinstance(v, list) or len(v) != 2 or not all(_es_num(x) and 0 <= x <= 1 for x in v):
        raise ErrorHistorias(f"`foco` de {donde} debe ser [x, y] con valores de 0 a 1")
    return v


def dato_foto(catalogo: dict, nombre: str) -> dict:
    """Ficha de una foto con sus campos comprobados."""
    dato = catalogo.get(nombre)
    if not dato or not isinstance(dato.get("descripcion"), str) or not dato["descripcion"].strip():
        raise ErrorHistorias(f"{nombre} no está descrita en fotos/catalogo.json (corre `catalogo` y descríbela)")
    r = dato.get("rostro")
    if r is not None and not (isinstance(r, list) and len(r) == 4 and all(_es_num(x) for x in r)
                              and 0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1):
        raise ErrorHistorias(f"{nombre}: `rostro` debe ser [x0, y0, x1, y1] de 0 a 1, con x0 < x1 y y0 < y1 (o null si no hay)")
    if "foco" in dato:
        _foco(dato["foco"], f"{nombre} en el catálogo")
    if not isinstance(dato.get("personas", []), list) or not all(isinstance(p, str) for p in dato.get("personas", [])):
        raise ErrorHistorias(f"{nombre}: `personas` debe ser una lista de nombres")
    return dato


def encuadre(w: int, h: int, foco=(0.5, 0.5)) -> tuple[float, int, int]:
    """Escala y desplazamiento del recorte que llena 1080x1920 cuidando el punto de interés."""
    r = max(W / w, H / h)
    return r, round((round(w * r) - W) * foco[0]), round((round(h * r) - H) * foco[1])


def rostro_en_lienzo(rostro, ancho: int, alto: int, foco) -> tuple[int, int, int, int] | None:
    if not rostro:
        return None
    r, l, t = encuadre(ancho, alto, foco)
    nw, nh = ancho * r, alto * r
    return (round(rostro[0] * nw - l), round(rostro[1] * nh - t), round(rostro[2] * nw - l), round(rostro[3] * nh - t))


# ---------- texto ----------

def _texto_visible(bloque: dict, perfil: dict) -> str:
    t = str(bloque.get("texto", ""))
    return t.upper() if bloque.get("estilo") == "titular" and perfil.get("titular") == "Anton" else t


def familia_de(bloque: dict, perfil: dict) -> str:
    return ESTILOS_BLOQUE[bloque.get("estilo", "cuerpo")][0] or perfil["titular"]


def _marcadas(palabras: list[str], resaltar: list[str]) -> set[int]:
    """Índices de las palabras a resaltar. Una frase solo cuenta si sus palabras van seguidas."""
    normal = [_norm(p) for p in palabras]
    marcadas: set[int] = set()
    for frase in resaltar:
        clave = [n for n in (_norm(x) for x in frase.split()) if n]
        if not clave:
            continue
        for i in range(len(normal) - len(clave) + 1):
            if normal[i:i + len(clave)] == clave:
                marcadas.update(range(i, i + len(clave)))
    return marcadas


def capa_bloque(bloque: dict, perfil: dict, tam: int, fondo_rgb, sombra: bool) -> dict:
    """Dibuja el bloque en una capa transparente recortada a su tinta real (ya girada).

    Devuelve la capa, su tamaño de tinta (w, h) y el margen `pad` que la rodea (sitio para la sombra).
    `fondo_rgb` es el color del fondo liso, o None si va sobre una foto.
    """
    estilo = bloque.get("estilo", "cuerpo")
    _, peso, _, inter = ESTILOS_BLOQUE[estilo]
    fnt = fuente(familia_de(bloque, perfil), tam, peso)
    relleno = round(tam * 0.5) if estilo == "etiqueta" else 0
    ancho_max = int(bloque.get("ancho", ANCHO_SEG)) - 2 * relleno
    lineas: list[list[str]] = []
    for trozo in _texto_visible(bloque, perfil).split("\n"):
        actual: list[str] = []
        for palabra in trozo.split():
            if actual and fnt.getlength(" ".join(actual + [palabra])) > ancho_max:
                lineas.append(actual)
                actual = []
            actual.append(palabra)
        if actual:
            lineas.append(actual)
    if not lineas:
        raise ErrorHistorias("hay un bloque sin texto")
    anchos = [fnt.getlength(" ".join(l)) for l in lineas]
    desborda = max(anchos) > ancho_max
    asc, desc = fnt.getmetrics()
    alto_linea = round(tam * inter)
    m = tam  # margen holgado: acentos, descendentes y rasgos de la letra a mano
    ancho_capa = round(max(anchos)) + 2 * relleno
    capa = Image.new("RGBA", (ancho_capa + 2 * m, alto_linea * len(lineas) + 2 * m), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    if estilo == "etiqueta":
        caja_rgb = color(bloque.get("fondo", "blanco"), perfil)
        tinta = color(bloque.get("color", "negro" if _luz(caja_rgb) > 0.5 else "blanco"), perfil)
    else:
        auto = "blanco" if fondo_rgb is None else ("tinta" if _luz(fondo_rgb) > 0.5 else "papel")
        if fondo_rgb is not None and abs(_luz(color(auto, perfil)) - _luz(fondo_rgb)) < 0.25:
            auto = "negro" if _luz(fondo_rgb) > 0.5 else "blanco"
        tinta = color(bloque.get("color", auto), perfil)
        if fondo_rgb is not None and abs(_luz(tinta) - _luz(fondo_rgb)) < 0.12:
            raise ErrorHistorias(f"«{str(bloque.get('texto'))[:30]}» no se leería: su color casi iguala al del fondo")
    acento = color(bloque.get("color_resalte", "acento"), perfil)
    marcadas = _marcadas([p for l in lineas for p in l], bloque.get("resaltar", []))
    espacio = fnt.getlength(" ")
    alinear = bloque.get("alinear", "centro")
    n = 0
    for i, (palabras, ancho) in enumerate(zip(lineas, anchos)):
        y = m + i * alto_linea
        libre = ancho_capa - 2 * relleno - ancho
        x = m + relleno + {"izq": 0, "centro": libre / 2, "der": libre}[alinear]
        base_y = y + (alto_linea - (asc + desc)) / 2 + asc  # línea base, centrada en su renglón
        if estilo == "etiqueta":
            d.rounded_rectangle([x - relleno, y + 4, x + ancho + relleno, y + alto_linea - 4], radius=round(tam * 0.33), fill=(*caja_rgb, 255))
        for p in palabras:
            marcada = n in marcadas
            n += 1
            largo = fnt.getlength(p)
            if marcada and estilo in ("nota", "etiqueta"):  # subrayado a mano en vez de cambiar el color
                d.line([x, base_y + tam * 0.14, x + largo, base_y + tam * 0.11], fill=(*acento, 255), width=max(5, tam // 12))
            d.text((x, base_y), p, font=fnt, fill=(*(acento if marcada and estilo not in ("nota", "etiqueta") else tinta), 255), anchor="ls")
            x += largo + espacio
    giro = float(bloque.get("giro", -2.5 if estilo == "nota" else 0))
    if giro:
        capa = capa.rotate(giro, resample=Image.BICUBIC, expand=True)
    caja = capa.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
    if not caja:
        raise ErrorHistorias(f"«{str(bloque.get('texto'))[:30]}» no dibuja nada visible")
    capa = capa.crop(caja)
    w, h = capa.size
    pad = 0
    if sombra and estilo != "etiqueta":
        pad = 24
        lienzo = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        negro = Image.new("RGBA", capa.size, (0, 0, 0, 255))
        negro.putalpha(capa.getchannel("A").point(lambda v: int(v * 0.6)))
        lienzo.alpha_composite(negro, (pad, pad + 3))
        lienzo = lienzo.filter(ImageFilter.GaussianBlur(7))
        lienzo.alpha_composite(capa, (pad, pad))
        capa = lienzo
    return {"capa": capa, "w": w, "h": h, "pad": pad, "tam": tam, "desborda": desborda}


def ajustar_bloque(bloque: dict, perfil: dict, alto_max: int, fondo_rgb=(255, 255, 255), sombra: bool = False) -> dict:
    """Reduce el cuerpo de letra hasta que quepa; si ni al 60 % cabe, el texto sobra y hay que recortarlo."""
    base = int(bloque.get("tam") or ESTILOS_BLOQUE[bloque.get("estilo", "cuerpo")][2])
    tam = base
    while True:
        m = capa_bloque(bloque, perfil, tam, fondo_rgb, sombra)
        if not m["desborda"] and m["w"] <= ANCHO_SEG and m["h"] <= alto_max:
            return m
        tam = int(tam * 0.94)
        if tam < base * 0.6:
            raise ErrorHistorias(f"el texto no cabe ni reduciendo la letra: «{str(bloque.get('texto'))[:50]}». Acórtalo o quítale giro.")


# ---------- composición ----------

def _opcion(e: dict, campo: str, opciones, que: str) -> None:
    v = e.get(campo, "centro")
    if not isinstance(v, str) or v not in opciones:
        raise ErrorHistorias(f"{que} desconocida: {v!r} ({', '.join(opciones)})")


def revisar_lamina(lam) -> None:
    """Tipos y valores de una lámina. Lanza el primer problema con palabras que Emi o una IA puedan corregir."""
    if not isinstance(lam, dict):
        raise ErrorHistorias("debe ser un objeto")
    fondo = lam.get("fondo", {"tipo": "color"})
    if not isinstance(fondo, dict) or not isinstance(fondo.get("tipo"), str) or fondo["tipo"] not in ("foto", "ia", "color"):
        raise ErrorHistorias('`fondo` debe ser un objeto con `tipo`: "foto", "ia" o "color"')
    if fondo["tipo"] in ("foto", "ia") and (not isinstance(fondo.get("archivo"), str) or not fondo["archivo"].strip()):
        raise ErrorHistorias("`fondo.archivo` debe ser el nombre del archivo")
    if "foco" in fondo:
        _foco(fondo["foco"], "la lámina")
    if not isinstance(fondo.get("grano", True), bool):
        raise ErrorHistorias("`fondo.grano` debe ser true o false")
    if "filtro" in lam and not isinstance(lam["filtro"], (str, dict)):
        raise ErrorHistorias("`filtro` debe ser un nombre o un objeto")
    if "velo" in lam:
        _num(lam["velo"], "velo", 0, 0.85)
    bloques = lam.get("bloques", [])
    if not isinstance(bloques, list) or not all(isinstance(b, dict) for b in bloques):
        raise ErrorHistorias("`bloques` debe ser una lista de objetos")
    for b in bloques:
        if not isinstance(b.get("texto"), str) or not b["texto"].strip():
            raise ErrorHistorias("hay un bloque sin texto")
        if not isinstance(b.get("estilo", "cuerpo"), str) or b.get("estilo", "cuerpo") not in ESTILOS_BLOQUE:
            raise ErrorHistorias(f"estilo de texto desconocido: {b.get('estilo')!r}. Existen: {', '.join(ESTILOS_BLOQUE)}")
        if "resaltar" in b and (not isinstance(b["resaltar"], list) or not all(isinstance(x, str) for x in b["resaltar"])):
            raise ErrorHistorias('`resaltar` debe ser una lista de palabras o frases, por ejemplo ["gym"]')
        if "tam" in b:
            _num(b["tam"], "tam", 20, 400)
        if "ancho" in b:
            _num(b["ancho"], "ancho", 200, ANCHO_SEG)
        if "giro" in b:
            _num(b["giro"], "giro", -15, 15)
    st = lam.get("sticker")
    if st is not None:
        if not isinstance(st, dict) or not isinstance(st.get("tipo"), str) or st["tipo"] not in STICKERS:
            raise ErrorHistorias(f'`sticker` debe ser un objeto con `tipo`: {", ".join(STICKERS)}')
        if "texto" in st and not isinstance(st["texto"], str):
            raise ErrorHistorias("`sticker.texto` debe ser texto")
    for e in bloques + ([st] if st else []):
        _opcion(e, "pos", POSICIONES, "posición")
        _opcion(e, "alinear", ALINEACIONES, "alineación")
    if "nota_publicacion" in lam and not isinstance(lam["nota_publicacion"], str):
        raise ErrorHistorias("`nota_publicacion` debe ser texto")


def componer(lamina: dict, perfil: dict, fondo_rgb=(255, 255, 255)) -> list[dict]:
    """Dónde cae cada bloque y cada sticker. Las cajas son las de la tinta real, ya girada."""
    revisar_lamina(lamina)
    sombra = fondo_rgb is None
    alto_zona = SEG_Y1 - SEG_Y0
    hueco = 30
    elementos = [dict(b, _tipo="bloque") for b in lamina.get("bloques", [])]
    if lamina.get("sticker"):
        elementos.append(dict(lamina["sticker"], _tipo="sticker"))
    piezas, limites = [], {}
    for pos in POSICIONES:
        medidos = []
        for e in (x for x in elementos if x.get("pos", "centro") == pos):
            if e["_tipo"] == "sticker":
                medidos.append((e, None, *STICKERS[e["tipo"]]))
            else:
                faltan = sin_glifo(familia_de(e, perfil), _texto_visible(e, perfil))
                if faltan:
                    raise ErrorHistorias(f"la tipografía no tiene {' '.join(faltan)} (saldría un rectángulo vacío): quítalo o ponlo en Instagram al publicar")
                m = ajustar_bloque(e, perfil, alto_zona, fondo_rgb, sombra)
                medidos.append((e, m, m["w"], m["h"]))
        if not medidos:
            continue
        total = sum(h for *_, h in medidos) + hueco * (len(medidos) - 1)
        if total > alto_zona:
            raise ErrorHistorias(f"lo que va «{pos}» mide {total}px y la zona segura tiene {alto_zona}px: quita texto o divide la lámina")
        y = {"arriba": SEG_Y0, "centro": SEG_Y0 + (alto_zona - total) // 2, "abajo": SEG_Y1 - total}[pos]
        limites[pos] = (y, y + total)
        for e, m, w, h in medidos:
            x = {"izq": SEG_X0, "centro": (W - w) // 2, "der": SEG_X1 - w}[e.get("alinear", "centro")]
            piezas.append({"elemento": e, "medida": m, "caja": (x, y, x + w, y + h)})
            y += h + hueco
    orden = [limites[p] for p in POSICIONES if p in limites]
    for (_, fin), (ini, _) in zip(orden, orden[1:]):
        if fin + hueco > ini:
            raise ErrorHistorias("los textos de arriba, centro y abajo se enciman: quita texto o divide la lámina")
    return piezas


def _chocan(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def disposicion(plan: dict, i: int, perfil: dict, base: Path | None, catalogo: dict) -> dict:
    """Todo lo que hay que saber para dibujar la lámina i, con todas las comprobaciones. No lee píxeles.

    La usan `validar` y `render`: si pasa aquí, se dibuja.
    """
    lam = plan["laminas"][i]
    revisar_lamina(lam)
    fondo = lam.get("fondo") or {"tipo": "color"}
    tipo = fondo["tipo"]
    d = {"tipo": tipo, "ruta": None, "foco": [0.5, 0.5], "rostro": None, "avisos": [],
         "filtro": filtro_de(plan, lam, perfil), "velo": float(lam.get("velo", 0.18)), "fondo_rgb": None}
    if tipo == "color":
        d["fondo_rgb"] = color(fondo.get("color", "papel"), perfil)
    else:
        if tipo == "ia" and perfil.get("fondos_ia") is False:
            raise ErrorHistorias("este espacio no admite fondos generados con IA")
        carpeta = "fotos" if tipo == "foto" else "fondos"
        if base is not None:
            ruta = base / carpeta / fondo["archivo"]
            if not ruta.is_file() or ruta.resolve().parent != (base / carpeta).resolve():
                raise ErrorHistorias(f"no encuentro {fondo['archivo']!r} directamente en {carpeta}/ de la secuencia")
            d["ruta"] = ruta
            dato = {}
            if tipo == "foto":
                dato = dato_foto(catalogo, fondo["archivo"])
                if dato.get("personas") and not dato.get("permiso"):
                    d["avisos"].append(f"{fondo['archivo']} muestra a {', '.join(dato['personas'])}; confirma con Emi que se puede publicar")
            d["foco"] = fondo.get("foco") or dato.get("foco") or [0.5, 0.5]
            d["rostro"] = rostro_en_lienzo(dato.get("rostro"), *tam_imagen(ruta), d["foco"])
    d["piezas"] = componer(lam, perfil, d["fondo_rgb"])
    for p in d["piezas"]:
        x0, y0, x1, y1 = p["caja"]
        nombre = str(p["elemento"].get("texto") or p["elemento"].get("tipo"))[:40]
        if x0 < SEG_X0 or x1 > SEG_X1 or y0 < SEG_Y0 or y1 > SEG_Y1:
            raise ErrorHistorias(f"«{nombre}» se sale de la zona segura")
        if d["rostro"] and _chocan(p["caja"], d["rostro"]):
            raise ErrorHistorias(f"«{nombre}» cae sobre el rostro; cambia `pos`, `alinear` o el `foco`")
    return d


def dibujar_lamina(plan: dict, i: int, perfil: dict, base: Path | None, catalogo: dict, guias: bool = False, marca: str = "") -> Image.Image:
    d = disposicion(plan, i, perfil, base, catalogo)
    if d["tipo"] == "color":
        img = Image.new("RGB", (W, H), d["fondo_rgb"])
        if (plan["laminas"][i].get("fondo") or {}).get("grano", True):
            img = aplicar_filtro(img, {"grano": 0.06}, semilla=i)  # el papel liso se ve digital; un poco de fibra lo arregla
    elif d["ruta"] is None:
        raise ErrorHistorias("para dibujar una foto hace falta la carpeta de la secuencia")
    else:
        img = abrir_imagen(d["ruta"], color("papel", perfil))
        r, l, t = encuadre(*img.size, d["foco"])
        img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS).crop((l, t, l + W, t + H))
        img = aplicar_filtro(img, d["filtro"], semilla=i)
        if d["velo"]:
            img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), d["velo"])
    img = img.convert("RGBA")
    pincel = ImageDraw.Draw(img)
    for p in d["piezas"]:
        e, caja, m = p["elemento"], p["caja"], p["medida"]
        if e["_tipo"] == "bloque":
            img.alpha_composite(m["capa"], (caja[0] - m["pad"], caja[1] - m["pad"]))
        elif guias:
            pincel.rounded_rectangle(caja, radius=28, outline=(255, 60, 120, 255), width=5)
            pincel.text((caja[0] + 22, caja[1] + 18), f"sticker: {e['tipo']}", font=fuente("Inter", 34, 600), fill=(255, 60, 120, 255))
    if guias:
        pincel.rectangle([SEG_X0, SEG_Y0, SEG_X1, SEG_Y1], outline=(0, 220, 255, 255), width=3)
        if d["rostro"]:
            pincel.rectangle(d["rostro"], outline=(255, 220, 0, 255), width=4)
    if marca:
        pincel.text((SEG_X0, 150), marca, font=fuente("Inter", 44, 800), fill=(255, 60, 120, 255))
    return img.convert("RGB")


# ---------- plan ----------

def cargar_plan(ruta: Path) -> dict:
    plan = _leer_json(ruta, "el plan")
    if not isinstance(plan, dict):
        raise ErrorHistorias("el plan debe ser un objeto JSON")
    return plan


def _contiene(texto: str, frase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(frase) + r"(?!\w)", texto) is not None


def validar(plan: dict, base: Path | None = None, final: bool = True) -> tuple[list[str], list[str]]:
    """Errores (impiden dibujar) y avisos (decide Emi). Sin `base` no se comprueban los archivos de fondo."""
    errores, avisos = [], []
    try:
        perfil = perfil_de(plan.get("espacio"))
    except ErrorHistorias as exc:
        return [str(exc)], []
    if base is not None and base.resolve().parent.parent == dir_producciones().resolve() and base.resolve().parent.name != plan["espacio"]:
        errores.append(f"la secuencia está en la carpeta de «{base.resolve().parent.name}» y el plan dice «{plan['espacio']}»: los espacios no se mezclan")
    if not isinstance(plan.get("titulo"), str) or not plan["titulo"].strip():
        errores.append("falta `titulo`")
    brief = plan.get("brief")
    if not isinstance(brief, dict):
        brief = {}
        errores.append("falta `brief` (objeto con objetivo, publico, accion y respuestas_emi)")
    else:
        for campo, que in (("objetivo", "para qué es la secuencia"), ("publico", "a quién le habla"),
                           ("accion", "qué debe hacer quien la vea"), ("respuestas_emi", "lo que Emi contestó, con sus palabras")):
            if not isinstance(brief.get(campo), str) or len(brief[campo].strip()) < 4:
                errores.append(f"falta `brief.{campo}` ({que}): se le pregunta a Emi, no se inventa")
    if final and plan.get("guion_aprobado") is not True:
        errores.append("`guion_aprobado` no es true: Emi aprueba el guion antes del render final (usa --borrador para verlo antes)")
    estilo = plan.get("estilo", {})
    if (not isinstance(estilo, dict) or not isinstance(estilo.get("filtro", ""), (str, dict))
            or not isinstance(estilo.get("referencia", ""), str)):
        return errores + ["`estilo` debe ser un objeto; `estilo.filtro` un nombre u objeto y `estilo.referencia` un nombre"], avisos
    laminas = plan.get("laminas")
    if not isinstance(laminas, list) or not 1 <= len(laminas) <= 12:
        return errores + ["`laminas` debe tener entre 1 y 12 láminas"], avisos
    try:
        catalogo = cargar_catalogo(base) if base is not None else {}
    except ErrorHistorias as exc:
        return errores + [str(exc)], avisos
    lim_palabras = int(perfil.get("max_palabras", MAX_PALABRAS))
    prohibidas = [" ".join(str(p).lower().split()) for p in perfil.get("frases_prohibidas", [])]
    for i, lam in enumerate(laminas, 1):
        try:
            d = disposicion(plan, i - 1, perfil, base, catalogo)
        except ErrorHistorias as exc:
            errores.append(f"lámina {i}: {exc}")
            continue
        avisos += [f"lámina {i}: {a}" for a in d["avisos"]]
        if not d["piezas"] and d["tipo"] != "foto":
            errores.append(f"lámina {i}: vacía (sin texto, sin sticker y sin foto)")
        textos = " ".join(b["texto"] for b in lam.get("bloques", []))
        n = len(textos.split())
        if n > lim_palabras:
            errores.append(f"lámina {i}: {n} palabras (máximo {lim_palabras}); una historia se lee en 3 segundos")
        bajo = " ".join(textos.lower().split())
        avisos += [f"lámina {i}: «{f}» suena a texto de máquina; dilo como lo diría Emi" for f in FRASES_IA if _contiene(bajo, f)]
        errores += [f"lámina {i}: «{f}» está prohibida en este espacio" for f in prohibidas if f and _contiene(bajo, f)]
        if "—" in textos:
            avisos.append(f"lámina {i}: lleva raya larga (—); en una historia escrita a mano casi nadie la usa")
    if final and len(laminas) > 1 and isinstance(laminas[-1], dict) and not (laminas[-1].get("sticker") or brief.get("sin_cierre")):
        avisos.append("la última lámina no reserva sticker ni cierre: ¿cómo responde la gente? (o marca `brief.sin_cierre`)")
    return errores, avisos


# ---------- red y Kie ----------

class _SinSaltoDeHost(urllib.request.HTTPRedirectHandler):
    """Una redirección a otro servidor no se sigue: la clave no debe viajar a un host que no elegimos."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        nuevo = urllib.parse.urlparse(newurl)
        if nuevo.scheme != "https" or nuevo.hostname != urllib.parse.urlparse(req.full_url).hostname:
            raise urllib.error.HTTPError(req.full_url, code, f"redirección a otro host rechazada ({nuevo.hostname})", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_ABRIR = urllib.request.build_opener(_SinSaltoDeHost)


def _pedir(url: str, *, metodo="GET", cabeceras=None, cuerpo=None, espera=120) -> bytes:
    if urllib.parse.urlparse(url).scheme != "https":
        raise ErrorHistorias("solo se permiten URLs https")
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method=metodo, headers=cabeceras or {})
    if datos is not None:
        req.add_header("Content-Type", "application/json")
    host = urllib.parse.urlparse(url).hostname
    try:
        with _ABRIR.open(req, timeout=espera) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        raise ErrorHistorias(f"{host} respondió HTTP {exc.code}: {str(exc.reason)[:160]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        aviso = " No se sabe si el proveedor cobró: revisa su historial antes de reintentar." if metodo == "POST" else ""
        raise ErrorHistorias(f"sin respuesta de {host}: {exc}.{aviso}") from exc


def _json(crudo: bytes, quien: str) -> dict:
    try:
        d = json.loads(crudo)
    except ValueError as exc:
        raise ErrorHistorias(f"{quien} devolvió algo que no es JSON") from exc
    if not isinstance(d, dict):
        raise ErrorHistorias(f"{quien} devolvió un JSON inesperado")
    return d


def _datos(r: dict) -> dict:
    return r["data"] if isinstance(r.get("data"), dict) else {}


def _kie() -> dict:
    return {"Authorization": "Bearer " + (os.environ.get("KIE_API_KEY") or MARCADOR)}


def saldo_kie() -> dict:
    """Saldo real. Sin conexión se informa como tal; nunca se estima."""
    try:
        r = _json(_pedir(f"{KIE}/chat/credit", cabeceras=_kie(), espera=30), "Kie")
        if r.get("code") != 200 or not _es_num(r.get("data")):
            return {"kie_error": f"Kie respondió {r.get('code')}: {str(r.get('msg'))[:90]}"}
        return {"kie_creditos": r["data"]}
    except ErrorHistorias as exc:
        return {"kie_error": str(exc)[:140]}


def prompt_fondo(descripcion: str, estilo: str) -> str:
    if estilo not in ESTILOS_FONDO:
        raise ErrorHistorias(f"estilo de fondo desconocido: {estilo!r}. Existen: {', '.join(ESTILOS_FONDO)}")
    descripcion = " ".join(descripcion.split())
    if len(descripcion) < 12:
        raise ErrorHistorias("el prompt del fondo está vacío o es demasiado corto")
    return f"{descripcion}. {ESTILOS_FONDO[estilo]}. {SIN_TEXTO}"


def generar_fondo(prompt: str, salida: Path, estado: Path, modelo="nano-banana-2-lite", espera=300) -> None:
    if modelo not in MODELOS_KIE:
        raise ErrorHistorias(f"modelo {modelo!r} sin esquema comprobado; añade su contrato antes de usarlo")
    firma = hashlib.sha256(json.dumps([prompt, modelo]).encode()).hexdigest()[:16]
    if estado.exists():
        est = _leer_json(estado, "el estado de la tarea")
        if not isinstance(est, dict) or not isinstance(est.get("taskId"), str):
            raise ErrorHistorias(f"{estado} no es un estado de tarea válido; usa un archivo de estado nuevo")
        if est.get("firma") != firma:
            raise ErrorHistorias(f"{estado} pertenece a otro prompt o modelo; usa un archivo de estado nuevo")
        if est.get("fallo"):
            raise ErrorHistorias(f"esa tarea ya falló ({est['fallo']}); cambia el prompt y usa un estado nuevo")
    else:
        estado.parent.mkdir(parents=True, exist_ok=True)
        r = _json(_pedir(f"{KIE}/jobs/createTask", metodo="POST", cabeceras=_kie(),
                         cuerpo={"model": modelo, "input": {"prompt": prompt, "aspect_ratio": "9:16", **MODELOS_KIE[modelo]}}), "Kie")
        tid = _datos(r).get("taskId")
        if not isinstance(tid, str) or not tid:
            raise ErrorHistorias(f"Kie no devolvió taskId: {str(r)[:200]}")
        est = {"taskId": tid, "modelo": modelo, "firma": firma}
        estado.write_text(json.dumps(est), encoding="utf-8")
    limite = time.time() + espera
    while time.time() < limite:
        d = _datos(_json(_pedir(f"{KIE}/jobs/recordInfo?taskId={urllib.parse.quote(est['taskId'])}", cabeceras=_kie()), "Kie"))
        st = str(d.get("state", "")).lower()
        if st == "success":
            rj = d.get("resultJson")
            try:
                rj = json.loads(rj) if isinstance(rj, str) else rj
            except ValueError:
                rj = None
            urls = rj.get("resultUrls") if isinstance(rj, dict) else None
            if not isinstance(urls, list) or not urls or not isinstance(urls[0], str):
                raise ErrorHistorias("Kie terminó sin URL de resultado")
            if urllib.parse.urlparse(urls[0]).hostname not in HOSTS_DESCARGA:
                raise ErrorHistorias(f"host de descarga no autorizado: {urllib.parse.urlparse(urls[0]).hostname}")
            crudo = _pedir(urls[0])  # sin cabecera de autorización: la clave no sale de Kie
            try:
                with Image.open(io.BytesIO(crudo)) as prueba:
                    prueba.verify()
            except Exception as exc:  # noqa: BLE001 - cualquier fallo de Pillow significa que no es una imagen
                raise ErrorHistorias("lo que devolvió Kie no es una imagen; no se guardó nada") from exc
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(crudo)
            return
        if st in {"fail", "failed", "error"}:
            est["fallo"] = str(d.get("failMsg"))[:200]
            estado.write_text(json.dumps(est), encoding="utf-8")
            raise ErrorHistorias(f"Kie falló: {est['fallo']}")
        time.sleep(4)
    raise ErrorHistorias(f"Kie no terminó a tiempo; repite el mismo comando con {estado} para reconsultar sin crear otra tarea")


# ---------- proyecto, render y cierre ----------

PLAN_EJEMPLO = {
    "titulo": "", "espacio": "", "fecha": "",
    "brief": {"objetivo": "", "publico": "", "accion": "", "respuestas_emi": ""},
    "estructura": "", "estilo": {"filtro": "", "referencia": ""},
    "guion_aprobado": False,
    "laminas": [
        {"fondo": {"tipo": "color", "color": "papel"},
         "bloques": [{"texto": "Escribe aquí el gancho", "estilo": "titular", "pos": "centro", "resaltar": ["gancho"]},
                     {"texto": "una nota como la pondrías tú", "estilo": "nota", "pos": "abajo"}]},
        {"fondo": {"tipo": "color", "color": "tinta"},
         "bloques": [{"texto": "El cierre: qué quieres que hagan", "estilo": "cuerpo", "pos": "centro"}],
         "sticker": {"tipo": "pregunta", "pos": "abajo"}},
    ],
}


def crear_proyecto(destino: Path, espacio: str) -> Path:
    perfil = perfil_de(espacio)
    destino = destino.resolve()
    if destino.parent != (dir_producciones() / espacio).resolve():
        raise ErrorHistorias(f"las secuencias de «{espacio}» van en {dir_producciones() / espacio}/<tema>/ (privadas, no se suben a GitHub)")
    if destino.exists():
        raise ErrorHistorias(f"{destino} ya existe")
    for sub in ("fotos", "fondos", "prompts", "estados", "out"):
        (destino / sub).mkdir(parents=True)
    plan = json.loads(json.dumps(PLAN_EJEMPLO))
    plan.update(espacio=espacio, fecha=dt.date.today().isoformat(), titulo=destino.name.replace("-", " "))
    plan["estilo"]["filtro"] = perfil["filtro"]
    (destino / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destino / "estados" / "saldo_inicial.json").write_text(json.dumps(saldo_kie()), encoding="utf-8")
    return destino


def hoja(imagenes: list[Image.Image]) -> Image.Image:
    """Todas las láminas en una sola imagen, con la zona segura marcada, para revisar de un vistazo."""
    aw, ah, m = 360, 640, 16
    cols = min(5, len(imagenes))
    filas = -(-len(imagenes) // cols)
    lienzo = Image.new("RGB", (m + cols * (aw + m), m + filas * (ah + m)), (28, 28, 30))
    for n, img in enumerate(imagenes):
        lienzo.paste(img.resize((aw, ah), Image.LANCZOS), (m + (n % cols) * (aw + m), m + (n // cols) * (ah + m)))
    return lienzo


def render(base: Path, borrador: bool = False) -> dict:
    plan = cargar_plan(base / "plan.json")
    errores, avisos = validar(plan, base, final=not borrador)
    if errores:
        raise ErrorHistorias("el plan no pasa la validación:\n  - " + "\n  - ".join(errores))
    perfil = perfil_de(plan["espacio"])
    catalogo = cargar_catalogo(base)
    marca = "BORRADOR" if borrador else ""
    total = len(plan["laminas"])
    # Primero se dibuja todo en memoria: si algo falla, lo que había en out/ queda intacto.
    limpias = [dibujar_lamina(plan, i, perfil, base, catalogo, marca=marca) for i in range(total)]
    guias = [dibujar_lamina(plan, i, perfil, base, catalogo, guias=True, marca=marca) for i in range(total)]
    out = base / "out"
    out.mkdir(exist_ok=True)
    for viejo in out.glob("[0-9][0-9].png"):
        viejo.unlink()
    for i, img in enumerate(limpias, 1):
        img.save(out / f"{i:02d}.png", optimize=True)
    hoja(guias).save(out / "hoja.png", optimize=True)
    pie = [f"# {plan['titulo']}", "", f"Espacio: {perfil['nombre']} · {plan.get('fecha', '')} · {total} láminas" + (" · BORRADOR" if borrador else ""),
           "", "## Para publicar", ""]
    for i, lam in enumerate(plan["laminas"], 1):
        st = lam.get("sticker")
        if st:
            pie.append(f"- Lámina {i}: añadir en Instagram el sticker de **{st['tipo']}**" + (f" con «{st['texto']}»" if st.get("texto") else "")
                       + f", {st.get('pos', 'centro')}.")
        if lam.get("nota_publicacion"):
            pie.append(f"- Lámina {i}: {lam['nota_publicacion']}")
    pie += ["", "## Texto de cada lámina (para copiar)", ""]
    for i, lam in enumerate(plan["laminas"], 1):
        pie.append(f"{i}. " + " / ".join(" ".join(b["texto"].split()) for b in lam.get("bloques", [])))
    if avisos:
        pie += ["", "## Avisos para Emi", ""] + [f"- {a}" for a in avisos]
    (out / "LEEME.md").write_text("\n".join(pie) + "\n", encoding="utf-8")
    return {"laminas": total, "salida": str(out), "avisos": avisos, "borrador": borrador}


def cierre(base: Path) -> str:
    ini_f = base / "estados" / "saldo_inicial.json"
    ini = _leer_json(ini_f, "el saldo inicial") if ini_f.exists() else {}
    ahora = saldo_kie()
    if "kie_creditos" not in ahora:
        return f"Proveedor | Gastado | Queda\nKie       | sin dato | no conectado ({ahora.get('kie_error')})"
    gastado = (f"{ini['kie_creditos'] - ahora['kie_creditos']:g} créditos" if isinstance(ini, dict) and _es_num(ini.get("kie_creditos"))
               else "sin saldo inicial")
    return (f"Proveedor | Gastado | Queda\nKie       | {gastado} | {ahora['kie_creditos']:g} créditos\n"
            "(Gastado = saldo al crear la secuencia menos saldo actual; incluye lo que Vox haya gastado entretanto.)")


# ---------- CLI ----------

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("espacios")
    a = s.add_parser("aprendizajes"); a.add_argument("--espacio", default="")
    a = s.add_parser("aprender"); a.add_argument("texto"); a.add_argument("--espacio", default="")
    a = s.add_parser("nicho"); a.add_argument("--espacio", required=True)
    a = s.add_parser("vox"); a.add_argument("--ruta", default="")
    a = s.add_parser("proyecto"); a.add_argument("dir", type=Path); a.add_argument("--espacio", required=True)
    a = s.add_parser("catalogo"); a.add_argument("dir", type=Path)
    a = s.add_parser("medir"); a.add_argument("imagen", type=Path)
    a = s.add_parser("referencia"); a.add_argument("imagen", type=Path); a.add_argument("--espacio", required=True); a.add_argument("--nombre", required=True)
    a = s.add_parser("comparar"); a.add_argument("referencia", type=Path); a.add_argument("imagen", type=Path)
    a = s.add_parser("validar"); a.add_argument("plan", type=Path); a.add_argument("--borrador", action="store_true")
    a = s.add_parser("fondo")
    a.add_argument("--espacio", required=True); a.add_argument("--prompt-file", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True); a.add_argument("--estado", type=Path, required=True)
    a.add_argument("--estilo", choices=sorted(ESTILOS_FONDO)); a.add_argument("--modelo", choices=sorted(MODELOS_KIE), default="nano-banana-2-lite")
    a.add_argument("--execute", action="store_true")
    a = s.add_parser("render"); a.add_argument("dir", type=Path); a.add_argument("--borrador", action="store_true")
    s.add_parser("saldo")
    a = s.add_parser("cierre"); a.add_argument("dir", type=Path)
    return p


def _ejecutar(args) -> None:
    if args.cmd == "espacios":
        for n, pf in perfiles().items():
            print(f"{n:10} {pf['nombre']} · {pf.get('estado', '')} · @{pf.get('handle') or 'sin definir'}")
    elif args.cmd == "aprendizajes":
        print(leer_aprendizajes(args.espacio))
    elif args.cmd == "aprender":
        print(f"Guardado en {aprender(args.texto, args.espacio)}")
    elif args.cmd == "nicho":
        texto, dias = estado_nicho(args.espacio)
        print(texto or "Este espacio aún no tiene NICHO.md.")
        if dias is None:
            print("\nAVISO: el nicho no tiene una fecha de revisión válida. Revísalo con Emi antes de proponer temas.")
        elif dias > 7:
            print(f"\nAVISO: el nicho lleva {dias} días sin revisarse (toca cada semana).")
    elif args.cmd == "vox":
        avisos = sincronizar_vox(args.ruta)
        print("Vox leído. " + ("Diferencias a consultar con Emi:\n- " + "\n- ".join(avisos) if avisos else "Sin diferencias de marca."))
    elif args.cmd == "proyecto":
        d = crear_proyecto(args.dir, args.espacio)
        print(f"Secuencia creada en {d}\n\n--- Aprendizajes vigentes ---\n{leer_aprendizajes(args.espacio)}")
    elif args.cmd == "catalogo":
        print(json.dumps(catalogar(args.dir), ensure_ascii=False, indent=2))
    elif args.cmd == "medir":
        print(json.dumps(medir(args.imagen), ensure_ascii=False, indent=2))
    elif args.cmd == "referencia":
        destino, ficha = guardar_referencia(args.imagen, args.espacio, args.nombre)
        print(f"Referencia guardada en {destino}. Completa tipografía, composición y espíritu mirando la imagen.\n"
              f'En el plan: "estilo": {{"referencia": "{destino.stem}"}}\n' + json.dumps(ficha["filtro"], ensure_ascii=False))
    elif args.cmd == "comparar":
        print(json.dumps(comparar(args.referencia, args.imagen), ensure_ascii=False, indent=2))
    elif args.cmd == "validar":
        errores, avisos = validar(cargar_plan(args.plan), args.plan.parent, final=not args.borrador)
        for a_ in avisos:
            print("AVISO:", a_)
        if errores:
            raise ErrorHistorias("\n  - ".join(["el plan no pasa:"] + errores))
        print("Plan válido.")
    elif args.cmd == "fondo":
        perfil = perfil_de(args.espacio)
        if perfil.get("fondos_ia") is False:
            raise ErrorHistorias(f"el espacio «{args.espacio}» no admite fondos generados con IA")
        estilo = args.estilo or (perfil.get("estilo_imagen") if perfil.get("estilo_imagen") in ESTILOS_FONDO else "foto")
        try:
            descripcion = args.prompt_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise ErrorHistorias(f"no se puede leer {args.prompt_file}: {exc}") from exc
        prompt = prompt_fondo(descripcion, estilo)
        if not args.execute:
            print(f"SIMULACIÓN (sin gasto). Con --execute se pediría a Kie ({args.modelo}):\n{prompt}")
        else:
            generar_fondo(prompt, args.out, args.estado, args.modelo)
            print(f"Fondo guardado en {args.out}")
    elif args.cmd == "render":
        print(json.dumps(render(args.dir, args.borrador), ensure_ascii=False, indent=2))
    elif args.cmd == "saldo":
        print(json.dumps(saldo_kie(), ensure_ascii=False))
    elif args.cmd == "cierre":
        print(cierre(args.dir))


def main(argv=None) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(errors="replace")  # una consola sin UTF-8 no debe tumbar el comando
    args = _parser().parse_args(argv)
    try:
        _ejecutar(args)
    except ErrorHistorias as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        # Red de seguridad: un dato mal formado no debe terminar en una traza ilegible.
        print(f"ERROR inesperado ({type(exc).__name__}): {exc}. Revisa el archivo de entrada; si persiste, es un fallo del motor.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
