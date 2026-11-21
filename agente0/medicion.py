from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agente0 import postulaciones, revisiones_semanales
from agente0.datos import cargar_configuracion
from agente0.esquemas import Medicion

NOTA = (
    "Asociación, no causalidad: el mercado, la estacionalidad y los cambios de CV, de autonomía o de portales "
    "se mezclan con cualquier efecto de las respuestas (D17)."
)


class Ventana(BaseModel):
    """Los envíos confirmados en un tramo de fechas (cohorte) y cuántos llegaron a un primer contacto (D17)."""

    model_config = ConfigDict(extra="forbid")

    numero: int
    desde: date
    hasta: date
    completa: bool
    # Los contactos de una cohorte siguen llegando: antes de `dias_para_resolver` desde su último envío, la cifra sube.
    madura: bool
    envios: int
    contactos: int
    tasa_contacto: float | None
    horas_esfuerzo: float | None
    contactos_por_hora: float | None
    conclusion: Literal["sin_conclusion", "con_datos"]


class Comparacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ventana: int
    tasa_contacto_dif: float | None
    contactos_por_hora_dif: float | None
    lectura: str


class ReporteVentanas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ventana_semanas: int
    minimo_contactos: int
    # Línea base: la primera ventana, de cuando aún no había recomendaciones (D17).
    linea_base: int | None
    ventanas: list[Ventana]
    comparaciones: list[Comparacion]
    nota: str = NOTA


class UsoRespuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    respuesta_id: str
    version: str
    usos: int
    contactos: int
    tasa_suavizada: float | None
    marca: Literal["pocos_datos", "sobre_la_base", "bajo_la_base"]
    recomendar: bool


class ReporteRespuestas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usos_totales: int
    contactos_totales: int
    tasa_base: float | None
    respuestas: list[UsoRespuesta]
    nota: str = NOTA


class _Envio(BaseModel):
    id: str
    fecha: date
    contacto: bool
    resuelta: bool
    pares: list[tuple[str, str]]


def _envios(raiz: Path, config: Medicion, hoy: date) -> list[_Envio]:
    """Cada postulación con envío confirmado: su fecha, si llegó a primer contacto y las respuestas de la biblioteca."""
    envios = []
    for p in postulaciones.listar(raiz):
        if p.fecha_postulacion is None:
            continue
        eventos = postulaciones.eventos_de(raiz, p.id)
        resuelta = p.estado in ("EN_PROCESO", "FINALIZADA") or (
            hoy - p.fecha_postulacion >= timedelta(days=config.dias_para_resolver)
        )
        pares = [
            (r.respuesta_id, r.version)
            for r in postulaciones.instantanea(raiz, p.id).respuestas
            if r.respuesta_id and r.version
        ]
        envios.append(
            _Envio(
                id=p.id,
                fecha=p.fecha_postulacion,
                contacto=any(e.tipo == "PRIMER_CONTACTO_ENTREVISTA" for e in eventos),
                resuelta=resuelta,
                pares=pares,
            )
        )
    return envios


def ventanas(raiz: Path, hoy: date | None = None) -> ReporteVentanas:
    hoy = hoy or date.today()
    config = cargar_configuracion(raiz).medicion
    envios = _envios(raiz, config, hoy)
    horas = revisiones_semanales.revisiones(raiz)
    if not envios:
        return ReporteVentanas(
            ventana_semanas=config.ventana_semanas,
            minimo_contactos=config.minimo_contactos,
            linea_base=None,
            ventanas=[],
            comparaciones=[],
        )
    largo = timedelta(weeks=config.ventana_semanas)
    inicio = min(e.fecha for e in envios)
    resultado: list[Ventana] = []
    numero = 1
    while inicio + (numero - 1) * largo <= hoy:
        desde = inicio + (numero - 1) * largo
        hasta = desde + largo - timedelta(days=1)
        cohorte = [e for e in envios if desde <= e.fecha <= hasta]
        contactos = sum(e.contacto for e in cohorte)
        del_periodo = [r for r in horas if desde <= r.hasta <= hasta]
        total_horas = sum(r.horas_esfuerzo for r in del_periodo) if del_periodo else None
        resultado.append(
            Ventana(
                numero=numero,
                desde=desde,
                hasta=hasta,
                completa=hasta < hoy,
                madura=hoy - hasta >= timedelta(days=config.dias_para_resolver),
                envios=len(cohorte),
                contactos=contactos,
                tasa_contacto=round(contactos / len(cohorte), 4) if cohorte else None,
                horas_esfuerzo=total_horas,
                contactos_por_hora=round(contactos / total_horas, 4) if total_horas else None,
                conclusion="con_datos" if contactos >= config.minimo_contactos else "sin_conclusion",
            )
        )
        numero += 1
    return ReporteVentanas(
        ventana_semanas=config.ventana_semanas,
        minimo_contactos=config.minimo_contactos,
        linea_base=1,
        ventanas=resultado,
        comparaciones=[_comparar(resultado[0], v, config) for v in resultado[1:]],
    )


def _comparar(base: Ventana, ventana: Ventana, config: Medicion) -> Comparacion:
    if base.conclusion == "sin_conclusion" or ventana.conclusion == "sin_conclusion":
        return Comparacion(
            ventana=ventana.numero,
            tasa_contacto_dif=None,
            contactos_por_hora_dif=None,
            lectura=(
                f"sin conclusión: la línea base tiene {base.contactos} contactos y la ventana {ventana.numero} "
                f"tiene {ventana.contactos}; se piden al menos {config.minimo_contactos} en cada una."
            ),
        )

    def dif(a: float | None, b: float | None) -> float | None:
        return round(a - b, 4) if a is not None and b is not None else None

    return Comparacion(
        ventana=ventana.numero,
        tasa_contacto_dif=dif(ventana.tasa_contacto, base.tasa_contacto),
        contactos_por_hora_dif=dif(ventana.contactos_por_hora, base.contactos_por_hora),
        lectura="tendencia asociada frente a la línea base; no prueba que una respuesta o un cambio la causara.",
    )


def respuestas(raiz: Path, hoy: date | None = None) -> ReporteRespuestas:
    """D16: tasa de contacto por versión de respuesta, suavizada hacia la tasa base del usuario."""
    hoy = hoy or date.today()
    config = cargar_configuracion(raiz).medicion
    usadas = [e for e in _envios(raiz, config, hoy) if e.resuelta]
    usos_totales, contactos_totales = len(usadas), sum(e.contacto for e in usadas)
    base = contactos_totales / usos_totales if usos_totales else None
    por_par: dict[tuple[str, str], list[_Envio]] = {}
    for e in usadas:
        for par in set(e.pares):
            por_par.setdefault(par, []).append(e)
    filas = []
    for (respuesta_id, version), grupo in por_par.items():
        usos, contactos = len(grupo), sum(e.contacto for e in grupo)
        suavizada = (contactos + config.usos_virtuales * base) / (usos + config.usos_virtuales)
        suficiente = usos >= config.usos_para_recomendar
        filas.append(
            UsoRespuesta(
                respuesta_id=respuesta_id,
                version=version,
                usos=usos,
                contactos=contactos,
                tasa_suavizada=round(suavizada, 4),
                marca="pocos_datos" if not suficiente else ("sobre_la_base" if suavizada > base else "bajo_la_base"),
                recomendar=suficiente and suavizada > base,
            )
        )
    return ReporteRespuestas(
        usos_totales=usos_totales,
        contactos_totales=contactos_totales,
        tasa_base=round(base, 4) if base is not None else None,
        respuestas=sorted(filas, key=lambda f: (-f.usos, f.respuesta_id, f.version)),
    )
