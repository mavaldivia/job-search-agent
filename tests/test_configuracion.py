import json
import os
import subprocess
import sys
from datetime import datetime

import pytest

from agente0 import fuentes
from agente0.autonomia import AutonomiaError, aviso, vista_previa
from agente0.configuracion import ARCHIVO_AUTONOMIA, ConfiguracionError, editar
from agente0.datos import ARCHIVO_CONFIGURACION, ENV_VAR, REPO, cargar_configuracion, crear_estructura


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    fuentes.guardar(
        tmp_path,
        [
            {"nombre": "Portal Bajo", "tipo": "generalista", "pais": "Chile", "metodo": "web", "riesgo": "bajo"},
            {"nombre": "Portal Alto", "tipo": "generalista", "pais": "Chile", "metodo": "navegador", "riesgo": "alto"},
            {
                "nombre": "Portal Inactivo",
                "tipo": "generalista",
                "pais": "Chile",
                "metodo": "web",
                "riesgo": "bajo",
                "activa": False,
            },
        ],
    )
    return tmp_path


def bitacora(raiz) -> list[dict]:
    archivo = raiz / ARCHIVO_AUTONOMIA
    return [json.loads(linea) for linea in archivo.read_text(encoding="utf-8").splitlines()] if archivo.exists() else []


def test_un_cambio_parcial_fusiona_clave_a_clave_y_conserva_el_resto(raiz):
    editar(raiz, {"compuerta": {"pausa_minutos": 5}, "priorizacion": {"umbrales": {"tengo": 80}}})

    c = cargar_configuracion(raiz)

    assert (c.compuerta.pausa_minutos, c.compuerta.limites_diarios.alto) == (5, 3)
    assert (c.priorizacion.umbrales.tengo, c.priorizacion.umbrales.quiero) == (80, 60)
    assert len(c.priorizacion.criterios) == 6


def test_los_mapas_se_reemplazan_completos(raiz):
    editar(raiz, {"compuerta": {"topes_por_portal": {"Portal Alto": 75}}})
    editar(raiz, {"compuerta": {"topes_por_portal": {"Portal Bajo": 25}, "tope_por_riesgo": {}}})

    c = cargar_configuracion(raiz).compuerta

    assert (c.topes_por_portal, c.tope_por_riesgo) == ({"Portal Bajo": 25}, {})


def test_un_cambio_invalido_se_rechaza_y_no_toca_el_archivo(raiz):
    antes = (raiz / ARCHIVO_CONFIGURACION).read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        editar(raiz, {"compuerta": {"pausa_minutos": -1}})
    with pytest.raises(ValueError):
        editar(raiz, {"compuerta": {"inventado": 1}})

    assert (raiz / ARCHIVO_CONFIGURACION).read_text(encoding="utf-8") == antes


def test_un_nivel_intermedio_se_redondea_hacia_abajo_y_se_avisa(raiz):
    _, advertencias = editar(raiz, {"autonomia": 60})

    assert cargar_configuracion(raiz).autonomia == 50
    assert any("redondeada hacia abajo a 50" in a for a in advertencias)


def test_cada_cambio_de_autonomia_queda_en_la_bitacora_y_los_demas_no(raiz):
    editar(raiz, {"autonomia": 25}, ahora=datetime(2026, 11, 20, 9, 0).astimezone())
    editar(raiz, {"compuerta": {"pausa_minutos": 3}})
    editar(raiz, {"autonomia": 25})
    editar(raiz, {"autonomia": 0})

    registros = bitacora(raiz)

    assert [(r["de"], r["a"]) for r in registros] == [(0, 25), (25, 0)]
    assert registros[0]["fecha"].startswith("2026-11-20T09:00")


