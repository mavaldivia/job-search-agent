import hashlib
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from agente0 import busquedas, carriles, configuracion, fuentes, oportunidades, postulaciones, ranking, respuestas
from agente0.datos import ENV_VAR, REPO, crear_estructura
from agente0.medicion import respuestas as respuestas_medidas
from agente0.medicion import ventanas
from agente0.oportunidades import evaluar, registrar
from tests.test_medicion import postular
from tests.test_oportunidades import VIGENCIA, criterios, filtros

URL = "https://empleos.example.com/vacante/1"
FUENTE = {"nombre": "Portal", "tipo": "generalista", "pais": "Chile", "metodo": "web", "riesgo": "bajo"}


@pytest.fixture
def usuarios(tmp_path):
    a, b = tmp_path / "ana", tmp_path / "beto"
    for raiz in (a, b):
        crear_estructura(raiz)
        fuentes.guardar(raiz, [FUENTE])
    return a, b


def _huellas(raiz: Path) -> dict[str, str]:
    return {
        str(archivo.relative_to(raiz)): hashlib.sha256(archivo.read_bytes()).hexdigest()
        for archivo in sorted(raiz.rglob("*"))
        if archivo.is_file()
    }


def _trabajar(raiz: Path) -> str:
    """Una jornada completa de un usuario: vacante, ranking, postulación con respuesta, contacto, config y búsquedas."""
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA, publicada=date.today())
    evaluar(raiz, o.id, "Publicación.", criterios(90, 80), filtros(), "Brecha.")
    ranking.generar(raiz)
    respuestas.guardar(raiz, "renta", "Mi expectativa.", "hecho", "usuario")
    busquedas.registrar_consulta(
        raiz, "Portal", "jefe de datos", paginas=1, lecturas=1, vistas=5, nuevas=1, cubre_desde=date.today()
    )
    configuracion.editar(raiz, {"autonomia": 25})
    id_ = postular(raiz, 2, date.today() - timedelta(days=40), pares=[("renta", "v001")], contacto=True)
    return id_


def test_una_jornada_de_un_usuario_no_toca_ni_un_archivo_del_otro(usuarios, tmp_path):
    a, b = usuarios
    antes_de_b = _huellas(b)

    _trabajar(a)

    assert _huellas(b) == antes_de_b
    assert {hijo.name for hijo in tmp_path.iterdir()} == {"ana", "beto"}
    assert (a / "oportunidades").iterdir() and _huellas(a) != _huellas(b)


def test_el_otro_usuario_no_ve_vacantes_postulaciones_respuestas_ni_aprendizaje(usuarios):
    a, b = usuarios
    _trabajar(a)

    assert oportunidades.listar(b) == [] and postulaciones.listar(b) == []
    assert respuestas.listar(b) == []
    assert [(f.ultima_busqueda, f.consultas_distintas) for f in busquedas.resumen(b)] == [(None, 0)]
    assert ranking.ultimo(b) is None
    assert ranking.generar(b).top == []
    assert ventanas(b).ventanas == []
    assert respuestas_medidas(b).usos_totales == 0
    assert carriles.planear(b).carriles == []


def test_la_deduplicacion_de_busqueda_no_cruza_usuarios(usuarios):
    a, b = usuarios
    _trabajar(a)

    assert busquedas.conocida(a, url=URL) is not None
    assert busquedas.conocida(b, url=URL) is None


def test_la_misma_vacante_tiene_el_mismo_id_pero_estado_y_postulacion_independientes(usuarios):
    a, b = usuarios
    en_a = registrar(a, "Acme", "Jefe de Datos", URL, VIGENCIA)
    en_b = registrar(b, "Acme", "Jefe de Datos", URL, VIGENCIA)
    oportunidades.cambiar_estado(a, en_a.id, "CERRADO", "cerrada")
    postulaciones.crear(a, "Acme", "Jefe de Datos", URL)

    assert en_a.id == en_b.id
    assert oportunidades.cargar(b, en_b.id).estado == "POTENCIAL"
    assert postulaciones.crear(b, "Acme", "Jefe de Datos", URL).id == en_b.id


def test_la_configuracion_de_cada_usuario_es_propia_y_un_usuario_nuevo_parte_en_cero(usuarios, tmp_path):
    a, b = usuarios
    configuracion.editar(a, {"autonomia": 50})
    nuevo = tmp_path / "carla"

    def cli(raiz, *args):
        env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
        return subprocess.run(
            [sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, capture_output=True, text=True
        )

    iniciado = cli(nuevo, "init")
    niveles = [json.loads(cli(raiz, "configuracion", "ver").stdout)["autonomia"] for raiz in (a, b, nuevo)]

    assert iniciado.returncode == 0, iniciado.stderr
    assert niveles == [50, 0, 0]
    assert list((nuevo / "oportunidades").iterdir()) == []
