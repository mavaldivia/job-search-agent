import json
import os
import subprocess
import sys
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from agente0.configuracion import editar
from agente0.datos import ENV_VAR, REPO, crear_estructura
from agente0.mercado import MercadoError, RangoMercado, buscar, evaluar, guardar, listar
from agente0.oportunidades import cargar, observar_renta, registrar

CHILE = "CLP líquido mensual"
USD = "USD bruto mensual"
FUENTE = {"nombre": "Guía salarial", "url": "https://sueldos.example.com/datos", "dato": "Rango publicado del rol."}
VIGENCIA = {"verificada_el": date.today().isoformat(), "fuente": "portal", "evidencia": "botón visible"}


def rango(**cambios) -> RangoMercado:
    base = {
        "rol": "Data Lead",
        "seniority": "Lead",
        "mercado": "Chile",
        "unidad": CHILE,
        "p50": 3_200_000,
        "p75": 3_600_000,
        "p90": 4_200_000,
        "confianza": "media",
        "metodo": "Percentiles interpolados del rango publicado.",
        "fuentes": [FUENTE],
        "investigado": date.today(),
    }
    return RangoMercado.model_validate({**base, **cambios})


def vacante(raiz, n: int = 1, empresa: str = "Acme", **datos) -> str:
    return registrar(raiz, empresa, f"Cargo {n}", f"https://empleos.example.com/vacante/{n}", VIGENCIA, **datos).id


def pedir(raiz, id_, presencialidad="hibrida", lejos_de_casa=False, **extra):
    datos = {
        "rol": "Data Lead",
        "seniority": "Lead",
        "mercado": "Chile",
        "presencialidad": presencialidad,
        "lejos_de_casa": lejos_de_casa,
        "evidencia": "La publicación indica la modalidad.",
        **extra,
    }
    return evaluar(raiz, id_, **datos)


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    editar(tmp_path, {"priorizacion": {"renta_minima": 3_000_000}})
    guardar(tmp_path, rango())
    return tmp_path


@pytest.mark.parametrize(
    "presencialidad, lejos, esperado",
    [
        ("remota", False, 3_600_000),
        ("hibrida", False, 3_600_000),
        ("alta", False, 3_600_000),
        ("alta", True, 4_200_000),
        ("total", False, 4_200_000),
        ("total", True, 4_200_000),
    ],
)
def test_el_percentil_propuesto_depende_de_la_modalidad(raiz, presencialidad, lejos, esperado):
    resultado = pedir(raiz, vacante(raiz), presencialidad, lejos)

    assert resultado.propuesta.monto == esperado
    assert resultado.propuesta.percentil == (90 if esperado == 4_200_000 else 75)


def test_la_propuesta_nunca_baja_de_la_renta_minima(raiz):
    editar(raiz, {"priorizacion": {"renta_minima": 3_900_000}})

    resultado = pedir(raiz, vacante(raiz))

    assert (resultado.propuesta.monto, resultado.propuesta.subida_a_minima) == (3_900_000, True)


def test_sin_p90_publicado_se_usa_el_75_y_se_avisa(raiz):
    guardar(raiz, rango(rol="Otro Rol", p90=None))

    resultado = pedir(raiz, vacante(raiz), "total", rol="Otro Rol")

    assert (resultado.propuesta.percentil, resultado.propuesta.monto) == (75, 3_600_000)
    assert "no publica el percentil 90" in resultado.propuesta.nota


def test_el_techo_de_renta_limita_la_propuesta_y_es_la_referencia_de_la_omision(raiz):
    editar(raiz, {"mercado": {"renta_maxima": 3_300_000}})
    cubre, no_cubre = vacante(raiz, 1, renta_publicada=3_400_000), vacante(raiz, 2, renta_publicada=3_200_000)

    resultado = pedir(raiz, cubre, "total")
    omitida = pedir(raiz, no_cubre, "total")

    assert (resultado.propuesta.monto, resultado.propuesta.bajada_a_maxima) == (3_300_000, True)
    assert (resultado.cuadre.resultado, resultado.sugerida) == ("cuadra", 3_300_000)
    assert omitida.cuadre.resultado == "omitir"


def test_el_techo_nunca_deja_la_propuesta_bajo_la_minima_y_debe_ser_coherente_con_ella(raiz):
    editar(raiz, {"mercado": {"renta_maxima": 3_500_000}})
    assert pedir(raiz, vacante(raiz)).propuesta.monto == 3_500_000

    editar(raiz, {"mercado": {"renta_maxima": 2_900_000}})
    with pytest.raises(MercadoError, match="techo de renta"):
        pedir(raiz, vacante(raiz))


def test_un_rango_en_otra_unidad_exige_el_techo_convertido_si_hay_techo(raiz):
    guardar(raiz, rango(mercado="Remoto internacional", unidad=USD, p50=3_000, p75=3_500, p90=4_000))
    editar(raiz, {"mercado": {"renta_maxima": 4_400_000}})
    datos = {"mercado": "Remoto internacional", "minima_equivalente": 2_800}

    with pytest.raises(MercadoError, match="maxima_equivalente"):
        pedir(raiz, vacante(raiz), "total", **datos)
    resultado = pedir(raiz, vacante(raiz), "total", maxima_equivalente=3_700, **datos)

    assert (resultado.propuesta.monto, resultado.propuesta.bajada_a_maxima) == (3_700, True)


def test_los_percentiles_se_editan_en_la_configuracion(raiz):
    editar(raiz, {"mercado": {"percentil_base": 50}})

    assert pedir(raiz, vacante(raiz)).propuesta.monto == 3_200_000


