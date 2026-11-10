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
  validar PLAN                              revisa el plan sin dibujar nada
  fondo --prompt-file F --out O --estado S  fondo con Kie (sin --execute no gasta)
  render DIR [--borrador]                   dibuja las láminas, la hoja de revisión y el pie de entrega
  saldo | cierre DIR                        créditos de Kie: lo que queda y lo gastado en la secuencia

La clave de Kie es la misma de Vox Studio: variable KIE_API_KEY o, en la nube, la que inyecta el proxy.
Nunca se escribe en archivos.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
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
ESTILOS_BLOQUE = {
    #            fuente      peso  tam  interlinea
    "titular":  (None,       700,  118, 1.04),
    "cuerpo":   ("Inter",    600,   54, 1.28),
    "serif":    ("Gelasio",  500,   64, 1.22),
    "nota":     ("Caveat",   600,   82, 1.05),
    "etiqueta": ("Inter",    700,   54, 1.50),
}
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
CLAVES_FILTRO = {"calidez", "desvanecido", "contraste", "saturacion", "brillo", "grano", "vineta", "bn", "desenfoque", "tinte", "tinte_fuerza"}
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


# ---------- espacios y memoria ----------

def dir_espacios() -> Path:
    return Path(os.environ["HISTORIAS_ESPACIOS"]) if os.environ.get("HISTORIAS_ESPACIOS") else RAIZ / "espacios"


def perfiles() -> dict:
    out = {f.parent.name: json.loads(f.read_text(encoding="utf-8")) for f in sorted(dir_espacios().glob("*/perfil.json"))}
    if not out:
        raise ErrorHistorias(f"no hay espacios en {dir_espacios()}")
    return out


def perfil_de(espacio: str) -> dict:
    todos = perfiles()
    if espacio not in todos:
        raise ErrorHistorias(f"espacio desconocido: {espacio!r}. Existen: {', '.join(todos)}")
    return todos[espacio]


def archivo_aprendizajes(espacio: str = "") -> Path:
    if espacio:
        perfil_de(espacio)
        return dir_espacios() / espacio / "aprendizajes.md"
    return dir_espacios() / "APRENDIZAJES.md"


def leer_aprendizajes(espacio: str = "") -> str:
    partes = []
    archivos = [archivo_aprendizajes("")]
    if espacio:
        archivos += [archivo_aprendizajes(espacio), dir_espacios() / espacio / "desde-vox.md"]
    for f in archivos:
        if f.exists():
            partes.append(f.read_text(encoding="utf-8").strip())
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
    """Devuelve el texto del nicho y los días desde su última revisión (None si nunca se revisó)."""
    f = dir_espacios() / espacio / "NICHO.md"
    perfil_de(espacio)
    if not f.exists():
        return "", None
    texto = f.read_text(encoding="utf-8")
    m = re.search(r"Revisado:\s*(\d{4}-\d{2}-\d{2})", texto)
    if not m:
        return texto, None
    return texto, ((hoy or dt.date.today()) - dt.date.fromisoformat(m.group(1))).days


# ---------- puente con Vox Studio (solo lectura) ----------

def ruta_vox(ruta: str = "") -> Path:
    candidatas = [ruta, os.environ.get("VOX_REPO", ""), str(RAIZ.parent / "VIDEOS-IA-SKILL-MILLA")]
    for c in candidatas:
        if c and (Path(c) / "espacios").is_dir():
            return Path(c)
    raise ErrorHistorias("no encuentro el repositorio de Vox Studio: pasa --ruta o define VOX_REPO "
                         "(git clone https://github.com/lianfixx/VIDEOS-IA-SKILL-MILLA)")


def sincronizar_vox(ruta: str = "") -> list[str]:
    """Copia de Vox lo que sirve a las historias (lecciones y marca) sin tocar sus instrucciones ni las nuestras.

    Deja `espacios/DESDE-VOX.md` y `espacios/<e>/desde-vox.md`, y avisa si los colores o el tono difieren.
    """
    vox = ruta_vox(ruta) / "espacios"
    hoy = dt.date.today().isoformat()
    avisos = []
    cab = (f"# Traído de Vox Studio\n\nCopia de solo lectura, actualizada el {hoy} con `historias.py vox`. "
           "No editar aquí: lo de video se corrige en Vox; lo propio de historias va en `aprendizajes.md`.\n\n")
    general = vox / "APRENDIZAJES.md"
    if general.exists():
        (dir_espacios() / "DESDE-VOX.md").write_text(cab + _solo_lecciones(general.read_text(encoding="utf-8")), encoding="utf-8")
    for nombre, mio in perfiles().items():
        suyo_f = vox / nombre / "perfil.json"
        if not suyo_f.exists():
            avisos.append(f"{nombre}: Vox no tiene este espacio")
            continue
        suyo = json.loads(suyo_f.read_text(encoding="utf-8"))
        for k in ("colores", "titular", "tono", "estilo_imagen"):
            if suyo.get(k) != mio.get(k):
                avisos.append(f"{nombre}: «{k}» difiere de Vox ({json.dumps(suyo.get(k), ensure_ascii=False)[:90]})")
        partes = [cab]
        for f in (vox / nombre / "aprendizajes.md", vox / nombre / "MARCA.md"):
            if f.exists():
                partes.append(f"## {f.name}\n\n" + _solo_lecciones(f.read_text(encoding="utf-8")) + "\n")
        (dir_espacios() / nombre / "desde-vox.md").write_text("\n".join(partes), encoding="utf-8")
    for nombre in sorted(p.parent.name for p in vox.glob("*/perfil.json")):
        if nombre not in perfiles():
            avisos.append(f"{nombre}: existe en Vox y no aquí; créalo con Emi si también quiere historias")
    return avisos


