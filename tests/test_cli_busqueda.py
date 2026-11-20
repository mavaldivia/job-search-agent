import json
import os
import subprocess
import sys

import pytest

from agente0.datos import ENV_VAR, REPO, crear_estructura
from tests.test_oportunidades import URL, VIGENCIA, criterios, filtros


def _cli(raiz, *args: str, entrada: str = "") -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
    return subprocess.run(
        [sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, input=entrada, capture_output=True, text=True
    )


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    return tmp_path


def test_flujo_completo_por_cli_hasta_el_ranking(raiz):
    registrada = _cli(
        raiz,
        "oportunidad",
        "registrar",
        entrada=json.dumps({"empresa": "Acme", "cargo": "Jefe de Datos", "url": URL, "vigencia": VIGENCIA}),
    )
    assert registrada.returncode == 0, registrada.stderr
    id_ = json.loads(registrada.stdout)["id"]

    evaluada = _cli(
        raiz,
        "oportunidad",
        "evaluar",
        id_,
        entrada=json.dumps(
            {
                "publicacion": "Texto literal de la vacante.",
                "criterios": criterios(80, 60),
                "filtros": filtros(),
                "brecha_principal": "Falta experiencia en el sector.",
            }
        ),
    )
    assert evaluada.returncode == 0, evaluada.stderr

    generado = _cli(raiz, "ranking", "generar")
    assert generado.returncode == 0, generado.stderr
    top = json.loads(generado.stdout)["top"]
    assert [(e["id"], e["cambio"], e["total"]) for e in top] == [(id_, "NUEVA", 71.0)]

    assert json.loads(_cli(raiz, "ranking", "ultimo").stdout)["top"][0]["id"] == id_
    assert [o["id"] for o in json.loads(_cli(raiz, "oportunidad", "listar", "POTENCIAL").stdout)] == [id_]


def test_configuracion_ver_muestra_la_priorizacion_vigente_aunque_el_archivo_no_la_tenga(raiz):
    (raiz / "configuracion" / "configuracion.json").write_text('{"autonomia": 25}', encoding="utf-8")

    resultado = _cli(raiz, "configuracion", "ver")

    efectiva = json.loads(resultado.stdout)
    assert (resultado.returncode, efectiva["autonomia"], efectiva["priorizacion"]["top"]) == (0, 25, 10)


def test_ranking_ultimo_sin_ranking_lo_dice(raiz):
    resultado = _cli(raiz, "ranking", "ultimo")

    assert (resultado.returncode, resultado.stdout.strip()) == (0, "sin_ranking")


def test_cambiar_estado_y_fuentes_por_cli(raiz):
    id_ = json.loads(
        _cli(
            raiz,
            "oportunidad",
            "registrar",
            entrada=json.dumps({"empresa": "Acme", "cargo": "Jefe de Datos", "url": URL, "vigencia": VIGENCIA}),
        ).stdout
    )["id"]
    cerrada = _cli(
        raiz, "oportunidad", "estado", id_, entrada=json.dumps({"nuevo": "CERRADO", "motivo": "cerrada en el portal"})
    )
    assert json.loads(cerrada.stdout)["estado"] == "CERRADO"

    fuente = {"nombre": "Get on Board", "tipo": "especializada", "pais": "Chile", "metodo": "web", "riesgo": "bajo"}
    assert _cli(raiz, "fuentes", "agregar", entrada=json.dumps(fuente)).returncode == 0
    assert [f["nombre"] for f in json.loads(_cli(raiz, "fuentes", "listar").stdout)] == ["Get on Board"]


@pytest.mark.parametrize(
    "args, entrada",
    [
        (("oportunidad", "ver", "no-existe"), ""),
        (("oportunidad", "listar", "INVENTADO"), ""),
        (("oportunidad", "registrar"), "{no es json"),
        (("fuentes", "agregar"), json.dumps({"nombre": "X"})),
    ],
)
def test_los_errores_salen_con_codigo_1_y_mensaje(raiz, args, entrada):
    resultado = _cli(raiz, *args, entrada=entrada)

    assert resultado.returncode == 1
    assert resultado.stderr.startswith("error:")


def test_busqueda_por_cli_registra_consulta_calcula_pendiente_cupo_y_reconoce_vistas(raiz):
    fuente = {"nombre": "LinkedIn Jobs", "tipo": "generalista", "pais": "Chile", "metodo": "navegador", "riesgo": "alto"}
    assert _cli(raiz, "fuentes", "guardar", entrada=json.dumps([fuente])).returncode == 0

    consulta = _cli(
        raiz,
        "busqueda",
        "consulta",
        entrada=json.dumps(
            {
                "fuente": "LinkedIn Jobs",
                "consulta": "Data Science Lead",
                "paginas": 3,
                "lecturas": 9,
                "vistas": 60,
                "nuevas": 5,
                "cubre_desde": "2026-10-21",
            }
        ),
    )
    assert consulta.returncode == 0, consulta.stderr

    pendiente = _cli(
        raiz, "busqueda", "pendiente", entrada=json.dumps({"fuente": "LinkedIn Jobs", "consulta": "data science lead"})
    )
    assert pendiente.returncode == 0, pendiente.stderr
    assert json.loads(pendiente.stdout)[-1]["hasta"] == json.loads(consulta.stdout)["fecha"][:10]

    cupo = json.loads(_cli(raiz, "busqueda", "cupo", entrada=json.dumps({"fuente": "LinkedIn Jobs"})).stdout)
    assert (cupo["primera_pasada"], cupo["paginas_usadas_hoy"], cupo["paginas_restantes"]) == (True, 3, None)

    vista = _cli(
        raiz,
        "busqueda",
        "vista",
        entrada=json.dumps(
            {
                "fuente": "LinkedIn Jobs",
                "empresa": "Beta",
                "cargo": "Gerente de Ventas",
                "url": "https://www.linkedin.com/jobs/view/1",
                "motivo": "mal fit declarado",
            }
        ),
    )
    assert vista.returncode == 0, vista.stderr
    conocida = _cli(raiz, "busqueda", "conocida", entrada=json.dumps({"url": "https://www.linkedin.com/jobs/view/1/"}))
    assert json.loads(conocida.stdout)["origen"] == "VISTA"
    desconocida = _cli(raiz, "busqueda", "conocida", entrada=json.dumps({"url": "https://www.linkedin.com/jobs/view/2"}))
    assert desconocida.stdout.strip() == "no_conocida"
    assert [r["ultima_busqueda"] is not None for r in json.loads(_cli(raiz, "busqueda", "resumen").stdout)] == [True]


def test_busqueda_por_cli_rechaza_una_fuente_desconocida(raiz):
    resultado = _cli(
        raiz,
        "busqueda",
        "consulta",
        entrada=json.dumps(
            {"fuente": "Nada", "consulta": "x", "paginas": 1, "lecturas": 1, "vistas": 1, "nuevas": 0, "cubre_desde": "2026-11-01"}
        ),
    )

    assert resultado.returncode == 1
    assert "no está en fuentes.json" in resultado.stderr
