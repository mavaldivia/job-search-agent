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
# `status` y `notas` son del usuario: validar contra el correo del portal, anotar pruebas o datos pedidos.
COLUMNAS = (
    "id",
    "fecha_postulacion",
    "rol",
    "empresa",
    "portal",
    "renta_clp_liquida",
    "renta_declarada",
    "fit_tengo",
    "fit_quiero",
    "fit_total",
    "brecha_principal",
    "autonomia",
    "url",
    "status",
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


def sincronizar(raiz: Path) -> list[str]:
    """Agrega a `postulaciones.csv` cada postulación confirmada que aún no está, con el status por defecto.

    Solo agrega: las filas existentes no se tocan, así que el status y las notas del usuario sobrevuelven a
    cualquier sincronización. Es idempotente, por lo que dos carriles que lo corran a la vez no pierden filas
    de forma permanente (la siguiente corrida repone la que quedó fuera). Devuelve los ID agregados.
    """
    archivo = raiz / ARCHIVO
    filas: list[dict[str, str]] = []
    campos = list(COLUMNAS)
    if archivo.exists():
        with archivo.open(encoding="utf-8-sig", newline="") as f:
            lector = csv.DictReader(f)
            campos = list(lector.fieldnames or COLUMNAS)
            filas = list(lector)
    existentes = {f["id"] for f in filas}
    priorizacion = cargar_configuracion(raiz).priorizacion
    nuevas = [
        _fila(raiz, p, priorizacion)
        for p in postulaciones.listar(raiz)
        if p.fecha_postulacion is not None and p.id not in existentes
    ]
    if not nuevas:
        return []
    nuevas.sort(key=lambda f: (f["fecha_postulacion"], f["id"]))
    temporal = archivo.with_suffix(".csv.tmp")
    # utf-8-sig: Excel y Numbers reconocen así las tildes.
    with temporal.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", restval="")
        escritor.writeheader()
        escritor.writerows(filas + nuevas)
    os.replace(temporal, archivo)
    return [str(f["id"]) for f in nuevas]