def _solo_lecciones(texto: str) -> str:
    return "\n".join(l for l in texto.splitlines() if not l.startswith("# ")).strip() + "\n"


# ---------- tipografía ----------

def fuente(nombre: str, tam: int, peso: int = 600) -> ImageFont.FreeTypeFont:
    archivos = {"Anton": "Anton-Regular.ttf", "Gelasio": "Gelasio.ttf", "Inter": "Inter.ttf", "Caveat": "Caveat.ttf"}
    if nombre not in archivos:
        raise ErrorHistorias(f"tipografía sin archivo: {nombre!r}. Disponibles: {', '.join(archivos)}")
    f = ImageFont.truetype(str(FUENTES / archivos[nombre]), int(tam))
    try:
        ejes = f.get_variation_axes()
    except OSError:
        return f
    valores = []
    for e in ejes:
        n = e["name"].decode() if isinstance(e["name"], bytes) else e["name"]
        v = peso if n == "Weight" else min(e["maximum"], max(e["minimum"], tam))
        valores.append(min(e["maximum"], max(e["minimum"], v)))
    f.set_variation_by_axes(valores)
    return f


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", c):
        raise ErrorHistorias(f"color inválido: #{c}")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def color(nombre: str, perfil: dict) -> tuple[int, int, int]:
    fijos = {"blanco": "#FFFFFF", "negro": "#111111"}
    if nombre in perfil["colores"]:
        return _hex(perfil["colores"][nombre])
    return _hex(fijos.get(nombre, nombre))


def _norm(p: str) -> str:
    p = unicodedata.normalize("NFD", p.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in p if unicodedata.category(c) != "Mn" or c == "\u0303"))


# ---------- filtros ----------

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
        r = r.point(lambda v: min(255, int(v * (1 + 0.16 * cal))))
        b = b.point(lambda v: min(255, int(v * (1 - 0.16 * cal))))
        img = Image.merge("RGB", (r, g, b))
    des = float(f.get("desvanecido", 0))
    if des:  # sube los negros, como una foto revelada o un filtro «fade»
        piso = int(70 * des)
        img = img.point(lambda v: piso + int(v * (255 - piso) / 255))
    if f.get("tinte"):
        capa = Image.new("RGB", img.size, _hex(f["tinte"]))
        img = Image.blend(img, ImageChops.soft_light(img, capa), min(1.0, float(f.get("tinte_fuerza", 0.5))))
    vin = float(f.get("vineta", 0))
    if vin:
        m = Image.new("L", (270, 480), 0)
        ImageDraw.Draw(m).ellipse([-40, -70, 310, 550], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(70)).resize(img.size)
        oscuro = ImageEnhance.Brightness(img).enhance(1 - 0.75 * vin)
        img = Image.composite(img, oscuro, m)
    gr = float(f.get("grano", 0))
    if gr:
        ruido = Image.frombytes("L", (540, 960), random.Random(f"grano{semilla}").randbytes(540 * 960))
        ruido = ruido.filter(ImageFilter.GaussianBlur(0.7)).resize(img.size, Image.BICUBIC)
        ruido = ImageOps.autocontrast(ruido).convert("RGB")
        img = Image.blend(img, ImageChops.overlay(img, ruido), min(0.9, gr * 1.8))
    return img


def filtro_de(plan: dict, lamina: dict, perfil: dict) -> dict:
    eleccion = lamina.get("filtro", (plan.get("estilo") or {}).get("filtro", perfil.get("filtro", "natural")))
    if isinstance(eleccion, str):
        if eleccion not in FILTROS:
            raise ErrorHistorias(f"filtro desconocido: {eleccion!r}. Existen: {', '.join(FILTROS)}")
        return dict(FILTROS[eleccion])
    sobran = set(eleccion) - CLAVES_FILTRO
    if sobran:
        raise ErrorHistorias(f"claves de filtro desconocidas: {', '.join(sorted(sobran))}")
    return dict(eleccion)


# ---------- medir y comparar looks (referencias de Pinterest) ----------

