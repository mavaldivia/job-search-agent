import os
import subprocess
import sys

import pytest

from agente0.datos import (
    ARCHIVO_CONFIGURACION,
    DIRECTORIOS,
    ENV_VAR,
    REPO,
    DatosError,
    cargar_configuracion,
    crear_estructura,
    datos_dir,
)


def _cli(env_extra: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | env_extra
    return subprocess.run(
        [sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, capture_output=True, text=True
    )


def test_crear_estructura_genera_el_arbol_y_una_configuracion_valida(tmp_path):
    crear_estructura(tmp_path)

    for directorio in DIRECTORIOS:
        assert (tmp_path / directorio).is_dir()
    configuracion = cargar_configuracion(tmp_path)
    assert configuracion.autonomia == 0
    assert configuracion.recordatorios_dias.experiencia == 15


def test_crear_estructura_es_idempotente_y_no_pisa_lo_editado(tmp_path):
    crear_estructura(tmp_path)
    (tmp_path / ARCHIVO_CONFIGURACION).write_text('{"autonomia": 50}', encoding="utf-8")
    (tmp_path / "origen" / "perfil.md").write_text("datos del usuario", encoding="utf-8")

    crear_estructura(tmp_path)

    assert cargar_configuracion(tmp_path).autonomia == 50
    assert (tmp_path / "origen" / "perfil.md").read_text(encoding="utf-8") == "datos del usuario"


def test_configuracion_con_clave_mal_escrita_falla(tmp_path):
    crear_estructura(tmp_path)
    (tmp_path / ARCHIVO_CONFIGURACION).write_text('{"autonomya": 50}', encoding="utf-8")

    with pytest.raises(ValueError):
        cargar_configuracion(tmp_path)


def test_datos_dir_sin_variable_falla(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    with pytest.raises(DatosError, match=ENV_VAR):
        datos_dir()


def test_datos_dir_con_carpeta_inexistente_falla_salvo_que_no_se_exija(monkeypatch, tmp_path):
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "no_existe"))
    with pytest.raises(DatosError, match="no existe"):
        datos_dir()
    assert datos_dir(debe_existir=False) == (tmp_path / "no_existe").resolve()


def test_datos_dir_rechaza_rutas_dentro_del_repo(monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(REPO / "docs" / "usuarios"))
    with pytest.raises(DatosError, match="dentro del repo"):
        datos_dir(debe_existir=False)


def test_datos_dir_devuelve_la_carpeta_del_usuario(monkeypatch, tmp_path):
    monkeypatch.setenv(ENV_VAR, str(tmp_path))
    assert datos_dir() == tmp_path.resolve()


def test_cli_init_crea_la_estructura_en_la_ruta_de_la_variable(tmp_path):
    raiz = tmp_path / "Agente0-datos"

    resultado = _cli({ENV_VAR: str(raiz)}, "init")

    assert resultado.returncode == 0, resultado.stderr
    assert (raiz / "postulaciones").is_dir()
    assert cargar_configuracion(raiz).autonomia == 0


def test_cli_init_sin_variable_sale_con_error_y_no_crea_nada(tmp_path):
    resultado = _cli({}, "init")

    assert resultado.returncode == 1
    assert ENV_VAR in resultado.stderr
