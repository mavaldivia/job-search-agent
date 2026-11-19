import os
import subprocess
import sys
from datetime import date

import pytest

from agente0.datos import ENV_VAR, REPO
from agente0.revisiones import ARCHIVO_REVISIONES, Cambio, Revision, fecha_ultima_revision, registrar_revision


def _cli(raiz, *args: str, entrada: str = "") -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
    return subprocess.run(
        [sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, input=entrada, capture_output=True, text=True
    )


def _perfil(raiz, texto: str) -> None:
    (raiz / "perfil").mkdir(exist_ok=True)
    (raiz / "perfil" / "perfil.md").write_text(texto, encoding="utf-8")


def test_sin_bitacora_ni_perfil_no_hay_fecha(tmp_path):
    assert fecha_ultima_revision(tmp_path) is None


def test_sin_bitacora_usa_la_fecha_del_onboarding(tmp_path):
    _perfil(tmp_path, "# Perfil\n\nonboarding_completo: 2026-11-16\n\n## E1\n")

    assert fecha_ultima_revision(tmp_path) == date(2026, 11, 16)


def test_la_ultima_revision_registrada_manda_sobre_el_onboarding(tmp_path):
    _perfil(tmp_path, "onboarding_completo: 2026-11-16\n")
    registrar_revision(tmp_path, Revision(fecha=date(2026, 11, 20), modo="cuentame"))
    registrar_revision(
        tmp_path,
        Revision(fecha=date(2026, 12, 1), modo="preguntame", cambios=[Cambio(seccion="E8b", resumen="Proyecto medido")]),
    )

    assert fecha_ultima_revision(tmp_path) == date(2026, 12, 1)
    assert len((tmp_path / ARCHIVO_REVISIONES).read_text(encoding="utf-8").splitlines()) == 2


def test_una_revision_sin_cambios_es_valida(tmp_path):
    registrar_revision(tmp_path, Revision(fecha=date(2026, 11, 20), modo="preguntame"))

    assert fecha_ultima_revision(tmp_path) == date(2026, 11, 20)


def test_una_entrada_de_diario_es_un_cambio_valido():
    assert Cambio(seccion="diario", resumen="Brasil 2027").seccion == "diario"


@pytest.mark.parametrize("seccion", ["", "8", "X1", "E8B", "perfil", "Diario"])
def test_seccion_invalida_se_rechaza(seccion):
    with pytest.raises(ValueError):
        Cambio(seccion=seccion, resumen="algo")


def test_modo_invalido_se_rechaza():
    with pytest.raises(ValueError):
        Revision(modo="libre")


def test_cli_registrar_y_consultar_la_ultima_revision(tmp_path):
    antes = _cli(tmp_path, "revision", "ultima")
    assert antes.stdout.strip() == "sin_revision"

    entrada = '{"fecha": "2026-11-20", "modo": "cuentame", "cambios": [{"seccion": "E6", "resumen": "Nuevo alcance"}]}'
    registro = _cli(tmp_path, "revision", "registrar", entrada=entrada)
    despues = _cli(tmp_path, "revision", "ultima")

    assert registro.returncode == 0, registro.stderr
    assert despues.stdout.strip() == "2026-11-20"


def test_cli_registrar_con_json_invalido_falla_y_no_escribe(tmp_path):
    resultado = _cli(tmp_path, "revision", "registrar", entrada='{"modo": "libre"}')

    assert resultado.returncode == 1
    assert not (tmp_path / ARCHIVO_REVISIONES).exists()
