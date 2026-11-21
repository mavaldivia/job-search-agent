import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

import pytest

from agente0.datos import ENV_VAR, REPO, crear_estructura
from agente0.recordatorios import fecha_ultima_operacion, pendientes, registrar_operacion, registrar_pregunta
from agente0.revisiones import Revision, registrar_revision

HOY = datetime(2026, 11, 19, 10, 0)


def _cli(raiz, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
    return subprocess.run([sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, capture_output=True, text=True)


def _casos(raiz, ahora=HOY) -> list[str]:
    return [p.caso for p in pendientes(raiz, ahora)]


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    (tmp_path / "perfil" / "perfil.md").write_text("onboarding_completo: 2026-11-01\n", encoding="utf-8")
    return tmp_path


def test_nada_vencido_al_poco_del_onboarding(raiz):
    assert _casos(raiz, datetime(2026, 11, 15)) == []


def test_experiencia_vence_a_los_15_dias_desde_la_ultima_revision(raiz):
    registrar_revision(raiz, Revision(fecha=date(2026, 11, 4), modo="cuentame"))
    assert _casos(raiz, datetime(2026, 11, 18, 9, 0)) == []
    vencidos = pendientes(raiz, datetime(2026, 11, 19, 9, 0))
    assert [(p.caso, p.dias_desde, p.ventana_dias) for p in vencidos] == [("experiencia", 15, 15)]


def test_configuracion_sin_registro_mide_desde_el_onboarding(raiz):
    assert "configuracion" not in _casos(raiz, datetime(2026, 12, 30))
    assert "configuracion" in _casos(raiz, datetime(2026, 12, 31))


def test_cv_base_usa_la_mas_reciente_entre_carpeta_y_ejecucion_de_investigar_cv(raiz):
    (raiz / "cv" / "base" / "2026-10-01").mkdir(parents=True)
    (raiz / "cv" / "base" / "borrador").mkdir()
    assert fecha_ultima_operacion(raiz, "cv_base") == date(2026, 10, 1)
    registrar_operacion(raiz, "cv_base", date(2026, 11, 10))
    assert fecha_ultima_operacion(raiz, "cv_base") == date(2026, 11, 10)


def test_cv_base_sin_carpeta_ni_registro_no_se_pregunta(raiz):
    assert fecha_ultima_operacion(raiz, "cv_base") is None
    assert "cv_base" not in _casos(raiz, datetime(2027, 6, 1))


def test_ahora_no_no_reinicia_el_reloj_y_calla_solo_24_horas(raiz):
    registrar_revision(raiz, Revision(fecha=date(2026, 11, 1), modo="cuentame"))
    assert _casos(raiz) == ["experiencia"]
    registrar_pregunta(raiz, "experiencia", HOY)
    assert _casos(raiz, HOY + timedelta(hours=23, minutes=59)) == []
    siguiente = pendientes(raiz, HOY + timedelta(hours=24))
    assert [(p.caso, p.ultima_operacion) for p in siguiente] == [("experiencia", date(2026, 11, 1))]


def test_solo_se_silencia_el_caso_preguntado(raiz):
    registrar_revision(raiz, Revision(fecha=date(2026, 9, 1), modo="cuentame"))
    ahora = datetime(2027, 1, 20)
    assert _casos(raiz, ahora) == ["experiencia", "configuracion"]
    registrar_pregunta(raiz, "experiencia", ahora)
    assert _casos(raiz, ahora + timedelta(hours=1)) == ["configuracion"]


def test_la_repeticion_en_horas_es_configurable(raiz):
    registrar_revision(raiz, Revision(fecha=date(2026, 11, 1), modo="cuentame"))
    archivo = raiz / "configuracion" / "configuracion.json"
    configuracion = json.loads(archivo.read_text(encoding="utf-8")) | {"repetir_recordatorio_horas": 2}
    archivo.write_text(json.dumps(configuracion), encoding="utf-8")
    registrar_pregunta(raiz, "experiencia", HOY)
    assert _casos(raiz, HOY + timedelta(hours=1)) == []
    assert _casos(raiz, HOY + timedelta(hours=2)) == ["experiencia"]


def test_hacer_la_operacion_reinicia_el_reloj(raiz):
    ahora = datetime(2027, 1, 20)
    assert "configuracion" in _casos(raiz, ahora)
    registrar_operacion(raiz, "configuracion", ahora.date())
    assert "configuracion" not in _casos(raiz, ahora)


def test_experiencia_no_se_registra_en_recordatorios(raiz):
    with pytest.raises(ValueError, match="bitácora de revisiones"):
        registrar_operacion(raiz, "experiencia")


def test_cli_pendientes_preguntado_y_operacion(raiz):
    registrar_revision(raiz, Revision(fecha=date(2020, 1, 1), modo="cuentame"))
    salida = _cli(raiz, "recordatorio", "pendientes")
    assert salida.returncode == 0
    assert [p["caso"] for p in json.loads(salida.stdout)][0] == "experiencia"

    assert _cli(raiz, "recordatorio", "preguntado", "experiencia").returncode == 0
    assert "experiencia" not in [p["caso"] for p in json.loads(_cli(raiz, "recordatorio", "pendientes").stdout)]

    assert _cli(raiz, "recordatorio", "operacion", "cv_base").returncode == 0
    assert (raiz / "configuracion" / "recordatorios.json").exists()


def test_cli_rechaza_caso_desconocido_y_operacion_de_experiencia(raiz):
    assert _cli(raiz, "recordatorio", "preguntado", "otro").returncode == 2
    asignada = _cli(raiz, "recordatorio", "operacion", "experiencia")
    assert asignada.returncode == 1
    assert "bitácora de revisiones" in asignada.stderr


def test_terminos_no_se_preguntan_sin_una_renovacion_registrada(raiz):
    assert fecha_ultima_operacion(raiz, "terminos") is None
    assert "terminos" not in _casos(raiz, datetime(2027, 6, 1))


def test_terminos_vencen_a_los_15_dias_desde_su_ultima_renovacion(raiz):
    registrar_operacion(raiz, "terminos", date(2026, 11, 20))

    antes = _casos(raiz, datetime(2026, 12, 4))
    vencido = [p for p in pendientes(raiz, datetime(2026, 12, 5)) if p.caso == "terminos"]

    assert "terminos" not in antes
    assert [(p.dias_desde, p.ventana_dias) for p in vencido] == [(15, 15)]


def test_renovar_los_terminos_reinicia_su_reloj_y_el_cli_lo_registra(raiz):
    registrar_operacion(raiz, "terminos", date(2026, 10, 1))
    assert "terminos" in _casos(raiz, HOY)

    assert _cli(raiz, "recordatorio", "operacion", "terminos").returncode == 0

    assert "terminos" not in [p["caso"] for p in json.loads(_cli(raiz, "recordatorio", "pendientes").stdout)]


def test_el_cli_dice_la_fecha_de_la_ultima_operacion_o_que_no_hay_registro(raiz):
    assert _cli(raiz, "recordatorio", "ultima", "terminos").stdout.strip() == "sin_registro"

    registrar_operacion(raiz, "terminos", date(2026, 11, 20))

    assert _cli(raiz, "recordatorio", "ultima", "terminos").stdout.strip() == "2026-11-20"
