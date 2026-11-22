import csv
import os
from pathlib import Path

from agente0 import oportunidades, postulaciones
from agente0.datos import cargar_configuracion
from agente0.esquemas import Priorizacion
from agente0.ids import url_canonica
from agente0.oportunidades import Oportunidad
from agente0.ranking import puntuar

ARCHIVO = "postulaciones.csv"
STATUS_POR_DEFECTO = "Postulado sin validar"
# `status` y `notas` son del usuario: validar contra el correo del portal, anotar datos pedidos.
# `accionables` lo escribe el agente (`poner_accionables`): lo que viene después, por ejemplo una prueba
# por completar, con su enlace.
COLUMNAS = (
    "id",
    "fecha_postulacion",
    "rol",
    "empresa",
    "status",
    "accionables",
    "portal",
    "renta_clp_liquida",
    "renta_declarada",
    "fit_tengo",
    "fit_quiero",
    "fit_total",
    "brecha_principal",
    "autonomia",
    "url",
    "notas",
)


def _oportunidad_de(raiz: Path, postulacion: postulaciones.Postulacion) -> Oportunidad | None:
    # El ID de la postulación coincide con el de la oportunidad salvo que la empresa se haya escrito distinto.
    try:
        return oportunidades.cargar(raiz, postulacion.id)
    except oportunidades.OportunidadError:
        pass
    url = url_canonica(postulacion.url)
    return next((o for o in oportunidades.listar(raiz) if url_canonica(o.url) == url), None)


def _fila(
    raiz: Path, postulacion: postulaciones.Postulacion, priorizacion: Priorizacion
) -> dict[str, str | int | float]:
    oportunidad = _oportunidad_de(raiz, postulacion)
    envio = postulaciones.instantanea(raiz, postulacion.id, postulacion.intentos)
    fila: dict[str, str | int | float] = {
        "id": postulacion.id,
        "fecha_postulacion": (postulacion.fecha_postulacion.isoformat() if postulacion.fecha_postulacion else ""),
        "rol": postulacion.cargo,
        "empresa": postulacion.empresa,
        "portal": envio.portal or "",
        "renta_clp_liquida": envio.renta_clp_liquida or "",
        "renta_declarada": envio.renta_declarada or "",
        "autonomia": (envio.nivel_efectivo if envio.nivel_efectivo is not None else envio.autonomia),
        "url": postulacion.url,
        "status": STATUS_POR_DEFECTO,
        "accionables": "",
        "notas": "",
    }
    if oportunidad is not None:
        if not fila["portal"]:
            # Envíos anteriores a B11 no traen el portal: sale de la fuente de la oportunidad que calza con el enlace.
            url = url_canonica(postulacion.url)
            fuente = next(
                (f for f in oportunidad.fuentes if url_canonica(f.url) == url),
                oportunidad.fuentes[0],
            )
            fila["portal"] = fuente.nombre
        if oportunidad.evaluacion:
            quiero, tengo, total, _ = puntuar(oportunidad, priorizacion)
            fila |= {
                "fit_tengo": tengo,
                "fit_quiero": quiero,
                "fit_total": total,
                "brecha_principal": oportunidad.evaluacion.brecha_principal,
            }
    return fila


def _leer(archivo: Path) -> tuple[list[str], list[dict[str, str]]]:
    with archivo.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        return list(lector.fieldnames or []), list(lector)


def _ordenar(existentes: list[str]) -> list[str]:
    # Las columnas conocidas van en el orden de `COLUMNAS`; las que el usuario agregó quedan al final.
    return [*COLUMNAS, *(c for c in existentes if c not in COLUMNAS)]


def _escribir(archivo: Path, campos: list[str], filas: list[dict[str, str]]) -> None:
    temporal = archivo.with_suffix(".csv.tmp")
    # utf-8-sig: Excel y Numbers reconocen así las tildes.
    with temporal.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", restval="")
        escritor.writeheader()
        escritor.writerows(filas)
    os.replace(temporal, archivo)


def sincronizar(raiz: Path) -> list[str]:
    """Agrega a `postulaciones.csv` cada postulación confirmada que aún no está, con el status por defecto.

    Solo agrega: las filas existentes no se tocan, así que el status, los accionables y las notas sobrevuelven
    a cualquier sincronización. Si el archivo viene con otro orden de columnas o le faltan columnas nuevas, lo
    reordena y completa sin perder datos ni columnas del usuario. Es idempotente, por lo que dos carriles que lo
    corran a la vez no pierden filas de forma permanente (la siguiente corrida repone la que quedó fuera).
    Devuelve los ID agregados.
    """
    archivo = raiz / ARCHIVO
    existentes: list[str] = []
    filas: list[dict[str, str]] = []
    if archivo.exists():
        existentes, filas = _leer(archivo)
    campos = _ordenar(existentes)
    ya_estan = {f["id"] for f in filas}
    priorizacion = cargar_configuracion(raiz).priorizacion
    nuevas = [
        _fila(raiz, p, priorizacion)
        for p in postulaciones.listar(raiz)
        if p.fecha_postulacion is not None and p.id not in ya_estan
    ]
    if not nuevas and (not archivo.exists() or existentes == campos):
        return []
    nuevas.sort(key=lambda f: (f["fecha_postulacion"], f["id"]))
    _escribir(archivo, campos, filas + nuevas)
    return [str(f["id"]) for f in nuevas]


def poner_accionables(raiz: Path, id_: str, texto: str) -> None:
    """Escribe la columna `accionables` de una postulación (texto vacío la limpia) sin tocar el resto."""
    archivo = raiz / ARCHIVO
    if not archivo.exists():
        raise ValueError(f"no existe {ARCHIVO}: corre `planilla sync` antes")
    existentes, filas = _leer(archivo)
    fila = next((f for f in filas if f["id"] == id_), None)
    if fila is None:
        raise ValueError(f"la postulación {id_} no está en {ARCHIVO}")
    fila["accionables"] = texto.strip()
    _escribir(archivo, _ordenar(existentes), filas)
