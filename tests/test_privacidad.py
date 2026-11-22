import json
import os
import subprocess
import sys

import pytest

from agente0.datos import ENV_VAR, REPO, DatosError, crear_estructura, datos_dir
from agente0.privacidad import LISTA, revisar, valores_sensibles

# Todo lo de este archivo es inventado: ningún valor real puede vivir en el repo público.
PERFIL = """# Perfil de Ana

## E1 · Nombre completo en el CV

Ana Pérez Rojas

- Correo: ana.perez@example.com
- Teléfono: +56 9 1234 5678
- LinkedIn: linkedin.com/in/anaperezrojas
"""
DATOS_PERSONALES = "RUT 11.111.111-1. Fecha de nacimiento 05-03-1990. Dirección: Calle Falsa 123, Providencia"
RENTA = "Preferencia $2.750.000 líquidos mensuales"
VALORES_EN_ARCHIVOS = {
    "nombre.md": "Ana Pérez Rojas",
    "correo.md": "escríbele a ANA.PEREZ@example.com",
    "telefono.md": "llámala al 56912345678",
    "rut.md": "su RUT es 11111111-1",
    "nacimiento.md": "nació el 1990-03-05",
    "direccion.md": "vive en calle falsa 123",
    "usuario.md": "perfil en anaperezrojas",
    "renta.md": "pide 2750000 líquidos",
    "lista.md": "trabaja en Empresa Ficticia",
}


@pytest.fixture
def datos(tmp_path):
    raiz = tmp_path / "datos"
    crear_estructura(raiz)
    (raiz / "perfil" / "perfil.md").write_text(PERFIL, encoding="utf-8")
    for categoria, texto in (("datos-personales", DATOS_PERSONALES), ("renta", RENTA)):
        carpeta = raiz / "respuestas" / categoria
        carpeta.mkdir(parents=True)
        (carpeta / "v001_2026-01-01.md").write_text(texto, encoding="utf-8")
    (raiz / LISTA).write_text("# comentario\nEmpresa Ficticia\n", encoding="utf-8")
    return raiz


@pytest.fixture
def repo(tmp_path):
    carpeta = tmp_path / "repo"
    carpeta.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=carpeta, check=True)
    (carpeta / "README.md").write_text("Un agente de búsqueda laboral con ejemplos inventados.\n", encoding="utf-8")
    return carpeta


def _cli(repo, datos, entrada, *args, con_datos=True):
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR}
    if con_datos:
        env[ENV_VAR] = str(datos)
    return subprocess.run(
        [sys.executable, "-m", "agente0", "privacidad", *args, str(repo)],
        cwd=REPO,
        env=env,
        input=entrada,
        capture_output=True,
        text=True,
    )


def test_saca_cada_tipo_de_valor_de_los_datos_privados(datos):
    assert set(valores_sensibles(datos).values()) == {
        "RUT",
        "correo",
        "teléfono",
        "fecha de nacimiento",
        "dirección",
        "nombre completo",
        "usuario de LinkedIn o GitHub",
        "monto de renta",
        f"cadena de {LISTA}",
    }


def test_un_repo_limpio_no_da_hallazgos(datos, repo):
    assert revisar(repo, datos) == []


def test_encuentra_cada_valor_en_sus_variantes_y_sin_repetirlo(datos, repo):
    for nombre, texto in VALORES_EN_ARCHIVOS.items():
        (repo / nombre).write_text(texto + "\n", encoding="utf-8")

    hallazgos = revisar(repo, datos)

    assert {h.archivo for h in hallazgos} == set(VALORES_EN_ARCHIVOS)
    assert all(h.linea == 1 for h in hallazgos)
    salida = "\n".join(str(h) for h in hallazgos).lower()
    for valor in ("ana", "perez", "1234", "11111111", "1990", "falsa", "2750000", "ficticia"):
        assert valor not in salida


def test_ignora_lo_que_git_ignora_y_los_binarios(datos, repo):
    (repo / ".gitignore").write_text("privado.txt\n", encoding="utf-8")
    (repo / "privado.txt").write_text("Ana Pérez Rojas", encoding="utf-8")
    (repo / "imagen.bin").write_bytes(b"\xff\xfe\x00Ana P\xe9rez Rojas")

    assert revisar(repo, datos) == []


def test_el_hook_bloquea_un_commit_si_hay_datos_en_lo_versionado(datos, repo):
    (repo / "nota.md").write_text("Ana Pérez Rojas\n", encoding="utf-8")
    evento = json.dumps({"tool_input": {"command": "git commit -m 'cambios'"}})

    resultado = _cli(repo, datos, evento, "--hook")

    assert resultado.returncode == 2
    assert "nota.md:1: nombre completo" in resultado.stderr
    assert "Pérez" not in resultado.stderr


def test_el_hook_bloquea_un_mensaje_de_commit_con_datos(datos, repo):
    evento = json.dumps({"tool_input": {"command": "git commit -m 'agrega la renta 2750000'"}})

    resultado = _cli(repo, datos, evento, "--hook")

    assert resultado.returncode == 2
    assert "(comando de git)" in resultado.stderr


def test_el_hook_deja_pasar_lo_que_no_es_commit_ni_push_y_lo_limpio(datos, repo):
    (repo / "nota.md").write_text("Ana Pérez Rojas\n", encoding="utf-8")

    assert _cli(repo, datos, json.dumps({"tool_input": {"command": "ls -la"}}), "--hook").returncode == 0
    assert _cli(repo, datos, json.dumps({"tool_input": {"command": "git status"}}), "--hook").returncode == 0
    assert _cli(repo, datos, "no es json", "--hook").returncode == 0
    (repo / "nota.md").unlink()
    assert _cli(repo, datos, json.dumps({"tool_input": {"command": "git push"}}), "--hook").returncode == 0


def test_sin_carpeta_de_datos_el_hook_se_omite_y_la_revision_manual_falla(datos, repo):
    (repo / "nota.md").write_text("Ana Pérez Rojas\n", encoding="utf-8")
    evento = json.dumps({"tool_input": {"command": "git commit -m x"}})

    assert _cli(repo, datos, evento, "--hook", con_datos=False).returncode == 0
    assert _cli(repo, datos, "", con_datos=False).returncode == 1


def test_el_repo_real_no_lleva_datos_del_usuario():
    try:
        raiz = datos_dir()
    except DatosError:
        pytest.skip("sin carpeta de datos propia no hay valores que buscar")

    assert revisar(REPO, raiz) == []
