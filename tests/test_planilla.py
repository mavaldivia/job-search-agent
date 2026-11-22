import csv
import json
import os
import subprocess
import sys
from datetime import date

import pytest

from agente0.datos import ENV_VAR, REPO, crear_estructura
from agente0.oportunidades import evaluar, registrar
from agente0.planilla import ARCHIVO, COLUMNAS, STATUS_POR_DEFECTO, sincronizar
from agente0.postulaciones import Envio, Evidencia, confirmar_envio, crear, intentar_envio
from tests.test_oportunidades import VIGENCIA, criterios, filtros

URL = "https://empleos.example.com/vacante/{}"


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    return tmp_path


def _leer(raiz) -> list[dict[str, str]]:
    with (raiz / ARCHIVO).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _vacante(raiz, n: int, evaluada: bool = True) -> str:
    o = registrar(raiz, f"Empresa {n}", f"Cargo {n}", URL.format(n), VIGENCIA)
    if evaluada:
        evaluar(raiz, o.id, f"Publicación {n}", criterios(80, 60), filtros(), f"Brecha {n}")
    return o.id


def _postulada(raiz, tmp_path, n: int, confirmar: bool = True, **renta) -> str:
    id_ = _vacante(raiz, n)
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"pdf")
    crear(raiz, f"Empresa {n}", f"Cargo {n}", URL.format(n))
    intentar_envio(
        raiz,
        id_,
        Envio(autonomia=50, aprobacion="usuario", cv=cv, portal="Portal Ejemplo", **renta),
    )
    if confirmar:
        confirmar_envio(raiz, id_, Evidencia(tipo="confirmacion_visible", detalle="folio"))
    return id_


def test_agrega_las_confirmadas_con_el_status_por_defecto_y_sus_datos(raiz, tmp_path):
    id_ = _postulada(
        raiz,
        tmp_path,
        1,
        renta_declarada="CLP 3.900.000 líquidos",
        renta_clp_liquida=3900000,
    )

    assert sincronizar(raiz) == [id_]

    (fila,) = _leer(raiz)
    assert list(fila) == list(COLUMNAS)
    assert fila["id"] == id_
    assert (fila["rol"], fila["empresa"], fila["portal"]) == (
        "Cargo 1",
        "Empresa 1",
        "Portal Ejemplo",
    )
    assert fila["renta_clp_liquida"] == "3900000"
    assert fila["renta_declarada"] == "CLP 3.900.000 líquidos"
    assert fila["status"] == STATUS_POR_DEFECTO == "Postulado sin validar"
    assert (fila["fit_tengo"], fila["fit_quiero"]) == ("80.0", "60.0")
    assert fila["brecha_principal"] == "Brecha 1"
    assert fila["autonomia"] == "50"


def test_sin_renta_declarada_la_deja_en_blanco(raiz, tmp_path):
    _postulada(raiz, tmp_path, 1)

    sincronizar(raiz)

    (fila,) = _leer(raiz)
    assert fila["renta_clp_liquida"] == fila["renta_declarada"] == ""


def test_solo_entran_las_postulaciones_confirmadas(raiz, tmp_path):
    _postulada(raiz, tmp_path, 1, confirmar=False)
    crear(raiz, "Empresa 2", "Cargo 2", URL.format(2))
    confirmada = _postulada(raiz, tmp_path, 3)

    assert sincronizar(raiz) == [confirmada]
    assert [f["id"] for f in _leer(raiz)] == [confirmada]


def test_sin_confirmadas_no_crea_el_archivo(raiz):
    assert sincronizar(raiz) == []
    assert not (raiz / ARCHIVO).exists()


def test_no_duplica_ni_pisa_lo_que_edito_el_usuario(raiz, tmp_path):
    primera = _postulada(raiz, tmp_path, 1)
    sincronizar(raiz)
    editado = [{**f, "status": "Validado por correo", "notas": "me pidieron una prueba"} for f in _leer(raiz)]
    with (raiz / ARCHIVO).open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(editado)
    segunda = _postulada(raiz, tmp_path, 2)

    assert sincronizar(raiz) == [segunda]
    assert sincronizar(raiz) == []

    filas = _leer(raiz)
    assert [f["id"] for f in filas] == [primera, segunda]
    assert (filas[0]["status"], filas[0]["notas"]) == (
        "Validado por correo",
        "me pidieron una prueba",
    )
    assert filas[1]["status"] == STATUS_POR_DEFECTO


