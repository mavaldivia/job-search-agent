from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agente0 import autonomia, configuracion, fuentes, oportunidades, postulaciones, ranking
from agente0.autonomia import Juicios, JuicioValor
from agente0.datos import cargar_configuracion
from agente0.esquemas import Compuerta, Configuracion
from agente0.fuentes import FuenteBusqueda
from agente0.ids import slug_empresa
from agente0.oportunidades import Estado, Oportunidad

# `auto_condicionado`: automático si el agente califica seniority y ubicación dentro de las listas al enviar.
Destino = Literal["fuera", "sin_evaluacion", "cola", "auto_condicionado", "auto"]

NO_SIMULADO = [
    "seniority y ubicación: las califica el agente al enviar (se suponen dentro de las listas permitidas)",
    "vigencia verificada hoy, CV auditado y respuestas documentadas: dependen del momento de postular",
    "límites diarios y pausa entre envíos: dependen de lo enviado ese día",
]
_SUPUESTO = "supuesto de la simulación: lo califica el agente al enviar"
# Para una vacante sin portal en las fuentes del usuario: sin tope de nivel ni excepciones por portal.
_SIN_PORTAL = FuenteBusqueda(nombre="(sin portal)", tipo="generalista", pais="-", metodo="web", riesgo="bajo")


class Resultado(BaseModel):
    """Qué pasa con una vacante bajo una configuración."""

    model_config = ConfigDict(extra="forbid")

    destino: Destino
    motivos: list[str]
    quiero: float | None = None
    tengo: float | None = None
    cumple_umbrales: bool | None = None
    # Lugar en el Top; None si quedó fuera de él.
    posicion: int | None = None
    nivel_efectivo: int | None = None


