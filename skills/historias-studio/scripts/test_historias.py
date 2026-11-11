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

_png = io.BytesIO()
Image.new("RGB", (8, 8), (10, 20, 30)).save(_png, "PNG")
PNG = _png.getvalue()

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
            {"fondo": {"tipo": "color", "color": "tinta"}, "bloques": [{"texto": "Te leo", "estilo": "cuerpo"}],
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
        self.assertLessEqual(m["w"], h.ANCHO_SEG)
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
                    {"sticker": {"tipo": "gif"}}, {"bloques": [{"texto": "  "}]}, {"sticker": "pregunta"},
                    {"bloques": "Hola"}, {"bloques": ["Hola"]}, {"fondo": "papel"}, {"fondo": {"color": "tinta"}},
                    {"bloques": [{"texto": "a", "giro": "mucho"}]}, {"bloques": [{"texto": "a", "ancho": 1400}]},
                    {"bloques": [{"texto": "a", "resaltar": "gym"}]}, {"bloques": [{"texto": "a", "pos": ["arriba"]}]},
                    {"bloques": [{"texto": "a"}], "velo": -1}, {"bloques": [{"texto": "a", "tam": "grande"}]},
                    {"bloques": [{"texto": "a", "color": "rojo"}]}, {"bloques": [{"texto": "a", "color": 5}]}):
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
        self.assertEqual(h.rostro_en_lienzo([0.25, 0.25, 0.75, 0.75], 1080, 1920, [0.5, 0.5]), (270, 480, 810, 1440))
        self.assertEqual(h.rostro_en_lienzo([0.4, 0.4, 0.6, 0.6], 3840, 1920, [0, 0.5]), (1536, 768, 2304, 1152))
        self.assertIsNone(h.rostro_en_lienzo(None, 10, 10, [0.5, 0.5]))


