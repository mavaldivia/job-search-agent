import json
import os
import subprocess
import sys
from datetime import date

import pytest

from agente0.datos import ENV_VAR, REPO
from agente0.respuestas import (
    RespuestaError,
    SinRespuestaConfirmada,
    guardar,
    listar,
    pendientes,
    revisar,
    versiones,
    vigente,
)


def _cli(raiz, *args: str, entrada: str = "") -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
    return subprocess.run(
        [sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, input=entrada, capture_output=True, text=True
    )


def _usuario(raiz, categoria="renta", texto="Texto base", **extra):
    return guardar(raiz, categoria, texto, "hecho", "usuario", **extra)


def _agente(raiz, categoria="idiomas", texto="Inglés B2", **extra):
    return guardar(raiz, categoria, texto, "hecho", "agente", fuente="perfil E5", **extra)


def test_guardar_crea_la_primera_version_en_su_carpeta_y_se_recupera(tmp_path):
    respuesta = _usuario(tmp_path, fecha=date(2026, 11, 16))

    archivo = tmp_path / "respuestas" / "renta" / "v001_2026-11-16.md"
    assert archivo.is_file()
    assert respuesta.id == "renta" and respuesta.etiqueta_version == "v001"
    assert vigente(tmp_path, "renta") == respuesta


def test_editar_crea_otra_version_y_deja_intacta_la_anterior(tmp_path):
    primera = _usuario(tmp_path, texto="Primera", fecha=date(2026, 11, 16))
    antes = (tmp_path / "respuestas" / "renta" / "v001_2026-11-16.md").read_bytes()

    segunda = _usuario(tmp_path, texto="Segunda", fecha=date(2026, 12, 1))

    assert segunda.version == 2
    assert vigente(tmp_path, "renta").texto == "Segunda"
    assert [r.texto for r in versiones(tmp_path, "renta")] == ["Primera", "Segunda"]
    assert (tmp_path / "respuestas" / "renta" / "v001_2026-11-16.md").read_bytes() == antes
    assert primera.version == 1


def test_una_version_guardada_no_se_puede_sobrescribir(tmp_path):
    _usuario(tmp_path, fecha=date(2026, 11, 16))
    archivo = tmp_path / "respuestas" / "renta" / "v001_2026-11-16.md"

    with pytest.raises(PermissionError):
        archivo.write_text("pisado", encoding="utf-8")


def test_el_texto_con_saltos_y_rayas_se_recupera_igual(tmp_path):
    texto = "Primera línea\n\n---\n\nTercera: con dos puntos"
    guardar(tmp_path, "pitch-corto", texto, "narrativa", "usuario", fuente="E1, E2", notas="Sin cifras: E12.6")

    leida = vigente(tmp_path, "pitch-corto")

    assert leida.texto == texto
    assert (leida.fuente, leida.notas, leida.tipo) == ("E1, E2", "Sin cifras: E12.6", "narrativa")


def test_la_variante_de_la_familia_manda_y_si_falta_se_usa_la_general(tmp_path):
    guardar(tmp_path, "motivacion", "General", "narrativa", "usuario")
    guardar(tmp_path, "motivacion", "Para optimización", "narrativa", "usuario", variante="familia-b")

    especifica = vigente(tmp_path, "motivacion", "familia-b")
    respaldo = vigente(tmp_path, "motivacion", "familia-a")

    assert (especifica.texto, especifica.id) == ("Para optimización", "motivacion.familia-b")
    assert (respaldo.texto, respaldo.id) == ("General", "motivacion")


def test_sin_general_ni_variante_hay_que_pedir_intervencion(tmp_path):
    guardar(tmp_path, "motivacion", "Solo familia b", "narrativa", "usuario", variante="familia-b")

    with pytest.raises(SinRespuestaConfirmada):
        vigente(tmp_path, "motivacion", "familia-a")
    with pytest.raises(SinRespuestaConfirmada):
        vigente(tmp_path, "inexistente")


def test_listar_trae_la_vigente_de_cada_categoria_y_variante(tmp_path):
    _usuario(tmp_path, "renta", "v1")
    _usuario(tmp_path, "renta", "v2")
    guardar(tmp_path, "motivacion", "General", "narrativa", "usuario")
    guardar(tmp_path, "motivacion", "Familia b", "narrativa", "usuario", variante="familia-b")

    assert [(r.id, r.texto) for r in listar(tmp_path)] == [
        ("motivacion", "General"),
        ("motivacion.familia-b", "Familia b"),
        ("renta", "v2"),
    ]


def test_el_agente_exige_fuente(tmp_path):
    with pytest.raises(ValueError, match="fuente"):
        guardar(tmp_path, "idiomas", "Inglés B2", "hecho", "agente")

    assert not (tmp_path / "respuestas" / "idiomas").exists()


def test_el_agente_solo_crea_la_primera_version_de_un_id(tmp_path):
    _usuario(tmp_path, "idiomas", "Del usuario")

    with pytest.raises(RespuestaError, match="no edita"):
        _agente(tmp_path, "idiomas", "Del agente")

    assert vigente(tmp_path, "idiomas").texto == "Del usuario"


def test_el_tipo_de_un_id_no_cambia_entre_versiones(tmp_path):
    _usuario(tmp_path, "renta")

    with pytest.raises(RespuestaError, match="tipo"):
        guardar(tmp_path, "renta", "Ahora narrativa", "narrativa", "usuario")


@pytest.mark.parametrize("categoria", ["../fuera", "Con Mayusculas", "con espacio", "a/b", ""])
def test_los_nombres_invalidos_no_salen_de_la_carpeta_de_respuestas(tmp_path, categoria):
    with pytest.raises(ValueError):
        _usuario(tmp_path, categoria)

    assert list(tmp_path.iterdir()) == []


def test_lo_que_guarda_el_agente_queda_pendiente_hasta_que_se_revisa(tmp_path):
    _usuario(tmp_path, "renta")
    guardada = _agente(tmp_path)

    assert [r.id for r in pendientes(tmp_path)] == ["idiomas"]
    assert vigente(tmp_path, "idiomas") == guardada

    revisar(tmp_path, "idiomas", 1, "aprobada")

    assert pendientes(tmp_path) == []
    assert vigente(tmp_path, "idiomas") == guardada


def test_una_respuesta_rechazada_deja_de_ser_vigente_y_no_vuelve_a_pendiente(tmp_path):
    _agente(tmp_path)

    revisar(tmp_path, "idiomas", 1, "rechazada")

    assert pendientes(tmp_path) == []
    with pytest.raises(SinRespuestaConfirmada):
        vigente(tmp_path, "idiomas")
    assert _usuario(tmp_path, "idiomas", "Corregida").version == 2
    assert vigente(tmp_path, "idiomas").texto == "Corregida"


def test_editar_una_version_del_agente_la_saca_de_pendientes(tmp_path):
    _agente(tmp_path)

    _usuario(tmp_path, "idiomas", "Inglés B2 alto")

    assert pendientes(tmp_path) == []
    assert vigente(tmp_path, "idiomas").texto == "Inglés B2 alto"
    revisiones = (tmp_path / "respuestas" / "revisiones.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(revisiones[0])["resultado"] == "editada"


def test_solo_se_revisan_versiones_del_agente_y_una_sola_vez(tmp_path):
    _usuario(tmp_path, "renta")
    _agente(tmp_path)
    revisar(tmp_path, "idiomas", 1, "aprobada")

    with pytest.raises(RespuestaError, match="pendiente"):
        revisar(tmp_path, "renta", 1, "aprobada")
    with pytest.raises(RespuestaError, match="pendiente"):
        revisar(tmp_path, "idiomas", 1, "rechazada")
    with pytest.raises(RespuestaError, match="no existe"):
        revisar(tmp_path, "idiomas", 7, "aprobada")
    with pytest.raises(RespuestaError, match="editada"):
        revisar(tmp_path, "idiomas", 1, "editada")


def test_el_cli_guarda_recupera_y_revisa(tmp_path):
    entrada = json.dumps(
        {"categoria": "idiomas", "texto": "Inglés B2", "tipo": "hecho", "aprobada_por": "agente", "fuente": "E5"}
    )
    assert _cli(tmp_path, "respuestas", "guardar", entrada=entrada).returncode == 0

    ver = _cli(tmp_path, "respuestas", "ver", "idiomas", "familia-a")
    pendientes_antes = json.loads(_cli(tmp_path, "respuestas", "pendientes").stdout)
    aprobar = json.dumps({"categoria": "idiomas", "version": 1, "resultado": "aprobada"})
    revisada = _cli(tmp_path, "respuestas", "revisar", entrada=aprobar)
    pendientes_despues = json.loads(_cli(tmp_path, "respuestas", "pendientes").stdout)
    listadas = json.loads(_cli(tmp_path, "respuestas", "listar").stdout)

    assert ver.returncode == 0 and json.loads(ver.stdout)["id"] == "idiomas"
    assert [r["id"] for r in pendientes_antes] == ["idiomas"]
    assert revisada.returncode == 0 and pendientes_despues == []
    assert listadas[0]["etiqueta_version"] == "v001"


def test_el_cli_falla_con_mensaje_si_no_hay_respuesta_confirmada(tmp_path):
    resultado = _cli(tmp_path, "respuestas", "ver", "renta")

    assert resultado.returncode == 1
    assert "sin respuesta confirmada" in resultado.stderr
