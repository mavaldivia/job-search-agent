import json
import os
import subprocess
import sys
from datetime import date

import pytest

from agente0.configuracion import editar
from agente0.datos import ENV_VAR, REPO, crear_estructura
from agente0.renta import FactorBruto, FactorNoVigente, cerrar_monto, convertir, factor_vigente, guardar_factor

HOY = date(2026, 11, 20)
FACTOR = FactorBruto(
    investigado=date(2026, 11, 10),
    liquido_referencia=3_000_000,
    factor=1.25,
    supuestos="contrato indefinido, salud 7 %, AFP 10 % más comisión promedio",
    fuentes=["https://www.sii.cl"],
)


def _cli(raiz, *args: str, entrada: str = "") -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
    return subprocess.run(
        [sys.executable, "-m", "agente0", *args],
        cwd=REPO,
        env=env,
        input=entrada,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    return tmp_path


def test_sin_factor_guardado_pide_investigarlo(raiz):
    with pytest.raises(FactorNoVigente, match="no hay factor"):
        convertir(raiz, 3_000_000, pais="CL", a_bruto=True, hoy=HOY)


def test_factor_guardado_se_reutiliza_dentro_de_la_vigencia(raiz):
    guardar_factor(raiz, "cl", FACTOR)
    assert factor_vigente(raiz, "CL", 3_000_000, HOY) == FACTOR
    bruto = convertir(raiz, 3_000_000, pais="CL", a_bruto=True, hoy=HOY)
    assert (bruto.monto, bruto.monto_exacto) == (3_800_000, 3_750_000)


def test_factor_vence_a_los_30_dias_por_defecto(raiz):
    guardar_factor(raiz, "CL", FACTOR)
    assert factor_vigente(raiz, "CL", 3_000_000, date(2026, 12, 9)).factor == 1.25
    with pytest.raises(FactorNoVigente, match="hace 30 días"):
        factor_vigente(raiz, "CL", 3_000_000, date(2026, 12, 10))


def test_factor_no_sirve_para_un_monto_lejos_del_de_referencia(raiz):
    guardar_factor(raiz, "CL", FACTOR)
    assert factor_vigente(raiz, "CL", 3_300_000, HOY).factor == 1.25
    with pytest.raises(FactorNoVigente, match="banda"):
        factor_vigente(raiz, "CL", 3_300_001, HOY)
    with pytest.raises(FactorNoVigente, match="banda"):
        factor_vigente(raiz, "CL", 2_000_000, HOY)


def test_vigencia_y_banda_salen_de_la_configuracion(raiz):
    guardar_factor(raiz, "CL", FACTOR)
    editar(raiz, {"conversion_renta": {"vigencia_factor_dias": 5, "banda_monto_pct": 50}})
    assert factor_vigente(raiz, "CL", 4_500_000, date(2026, 11, 14)).factor == 1.25
    with pytest.raises(FactorNoVigente, match="hace 10 días"):
        factor_vigente(raiz, "CL", 3_000_000, HOY)


def test_tasa_sola_cambia_de_moneda_sin_factor(raiz):
    assert convertir(raiz, 3_000_000, tasa=1000).monto == 3_000.0


def test_bruto_y_tasa_son_dos_pasos_independientes(raiz):
    guardar_factor(raiz, "CL", FACTOR)
    resultado = convertir(raiz, 3_000_000, pais="CL", a_bruto=True, tasa=1_002.07, hoy=HOY)
    assert (resultado.factor, resultado.tasa, resultado.monto) == (
        1.25,
        1_002.07,
        3_742.25,
    )


def test_argumentos_invalidos(raiz):
    with pytest.raises(ValueError, match="nada que convertir"):
        convertir(raiz, 3_000_000)
    with pytest.raises(ValueError, match="exige el país"):
        convertir(raiz, 3_000_000, a_bruto=True)
    with pytest.raises(ValueError, match="positivos"):
        convertir(raiz, 3_000_000, tasa=0)
    with pytest.raises(ValueError, match="dos letras"):
        guardar_factor(raiz, "Chile", FACTOR)


def test_un_factor_menor_que_uno_no_se_guarda():
    with pytest.raises(ValueError):
        FactorBruto(
            investigado=HOY,
            liquido_referencia=1,
            factor=0.9,
            supuestos="x",
            fuentes=["https://x.example.com"],
        )


def test_cli_guardar_ver_y_convertir(raiz):
    factor = FACTOR.model_copy(update={"investigado": date.today()}).model_dump(mode="json")
    guardado = _cli(
        raiz,
        "renta",
        "factor",
        "guardar",
        entrada=json.dumps({"pais": "CL", "factor": factor}),
    )
    assert guardado.returncode == 0, guardado.stderr
    assert (
        json.loads((raiz / "configuracion" / "renta_factores.json").read_text(encoding="utf-8"))["CL"]["factor"] == 1.25
    )

    visto = _cli(raiz, "renta", "factor", "ver", "CL", "3000000")
    assert visto.returncode == 0 and json.loads(visto.stdout)["factor"] == 1.25

    convertido = _cli(
        raiz,
        "renta",
        "convertir",
        entrada=json.dumps({"liquido": 3_000_000, "pais": "CL", "a_bruto": True, "tasa": 1000}),
    )
    assert convertido.returncode == 0 and json.loads(convertido.stdout)["monto"] == 3_750.0


def test_cli_factor_vencido_sale_con_error_y_sin_tocar_nada(raiz):
    vencido = FACTOR.model_copy(update={"investigado": date(2020, 1, 1)})
    guardar_factor(raiz, "CL", vencido)
    antes = (raiz / "configuracion" / "renta_factores.json").read_bytes()
    resultado = _cli(
        raiz,
        "renta",
        "convertir",
        entrada=json.dumps({"liquido": 3_000_000, "pais": "CL", "a_bruto": True}),
    )
    assert resultado.returncode == 1 and "investígalo de nuevo" in resultado.stderr
    assert (raiz / "configuracion" / "renta_factores.json").read_bytes() == antes


@pytest.mark.parametrize(
    "valor, piso, techo, esperado",
    [
        (3_990_000, None, None, 4_000_000),
        (3_940_000, None, None, 3_900_000),
        (3_960_000, 3_950_000, 3_970_000, 3_950_000),
        (4_120_000, None, 4_100_000, 4_100_000),
        (3_960_000, 3_955_000, 3_965_000, 3_960_000),
    ],
)
def test_cerrar_monto_prefiere_multiplos_de_100000_y_cae_a_50000_si_no_caben(valor, piso, techo, esperado):
    assert cerrar_monto(valor, piso, techo) == esperado