def test_activar_100_exige_la_confirmacion_y_la_deja_registrada_con_fecha(raiz):
    antes = (raiz / ARCHIVO_CONFIGURACION).read_text(encoding="utf-8")

    with pytest.raises(ConfiguracionError, match="100 %"):
        editar(raiz, {"autonomia": 100})
    with pytest.raises(ConfiguracionError):
        editar(raiz, {"autonomia": 100}, confirmacion="   ")
    assert (raiz / ARCHIVO_CONFIGURACION).read_text(encoding="utf-8") == antes and bitacora(raiz) == []

    editar(raiz, {"autonomia": 100}, confirmacion="Sí, activa el 100 % tras ver el aviso")

    (registro,) = bitacora(raiz)
    assert (registro["a"], registro["confirmacion"]) == (100, "Sí, activa el 100 % tras ver el aviso")
    assert registro["fecha"]


def test_bajar_de_100_y_editar_otra_cosa_estando_en_100_no_piden_confirmacion(raiz):
    editar(raiz, {"autonomia": 100}, confirmacion="ok")

    editar(raiz, {"compuerta": {"pausa_minutos": 4}})
    editar(raiz, {"autonomia": 50})

    assert [(r["de"], r["a"]) for r in bitacora(raiz)] == [(0, 100), (100, 50)]


def test_subir_a_75_sin_listas_avisa_que_nada_se_enviara_solo(raiz):
    _, sin_listas = editar(raiz, {"autonomia": 75})
    _, con_listas = editar(
        raiz, {"compuerta": {"seniority_permitido": ["Lead"], "ubicaciones_permitidas": ["santiago"]}}
    )

    assert len(sin_listas) == 2 and con_listas == []


def test_la_vista_previa_describe_cada_nivel_de_d12():
    assert vista_previa(0) == [
        "0 %: CV: tú apruebas; respuestas: tú apruebas; formulario: tú apruebas; envío: tú apruebas"
    ]
    assert "respuestas: revisas lo nuevo o sensible" in vista_previa(50)[0]
    assert "solo si cumple las condiciones de preferencia" in vista_previa(75)[0]
    assert len(vista_previa()) == 5
    with pytest.raises(AutonomiaError, match="nivel inválido"):
        vista_previa(60)


def test_el_aviso_de_100_lista_portales_limites_y_lo_que_deja_de_regir(raiz):
    texto = "\n".join(aviso(raiz, 100))

    assert "Portal Bajo (riesgo bajo): nivel 100 %, envío automático, hasta 8 por día" in texto
    assert "Portal Alto (riesgo alto): nivel 50 %, envío con tu aprobación, hasta 3 por día" in texto
    assert "Portal Inactivo" not in texto
    assert "Pausa mínima entre envíos: 2 minutos" in texto
    assert "Dejan de regir: seniority, ubicacion, umbral_match, sin_proceso_activo, renta_minima" in texto


def test_el_aviso_respeta_las_excepciones_configuradas(raiz):
    editar(raiz, {"compuerta": {"siempre_aprobar_portales": ["portal bajo"], "siempre_aprobar_empresas": ["Acme"]}})

    texto = "\n".join(aviso(raiz, 100))

    assert "Portal Bajo (riesgo bajo): nivel 100 %, envío con tu aprobación" in texto
    assert "Siempre con tu aprobación: empresas Acme" in texto


def _cli(raiz, *args, entrada=""):
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
    return subprocess.run(
        [sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, input=entrada, capture_output=True, text=True
    )


def test_cli_edita_la_configuracion_y_muestra_matriz_y_aviso(raiz):
    sin_confirmar = _cli(raiz, "configuracion", "editar", entrada='{"cambios": {"autonomia": 100}}')
    editada = _cli(raiz, "configuracion", "editar", entrada='{"cambios": {"autonomia": 100}, "confirmacion": "ok"}')
    matriz = _cli(raiz, "autonomia", "matriz", "75")
    todas = _cli(raiz, "autonomia", "matriz")
    texto = _cli(raiz, "autonomia", "aviso", "100")
    mal = _cli(raiz, "autonomia", "aviso")

    assert sin_confirmar.returncode == 1 and "100 %" in sin_confirmar.stderr
    assert editada.returncode == 0, editada.stderr
    assert json.loads(editada.stdout)["configuracion"]["autonomia"] == 100
    assert matriz.stdout.startswith("75 %:") and len(todas.stdout.splitlines()) == 5
    assert "Envíos por portal:" in texto.stdout
    assert mal.returncode == 1