class Render(Base):
    def secuencia(self) -> Path:
        base = h.crear_proyecto(self.raiz / "producciones" / "prueba" / "tema", "prueba")
        self.foto(base / "fotos")
        h.catalogar(base / "fotos")
        cat = json.loads((base / "fotos" / "catalogo.json").read_text(encoding="utf-8"))
        cat["a.jpg"].update(descripcion="cielo y pasto", rostro=[0.4, 0.3, 0.6, 0.5])
        (base / "fotos" / "catalogo.json").write_text(json.dumps(cat), encoding="utf-8")
        plan = plan_base()
        plan["laminas"][0] = {"fondo": {"tipo": "foto", "archivo": "a.jpg"}, "filtro": "pelicula",
                              "bloques": [{"texto": "Arriba del rostro", "estilo": "etiqueta", "pos": "arriba"}]}
        (base / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
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
        self.assertIn("sticker de **pregunta**", (base / "out" / "LEEME.md").read_text(encoding="utf-8"))

    def test_render_es_reproducible(self):
        base = self.secuencia()
        h.render(base)
        uno = (base / "out" / "01.png").read_bytes()
        h.render(base)
        self.assertEqual(uno, (base / "out" / "01.png").read_bytes())

    def test_texto_sobre_rostro_se_rechaza(self):
        base = self.secuencia()
        plan = json.loads((base / "plan.json").read_text(encoding="utf-8"))
        plan["laminas"][0]["bloques"][0]["pos"] = "centro"
        (base / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaisesRegex(h.ErrorHistorias, "rostro"):
            h.render(base)

    def test_render_final_exige_aprobacion_y_borrador_no(self):
        base = self.secuencia()
        plan = json.loads((base / "plan.json").read_text(encoding="utf-8"))
        plan["guion_aprobado"] = False
        (base / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
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
        plan = json.loads((base / "plan.json").read_text(encoding="utf-8"))
        plan["laminas"][0]["fondo"] = {"tipo": "ia", "archivo": "../../../../afuera.jpg"}
        (base / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaisesRegex(h.ErrorHistorias, "no encuentro"):
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
        (carpeta / "rota.jpg").write_bytes(b"no soy una foto")
        (carpeta / "carpeta.jpg").mkdir()
        self.assertEqual(h.catalogar(carpeta)["ilegibles"], ["rota.jpg"])
        cat = json.loads((carpeta / "catalogo.json").read_text(encoding="utf-8"))
        self.assertEqual(cat["a.jpg"]["zona_calma"], "arriba")
        cat["a.jpg"]["descripcion"] = "cielo"
        (carpeta / "catalogo.json").write_text(json.dumps(cat), encoding="utf-8")
        self.assertEqual(h.catalogar(carpeta)["sin_describir"], [])
        (carpeta / "a.jpg").unlink()  # la foto se va, su descripción se conserva
        h.catalogar(carpeta)
        self.assertTrue(json.loads((carpeta / "catalogo.json").read_text(encoding="utf-8"))["a.jpg"]["ausente"])
        (carpeta / "catalogo.json").write_text("{roto", encoding="utf-8")
        with self.assertRaises(h.ErrorHistorias):
            h.catalogar(carpeta)


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
        f.write_text("# Nicho\n\nRevisado: nunca\n", encoding="utf-8")
        self.assertIsNone(h.estado_nicho("prueba")[1])
        f.write_text("# Nicho\n\nRevisado: 2026-11-01\n", encoding="utf-8")
        self.assertEqual(h.estado_nicho("prueba", dt.date(2026, 11, 10))[1], 9)
        for mala in ("2026-13-45", "2027-01-01"):
            f.write_text(f"Revisado: {mala}\n", encoding="utf-8")
            self.assertIsNone(h.estado_nicho("prueba", dt.date(2026, 11, 10))[1])

    def test_vox_copia_sin_tocar_lo_propio(self):
        vox = self.raiz / "vox" / "espacios"
        (vox / "prueba").mkdir(parents=True)
        (vox / "otro").mkdir()
        (vox / "APRENDIZAJES.md").write_text("# Título\n\n- lección de video\n", encoding="utf-8")
        (vox / "prueba" / "perfil.json").write_text(json.dumps({**PERFIL, "titular": "Gelasio"}), encoding="utf-8")
        (vox / "otro" / "perfil.json").write_text(json.dumps(PERFIL), encoding="utf-8")
        (vox / "prueba" / "aprendizajes.md").write_text("- la voz de Laura\n", encoding="utf-8")
        h.aprender("lección propia de historias", "prueba")
        avisos = h.sincronizar_vox(str(self.raiz / "vox"))
        self.assertTrue(any("titular" in a for a in avisos))
        self.assertTrue(any(a.startswith("otro") for a in avisos))
        self.assertIn("lección de video", (self.esp / "DESDE-VOX.md").read_text(encoding="utf-8"))
        self.assertIn("voz de Laura", (self.esp / "prueba" / "desde-vox.md").read_text(encoding="utf-8"))
        self.assertIn("lección propia", (self.esp / "prueba" / "aprendizajes.md").read_text(encoding="utf-8"))
        self.assertIn("voz de Laura", h.leer_aprendizajes("prueba"))
        self.assertIn("lección de video", h.leer_aprendizajes("prueba"))
        self.assertIn("lección de video", h.leer_aprendizajes())
        with self.assertRaises(h.ErrorHistorias), mock.patch.dict(os.environ, {"VOX_REPO": str(self.raiz / "vox")}):
            h.sincronizar_vox(str(self.raiz / "no-existe"))  # una --ruta mala no cae en silencio a otra


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
        f.write_text("una mesa de madera con café por la mañana", encoding="utf-8")
        with mock.patch.object(h, "_pedir", side_effect=AssertionError("no debe llamar a la red")), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(h.main(["fondo", "--espacio", "prueba", "--prompt-file", str(f), "--out", str(self.raiz / "o.png"), "--estado", str(self.raiz / "e.json")]), 0)
        self.assertIn("SIMULACIÓN", out.getvalue())

    def test_generar_fondo_con_respuestas_simuladas(self):
        llamadas = []

        def falso(url, **kw):
            llamadas.append((url, kw.get("cuerpo")))
            if url.endswith("createTask"):
                return json.dumps({"code": 200, "data": {"taskId": "t1"}}).encode()
            if "recordInfo" in url:
                return json.dumps({"data": {"state": "success", "resultJson": json.dumps({"resultUrls": ["https://tempfile.aiquickdraw.com/x.png"]})}}).encode()
            return PNG

        salida, estado = self.raiz / "fondos" / "01.png", self.raiz / "estados" / "01.json"
        with mock.patch.object(h, "_pedir", side_effect=falso):
            h.generar_fondo("prompt uno", salida, estado)
            self.assertEqual(salida.read_bytes(), PNG)
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
        def falso(url, **kw):
            if url.endswith("createTask"):
                return json.dumps({"data": {"taskId": "t1"}}).encode()
            if "recordInfo" in url:
                return json.dumps({"data": {"state": "success", "resultJson": {"resultUrls": ["https://file.aiquickdraw.com/x.png"]}}}).encode()
            self.assertNotIn("cabeceras", kw)  # la descarga va sin clave
            return PNG

        with mock.patch.dict(os.environ, {"KIE_API_KEY": "secreta-123"}), mock.patch.object(h, "_pedir", side_effect=falso):
            self.assertEqual(h._kie()["Authorization"], "Bearer secreta-123")
            h.crear_proyecto(self.raiz / "producciones" / "prueba" / "k", "prueba")
            h.generar_fondo("prompt", self.raiz / "producciones" / "prueba" / "k" / "fondos" / "1.png", self.raiz / "producciones" / "prueba" / "k" / "estados" / "1.json")
        for f in self.raiz.rglob("*"):
            if f.is_file():
                self.assertNotIn(b"secreta-123", f.read_bytes(), f)
        for vacia in ({"KIE_API_KEY": ""}, {}):
            with mock.patch.dict(os.environ, vacia):
                if not vacia:
                    os.environ.pop("KIE_API_KEY", None)
                self.assertEqual(h._kie()["Authorization"], "Bearer " + h.MARCADOR)

    def test_respuestas_raras_de_kie_dan_error_limpio(self):
        casos = [
            ({"data": "oops"}, None, "taskId"),
            ({"data": {"taskId": "t"}}, {"data": {"state": "success", "resultJson": "no-json"}}, "sin URL"),
            ({"data": {"taskId": "t"}}, {"data": {"state": "success", "resultJson": "[1]"}}, "sin URL"),
            ({"data": {"taskId": "t"}}, {"data": {"state": "fail", "failMsg": "contenido"}}, "Kie falló"),
        ]
        for n, (crear, info, mensaje) in enumerate(casos):
            def falso(url, crear=crear, info=info, **kw):
                return json.dumps(crear if url.endswith("createTask") else info).encode()
            with mock.patch.object(h, "_pedir", side_effect=falso), self.assertRaisesRegex(h.ErrorHistorias, mensaje):
                h.generar_fondo("prompt", self.raiz / f"o{n}.png", self.raiz / f"e{n}.json")
        (self.raiz / "roto.json").write_text("{", encoding="utf-8")
        (self.raiz / "lista.json").write_text("[]", encoding="utf-8")
        for estado in ("roto.json", "lista.json"):
            with self.assertRaises(h.ErrorHistorias):
                h.generar_fondo("prompt", self.raiz / "o.png", self.raiz / estado)

    def test_lo_descargado_debe_ser_imagen(self):
        def falso(url, **kw):
            if url.endswith("createTask"):
                return json.dumps({"data": {"taskId": "t"}}).encode()
            if "recordInfo" in url:
                return json.dumps({"data": {"state": "success", "resultJson": {"resultUrls": ["https://file.aiquickdraw.com/x.png"]}}}).encode()
            return b"<html>no soy una imagen</html>"

        with mock.patch.object(h, "_pedir", side_effect=falso), self.assertRaisesRegex(h.ErrorHistorias, "no es una imagen"):
            h.generar_fondo("prompt", self.raiz / "o.png", self.raiz / "e.json")
        self.assertFalse((self.raiz / "o.png").exists())

    def test_redireccion_a_otro_host_se_rechaza(self):
        import urllib.error
        import urllib.request
        m = h._SinSaltoDeHost()
        req = urllib.request.Request("https://api.kie.ai/x", headers={"Authorization": "Bearer secreta"})
        with self.assertRaises(urllib.error.HTTPError):
            m.redirect_request(req, None, 302, "Found", {}, "https://malo.example/x")
        with self.assertRaises(urllib.error.HTTPError):
            m.redirect_request(req, None, 302, "Found", {}, "http://api.kie.ai/x")
        self.assertIsNotNone(m.redirect_request(req, None, 302, "Found", {}, "https://api.kie.ai/y"))

    def test_fondo_respeta_el_veto_del_espacio(self):
        (self.esp / "prueba" / "perfil.json").write_text(json.dumps({**PERFIL, "fondos_ia": False}), encoding="utf-8")
        f = self.raiz / "p.txt"
        f.write_text("una mesa de madera con café por la mañana", encoding="utf-8")
        with mock.patch.object(h, "_pedir", side_effect=AssertionError("no debe gastar")), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(h.main(["fondo", "--espacio", "prueba", "--prompt-file", str(f), "--out", "o.png", "--estado", "e.json", "--execute"]), 1)
        self.assertIn("no admite", err.getvalue())

    def test_cierre_sin_conexion_no_estima(self):
        base = self.raiz / "sec"
        (base / "estados").mkdir(parents=True)
        self.assertIn("no conectado", h.cierre(base))


def tinta(img: Image.Image, limpia: Image.Image):
    """Caja de los píxeles que cambian respecto a la misma lámina sin texto."""
    from PIL import ImageChops
    return ImageChops.difference(img, limpia).convert("L").point(lambda v: 255 if v > 24 else 0).getbbox()


class Pixeles(Base):
    """Lo que de verdad se pinta, no lo que el motor cree que pinta."""

    def lamina(self, bloque: dict, fondo: dict | None = None) -> tuple:
        fondo = fondo or {"tipo": "color", "color": "papel", "grano": False}
        con = h.dibujar_lamina(plan_base(laminas=[{"fondo": fondo, "bloques": [bloque]}]), 0, PERFIL, None, {})
        sin = Image.new("RGB", (h.W, h.H), h.color(fondo.get("color", "papel"), PERFIL))
        return tinta(con, sin)

    def test_la_tinta_real_queda_en_zona_segura(self):
        casos = [
            {"texto": "Hoy no fui al gym", "estilo": "titular", "pos": "abajo"},
            {"texto": "ÁÉÑ Qjgp, ya", "estilo": "titular", "pos": "abajo"},
            {"texto": "y aun así aprendí algo", "estilo": "nota", "pos": "abajo"},
            {"texto": "y aun así aprendí algo, ya qué", "estilo": "nota", "pos": "abajo", "alinear": "der", "giro": -3},
            {"texto": "una nota larga para girar bastante", "estilo": "nota", "pos": "abajo", "alinear": "izq", "giro": 12},
            {"texto": "Dos líneas de titular para girar", "estilo": "titular", "pos": "arriba", "alinear": "der", "giro": 12},
            {"texto": "Titular a la izquierda", "estilo": "titular", "pos": "arriba", "alinear": "izq", "giro": -3},
            {"texto": "Descansar también es entrenar", "estilo": "serif", "pos": "abajo"},
            {"texto": "Llevaba tres semanas sin faltar al gimnasio ni un día", "estilo": "etiqueta", "pos": "abajo", "alinear": "izq"},
            {"texto": "cuerpo de texto normal", "estilo": "cuerpo", "pos": "arriba"},
        ]
        for b in casos:
            x0, y0, x1, y1 = self.lamina(b)
            nombre = f"{b['estilo']} {b.get('pos')} {b.get('giro', '')}"
            self.assertGreaterEqual(x0, h.SEG_X0, nombre)
            self.assertLessEqual(x1, h.SEG_X1, nombre)
            self.assertGreaterEqual(y0, h.SEG_Y0, nombre)
            self.assertLessEqual(y1, h.SEG_Y1, nombre)

    def test_la_caja_calculada_es_la_tinta(self):
        b = {"texto": "Hoy no fui al gym", "estilo": "titular", "pos": "abajo"}
        caja = h.componer({"fondo": {"tipo": "color"}, "bloques": [b]}, PERFIL)[0]["caja"]
        real = self.lamina(b)
        for calculado, medido in zip(caja, real):
            self.assertLessEqual(abs(calculado - medido), 3)
        self.assertLessEqual(h.SEG_Y1 - real[3], 3)  # «abajo» apoya de verdad en el borde inferior

    def test_texto_sobre_fondo_oscuro_se_ve_sin_pedir_color(self):
        for nombre in ("tinta", "papel", "acento", "apoyo"):
            self.assertIsNotNone(self.lamina({"texto": "Hola a todos", "estilo": "titular"},
                                             {"tipo": "color", "color": nombre, "grano": False}), nombre)
        with self.assertRaisesRegex(h.ErrorHistorias, "no se leería"):
            self.lamina({"texto": "Hola", "estilo": "titular", "color": "papel"})

    def test_resaltar(self):
        m = h._marcadas
        self.assertEqual(m(["Hoy", "no", "fui", "al", "gym,"], ["gym"]), {4})
        self.assertEqual(m(["¿Cuántos", "días", "¿descansas?"], ["descansas"]), {2})
        self.assertEqual(m(["no", "fui", "y", "no", "pasó", "nada"], ["no pasó"]), {3, 4})
        self.assertEqual(m(["un", "año", "sin", "ano"], ["año"]), {1})
        self.assertEqual(m(["hola", "—", "mundo"], ["¡!"]), set())

    def test_sin_palabra_huerfana(self):
        m = h.capa_bloque({"texto": "Lo dice el propio decreto, artículo 12", "estilo": "etiqueta", "ancho": 760}, PERFIL, 54, None, False)
        sola = h.capa_bloque({"texto": "12", "estilo": "etiqueta"}, PERFIL, 54, None, False)
        self.assertGreater(m["w"], sola["w"] * 2)

    def test_el_resalte_se_lee_sobre_foto_en_cada_espacio_real(self):
        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop("HISTORIAS_ESPACIOS", None)
            reales = {n: json.loads((Path(h.__file__).resolve().parents[3] / "espacios" / n / "perfil.json").read_text(encoding="utf-8"))
                      for n in ("personal", "milla", "castorena", "pan")}
        for nombre, pf in reales.items():
            capa = h.capa_bloque({"texto": "MMMM", "estilo": "titular", "resaltar": ["MMMM"]}, pf, 118, None, False)["capa"].convert("RGB")
            self.assertGreaterEqual(capa.convert("L").getextrema()[1] / 255, 0.45, nombre)  # no queda oscura sobre una foto

    def test_salto_de_linea(self):
        una = h.capa_bloque({"texto": "uno dos", "estilo": "cuerpo"}, PERFIL, 54, (255, 255, 255), False)
        dos = h.capa_bloque({"texto": "uno\ndos", "estilo": "cuerpo"}, PERFIL, 54, (255, 255, 255), False)
        self.assertEqual(dos["w"], h.capa_bloque({"texto": "uno\n\ndos", "estilo": "cuerpo"}, PERFIL, 54, (255, 255, 255), False)["w"])
        self.assertGreater(dos["h"], una["h"] + 40)


class Rostros(Base):
    def secuencia(self, rostro, bloque, tipo="foto", sticker=None) -> Path:
        base = self.raiz / "producciones" / "prueba" / "r"
        (base / "fotos").mkdir(parents=True, exist_ok=True)
        (base / "fondos").mkdir(exist_ok=True)
        Image.new("RGB", (1080, 1920), (90, 130, 170)).save(base / "fotos" / "v.jpg")
        cat = {"v.jpg": {"ancho": 1080, "alto": 1920, "descripcion": "retrato", "rostro": rostro}}
        (base / "fotos" / "catalogo.json").write_text(json.dumps(cat), encoding="utf-8")
        lam = {"fondo": {"tipo": tipo, "archivo": "v.jpg" if tipo == "foto" else "../fotos/v.jpg"}, "filtro": "ninguno", "velo": 0,
               "bloques": [bloque] if bloque else []}
        if sticker:
            lam["sticker"] = sticker
        (base / "plan.json").write_text(json.dumps(plan_base(laminas=[lam])), encoding="utf-8")
        return base

    def errores(self, base: Path) -> list[str]:
        return h.validar(json.loads((base / "plan.json").read_text(encoding="utf-8")), base)[0]

    def test_ningun_pixel_de_texto_toca_el_rostro(self):
        rostro_px = (300, 395, 800, 700)
        rostro = [rostro_px[0] / 1080, rostro_px[1] / 1920, rostro_px[2] / 1080, rostro_px[3] / 1920]
        for bloque in ({"texto": "Hoy no fui, ya qué", "estilo": "titular", "pos": "arriba"},
                       {"texto": "Dos líneas de titular para girar bien", "estilo": "titular", "pos": "arriba", "giro": 8},
                       {"texto": "una nota girada cerca", "estilo": "nota", "pos": "arriba", "giro": -6},
                       {"texto": "texto pequeño arriba", "estilo": "cuerpo", "pos": "arriba"}):
            base = self.secuencia(rostro, bloque)
            if self.errores(base):
                with self.assertRaisesRegex(h.ErrorHistorias, "rostro"):
                    h.render(base)
                continue
            h.render(base)  # si el motor lo deja pasar, no puede haber tinta dentro del rostro
            with Image.open(base / "out" / "01.png") as img:
                zona = img.convert("RGB").crop(rostro_px)
            limpio = Image.new("RGB", zona.size, zona.getpixel((250, 150)))
            self.assertIsNone(tinta(zona, limpio), bloque["texto"])

    def test_validar_y_render_coinciden(self):
        centro = {"texto": "Encima de la cara", "estilo": "titular", "pos": "centro"}
        base = self.secuencia([0.3, 0.35, 0.7, 0.65], centro)
        self.assertTrue(any("rostro" in e for e in self.errores(base)))
        base = self.secuencia([0.3, 0.6, 0.7, 0.8], None, sticker={"tipo": "pregunta", "pos": "abajo"})
        self.assertTrue(any("rostro" in e for e in self.errores(base)))  # el sticker también tapa

    def test_rostro_mal_escrito_no_desactiva_la_proteccion(self):
        b = {"texto": "Hola", "estilo": "titular", "pos": "centro"}
        for malo in ([0.5, 0.9, 0.3, 0.6], [324, 384, 540, 768], [0.1, 0.2], "cara", {"x": 1}):
            self.assertTrue(any("rostro" in e for e in self.errores(self.secuencia(malo, b))), malo)

    def test_no_se_rodea_por_fondo_ia(self):
        b = {"texto": "Encima de la cara", "estilo": "titular", "pos": "centro"}
        self.assertTrue(any("no encuentro" in e for e in self.errores(self.secuencia([0.3, 0.35, 0.7, 0.65], b, tipo="ia"))))

    def test_foto_horizontal_con_exif_y_foco(self):
        base = self.secuencia(None, {"texto": "Hola", "estilo": "cuerpo", "pos": "arriba"})
        img = Image.new("RGB", (1600, 900), (60, 60, 60))
        ImageDraw.Draw(img).rectangle([1200, 300, 1400, 600], fill=(255, 0, 0))
        exif = Image.Exif()
        exif[274] = 6  # girada 90°: al enderezarla mide 900x1600
        img.save(base / "fotos" / "v.jpg", exif=exif, quality=95)
        self.assertEqual(h.tam_imagen(base / "fotos" / "v.jpg"), (900, 1600))
        self.assertEqual(h.abrir_imagen(base / "fotos" / "v.jpg").size, (900, 1600))
        transparente = self.raiz / "t.png"
        Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(transparente)
        self.assertEqual(h.abrir_imagen(transparente, (244, 236, 214)).getpixel((5, 5)), (244, 236, 214))


class Robustez(Base):
    def test_tipos_erroneos_dan_error_y_no_excepcion(self):
        lam = plan_base()["laminas"][0]
        malos = [
            {"espacio": ["prueba"]}, {"brief": "hola"}, {"brief": []}, {"laminas": [lam, "hola"]}, {"laminas": "x"},
            {"estilo": "calido"}, {"estilo": {"filtro": None}}, {"estilo": {"filtro": 3}}, {"titulo": 5},
            {"laminas": [{**lam, "filtro": None}]}, {"laminas": [{**lam, "filtro": {"calidez": "mucho"}}]},
            {"laminas": [{**lam, "filtro": {"tinte": "rojo"}}]}, {"laminas": [{**lam, "filtro": {"grano": 50}}]},
            {"laminas": [{**lam, "velo": None}]}, {"laminas": [{**lam, "fondo": {"tipo": "video"}}]},
            {"laminas": [{**lam, "fondo": {"tipo": "color", "color": "rojo"}}]},
            {"laminas": [{**lam, "fondo": {"tipo": "foto", "archivo": "a.jpg", "foco": "centro"}}]},
            {"laminas": [{**lam, "bloques": [{"texto": "a", "resaltar": [5]}]}]},
            {"laminas": [{**lam, "bloques": [{"texto": 7}]}]},
            {"estilo": {"referencia": "no-existe"}},
        ]
        for cambio in malos:
            errores, _ = h.validar(plan_base(**cambio), self.raiz)
            self.assertTrue(errores, cambio)

    def test_catalogo_roto_da_error_limpio(self):
        base = self.raiz / "sec"
        (base / "fotos").mkdir(parents=True)
        Image.new("RGB", (100, 200)).save(base / "fotos" / "a.jpg")
        plan = plan_base()
        plan["laminas"][0]["fondo"] = {"tipo": "foto", "archivo": "a.jpg"}
        for contenido in ("{roto", "[]", '{"a.jpg": "x"}', '{"a.jpg": {"descripcion": "x", "personas": [1, 2]}}',
                          '{"a.jpg": {"descripcion": "x", "foco": [7, -3]}}', '{"a.jpg": {"descripcion": 5}}'):
            (base / "fotos" / "catalogo.json").write_text(contenido, encoding="utf-8")
            self.assertTrue(h.validar(plan, base)[0], contenido)

    def test_emojis_y_simbolos_sin_glifo(self):
        self.assertEqual(h.sin_glifo("Inter", "Hoy sí fui 💪"), ["💪"])
        self.assertEqual(h.sin_glifo("Anton", "¿ÁÉÍÓÚ ÑÜ? ¡sí! 100% $1,200 «ya» #1 @emi"), [])
        self.assertEqual(h.sin_glifo("Caveat", "áéíóú ñ ¿? ¡!"), [])
        plan = plan_base()
        plan["laminas"][0]["bloques"][0]["texto"] = "Hoy sí fui 💪"
        self.assertTrue(any("no tiene" in e for e in h.validar(plan)[0]))

    def test_frases_no_se_evaden_con_saltos_ni_espacios(self):
        for texto in ("resultado\ngarantizado", "resultado   GARANTIZADO"):
            plan = plan_base()
            plan["laminas"][0]["bloques"][0] = {"texto": texto, "estilo": "cuerpo"}
            self.assertTrue(any("prohibida" in e for e in h.validar(plan)[0]), texto)
        plan = plan_base()
        plan["laminas"][0]["bloques"][0] = {"texto": "al siguiente\nnivel", "estilo": "cuerpo"}
        self.assertTrue(any("máquina" in a for a in h.validar(plan)[1]))
        plan["laminas"][0]["bloques"][0] = {"texto": "Eso conlleva tu firma", "estilo": "cuerpo"}
        self.assertEqual(h.validar(plan)[1], [])  # «lleva tu» dentro de otra palabra no cuenta

    def test_si_validar_pasa_render_dibuja_y_si_falla_no_toca_out(self):
        base = h.crear_proyecto(self.raiz / "producciones" / "prueba" / "v", "prueba")
        plan = plan_base()
        (base / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        h.render(base)
        antes = {f.name: f.read_bytes() for f in (base / "out").iterdir()}
        plan["laminas"][1]["bloques"][0]["color"] = "rojo"
        (base / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        self.assertTrue(any("lámina 2" in e and "color inválido" in e for e in h.validar(plan, base)[0]))
        with self.assertRaises(h.ErrorHistorias):
            h.render(base)
        self.assertEqual(antes, {f.name: f.read_bytes() for f in (base / "out").iterdir()})

    def test_espacio_del_plan_debe_ser_el_de_su_carpeta(self):
        (self.esp / "otro").mkdir()
        (self.esp / "otro" / "perfil.json").write_text(json.dumps(PERFIL), encoding="utf-8")
        base = h.crear_proyecto(self.raiz / "producciones" / "otro" / "v", "otro")
        self.assertTrue(any("no se mezclan" in e for e in h.validar(plan_base(), base)[0]))

    def test_proyecto_nuevo_usa_el_filtro_del_espacio(self):
        (self.esp / "prueba" / "perfil.json").write_text(json.dumps({**PERFIL, "filtro": "sobrio"}), encoding="utf-8")
        base = h.crear_proyecto(self.raiz / "producciones" / "prueba" / "f", "prueba")
        plan = json.loads((base / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(h.filtro_de(plan, plan["laminas"][0], h.perfil_de("prueba")), h.FILTROS["sobrio"])

    def test_referencia_da_el_filtro_y_conserva_lo_escrito_a_mano(self):
        ref = self.foto(self.raiz / "ref")
        destino, ficha = h.guardar_referencia(ref, "prueba", "Café  DOMINGO")
        self.assertEqual(destino.name, "cafe-domingo.json")
        ficha.update(espiritu="domingo lento", filtro={"grano": 0.3}, filtro_aprobado=True)
        destino.write_text(json.dumps(ficha), encoding="utf-8")
        _, otra = h.guardar_referencia(ref, "prueba", "café domingo")
        self.assertEqual(otra["espiritu"], "domingo lento")
        self.assertEqual(otra["filtro"], {"grano": 0.3})
        plan = plan_base(estilo={"referencia": "café domingo"})
        self.assertEqual(h.filtro_de(plan, {}, PERFIL), {"grano": 0.3})
        self.assertEqual(h.filtro_de(plan, {"filtro": "ninguno"}, PERFIL), {})

    def test_perfil_roto_da_error_limpio(self):
        for contenido in ("{roto", "[]", json.dumps({"nombre": "x"}), json.dumps({**PERFIL, "colores": {"papel": "#FFF"}}),
                          json.dumps({**PERFIL, "titular": "Comic Sans"}), json.dumps({**PERFIL, "filtro": "magia"})):
            (self.esp / "prueba" / "perfil.json").write_text(contenido, encoding="utf-8")
            with self.assertRaises(h.ErrorHistorias):
                h.perfiles()

    def test_cli_nunca_muestra_trazas(self):
        casos = [["medir", "/no/existe.jpg"], ["comparar", "/no/a.jpg", "/no/b.jpg"], ["catalogo", "/no/existe"],
                 ["validar", "/no/plan.json"], ["nicho", "--espacio", "otro"], ["render", str(self.raiz)],
                 ["fondo", "--espacio", "prueba", "--prompt-file", "/no/p.txt", "--out", "o", "--estado", "e"],
                 ["vox", "--ruta", "/no/existe"], ["aprender", "corta"]]
        for argv in casos:
            with contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(h.main(argv), 1, argv)
            self.assertTrue(err.getvalue().startswith("ERROR: "), argv)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(h.main(["espacios"]), 0)
            self.assertEqual(h.main(["nicho", "--espacio", "prueba"]), 0)
        self.assertIn("prueba", out.getvalue())


class Animacion(Base):
    def plan(self) -> dict:
        plan = plan_base()
        plan["laminas"][0]["bloques"].append({"texto": "segunda línea", "estilo": "nota", "pos": "abajo"})
        plan["laminas"][0]["duracion"] = 2
        return plan

    def test_el_ultimo_cuadro_es_la_lamina_fija_y_los_bloques_entran_en_orden(self):
        plan = self.plan()
        cuadros = list(h.cuadros_animados(plan, 0, PERFIL, None, {}))
        self.assertEqual(len(cuadros), 2 * h.FPS)
        fija = h.dibujar_lamina(plan, 0, PERFIL, None, {})
        self.assertEqual(cuadros[-1].tobytes(), fija.tobytes())
        papel = Image.new("RGB", (h.W, h.H), h.color("papel", PERFIL))
        self.assertIsNone(tinta(cuadros[0], papel))  # arranca con el fondo solo
        cajas = [p["caja"] for p in h.componer(plan["laminas"][0], PERFIL)]
        a_los_12 = cuadros[12]  # 0.4 s: ya entró el primer bloque, todavía no el segundo
        self.assertIsNotNone(tinta(a_los_12.crop(cajas[0]), papel.crop(cajas[0])))
        self.assertTrue(all(tinta(c.crop(cajas[1]), cuadros[0].crop(cajas[1])) is None for c in cuadros[:20]))
        for c in cuadros:  # ni al entrar un 4 % más grande se sale de la zona segura ampliada 20 px
            caja = tinta(c, cuadros[0])
            if caja:
                self.assertGreaterEqual(caja[0], h.SEG_X0 - 20)
                self.assertLessEqual(caja[2], h.SEG_X1 + 20)
                self.assertLessEqual(caja[3], h.SEG_Y1 + 20)

    def test_duracion_fuera_de_rango(self):
        plan = self.plan()
        plan["laminas"][0]["duracion"] = 60
        self.assertTrue(any("duracion" in e for e in h.validar(plan)[0]))

    def test_animar_crea_un_mp4_por_lamina(self):
        import shutil
        import subprocess
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("sin ffmpeg")
        base = h.crear_proyecto(self.raiz / "producciones" / "prueba" / "anim", "prueba")
        plan = self.plan()
        plan["laminas"][1]["duracion"] = 2
        (base / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        r = h.animar(base)
        self.assertEqual(r["videos"], ["01.mp4", "02.mp4"])
        dato = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames,pix_fmt",
                               "-of", "csv=p=0", str(base / "out" / "01.mp4")], capture_output=True, text=True).stdout.strip()
        self.assertEqual(dato, "1080,1920,yuv420p,30/1,60")
        self.assertEqual(list((base / "out").glob(".*.mp4")), [])

    def test_sin_ffmpeg_el_error_es_claro(self):
        with mock.patch("shutil.which", return_value=None), self.assertRaisesRegex(h.ErrorHistorias, "ffmpeg"):
            h.animar(self.raiz)


class Paquete(unittest.TestCase):
    def test_el_zip_funciona_fuera_del_repositorio(self):
        import subprocess
        import zipfile
        raiz = Path(h.__file__).resolve().parents[3]
        if not (raiz / "tools" / "empaquetar.py").exists():
            self.skipTest("fuera del repositorio")
        with tempfile.TemporaryDirectory() as tmp:
            zip_ = Path(tmp) / "skill.zip"
            subprocess.run([sys.executable, str(raiz / "tools" / "empaquetar.py"), str(zip_)], check=True, capture_output=True)
            zipfile.ZipFile(zip_).extractall(tmp)
            skill = Path(tmp) / "historias-studio"
            self.assertTrue((skill / "requirements.txt").exists())
            motor = [sys.executable, str(skill / "scripts" / "historias.py")]
            entorno = {k: v for k, v in os.environ.items() if not k.startswith("HISTORIAS_")}
            r = subprocess.run(motor + ["espacios"], capture_output=True, text=True, cwd=tmp, env=entorno)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("personal", r.stdout)
            r = subprocess.run(motor + ["proyecto", "producciones/personal/x", "--espacio", "personal"], capture_output=True, text=True, cwd=tmp, env=entorno)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((Path(tmp) / "producciones" / "personal" / "x" / "plan.json").exists())


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
            plan.update(espacio=nombre, titulo="x", brief={"objetivo": "probar", "publico": "nadie", "accion": "ninguna", "respuestas_emi": "prueba"})
            self.assertEqual(h.validar(plan, final=False)[0], [], nombre)
            self.assertEqual(h.dibujar_lamina(plan, 0, pf, Path("."), {}).size, (1080, 1920))

    def test_no_hay_claves_en_el_repositorio(self):
        import re
        import subprocess
        archivos = subprocess.run(["git", "ls-files"], cwd=h.RAIZ, capture_output=True, text=True).stdout.split("\n")
        patron = re.compile(r"(sk-[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9]{24,}|KIE_API_KEY\s*=\s*[A-Za-z0-9]{12,})")
        if not any(archivos):
            self.skipTest("fuera de git (por ejemplo, desde el ZIP)")
        for a in filter(None, archivos):
            f = h.RAIZ / a
            if f.suffix in {".ttf", ".png", ".jpg"} or not f.is_file():
                continue
            self.assertIsNone(patron.search(f.read_text(encoding="utf-8", errors="ignore")), a)


if __name__ == "__main__":
    unittest.main()
