#!/usr/bin/env python3
"""Pruebas de Historias Studio. No usan red ni gastan saldo: python3 -m unittest discover -s skills/historias-studio/scripts"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import historias as h  # noqa: E402

PERFIL = {
    "nombre": "Prueba", "handle": "", "estado": "candidato", "titular": "Anton", "estilo_imagen": "foto",
    "colores": {"papel": "#F4ECD6", "tinta": "#20180F", "acento": "#FF5A1F", "apoyo": "#FFD23F"},
    "tono": "", "filtro": "natural", "max_palabras": 30, "fondos_ia": True, "frases_prohibidas": ["garantizado"],
}


def plan_base(**cambios) -> dict:
    plan = {
        "titulo": "prueba", "espacio": "prueba", "guion_aprobado": True,
        "brief": {"objetivo": "probar", "publico": "nadie", "accion": "ninguna", "respuestas_emi": "es una prueba"},
        "laminas": [
            {"fondo": {"tipo": "color", "color": "papel"}, "bloques": [{"texto": "Hola a todos", "estilo": "titular", "pos": "centro"}]},
            {"fondo": {"tipo": "color", "color": "tinta"}, "bloques": [{"texto": "Te leo", "estilo": "cuerpo", "color": "papel"}],
             "sticker": {"tipo": "pregunta", "pos": "abajo"}},
        ],
    }
    plan.update(cambios)
    return plan


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self.esp = self.raiz / "espacios"
        (self.esp / "prueba").mkdir(parents=True)
        (self.esp / "prueba" / "perfil.json").write_text(json.dumps(PERFIL), encoding="utf-8")
        self.parches = [mock.patch.dict(os.environ, {"HISTORIAS_ESPACIOS": str(self.esp)}), mock.patch.object(h, "RAIZ", self.raiz),
                        mock.patch.object(h, "saldo_kie", return_value={"kie_error": "prueba sin red"})]
        for p in self.parches:
            p.start()

    def tearDown(self):
        for p in self.parches:
            p.stop()
        self.tmp.cleanup()

    def foto(self, carpeta: Path, nombre="a.jpg", tam=(1200, 1600)) -> Path:
        carpeta.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", tam, (90, 130, 170))
        d = ImageDraw.Draw(img)
        d.rectangle([0, tam[1] // 2, tam[0], tam[1]], fill=(40, 90, 50))
        for x in range(0, tam[0], 40):  # pasto: detalle abajo, cielo liso arriba
            d.line([x, tam[1] * 2 // 3, x + 20, tam[1]], fill=(20, 50, 25), width=6)
        img.save(carpeta / nombre)
        return carpeta / nombre


class Validacion(Base):
    def test_plan_valido(self):
        errores, avisos = h.validar(plan_base())
        self.assertEqual(errores, [])
        self.assertEqual(avisos, [])

    def test_sin_respuestas_de_emi_no_pasa(self):
        plan = plan_base()
        plan["brief"]["respuestas_emi"] = ""
        self.assertTrue(any("respuestas_emi" in e for e in h.validar(plan)[0]))

    def test_sin_aprobacion_solo_pasa_como_borrador(self):
        plan = plan_base(guion_aprobado=False)
        self.assertTrue(any("guion_aprobado" in e for e in h.validar(plan)[0]))
        self.assertEqual(h.validar(plan, final=False)[0], [])

    def test_aprobado_debe_ser_true_literal(self):
        self.assertTrue(h.validar(plan_base(guion_aprobado="sí"))[0])

    def test_espacio_desconocido(self):
        self.assertIn("espacio desconocido", h.validar(plan_base(espacio="otro"))[0][0])

    def test_demasiadas_palabras(self):
        plan = plan_base()
        plan["laminas"][0]["bloques"][0] = {"texto": "palabra " * 31, "estilo": "cuerpo"}
        self.assertTrue(any("31 palabras" in e for e in h.validar(plan)[0]))

    def test_frase_prohibida_del_espacio(self):
        plan = plan_base()
        plan["laminas"][0]["bloques"][0]["texto"] = "Resultado garantizado"
        self.assertTrue(any("prohibida" in e for e in h.validar(plan)[0]))

    def test_frase_de_maquina_es_aviso_no_error(self):
        plan = plan_base()
        plan["laminas"][0]["bloques"][0]["texto"] = "Lleva tu rutina al siguiente nivel"
        errores, avisos = h.validar(plan)
        self.assertEqual(errores, [])
        self.assertTrue(any("máquina" in a for a in avisos))

    def test_filtro_y_estilo_desconocidos(self):
        plan = plan_base()
        plan["laminas"][0]["filtro"] = "vintage9000"
        plan["laminas"][1]["bloques"][0]["estilo"] = "comic"
        errores = h.validar(plan)[0]
        self.assertTrue(any("filtro desconocido" in e for e in errores))
        self.assertTrue(any("estilo de texto desconocido" in e for e in errores))

    def test_clave_de_filtro_desconocida(self):
        plan = plan_base(estilo={"filtro": {"magia": 1}})
        self.assertTrue(any("claves de filtro" in e for e in h.validar(plan)[0]))

    def test_lamina_vacia_y_sin_laminas(self):
        plan = plan_base()
        plan["laminas"][0] = {"fondo": {"tipo": "color", "color": "papel"}}
        self.assertTrue(any("vacía" in e for e in h.validar(plan)[0]))
        self.assertTrue(h.validar(plan_base(laminas=[]))[0])

    def test_ultima_lamina_sin_cierre_avisa(self):
        plan = plan_base()
        del plan["laminas"][1]["sticker"]
        self.assertTrue(any("última lámina" in a for a in h.validar(plan)[1]))

    def test_foto_sin_describir_no_pasa(self):
        base = self.raiz / "sec"
        self.foto(base / "fotos")
        h.catalogar(base / "fotos")
        plan = plan_base()
        plan["laminas"][0]["fondo"] = {"tipo": "foto", "archivo": "a.jpg"}
        self.assertTrue(any("no está descrita" in e for e in h.validar(plan, base)[0]))

    def test_fondo_ia_vetado_por_espacio(self):
        (self.esp / "prueba" / "perfil.json").write_text(json.dumps({**PERFIL, "fondos_ia": False}), encoding="utf-8")
        plan = plan_base()
        plan["laminas"][0]["fondo"] = {"tipo": "ia", "archivo": "x.png"}
        self.assertTrue(any("no admite fondos" in e for e in h.validar(plan)[0]))


class Composicion(Base):
    def test_todo_queda_en_zona_segura(self):
        for c in h.componer(plan_base()["laminas"][1], PERFIL):
            x0, y0, x1, y1 = c["caja"]
            self.assertGreaterEqual(x0, h.SEG_X0)
            self.assertLessEqual(x1, h.SEG_X1)
            self.assertGreaterEqual(y0, h.SEG_Y0)
            self.assertLessEqual(y1, h.SEG_Y1)

    def test_texto_largo_reduce_la_letra(self):
        m = h.ajustar_bloque({"texto": "Institucionalizaciones hoy", "estilo": "titular"}, PERFIL, 1200)
        self.assertLess(m["tam"], 118)
        self.assertFalse(m["desborda"])

    def test_texto_imposible_da_error(self):
        with self.assertRaises(h.ErrorHistorias):
            h.ajustar_bloque({"texto": "x" * 80, "estilo": "titular"}, PERFIL, 1200)

    def test_pilas_que_se_enciman(self):
        lam = {"bloques": [{"texto": "uno dos tres cuatro " * 6, "estilo": "titular", "pos": "arriba"},
                           {"texto": "cinco seis siete ocho " * 6, "estilo": "titular", "pos": "centro"}]}
        with self.assertRaises(h.ErrorHistorias):
            h.componer(lam, PERFIL)

    def test_posicion_alineacion_y_sticker_invalidos(self):
        for lam in ({"bloques": [{"texto": "a", "pos": "lado"}]}, {"bloques": [{"texto": "a", "alinear": "medio"}]},
                    {"sticker": {"tipo": "gif"}}, {"bloques": [{"texto": "  "}]}):
            with self.assertRaises(h.ErrorHistorias):
                h.componer(lam, PERFIL)

    def test_titular_anton_va_en_mayusculas_y_serif_no(self):
        self.assertEqual(h._texto_visible({"texto": "hola", "estilo": "titular"}, PERFIL), "HOLA")
        self.assertEqual(h._texto_visible({"texto": "hola", "estilo": "titular"}, {**PERFIL, "titular": "Gelasio"}), "hola")

    def test_encuadre_cubre_el_lienzo(self):
        for tam in ((4000, 3000), (1080, 1920), (900, 3000)):
            r, l, t = h.encuadre(*tam)
            self.assertGreaterEqual(round(tam[0] * r), h.W)
            self.assertGreaterEqual(round(tam[1] * r), h.H)
            self.assertGreaterEqual(l, 0)
            self.assertGreaterEqual(t, 0)

    def test_rostro_se_traslada_al_lienzo(self):
        caja = h.rostro_en_lienzo({"rostro": [0.25, 0.25, 0.75, 0.75], "ancho": 1080, "alto": 1920}, [0.5, 0.5])
        self.assertEqual(caja, (270, 480, 810, 1440))
        self.assertIsNone(h.rostro_en_lienzo({"rostro": None, "ancho": 10, "alto": 10}, [0.5, 0.5]))


class Render(Base):
    def secuencia(self) -> Path:
        base = h.crear_proyecto(self.raiz / "producciones" / "prueba" / "tema", "prueba")
        self.foto(base / "fotos")
        h.catalogar(base / "fotos")
        cat = json.loads((base / "fotos" / "catalogo.json").read_text())
        cat["a.jpg"].update(descripcion="cielo y pasto", rostro=[0.4, 0.3, 0.6, 0.5])
        (base / "fotos" / "catalogo.json").write_text(json.dumps(cat))
        plan = plan_base()
        plan["laminas"][0] = {"fondo": {"tipo": "foto", "archivo": "a.jpg"}, "filtro": "pelicula",
                              "bloques": [{"texto": "Arriba del rostro", "estilo": "etiqueta", "pos": "arriba"}]}
        (base / "plan.json").write_text(json.dumps(plan))
        return base

    def test_render_completo(self):
        base = self.secuencia()
        r = h.render(base)
        self.assertEqual(r["laminas"], 2)
        for n in ("01.png", "02.png", "hoja.png", "LEEME.md"):
            self.assertTrue((base / "out" / n).exists(), n)
        with Image.open(base / "out" / "01.png") as img:
            self.assertEqual(img.size, (1080, 1920))
            self.assertEqual(img.mode, "RGB")
        self.assertIn("sticker de **pregunta**", (base / "out" / "LEEME.md").read_text())

    def test_render_es_reproducible(self):
        base = self.secuencia()
        h.render(base)
        uno = (base / "out" / "01.png").read_bytes()
        h.render(base)
        self.assertEqual(uno, (base / "out" / "01.png").read_bytes())

    def test_texto_sobre_rostro_se_rechaza(self):
        base = self.secuencia()
        plan = json.loads((base / "plan.json").read_text())
        plan["laminas"][0]["bloques"][0]["pos"] = "centro"
        (base / "plan.json").write_text(json.dumps(plan))
        with self.assertRaisesRegex(h.ErrorHistorias, "rostro"):
            h.render(base)

    def test_render_final_exige_aprobacion_y_borrador_no(self):
        base = self.secuencia()
        plan = json.loads((base / "plan.json").read_text())
        plan["guion_aprobado"] = False
        (base / "plan.json").write_text(json.dumps(plan))
        with self.assertRaises(h.ErrorHistorias):
            h.render(base)
        self.assertTrue(h.render(base, borrador=True)["borrador"])

    def test_render_limpia_laminas_viejas(self):
        base = self.secuencia()
        (base / "out" / "07.png").write_bytes(b"viejo")
        h.render(base)
        self.assertFalse((base / "out" / "07.png").exists())

    def test_fondo_fuera_de_la_secuencia_se_rechaza(self):
        base = self.secuencia()
        self.foto(self.raiz, "afuera.jpg")
        plan = json.loads((base / "plan.json").read_text())
        plan["laminas"][0]["fondo"]["archivo"] = "../../../../afuera.jpg"
        (base / "plan.json").write_text(json.dumps(plan))
        with self.assertRaises(h.ErrorHistorias):
            h.render(base)

    def test_proyecto_solo_en_su_espacio(self):
        with self.assertRaisesRegex(h.ErrorHistorias, "producciones/prueba"):
            h.crear_proyecto(self.raiz / "otra" / "tema", "prueba")
        base = h.crear_proyecto(self.raiz / "producciones" / "prueba" / "uno", "prueba")
        with self.assertRaisesRegex(h.ErrorHistorias, "ya existe"):
            h.crear_proyecto(base, "prueba")


class Looks(Base):
    def test_filtro_no_cambia_tamano_y_es_determinista(self):
        img = Image.new("RGB", (1080, 1920), (120, 100, 90))
        for nombre, f in h.FILTROS.items():
            a, b = h.aplicar_filtro(img, f, 3), h.aplicar_filtro(img, f, 3)
            self.assertEqual(a.size, img.size, nombre)
            self.assertEqual(a.tobytes(), b.tobytes(), nombre)
        self.assertEqual(set().union(*[set(f) for f in h.FILTROS.values()]) - h.CLAVES_FILTRO, set())

    def test_bn_no_tiene_color(self):
        out = h.aplicar_filtro(Image.new("RGB", (200, 300), (200, 80, 40)), {"bn": True})
        r, g, b = out.getpixel((100, 150))
        self.assertTrue(r == g == b)

    def test_medir_y_filtro_sugerido(self):
        ruta = self.foto(self.raiz / "ref")
        m = h.medir(ruta)
        self.assertEqual(len(m["paleta"]), len(set(m["paleta"])))
        self.assertTrue(0 <= m["luz"] <= 1)
        self.assertLess(m["calidez"], 0)  # la foto de prueba es azul y verde
        self.assertEqual(set(h.filtro_desde_medidas(m)) - h.CLAVES_FILTRO, set())
        gris = self.raiz / "gris.png"
        Image.new("RGB", (300, 500), (128, 128, 128)).save(gris)
        self.assertTrue(h.filtro_desde_medidas(h.medir(gris)).get("bn"))
        self.assertEqual(h.comparar(ruta, ruta)["luz"], 0)

    def test_catalogo_conserva_descripciones(self):
        carpeta = self.raiz / "f"
        self.foto(carpeta)
        (carpeta / "IMG_1.HEIC").write_bytes(b"x")
        r = h.catalogar(carpeta)
        self.assertEqual(r["sin_describir"], ["a.jpg"])
        self.assertEqual(r["heic_sin_convertir"], ["IMG_1.HEIC"])
        cat = json.loads((carpeta / "catalogo.json").read_text())
        self.assertEqual(cat["a.jpg"]["zona_calma"], "arriba")
        cat["a.jpg"]["descripcion"] = "cielo"
        (carpeta / "catalogo.json").write_text(json.dumps(cat))
        self.assertEqual(h.catalogar(carpeta)["sin_describir"], [])


class Memoria(Base):
    def test_aprender_agrega_sin_borrar(self):
        h.aprender("Emi prefiere letra a mano en el cierre")
        h.aprender("En este espacio nada de emojis", "prueba")
        texto = h.leer_aprendizajes("prueba")
        self.assertIn("letra a mano", texto)
        self.assertIn("nada de emojis", texto)
        with self.assertRaises(h.ErrorHistorias):
            h.aprender("corta")

    def test_nicho_avisa_a_los_siete_dias(self):
        f = self.esp / "prueba" / "NICHO.md"
        self.assertEqual(h.estado_nicho("prueba"), ("", None))
        f.write_text("# Nicho\n\nRevisado: nunca\n")
        self.assertIsNone(h.estado_nicho("prueba")[1])
        f.write_text("# Nicho\n\nRevisado: 2026-11-01\n")
        self.assertEqual(h.estado_nicho("prueba", dt.date(2026, 11, 10))[1], 9)

    def test_vox_copia_sin_tocar_lo_propio(self):
        vox = self.raiz / "vox" / "espacios"
        (vox / "prueba").mkdir(parents=True)
        (vox / "otro").mkdir()
        (vox / "APRENDIZAJES.md").write_text("# Título\n\n- lección de video\n")
        (vox / "prueba" / "perfil.json").write_text(json.dumps({**PERFIL, "titular": "Gelasio"}))
        (vox / "otro" / "perfil.json").write_text(json.dumps(PERFIL))
        (vox / "prueba" / "aprendizajes.md").write_text("- la voz de Laura\n")
        h.aprender("lección propia de historias", "prueba")
        avisos = h.sincronizar_vox(str(self.raiz / "vox"))
        self.assertTrue(any("titular" in a for a in avisos))
        self.assertTrue(any(a.startswith("otro") for a in avisos))
        self.assertIn("lección de video", (self.esp / "DESDE-VOX.md").read_text())
        self.assertIn("voz de Laura", (self.esp / "prueba" / "desde-vox.md").read_text())
        self.assertIn("lección propia", (self.esp / "prueba" / "aprendizajes.md").read_text())
        self.assertIn("voz de Laura", h.leer_aprendizajes("prueba"))
        with self.assertRaises(h.ErrorHistorias), mock.patch.dict(os.environ, {"VOX_REPO": ""}):
            h.sincronizar_vox(str(self.raiz / "no-existe"))


class Kie(Base):
    def test_prompt_de_fondo_prohibe_texto(self):
        p = h.prompt_fondo("una mesa de madera con café por la mañana", "foto")
        self.assertIn("no text", p)
        with self.assertRaises(h.ErrorHistorias):
            h.prompt_fondo("corto", "foto")
        with self.assertRaises(h.ErrorHistorias):
            h.prompt_fondo("una mesa de madera con café", "anime")

    def test_sin_execute_no_hay_red(self):
        f = self.raiz / "p.txt"
        f.write_text("una mesa de madera con café por la mañana")
        with mock.patch.object(h, "_pedir", side_effect=AssertionError("no debe llamar a la red")), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(h.main(["fondo", "--prompt-file", str(f), "--out", str(self.raiz / "o.png"), "--estado", str(self.raiz / "e.json")]), 0)
        self.assertIn("SIMULACIÓN", out.getvalue())

    def test_generar_fondo_con_respuestas_simuladas(self):
        llamadas = []

        def falso(url, **kw):
            llamadas.append((url, kw.get("cuerpo")))
            if url.endswith("createTask"):
                return json.dumps({"code": 200, "data": {"taskId": "t1"}}).encode()
            if "recordInfo" in url:
                return json.dumps({"data": {"state": "success", "resultJson": json.dumps({"resultUrls": ["https://tempfile.aiquickdraw.com/x.png"]})}}).encode()
            return b"PNG"

        salida, estado = self.raiz / "fondos" / "01.png", self.raiz / "estados" / "01.json"
        with mock.patch.object(h, "_pedir", side_effect=falso):
            h.generar_fondo("prompt uno", salida, estado)
            self.assertEqual(salida.read_bytes(), b"PNG")
            self.assertEqual(llamadas[0][1]["input"]["aspect_ratio"], "9:16")
            h.generar_fondo("prompt uno", salida, estado)  # reconsulta: no crea otra tarea
            self.assertEqual(sum(u.endswith("createTask") for u, _ in llamadas), 1)
            with self.assertRaisesRegex(h.ErrorHistorias, "otro prompt"):
                h.generar_fondo("prompt dos", salida, estado)

    def test_host_de_descarga_ajeno_se_rechaza(self):
        def falso(url, **kw):
            if url.endswith("createTask"):
                return json.dumps({"data": {"taskId": "t"}}).encode()
            return json.dumps({"data": {"state": "success", "resultJson": {"resultUrls": ["https://malo.example/x.png"]}}}).encode()

        with mock.patch.object(h, "_pedir", side_effect=falso), self.assertRaisesRegex(h.ErrorHistorias, "no autorizado"):
            h.generar_fondo("prompt", self.raiz / "o.png", self.raiz / "e.json")

    def test_la_clave_nunca_va_en_archivos(self):
        with mock.patch.dict(os.environ, {"KIE_API_KEY": "secreta-123"}):
            self.assertEqual(h._kie()["Authorization"], "Bearer secreta-123")
        with mock.patch.dict(os.environ, clear=False) as env:
            env.pop("KIE_API_KEY", None)
            self.assertEqual(h._kie()["Authorization"], "Bearer " + h.MARCADOR)

    def test_cierre_sin_conexion_no_estima(self):
        base = self.raiz / "sec"
        (base / "estados").mkdir(parents=True)
        self.assertIn("no conectado", h.cierre(base))


class Repositorio(unittest.TestCase):
    """Lo que está publicado en el repositorio debe ser coherente."""

    def test_espacios_reales_tienen_todo(self):
        for nombre, pf in h.perfiles().items():
            carpeta = h.dir_espacios() / nombre
            for archivo in ("MARCA.md", "NICHO.md", "aprendizajes.md", "ideas.md"):
                self.assertTrue((carpeta / archivo).exists(), f"{nombre}/{archivo}")
            self.assertEqual(set(pf["colores"]), {"papel", "tinta", "acento", "apoyo"}, nombre)
            self.assertIn(pf["filtro"], h.FILTROS, nombre)
            h.fuente(pf["titular"], 40)
            for c in pf["colores"].values():
                h._hex(c)

    def test_plan_de_ejemplo_se_dibuja_en_cada_espacio(self):
        for nombre, pf in h.perfiles().items():
            plan = json.loads(json.dumps(h.PLAN_EJEMPLO))
            plan.update(espacio=nombre, titulo="x")
            self.assertEqual([e for e in h.validar(plan, final=False)[0] if "brief" not in e], [], nombre)
            self.assertEqual(h.dibujar_lamina(plan, 0, pf, Path("."), {}).size, (1080, 1920))

    def test_no_hay_claves_en_el_repositorio(self):
        import re
        import subprocess
        archivos = subprocess.run(["git", "ls-files"], cwd=h.RAIZ, capture_output=True, text=True).stdout.split("\n")
        patron = re.compile(r"(sk-[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9]{24,}|KIE_API_KEY\s*=\s*[A-Za-z0-9]{12,})")
        for a in filter(None, archivos):
            f = h.RAIZ / a
            if f.suffix in {".ttf", ".png", ".jpg"} or not f.is_file():
                continue
            self.assertIsNone(patron.search(f.read_text(encoding="utf-8", errors="ignore")), a)


if __name__ == "__main__":
    unittest.main()
