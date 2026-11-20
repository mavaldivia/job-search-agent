import os
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agente0 import oportunidades, postulaciones
from agente0.datos import cargar_configuracion
from agente0.esquemas import Priorizacion
from agente0.ids import slug_empresa
from agente0.oportunidades import Fuente, Oportunidad

Cambio = Literal["NUEVA", "SUBE", "BAJA", "SIN_CAMBIOS"]
MotivoSalida = Literal["CERRADA", "POSTULADA", "DESCARTADA", "DESPLAZADA", "PENDIENTE"]


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    posicion: int
    id: str
    empresa: str
    cargo: str
    url: str
    fuentes: list[Fuente]
    quiero: float
    tengo: float
    total: float
    contribuciones: dict[str, float]
    cumple_umbrales: bool
    brecha_principal: str
    vigencia_verificada_el: date
    cierra_el: date | None
    cambio: Cambio


class FueraDelTop(BaseModel):
    """Evaluada, vigente y sin entrar al Top: queda a la vista para cuando suba el Top o bajen los umbrales."""

    model_config = ConfigDict(extra="forbid")

    id: str
    empresa: str
    cargo: str
    url: str
    quiero: float
    tengo: float
    total: float
    cumple_umbrales: bool
    brecha_principal: str


class Salida(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    empresa: str
    cargo: str
    motivo: MotivoSalida
    detalle: str = ""


class Descartada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    empresa: str
    cargo: str
    motivo: str


class Ranking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generado: datetime
    anterior: str | None
    top: list[Entrada]
    # Los rankings guardados antes de B18 no traen este campo.
    fuera_del_top: list[FueraDelTop] = Field(default_factory=list)
    salidas: list[Salida]
    # Descartadas por filtro en esta corrida y que no venían del Top anterior (esas figuran en `salidas`).
    descartadas: list[Descartada]
    # POTENCIAL con vigencia pero sin evaluación vigente: el agente debe evaluarlas antes de que puedan entrar.
    pendientes: list[str]


def _carpeta(raiz: Path) -> Path:
    return raiz / "ranking"


def ultimo(raiz: Path) -> Ranking | None:
    archivos = sorted(_carpeta(raiz).glob("*.json")) if _carpeta(raiz).is_dir() else []
    return Ranking.model_validate_json(archivos[-1].read_text(encoding="utf-8")) if archivos else None


def puntuar(o: Oportunidad, config: Priorizacion) -> tuple[float, float, float, dict[str, float]]:
    puntajes = o.evaluacion.criterios

    def promedio(criterios: dict) -> float:
        return sum(c.peso * puntajes[k].puntaje for k, c in criterios.items()) / sum(c.peso for c in criterios.values())

    por_eje = {eje: {k: c for k, c in config.criterios.items() if c.eje == eje} for eje in ("tengo", "quiero")}
    peso_total = sum(c.peso for c in config.criterios.values())
    contribuciones = {k: round(c.peso * puntajes[k].puntaje / peso_total, 1) for k, c in config.criterios.items()}
    return (
        round(promedio(por_eje["quiero"]), 1),
        round(promedio(por_eje["tengo"]), 1),
        round(promedio(config.criterios), 1),
        contribuciones,
    )


def motivo_de_descarte(o: Oportunidad, config: Priorizacion, empresas_en_proceso: set[str]) -> str | None:
    if o.rescatada:
        return None
    activos = set(config.filtros_activos)
    if "renta" in activos and config.renta_minima and o.renta_publicada and o.renta_publicada < config.renta_minima:
        return f"renta publicada {o.renta_publicada} bajo el mínimo {config.renta_minima}"
    if "empresa_excluida" in activos and slug_empresa(o.empresa) in {
        slug_empresa(e) for e in config.empresas_excluidas
    }:
        return "empresa excluida"
    if slug_empresa(o.empresa) in empresas_en_proceso:
        return "proceso activo en esa empresa"
    if o.evaluacion:
        for nombre, filtro in o.evaluacion.filtros.items():
            if nombre in activos and filtro.excluye:
                return f"{nombre}: {filtro.motivo}"
    return None


def _postulaciones_existentes(raiz: Path) -> tuple[set[str], set[str]]:
    carpeta = raiz / "postulaciones"
    cargadas = (
        [postulaciones.cargar(raiz, d.name) for d in sorted(carpeta.iterdir()) if d.is_dir()]
        if carpeta.is_dir()
        else []
    )
    ids = {p.id for p in cargadas}
    empresas_en_proceso = {slug_empresa(p.empresa) for p in cargadas if p.estado != "FINALIZADA"}
    return ids, empresas_en_proceso


def ordenar_top(totales: dict[str, float], ids_previos: list[str], top: int) -> list[str]:
    # Un empate lo gana quien ya estaba en el Top: una vacante nueva entra solo si supera a la última.
    return sorted(totales, key=lambda i: (-totales[i], i not in ids_previos, i))[:top]


def generar(raiz: Path, ahora: datetime | None = None) -> Ranking:
    """D11: filtra (las descartadas pasan a DESCARTADO), puntúa y arma el Top con la última lista como base."""
    ahora = ahora or datetime.now().astimezone()
    config = cargar_configuracion(raiz).priorizacion
    previo = ultimo(raiz)
    ids_previos = [e.id for e in previo.top] if previo else []
    ids_postulados, empresas_en_proceso = _postulaciones_existentes(raiz)

    puntuadas: dict[str, tuple[Oportunidad, float, float, float, dict[str, float]]] = {}
    descartadas, pendientes = [], []
    for o in oportunidades.listar(raiz, "POTENCIAL"):
        if o.id in ids_postulados:
            oportunidades.cambiar_estado(raiz, o.id, "EN_POSTULACION", "ya existe una postulación")
            continue
        motivo = motivo_de_descarte(o, config, empresas_en_proceso)
        if motivo:
            oportunidades.cambiar_estado(raiz, o.id, "DESCARTADO", motivo)
            descartadas.append(Descartada(id=o.id, empresa=o.empresa, cargo=o.cargo, motivo=motivo))
        elif o.evaluacion is None or set(o.evaluacion.criterios) != set(config.criterios):
            pendientes.append(o.id)
        else:
            puntuadas[o.id] = (o, *puntuar(o, config))

    orden = ordenar_top({i: p[3] for i, p in puntuadas.items()}, ids_previos, config.top)
    cambios = _cambios(ids_previos, orden)
    top = []
    for posicion, id_ in enumerate(orden, start=1):
        o, quiero, tengo, total, contribuciones = puntuadas[id_]
        top.append(
            Entrada(
                posicion=posicion,
                id=id_,
                empresa=o.empresa,
                cargo=o.cargo,
                url=o.url,
                fuentes=o.fuentes,
                quiero=quiero,
                tengo=tengo,
                total=total,
                contribuciones=contribuciones,
                cumple_umbrales=tengo >= config.umbrales.tengo and quiero >= config.umbrales.quiero,
                brecha_principal=o.evaluacion.brecha_principal,
                vigencia_verificada_el=o.vigencia.verificada_el,
                cierra_el=o.cierra_el,
                cambio=cambios[id_],
            )
        )

    fuera_del_top = [
        FueraDelTop(
            id=i,
            empresa=o.empresa,
            cargo=o.cargo,
            url=o.url,
            quiero=quiero,
            tengo=tengo,
            total=total,
            cumple_umbrales=tengo >= config.umbrales.tengo and quiero >= config.umbrales.quiero,
            brecha_principal=o.evaluacion.brecha_principal,
        )
        for i, (o, quiero, tengo, total, _) in sorted(puntuadas.items(), key=lambda p: (-p[1][3], p[0]))
        if i not in orden
    ]
    salidas = [_salida(raiz, id_, puntuadas) for id_ in ids_previos if id_ not in orden]
    ids_en_salidas = {s.id for s in salidas}
    ranking = Ranking(
        generado=ahora,
        anterior=_nombre(previo.generado) if previo else None,
        top=top,
        fuera_del_top=fuera_del_top,
        salidas=salidas,
        descartadas=[d for d in descartadas if d.id not in ids_en_salidas],
        pendientes=pendientes,
    )
    _guardar(raiz, ranking)
    return ranking


def _cambios(ids_previos: list[str], orden: list[str]) -> dict[str, Cambio]:
    # Se compara el orden relativo entre las que están en ambas listas: que una salga no hace "subir" a las demás.
    comunes_antes = [i for i in ids_previos if i in orden]
    comunes_ahora = [i for i in orden if i in ids_previos]
    cambios: dict[str, Cambio] = {}
    for id_ in orden:
        if id_ not in ids_previos:
            cambios[id_] = "NUEVA"
            continue
        antes, ahora = comunes_antes.index(id_), comunes_ahora.index(id_)
        cambios[id_] = "SUBE" if ahora < antes else "BAJA" if ahora > antes else "SIN_CAMBIOS"
    return cambios


def _salida(raiz: Path, id_: str, puntuadas: dict) -> Salida:
    o = oportunidades.cargar(raiz, id_)
    base = {"id": id_, "empresa": o.empresa, "cargo": o.cargo}
    if o.estado == "CERRADO":
        return Salida(**base, motivo="CERRADA", detalle=o.motivo or "")
    if o.estado == "DESCARTADO":
        return Salida(**base, motivo="DESCARTADA", detalle=o.motivo or "")
    if o.estado == "EN_POSTULACION":
        return Salida(**base, motivo="POSTULADA")
    return Salida(**base, motivo="DESPLAZADA" if id_ in puntuadas else "PENDIENTE")


def _nombre(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%dT%H%M%S")


def _guardar(raiz: Path, ranking: Ranking) -> None:
    carpeta = _carpeta(raiz)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{_nombre(ranking.generado)}.json"
    temporal = carpeta / f"{destino.name}.tmp"
    temporal.write_text(ranking.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.replace(temporal, destino)