def medir(ruta: Path) -> dict:
    img = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
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
    suave = gris.filter(ImageFilter.GaussianBlur(2))
    grano = ImageStat.Stat(ImageChops.difference(gris, suave)).mean[0] / 255
    w, h = gris.size
    centro = ImageStat.Stat(gris.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4))).mean[0]
    esquinas = [gris.crop(c) for c in ((0, 0, w // 6, h // 6), (w - w // 6, 0, w, h // 6), (0, h - h // 6, w // 6, h), (w - w // 6, h - h // 6, w, h))]
    borde = sum(ImageStat.Stat(e).mean[0] for e in esquinas) / 4
    paleta_img = img.quantize(5, method=Image.Quantize.MEDIANCUT)
    pal = paleta_img.getpalette()[:15]
    orden = sorted(paleta_img.getcolors(), reverse=True)
    paleta = ["#%02X%02X%02X" % tuple(pal[i * 3:i * 3 + 3]) for _, i in orden]
    return {
        "luz": round(ImageStat.Stat(gris).mean[0] / 255, 3), "negros": round(percentil(0.02) / 255, 3),
        "blancos": round(percentil(0.98) / 255, 3), "saturacion": round(sat, 3),
        "calidez": round((r - b) / 255, 3), "grano": round(grano, 4),
        "vineta": round(max(0.0, (centro - borde) / 255), 3), "paleta": paleta,
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
    rango = m["blancos"] - m["negros"]
    f["contraste"] = round(min(1.2, max(0.82, 0.78 + rango * 0.3)), 2)
    if m["grano"] > 0.012:
        f["grano"] = round(min(0.4, (m["grano"] - 0.008) * 9), 2)
    if m["vineta"] > 0.05:
        f["vineta"] = round(min(0.5, m["vineta"] * 1.6), 2)
    return f


def comparar(ref: Path, img: Path) -> dict:
    a, b = medir(ref), medir(img)
    return {k: round(b[k] - a[k], 4) for k in ("luz", "negros", "blancos", "saturacion", "calidez", "grano", "vineta")}


# ---------- catálogo de fotos ----------

def _calma(gris: Image.Image, caja: tuple) -> float:
    """0 = zona lisa (buena para texto), 1 = zona con mucho detalle."""
    zona = gris.crop(caja)
    return round(min(1.0, ImageStat.Stat(zona.filter(ImageFilter.FIND_EDGES)).mean[0] / 40), 2)


def catalogar(carpeta: Path) -> dict:
    """Mide cada foto y conserva lo ya descrito. La descripción la escribe quien la ve (IA con visión o Emi), una vez."""
    if not carpeta.is_dir():
        raise ErrorHistorias(f"no existe la carpeta de fotos: {carpeta}")
    archivo = carpeta / "catalogo.json"
    previo = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    cat, ignoradas = {}, []
    for f in sorted(carpeta.iterdir()):
        if f.suffix.lower() in {".heic", ".heif"}:
            ignoradas.append(f.name)
        if f.suffix.lower() not in EXT_FOTO:
            continue
        with Image.open(f) as cruda:
            img = ImageOps.exif_transpose(cruda).convert("RGB")
        w, h = img.size
        gris = ImageOps.grayscale(img)
        gris.thumbnail((360, 640))
        gw, gh = gris.size
        tercio = gh // 3
        zonas = {n: _calma(gris, (0, i * tercio, gw, (i + 1) * tercio)) for i, n in enumerate(("arriba", "centro", "abajo"))}
        luz = {n: round(ImageStat.Stat(gris.crop((0, i * tercio, gw, (i + 1) * tercio))).mean[0] / 255, 2)
               for i, n in enumerate(("arriba", "centro", "abajo"))}
        ant = previo.get(f.name, {})
        cat[f.name] = {
            "ancho": w, "alto": h, "vertical": h >= w,
            "detalle": zonas, "luz": luz, "zona_calma": min(zonas, key=zonas.get),
            "descripcion": ant.get("descripcion", ""), "cuando_usar": ant.get("cuando_usar", ""),
            "rostro": ant.get("rostro"), "foco": ant.get("foco", [0.5, 0.5]),
            "personas": ant.get("personas", []), "permiso": ant.get("permiso", ""),
        }
    archivo.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"fotos": len(cat), "sin_describir": [n for n, d in cat.items() if not d["descripcion"]], "heic_sin_convertir": ignoradas}


def encuadre(w: int, h: int, foco=(0.5, 0.5)) -> tuple[float, int, int]:
    """Escala y desplazamiento del recorte que llena 1080x1920 cuidando el punto de interés."""
    r = max(W / w, H / h)
    nw, nh = round(w * r), round(h * r)
    return r, round((nw - W) * min(1, max(0, foco[0]))), round((nh - H) * min(1, max(0, foco[1])))


def rostro_en_lienzo(dato: dict, foco) -> tuple[int, int, int, int] | None:
    caja = dato.get("rostro")
    if not caja:
        return None
    r, l, t = encuadre(dato["ancho"], dato["alto"], foco)
    nw, nh = dato["ancho"] * r, dato["alto"] * r
    return (round(caja[0] * nw - l), round(caja[1] * nh - t), round(caja[2] * nw - l), round(caja[3] * nh - t))


# ---------- texto ----------

def _texto_visible(bloque: dict, perfil: dict) -> str:
    t = " ".join(str(bloque.get("texto", "")).split())
    return t.upper() if bloque.get("estilo") == "titular" and perfil.get("titular") == "Anton" else t


def medir_bloque(bloque: dict, perfil: dict, tam: int | None = None) -> dict:
    """Parte el texto en líneas y calcula su caja. No dibuja."""
    estilo = bloque.get("estilo", "cuerpo")
    familia, peso, tam_base, inter = ESTILOS_BLOQUE[estilo]
    familia = familia or perfil.get("titular", "Anton")
    tam = int(tam or bloque.get("tam") or tam_base)
    fnt = fuente(familia, tam, peso)
    ancho_max = int(bloque.get("ancho", SEG_X1 - SEG_X0)) - (56 if estilo == "etiqueta" else 0)
    lineas, actual = [], []
    for trozo in str(bloque.get("texto", "")).split("\n"):
        for palabra in _texto_visible({**bloque, "texto": trozo}, perfil).split():
            if actual and fnt.getlength(" ".join(actual + [palabra])) > ancho_max:
                lineas.append(actual)
                actual = []
            actual.append(palabra)
        if actual:
            lineas.append(actual)
            actual = []
    anchos = [fnt.getlength(" ".join(l)) for l in lineas]
    alto_linea = round(tam * inter)
    relleno = 28 if estilo == "etiqueta" else 0
    return {"fuente": fnt, "lineas": lineas, "anchos": anchos, "alto_linea": alto_linea, "tam": tam, "relleno": relleno,
            "w": round(max(anchos, default=0)) + 2 * relleno, "h": alto_linea * len(lineas) + (12 if estilo == "etiqueta" else 0),
            "desborda": any(a > ancho_max for a in anchos)}


def ajustar_bloque(bloque: dict, perfil: dict, alto_max: int) -> dict:
    """Reduce el cuerpo de letra hasta que quepa; si ni al 60 % cabe, el texto sobra y hay que recortarlo."""
    base = int(bloque.get("tam") or ESTILOS_BLOQUE[bloque.get("estilo", "cuerpo")][2])
    tam = base
    while True:
        m = medir_bloque(bloque, perfil, tam)
        if not m["desborda"] and m["h"] <= alto_max:
            return m
        tam = int(tam * 0.94)
        if tam < base * 0.6:
            raise ErrorHistorias(f"el texto no cabe ni reduciendo la letra: «{str(bloque.get('texto'))[:50]}…». Acórtalo.")


def dibujar_bloque(bloque: dict, perfil: dict, m: dict, sobre_foto: bool) -> Image.Image:
    estilo = bloque.get("estilo", "cuerpo")
    alinear = bloque.get("alinear", "centro")
    margen = 30
    capa = Image.new("RGBA", (m["w"] + 2 * margen, m["h"] + 2 * margen), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    tinta_auto = "blanco" if sobre_foto else "tinta"
    if estilo == "etiqueta":
        fondo_et = color(bloque.get("fondo", "blanco"), perfil)
        tinta = color(bloque.get("color", "negro" if sum(fondo_et) > 380 else "blanco"), perfil)
    else:
        tinta = color(bloque.get("color", tinta_auto), perfil)
    acento = color(bloque.get("color_resalte", "acento" if estilo != "etiqueta" else "acento"), perfil)
    resaltar = {_norm(p) for frase in bloque.get("resaltar", []) for p in frase.split()}
    espacio = m["fuente"].getlength(" ")
    sombras = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sombras)
    y = margen
    for palabras, ancho in zip(m["lineas"], m["anchos"]):
        libre = m["w"] - 2 * m["relleno"] - ancho
        x = margen + m["relleno"] + {"izq": 0, "centro": libre / 2, "der": libre}[alinear]
        if estilo == "etiqueta":
            d.rounded_rectangle([x - m["relleno"], y, x + ancho + m["relleno"], y + m["alto_linea"] + 6], radius=18, fill=(*fondo_et, 255))
        ty = y + (m["alto_linea"] - m["tam"]) / 2 + (2 if estilo == "etiqueta" else 0)
        for p in palabras:
            marcada = _norm(p) in resaltar
            if marcada and estilo in ("nota", "etiqueta"):  # subrayado a mano en vez de cambiar el color
                d.line([x, ty + m["tam"] * 1.02, x + m["fuente"].getlength(p), ty + m["tam"] * 1.0], fill=(*acento, 255), width=max(5, m["tam"] // 12))
            relleno = acento if marcada and estilo not in ("nota", "etiqueta") else tinta
            if sobre_foto and estilo != "etiqueta":
                ds.text((x, ty + 3), p, font=m["fuente"], fill=(0, 0, 0, 150))
            d.text((x, ty), p, font=m["fuente"], fill=(*relleno, 255))
            x += m["fuente"].getlength(p) + espacio
        y += m["alto_linea"]
    if sobre_foto and estilo != "etiqueta":
        capa = Image.alpha_composite(sombras.filter(ImageFilter.GaussianBlur(7)), capa)
    giro = float(bloque.get("giro", -2.5 if estilo == "nota" else 0))
    if giro:
        capa = capa.rotate(giro, resample=Image.BICUBIC, expand=True)
    return capa


# ---------- composición ----------

def _elementos(lamina: dict) -> list[dict]:
    elementos = [dict(b, _tipo="bloque") for b in lamina.get("bloques", [])]
    st = lamina.get("sticker")
    if st:
        elementos.append(dict(st, _tipo="sticker"))
    return elementos


def componer(lamina: dict, perfil: dict) -> list[dict]:
    """Calcula dónde cae cada bloque y cada sticker. Devuelve cajas en el lienzo; lanza error si algo no cabe."""
    pilas: dict[str, list] = {"arriba": [], "centro": [], "abajo": []}
    for e in _elementos(lamina):
        pos = e.get("pos", "centro")
        if pos not in pilas:
            raise ErrorHistorias(f"posición desconocida: {pos!r} (arriba, centro, abajo)")
        pilas[pos].append(e)
    alto_zona = SEG_Y1 - SEG_Y0
    hueco = 30
    cajas = []
    limites = {}
    for pos, elementos in pilas.items():
        if not elementos:
            continue
        medidos = []
        for e in elementos:
            if e["_tipo"] == "sticker":
                if e.get("tipo") not in STICKERS:
                    raise ErrorHistorias(f"sticker desconocido: {e.get('tipo')!r}. Existen: {', '.join(STICKERS)}")
                w, h = STICKERS[e["tipo"]]
                medidos.append((e, None, w, h))
            else:
                if e.get("estilo", "cuerpo") not in ESTILOS_BLOQUE:
                    raise ErrorHistorias(f"estilo de texto desconocido: {e.get('estilo')!r}. Existen: {', '.join(ESTILOS_BLOQUE)}")
                if not str(e.get("texto", "")).strip():
                    raise ErrorHistorias("hay un bloque sin texto")
                m = ajustar_bloque(e, perfil, alto_zona)
                medidos.append((e, m, m["w"], m["h"]))
        total = sum(h for *_, h in medidos) + hueco * (len(medidos) - 1)
        if total > alto_zona:
            raise ErrorHistorias(f"lo que va «{pos}» mide {total}px y la zona segura tiene {alto_zona}px: quita texto o divide la lámina")
        y = {"arriba": SEG_Y0, "centro": SEG_Y0 + (alto_zona - total) // 2, "abajo": SEG_Y1 - total}[pos]
        limites[pos] = (y, y + total)
        for e, m, w, h in medidos:
            alinear = e.get("alinear", "centro")
            x = {"izq": SEG_X0, "centro": (W - w) // 2, "der": SEG_X1 - w}.get(alinear)
            if x is None:
                raise ErrorHistorias(f"alineación desconocida: {alinear!r} (izq, centro, der)")
            cajas.append({"elemento": e, "medida": m, "caja": (x, y, x + w, y + h)})
            y += h + hueco
    orden = [limites[p] for p in ("arriba", "centro", "abajo") if p in limites]
    for (_, fin), (ini, _) in zip(orden, orden[1:]):
        if fin + 10 > ini:
            raise ErrorHistorias("los textos de arriba, centro y abajo se enciman: quita texto o divide la lámina")
    return cajas


def _chocan(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def fondo_lamina(lamina: dict, perfil: dict, base: Path, catalogo: dict) -> tuple[Image.Image, bool, tuple | None]:
    fondo = lamina.get("fondo") or {"tipo": "color", "color": "papel"}
    tipo = fondo.get("tipo")
    if tipo == "color":
        return Image.new("RGB", (W, H), color(fondo.get("color", "papel"), perfil)), False, None
    if tipo not in ("foto", "ia"):
        raise ErrorHistorias(f"tipo de fondo desconocido: {tipo!r} (foto, ia, color)")
    nombre = fondo.get("archivo", "")
    ruta = (base / ("fotos" if tipo == "foto" else "fondos") / nombre) if nombre else None
    if not ruta or not ruta.is_file() or base.resolve() not in ruta.resolve().parents:
        raise ErrorHistorias(f"no encuentro el fondo {nombre!r} en {base / ('fotos' if tipo == 'foto' else 'fondos')}")
    with Image.open(ruta) as cruda:
        img = ImageOps.exif_transpose(cruda).convert("RGB")
    dato = catalogo.get(nombre, {}) if tipo == "foto" else {}
    foco = fondo.get("foco") or dato.get("foco") or [0.5, 0.5]
    rostro = rostro_en_lienzo({"rostro": dato.get("rostro"), "ancho": img.width, "alto": img.height}, foco)
    r, l, t = encuadre(*img.size, foco)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS).crop((l, t, l + W, t + H))
    return img, True, rostro


def dibujar_lamina(plan: dict, i: int, perfil: dict, base: Path, catalogo: dict, guias: bool = False) -> Image.Image:
    lamina = plan["laminas"][i]
    img, es_foto, rostro = fondo_lamina(lamina, perfil, base, catalogo)
    if es_foto:
        img = aplicar_filtro(img, filtro_de(plan, lamina, perfil), semilla=i)
        velo = float(lamina.get("velo", 0.18))
        if velo:
            img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), min(0.85, velo))
    elif (lamina.get("fondo") or {}).get("grano", True):
        img = aplicar_filtro(img, {"grano": 0.06}, semilla=i)  # el papel liso se ve digital; un poco de fibra lo arregla
    img = img.convert("RGBA")
    for c in componer(lamina, perfil):
        e, caja = c["elemento"], c["caja"]
        if rostro and _chocan(caja, rostro):
            raise ErrorHistorias(f"lámina {i + 1}: «{str(e.get('texto', e.get('tipo')))[:40]}» cae sobre el rostro; cambia `pos` o el `foco`")
        if e["_tipo"] == "sticker":
            if guias:
                d = ImageDraw.Draw(img)
                d.rounded_rectangle(caja, radius=28, outline=(255, 60, 120, 255), width=5)
                d.text((caja[0] + 22, caja[1] + 18), f"sticker: {e['tipo']}", font=fuente("Inter", 34, 600), fill=(255, 60, 120, 255))
            continue
        capa = dibujar_bloque(e, perfil, c["medida"], es_foto)
        cx, cy = (caja[0] + caja[2]) // 2, (caja[1] + caja[3]) // 2
        img.alpha_composite(capa, (max(0, cx - capa.width // 2), max(0, cy - capa.height // 2)))
    if guias:
        d = ImageDraw.Draw(img)
        d.rectangle([SEG_X0, SEG_Y0, SEG_X1, SEG_Y1], outline=(0, 220, 255, 255), width=3)
        if rostro:
            d.rectangle(rostro, outline=(255, 220, 0, 255), width=4)
    return img.convert("RGB")


# ---------- plan ----------

def cargar_plan(ruta: Path) -> dict:
    try:
        plan = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorHistorias(f"no existe {ruta}") from exc
    except ValueError as exc:
        raise ErrorHistorias(f"{ruta} no es JSON válido: {exc}") from exc
    if not isinstance(plan, dict):
        raise ErrorHistorias("el plan debe ser un objeto JSON")
    return plan


def cargar_catalogo(base: Path) -> dict:
    f = base / "fotos" / "catalogo.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def validar(plan: dict, base: Path | None = None, final: bool = True) -> tuple[list[str], list[str]]:
    """Errores (impiden dibujar) y avisos (decide Emi)."""
    errores, avisos = [], []
    try:
        perfil = perfil_de(plan.get("espacio", ""))
    except ErrorHistorias as exc:
        return [str(exc)], []
    if not str(plan.get("titulo", "")).strip():
        errores.append("falta `titulo`")
    brief = plan.get("brief") or {}
    for campo, que in (("objetivo", "para qué es la secuencia"), ("publico", "a quién le habla"),
                       ("accion", "qué debe hacer quien la vea"), ("respuestas_emi", "lo que Emi contestó, con sus palabras")):
        if len(str(brief.get(campo, "")).strip()) < 4:
            errores.append(f"falta `brief.{campo}` ({que}): se le pregunta a Emi, no se inventa")
    if final and plan.get("guion_aprobado") is not True:
        errores.append("`guion_aprobado` no es true: Emi aprueba el guion antes del render final (usa --borrador para verlo antes)")
    laminas = plan.get("laminas")
    if not isinstance(laminas, list) or not 1 <= len(laminas) <= 12:
        return errores + ["`laminas` debe tener entre 1 y 12 láminas"], avisos
    catalogo = cargar_catalogo(base) if base else {}
    lim_palabras = int(perfil.get("max_palabras", MAX_PALABRAS))
    prohibidas = [p.lower() for p in perfil.get("frases_prohibidas", [])]
    for i, lam in enumerate(laminas, 1):
        if not isinstance(lam, dict):
            errores.append(f"lámina {i}: debe ser un objeto")
            continue
        if not lam.get("bloques") and not lam.get("sticker") and (lam.get("fondo") or {}).get("tipo") != "foto":
            errores.append(f"lámina {i}: vacía (sin texto, sin sticker y sin foto)")
        try:
            filtro_de(plan, lam, perfil)
            componer(lam, perfil)
        except ErrorHistorias as exc:
            errores.append(f"lámina {i}: {exc}")
        textos = " ".join(str(b.get("texto", "")) for b in lam.get("bloques", []))
        n = len(textos.split())
        if n > lim_palabras:
            errores.append(f"lámina {i}: {n} palabras (máximo {lim_palabras}); una historia se lee en 3 segundos")
        bajo = textos.lower()
        for frase in FRASES_IA:
            if frase in bajo:
                avisos.append(f"lámina {i}: «{frase}» suena a texto de máquina; dilo como lo diría Emi")
        for frase in prohibidas:
            if frase and frase in bajo:
                errores.append(f"lámina {i}: «{frase}» está prohibida en este espacio")
        if "—" in textos:
            avisos.append(f"lámina {i}: lleva raya larga (—); en una historia escrita a mano casi nadie la usa")
        if len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", textos)) > 2:
            avisos.append(f"lámina {i}: más de dos emojis")
        fondo = lam.get("fondo") or {}
        if fondo.get("tipo") in ("foto", "ia") and base:
            carpeta = "fotos" if fondo["tipo"] == "foto" else "fondos"
            if not (base / carpeta / str(fondo.get("archivo", ""))).is_file():
                errores.append(f"lámina {i}: falta {carpeta}/{fondo.get('archivo')}")
            elif fondo["tipo"] == "foto":
                dato = catalogo.get(fondo["archivo"])
                if not dato or not dato.get("descripcion"):
                    errores.append(f"lámina {i}: {fondo['archivo']} no está descrita en fotos/catalogo.json (corre `catalogo` y descríbela)")
                else:
                    foco = fondo.get("foco") or dato.get("foco") or [0.5, 0.5]
                    rostro = rostro_en_lienzo(dato, foco)
                    try:
                        tapan = [c for c in componer(lam, perfil) if rostro and c["elemento"]["_tipo"] == "bloque" and _chocan(c["caja"], rostro)]
                    except ErrorHistorias:
                        tapan = []
                    for c in tapan:
                        errores.append(f"lámina {i}: «{str(c['elemento'].get('texto'))[:40]}» cae sobre el rostro; cambia `pos` o el `foco`")
                if dato and dato.get("personas") and not dato.get("permiso"):
                    avisos.append(f"lámina {i}: {fondo['archivo']} muestra a {', '.join(dato['personas'])}; confirma con Emi que se puede publicar")
        if fondo.get("tipo") == "ia" and perfil.get("fondos_ia") is False:
            errores.append(f"lámina {i}: este espacio no admite fondos generados con IA")
    if final and len(laminas) > 1 and not (laminas[-1].get("sticker") or brief.get("sin_cierre")):
        avisos.append("la última lámina no reserva sticker ni cierre: ¿cómo responde la gente? (o marca `brief.sin_cierre`)")
    return errores, avisos


# ---------- red y Kie ----------

def _pedir(url: str, *, metodo="GET", cabeceras=None, cuerpo=None, espera=120) -> bytes:
    if urllib.parse.urlparse(url).scheme != "https":
        raise ErrorHistorias("solo se permiten URLs https")
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method=metodo, headers=cabeceras or {})
    if datos is not None:
        req.add_header("Content-Type", "application/json")
    host = urllib.parse.urlparse(url).hostname
    try:
        with urllib.request.urlopen(req, timeout=espera) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        raise ErrorHistorias(f"{host} respondió HTTP {exc.code}: {exc.read()[:200]!r}") from exc
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


def _kie() -> dict:
    return {"Authorization": "Bearer " + os.environ.get("KIE_API_KEY", MARCADOR)}


def saldo_kie() -> dict:
    """Saldo real. Sin conexión se informa como tal; nunca se estima."""
    try:
        r = _json(_pedir(f"{KIE}/chat/credit", cabeceras=_kie(), espera=30), "Kie")
        if r.get("code") != 200 or not isinstance(r.get("data"), (int, float)):
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
        est = json.loads(estado.read_text())
        if est.get("firma") != firma:
            raise ErrorHistorias(f"{estado} pertenece a otro prompt o modelo; usa un archivo de estado nuevo")
        if est.get("fallo"):
            raise ErrorHistorias(f"esa tarea ya falló ({est['fallo']}); cambia el prompt y usa un estado nuevo")
    else:
        r = _json(_pedir(f"{KIE}/jobs/createTask", metodo="POST", cabeceras=_kie(),
                         cuerpo={"model": modelo, "input": {"prompt": prompt, "aspect_ratio": "9:16", **MODELOS_KIE[modelo]}}), "Kie")
        tid = (r.get("data") or {}).get("taskId")
        if not tid:
            raise ErrorHistorias(f"Kie no devolvió taskId: {str(r)[:200]}")
        est = {"taskId": tid, "modelo": modelo, "firma": firma}
        estado.parent.mkdir(parents=True, exist_ok=True)
        estado.write_text(json.dumps(est))
    limite = time.time() + espera
    while time.time() < limite:
        d = _json(_pedir(f"{KIE}/jobs/recordInfo?taskId={est['taskId']}", cabeceras=_kie()), "Kie").get("data") or {}
        st = str(d.get("state", "")).lower()
        if st == "success":
            rj = d.get("resultJson")
            urls = ((json.loads(rj) if isinstance(rj, str) else rj) or {}).get("resultUrls") or []
            if not urls:
                raise ErrorHistorias("Kie terminó sin URL de resultado")
            if urllib.parse.urlparse(urls[0]).hostname not in HOSTS_DESCARGA:
                raise ErrorHistorias(f"host de descarga no autorizado: {urllib.parse.urlparse(urls[0]).hostname}")
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_bytes(_pedir(urls[0]))
            return
        if st in {"fail", "failed", "error"}:
            est["fallo"] = str(d.get("failMsg"))[:200]
            estado.write_text(json.dumps(est))
            raise ErrorHistorias(f"Kie falló: {est['fallo']}")
        time.sleep(4)
    raise ErrorHistorias(f"Kie no terminó a tiempo; repite el mismo comando con {estado} para reconsultar sin crear otra tarea")


# ---------- proyecto, render y cierre ----------

def slug(texto: str) -> str:
    s = unicodedata.normalize("NFD", texto.lower())
    s = re.sub(r"[^a-z0-9]+", "-", "".join(c for c in s if unicodedata.category(c) != "Mn")).strip("-")
    return s[:60] or "historia"


PLAN_EJEMPLO = {
    "titulo": "", "espacio": "", "fecha": "",
    "brief": {"objetivo": "", "publico": "", "accion": "", "respuestas_emi": ""},
    "estructura": "", "estilo": {"filtro": "natural", "referencia": ""},
    "guion_aprobado": False,
    "laminas": [
        {"fondo": {"tipo": "color", "color": "papel"},
         "bloques": [{"texto": "Escribe aquí el gancho", "estilo": "titular", "pos": "centro", "resaltar": ["gancho"]},
                     {"texto": "una nota como la pondrías tú", "estilo": "nota", "pos": "abajo"}]},
        {"fondo": {"tipo": "color", "color": "tinta"},
         "bloques": [{"texto": "El cierre: qué quieres que hagan", "estilo": "cuerpo", "pos": "centro", "color": "papel"}],
         "sticker": {"tipo": "pregunta", "pos": "abajo"}},
    ],
}


def crear_proyecto(destino: Path, espacio: str) -> Path:
    perfil_de(espacio)
    destino = destino.resolve()
    padre = (RAIZ / "producciones" / espacio).resolve()
    if destino.parent != padre:
        raise ErrorHistorias(f"las secuencias de «{espacio}» van en producciones/{espacio}/<tema>/ (privadas, no se suben a GitHub)")
    if destino.exists():
        raise ErrorHistorias(f"{destino} ya existe")
    for sub in ("fotos", "fondos", "prompts", "estados", "out"):
        (destino / sub).mkdir(parents=True)
    plan = json.loads(json.dumps(PLAN_EJEMPLO))
    plan.update(espacio=espacio, fecha=dt.date.today().isoformat(), titulo=destino.name.replace("-", " "))
    (destino / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destino / "estados" / "saldo_inicial.json").write_text(json.dumps(saldo_kie()))
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
    out = base / "out"
    out.mkdir(exist_ok=True)
    for viejo in out.glob("[0-9][0-9].png"):
        viejo.unlink()
    guias = []
    for i in range(len(plan["laminas"])):
        img = dibujar_lamina(plan, i, perfil, base, catalogo)
        if borrador:
            d = ImageDraw.Draw(img)
            d.text((SEG_X0, 150), "BORRADOR", font=fuente("Inter", 44, 800), fill=(255, 60, 120))
        img.save(out / f"{i + 1:02d}.png", optimize=True)
        guias.append(dibujar_lamina(plan, i, perfil, base, catalogo, guias=True))
    hoja(guias).save(out / "hoja.png", optimize=True)
    pie = [f"# {plan['titulo']}", "", f"Espacio: {perfil['nombre']} · {plan.get('fecha', '')} · {len(guias)} láminas"
           + (" · BORRADOR" if borrador else ""), "", "## Para publicar", ""]
    for i, lam in enumerate(plan["laminas"], 1):
        st = lam.get("sticker")
        if st:
            pie.append(f"- Lámina {i}: añadir en Instagram el sticker de **{st['tipo']}**" + (f" con «{st['texto']}»" if st.get("texto") else "")
                       + f", {st.get('pos', 'centro')}.")
        if lam.get("nota_publicacion"):
            pie.append(f"- Lámina {i}: {lam['nota_publicacion']}")
    if avisos:
        pie += ["", "## Avisos para Emi", ""] + [f"- {a}" for a in avisos]
    (out / "LEEME.md").write_text("\n".join(pie) + "\n", encoding="utf-8")
    return {"laminas": len(guias), "salida": str(out), "avisos": avisos, "borrador": borrador}


def cierre(base: Path) -> str:
    ini_f = base / "estados" / "saldo_inicial.json"
    ini = json.loads(ini_f.read_text()) if ini_f.exists() else {}
    ahora = saldo_kie()
    if "kie_creditos" not in ahora:
        return f"Proveedor | Gastado | Queda\nKie       | —       | no conectado ({ahora.get('kie_error')})"
    gastado = f"{ini['kie_creditos'] - ahora['kie_creditos']:g} créditos" if "kie_creditos" in ini else "sin saldo inicial"
    return f"Proveedor | Gastado | Queda\nKie       | {gastado} | {ahora['kie_creditos']:g} créditos"


# ---------- CLI ----------

def main(argv=None) -> int:
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
    a.add_argument("--prompt-file", type=Path, required=True); a.add_argument("--out", type=Path, required=True)
    a.add_argument("--estado", type=Path, required=True); a.add_argument("--estilo", choices=sorted(ESTILOS_FONDO), default="foto")
    a.add_argument("--modelo", choices=sorted(MODELOS_KIE), default="nano-banana-2-lite"); a.add_argument("--execute", action="store_true")
    a = s.add_parser("render"); a.add_argument("dir", type=Path); a.add_argument("--borrador", action="store_true")
    s.add_parser("saldo")
    a = s.add_parser("cierre"); a.add_argument("dir", type=Path)
    args = p.parse_args(argv)
    try:
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
                print("\nAVISO: el nicho nunca se ha revisado. Hazlo con Emi antes de proponer temas.")
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
            perfil_de(args.espacio)
            m = medir(args.imagen)
            destino = dir_espacios() / args.espacio / "referencias" / f"{slug(args.nombre)}.json"
            destino.parent.mkdir(exist_ok=True)
            ficha = {"nombre": args.nombre, "fecha": dt.date.today().isoformat(), "medidas": m, "filtro": filtro_desde_medidas(m),
                     "tipografia": "", "composicion": "", "espiritu": "", "notas_emi": ""}
            destino.write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Referencia guardada en {destino}. Completa tipografía, composición y espíritu mirando la imagen.\n"
                  + json.dumps(ficha["filtro"], ensure_ascii=False))
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
            prompt = prompt_fondo(args.prompt_file.read_text(encoding="utf-8"), args.estilo)
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
    except ErrorHistorias as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