def test_conserva_las_columnas_que_el_usuario_agrego(raiz, tmp_path):
    _postulada(raiz, tmp_path, 1)
    sincronizar(raiz)
    anteriores = _leer(raiz)
    with (raiz / ARCHIVO).open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=[*COLUMNAS, "mi_columna"])
        escritor.writeheader()
        escritor.writerows({**fila, "mi_columna": "dato mío"} for fila in anteriores)
    _postulada(raiz, tmp_path, 2)

    sincronizar(raiz)

    filas = _leer(raiz)
    assert [f["mi_columna"] for f in filas] == ["dato mío", ""]


def test_sin_evaluacion_deja_el_fit_en_blanco_y_el_portal_sale_del_envio(raiz, tmp_path):
    registrar(raiz, "Sin Evaluar", "Cargo", URL.format(99), VIGENCIA)
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"pdf")
    postulacion = crear(raiz, "Sin Evaluar", "Cargo", URL.format(99))
    intentar_envio(
        raiz,
        postulacion.id,
        Envio(autonomia=0, aprobacion="usuario", cv=cv, portal="Portal Ejemplo"),
    )
    confirmar_envio(raiz, postulacion.id, Evidencia(tipo="correo", detalle="folio"))

    sincronizar(raiz)

    (fila,) = _leer(raiz)
    assert fila["fit_tengo"] == fila["fit_quiero"] == fila["fit_total"] == ""
    assert fila["portal"] == "Portal Ejemplo"


def test_cli_confirmar_actualiza_la_planilla_sin_pedirlo(tmp_path):
    raiz = tmp_path / "datos"
    raiz.mkdir()
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}

    def cli(*args, entrada=""):
        return subprocess.run(
            [sys.executable, "-m", "agente0", *args],
            cwd=REPO,
            env=env,
            input=entrada,
            capture_output=True,
            text=True,
        )

    assert cli("init").returncode == 0
    hoy = {
        "verificada_el": date.today().isoformat(),
        "fuente": "portal",
        "evidencia": "botón visible",
    }
    vacante = {
        "empresa": "Acme",
        "cargo": "Jefe",
        "url": URL.format(1),
        "vigencia": hoy,
    }
    assert cli("oportunidad", "registrar", entrada=json.dumps(vacante)).returncode == 0
    portal = {
        "nombre": "Portal Ejemplo",
        "tipo": "generalista",
        "pais": "Chile",
        "metodo": "web",
        "riesgo": "bajo",
    }
    assert cli("fuentes", "agregar", entrada=json.dumps(portal)).returncode == 0
    id_ = json.loads(
        cli(
            "postulacion",
            "crear",
            entrada=json.dumps({k: vacante[k] for k in ("empresa", "cargo", "url")}),
        ).stdout
    )["id"]
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"pdf")
    juicios = {
        "cv_auditado": {"cumple": True, "evidencia": "auditoría aprobada"},
        "respuestas_documentadas": {"cumple": True, "evidencia": "biblioteca"},
    }
    solicitud = {
        "portal": "Portal Ejemplo",
        "cv": str(cv),
        "juicios": juicios,
        "aprobacion": "usuario",
        "renta_declarada": "USD 4.750 brutos mensuales",
    }
    intento = cli("postulacion", "intentar", id_, entrada=json.dumps(solicitud))
    assert intento.returncode == 0, intento.stderr
    assert not (raiz / ARCHIVO).exists()

    confirmacion = cli(
        "postulacion",
        "confirmar",
        id_,
        entrada=json.dumps({"tipo": "correo", "detalle": "folio"}),
    )

    assert confirmacion.returncode == 0, confirmacion.stderr
    (fila,) = _leer(raiz)
    assert (fila["id"], fila["status"], fila["renta_declarada"]) == (
        id_,
        STATUS_POR_DEFECTO,
        "USD 4.750 brutos mensuales",
    )
    assert fila["renta_clp_liquida"] == ""
    assert cli("planilla", "sync").stdout.strip() == "[]"
