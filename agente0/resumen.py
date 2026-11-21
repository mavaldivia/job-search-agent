from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agente0 import oportunidades, postulaciones, revisiones_semanales
from agente0.configuracion import ARCHIVO_AUTONOMIA, CambioAutonomia
from agente0.datos import cargar_configuracion
from agente0.revisiones_semanales import RevisionSemanal

HITOS = ("NUEVA_ETAPA", "ENTREVISTA_REALIZADA", "OFERTA_RECIBIDA", "RECHAZO", "RETIRO", "CIERRE_POR_SILENCIO")


class EnvioResumen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    empresa: str
    cargo: str
    portal: str | None
    fecha: date
    autonomia_configurada: int
    nivel_efectivo: int | None
    # «automatico» si salió por la compuerta sin aprobación; «aprobado» si el usuario aprobó ese envío en el chat.
    resolucion: Literal["automatico", "aprobado"]
    estado_actual: str


class ResumenSemanal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desde: date
    hasta: date
    autonomia: int
    cambios_de_autonomia: list[CambioAutonomia]
    enviadas: list[EnvioResumen]
    por_portal: dict[str, int]
    automaticas: int
    aprobadas: int
    # ENVIO_INTENTADO sin confirmación: verificar en el portal o el correo antes de cualquier reintento (D14).
    por_verificar: list[str]
    # PREPARADA: esperan el OK del usuario o un reintento.
    en_cola: list[str]
    primeros_contactos: list[str]
    otros_hitos: dict[str, int]
    oportunidades_nuevas: int
    revision_anterior: RevisionSemanal | None


def _dia(momento: datetime) -> date:
    return momento.astimezone().date()


def _cambios_de_autonomia(raiz: Path, desde: date, hasta: date) -> list[CambioAutonomia]:
    archivo = raiz / ARCHIVO_AUTONOMIA
    if not archivo.exists():
        return []
    lineas = [linea for linea in archivo.read_text(encoding="utf-8").splitlines() if linea.strip()]
    cambios = [CambioAutonomia.model_validate_json(linea) for linea in lineas]
    return [c for c in cambios if desde <= _dia(c.fecha) <= hasta]


def _nuevas(raiz: Path, desde: date, hasta: date) -> int:
    nuevas = 0
    for o in oportunidades.listar(raiz):
        archivo = raiz / "oportunidades" / o.id / "eventos.jsonl"
        primera = archivo.read_text(encoding="utf-8").splitlines()[0]
        if desde <= _dia(oportunidades.Evento.model_validate_json(primera).fecha) <= hasta:
            nuevas += 1
    return nuevas


def resumir(raiz: Path, desde: date | None = None, hasta: date | None = None) -> ResumenSemanal:
    """Lo enviado y lo pendiente en el período (por defecto, desde la última revisión semanal hasta hoy)."""
    if desde is None or hasta is None:
        pendiente = revisiones_semanales.periodo_pendiente(raiz)
        desde, hasta = desde or pendiente[0], hasta or pendiente[1]
    enviadas, por_verificar, en_cola, contactos = [], [], [], []
    otros = {tipo: 0 for tipo in HITOS}
    for p in postulaciones.listar(raiz):
        eventos = postulaciones.eventos_de(raiz, p.id)
        if p.estado == "ENVIO_INTENTADO":
            por_verificar.append(p.id)
        elif p.estado == "PREPARADA":
            en_cola.append(p.id)
        confirmado = next((e for e in eventos if e.tipo == "CAMBIO_ESTADO" and e.estado == "POSTULADO"), None)
        if confirmado is not None and desde <= _dia(confirmado.fecha) <= hasta:
            envio = postulaciones.instantanea(raiz, p.id)
            enviadas.append(
                EnvioResumen(
                    id=p.id,
                    empresa=p.empresa,
                    cargo=p.cargo,
                    portal=envio.portal,
                    fecha=_dia(confirmado.fecha),
                    autonomia_configurada=envio.autonomia,
                    nivel_efectivo=envio.nivel_efectivo,
                    resolucion="automatico" if envio.aprobacion.startswith("automático") else "aprobado",
                    estado_actual=p.estado,
                )
            )
        for e in eventos:
            if not desde <= _dia(e.fecha) <= hasta:
                continue
            if e.tipo == "PRIMER_CONTACTO_ENTREVISTA":
                contactos.append(p.id)
            elif e.tipo in otros:
                otros[e.tipo] += 1
    por_portal: dict[str, int] = {}
    for e in enviadas:
        por_portal[e.portal or "sin portal"] = por_portal.get(e.portal or "sin portal", 0) + 1
    previas = revisiones_semanales.revisiones(raiz)
    return ResumenSemanal(
        desde=desde,
        hasta=hasta,
        autonomia=cargar_configuracion(raiz).autonomia,
        cambios_de_autonomia=_cambios_de_autonomia(raiz, desde, hasta),
        enviadas=sorted(enviadas, key=lambda e: e.fecha),
        por_portal=por_portal,
        automaticas=sum(e.resolucion == "automatico" for e in enviadas),
        aprobadas=sum(e.resolucion == "aprobado" for e in enviadas),
        por_verificar=por_verificar,
        en_cola=en_cola,
        primeros_contactos=contactos,
        otros_hitos={k: v for k, v in otros.items() if v},
        oportunidades_nuevas=_nuevas(raiz, desde, hasta),
        revision_anterior=previas[-1] if previas else None,
    )