class Fila(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    empresa: str
    cargo: str
    estado: Estado
    # Ya no es POTENCIAL: se muestra como evidencia para calibrar, no como candidata.
    referencial: bool
    actual: Resultado
    hipotetica: Resultado
    cambios: list[str]


class Simulacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nivel_actual: int
    nivel_hipotetico: int
    advertencias: list[str]
    filas: list[Fila]
    no_simulado: list[str]


def simular(raiz: Path, cambios: dict) -> Simulacion:
    """D11 y D12 con una configuración hipotética, sobre las evaluaciones guardadas. No escribe nada."""
    actual = cargar_configuracion(raiz)
    hipotetica, advertencias = configuracion.aplicar(actual, cambios)
    todas = postulaciones.listar(raiz)
    portales = fuentes.cargar(raiz)
    previo = ranking.ultimo(raiz)
    ids_previos = [e.id for e in previo.top] if previo else []
    vacantes = [o for o in oportunidades.listar(raiz) if o.estado != "CERRADO"]

    antes = _resultados(vacantes, actual, todas, portales, ids_previos)
    despues = _resultados(vacantes, hipotetica, todas, portales, ids_previos)
    sin_portal = [o for o in vacantes if _portal(o, portales, actual.compuerta) is None]
    advertencias += [f"{o.id}: sin portal en tus fuentes; se supuso sin tope de nivel." for o in sin_portal]

    filas = [
        Fila(
            id=o.id,
            empresa=o.empresa,
            cargo=o.cargo,
            estado=o.estado,
            referencial=o.estado != "POTENCIAL",
            actual=antes[o.id],
            hipotetica=despues[o.id],
            cambios=_diferencias(antes[o.id], despues[o.id]),
        )
        for o in vacantes
    ]
    filas.sort(key=lambda f: (f.hipotetica.posicion is None, f.hipotetica.posicion or 0, f.id))
    return Simulacion(
        nivel_actual=actual.autonomia,
        nivel_hipotetico=hipotetica.autonomia,
        advertencias=advertencias,
        filas=filas,
        no_simulado=NO_SIMULADO,
    )


def _resultados(
    vacantes: list[Oportunidad],
    config: Configuracion,
    todas: list[postulaciones.Postulacion],
    portales: list[FuenteBusqueda],
    ids_previos: list[str],
) -> dict[str, Resultado]:
    prio = config.priorizacion
    resultados: dict[str, Resultado] = {}
    puntuadas = {}
    for o in vacantes:
        en_proceso = {slug_empresa(p.empresa) for p in todas if p.estado != "FINALIZADA" and p.id != o.id}
        motivo = ranking.motivo_de_descarte(o, prio, en_proceso)
        if motivo:
            resultados[o.id] = Resultado(destino="fuera", motivos=[motivo])
        elif o.evaluacion is None or set(o.evaluacion.criterios) != set(prio.criterios):
            resultados[o.id] = Resultado(
                destino="sin_evaluacion", motivos=["la vacante no tiene una evaluación vigente con estos criterios"]
            )
        else:
            puntuadas[o.id] = (o, ranking.puntuar(o, prio))

    orden = ranking.ordenar_top({i: p[1][2] for i, p in puntuadas.items()}, ids_previos, prio.top)
    for id_, (o, (quiero, tengo, _, _)) in puntuadas.items():
        destino, motivos, nivel = _destino(o, config, todas, _portal(o, portales, config.compuerta))
        resultados[id_] = Resultado(
            destino=destino,
            motivos=motivos,
            quiero=quiero,
            tengo=tengo,
            cumple_umbrales=tengo >= prio.umbrales.tengo and quiero >= prio.umbrales.quiero,
            posicion=orden.index(id_) + 1 if id_ in orden else None,
            nivel_efectivo=nivel,
        )
    return resultados


def _portal(o: Oportunidad, portales: list[FuenteBusqueda], compuerta: Compuerta) -> FuenteBusqueda | None:
    """De los portales donde se vio la vacante, el de tope de nivel más bajo: la simulación no adivina cuál se usará."""
    vistos = {f.nombre.casefold() for f in o.fuentes}
    candidatos = [p for p in portales if p.nombre.casefold() in vistos]
    return min(candidatos, key=lambda p: autonomia.nivel_efectivo(100, compuerta, p), default=None)


def _destino(
    o: Oportunidad, config: Configuracion, todas: list[postulaciones.Postulacion], portal: FuenteBusqueda | None
) -> tuple[Destino, list[str], int]:
    compuerta = config.compuerta
    fuente = portal or _SIN_PORTAL
    nivel = autonomia.nivel_efectivo(config.autonomia, compuerta, fuente)
    preferencias = autonomia.evaluar_preferencias(
        o, config.priorizacion, compuerta, todas, _juicios_supuestos(compuerta), nivel
    )
    acciones, motivos = autonomia.acciones_de_envio(nivel, preferencias, compuerta, fuente, o)
    if nivel < config.autonomia:
        motivos.insert(0, f"nivel limitado a {nivel} % por el tope de {fuente.nombre} (riesgo {fuente.riesgo})")
    if acciones["envio"] == "aprobar":
        return "cola", motivos or [f"el nivel {nivel} % pide aprobar el envío"], nivel
    juzgadas = {"seniority", "ubicacion"} & set(compuerta.condiciones_preferencia)
    return ("auto_condicionado" if juzgadas and nivel < 100 else "auto"), motivos, nivel


def _juicios_supuestos(compuerta: Compuerta) -> Juicios:
    def supuesto(permitidos: list[str]) -> JuicioValor:
        return JuicioValor(valor=permitidos[0] if permitidos else "-", evidencia=_SUPUESTO)

    return Juicios(
        seniority=supuesto(compuerta.seniority_permitido), ubicacion=supuesto(compuerta.ubicaciones_permitidas)
    )


def _diferencias(antes: Resultado, despues: Resultado) -> list[str]:
    def top(posicion: int | None) -> str:
        return f"puesto {posicion}" if posicion else "fuera del Top"

    def umbrales(cumple: bool | None) -> str:
        return {True: "cumple", False: "no cumple", None: "sin puntaje"}[cumple]

    diferencias = []
    if antes.destino != despues.destino:
        diferencias.append(f"destino: {antes.destino} -> {despues.destino}")
    if antes.cumple_umbrales != despues.cumple_umbrales:
        diferencias.append(f"umbrales: {umbrales(antes.cumple_umbrales)} -> {umbrales(despues.cumple_umbrales)}")
    if antes.posicion != despues.posicion:
        diferencias.append(f"Top: {top(antes.posicion)} -> {top(despues.posicion)}")
    return diferencias