def test_en_un_cargo_presencial_se_omite_si_el_tope_publicado_queda_bajo_la_renta_propuesta(raiz):
    id_ = vacante(raiz, renta_publicada=4_000_000)

    sin_aplicar = pedir(raiz, id_, "total")

    assert sin_aplicar.cuadre.resultado == "omitir" and not sin_aplicar.descartada
    assert cargar(raiz, id_).estado == "POTENCIAL"

    aplicada = pedir(raiz, id_, "total", aplicar=True)

    assert aplicada.descartada
    o = cargar(raiz, id_)
    assert o.estado == "DESCARTADO" and "sin cuadre de renta" in o.motivo


def test_en_un_cargo_presencial_cuadra_si_el_tope_cubre_la_renta_propuesta(raiz):
    resultado = pedir(raiz, vacante(raiz, renta_publicada=4_300_000), "total", aplicar=True)

    assert (resultado.cuadre.resultado, resultado.sugerida, resultado.descartada) == ("cuadra", 4_200_000, False)


@pytest.mark.parametrize(
    "publicada, esperado, sugerida",
    [(2_800_000, "omitir", 3_600_000), (3_400_000, "cuadra", 3_400_000), (3_600_000, "cuadra", 3_600_000)],
)
def test_fuera_de_lo_presencial_solo_se_omite_si_el_tope_queda_bajo_la_renta_minima(
    raiz, publicada, esperado, sugerida
):
    resultado = pedir(raiz, vacante(raiz, renta_publicada=publicada))

    assert (resultado.cuadre.resultado, resultado.sugerida) == (esperado, sugerida)


def test_sin_tope_en_la_oferta_no_se_omite_nada(raiz):
    id_ = vacante(raiz)

    resultado = pedir(raiz, id_, "total", aplicar=True)

    assert (resultado.cuadre.resultado, resultado.sugerida, resultado.descartada) == ("sin_dato", 4_200_000, False)
    assert cargar(raiz, id_).estado == "POTENCIAL"


def test_el_tope_observado_en_el_formulario_tambien_decide_la_omision(raiz):
    omite, ambigua = vacante(raiz, 1), vacante(raiz, 2)
    observar_renta(raiz, omite, unidad=CHILE, acepta_hasta=3_800_000, avisa_desde=4_000_000, evidencia="Aviso.")
    observar_renta(raiz, ambigua, unidad=CHILE, acepta_hasta=3_800_000, avisa_desde=4_400_000, evidencia="Aviso.")

    assert pedir(raiz, omite, "total").cuadre.resultado == "omitir"
    assert pedir(raiz, ambigua, "total").cuadre.resultado == "sin_dato"


def test_un_rango_en_otra_unidad_exige_la_minima_convertida_y_no_usa_la_renta_publicada(raiz):
    guardar(raiz, rango(mercado="Remoto internacional", unidad=USD, p50=3_000, p75=3_500, p90=4_000))
    id_ = vacante(raiz, renta_publicada=1_000)
    datos = {"mercado": "Remoto internacional", "aplicar": True}

    with pytest.raises(MercadoError, match="minima_equivalente"):
        pedir(raiz, id_, "total", **datos)
    resultado = pedir(raiz, id_, "total", minima_equivalente=2_800, **datos)

    assert (resultado.propuesta.monto, resultado.propuesta.unidad) == (4_000, USD)
    assert (resultado.cuadre.resultado, resultado.descartada) == ("sin_dato", False)


def test_un_rango_vencido_o_ausente_se_niega_y_pide_investigar(raiz):
    guardar(raiz, rango(rol="Analytics Lead", investigado=date.today() - timedelta(days=40)))

    with pytest.raises(MercadoError, match="investígalo de nuevo"):
        buscar(raiz, "Analytics Lead", "Lead", "Chile")
    with pytest.raises(MercadoError, match="no hay rango"):
        buscar(raiz, "Otro Rol", "Lead", "Chile")
    assert {e.rango.rol: e.vigente for e in listar(raiz)} == {"Data Lead": True, "Analytics Lead": False}


def test_el_rango_de_la_empresa_prevalece_sobre_el_general(raiz):
    guardar(raiz, rango(empresa="Acme", p50=4_000_000, p75=4_400_000, p90=5_000_000))

    de_acme = pedir(raiz, vacante(raiz, 1, "Acme"))
    de_otra = pedir(raiz, vacante(raiz, 2, "Otra"))

    assert (de_acme.propuesta.monto, de_otra.propuesta.monto) == (4_400_000, 3_600_000)


def test_guardar_reemplaza_el_rango_con_la_misma_clave(raiz):
    guardar(raiz, rango(p75=3_700_000))

    assert [e.rango.p75 for e in listar(raiz)] == [3_700_000]


@pytest.mark.parametrize(
    "cambios",
    [{"p75": 3_000_000}, {"p90": 3_500_000}, {"confianza": "dudosa"}, {"fuentes": []}, {"metodo": ""}, {"p50": 0}],
)
def test_un_rango_sin_fuente_o_con_percentiles_desordenados_no_se_guarda(cambios):
    with pytest.raises(ValidationError):
        rango(**cambios)


def test_cli_evalua_la_renta_y_descarta_la_vacante_sin_cuadre(raiz):
    id_ = vacante(raiz, renta_publicada=4_000_000)
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
    entrada = {
        "rol": "Data Lead",
        "seniority": "Lead",
        "mercado": "Chile",
        "presencialidad": "total",
        "evidencia": "Cargo 100 % presencial.",
        "aplicar": True,
    }

    resultado = subprocess.run(
        [sys.executable, "-m", "agente0", "mercado", "evaluar", id_],
        cwd=REPO,
        env=env,
        input=json.dumps(entrada),
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert json.loads(resultado.stdout)["descartada"] is True
    assert cargar(raiz, id_).estado == "DESCARTADO"
