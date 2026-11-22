from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict

from agente0 import autonomia, fuentes, oportunidades, postulaciones, ranking
from agente0.datos import cargar_configuracion
from agente0.fuentes import FuenteBusqueda
from agente0.oportunidades import Oportunidad
from agente0.postulaciones import Modo


class CarrilesError(ValueError):
    pass


class VacanteCarril(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    # Solo las que vienen del Top; una ya preparada sale del ranking (pasa a EN_POSTULACION).
    posicion: int | None = None
    empresa: str
    cargo: str
    url: str
    total: float | None = None


class Carril(BaseModel):
    """Un portal: sus vacantes se trabajan en serie dentro del carril; los carriles de portales distintos, a la vez."""

    model_config = ConfigDict(extra="forbid")

    portal: str
    riesgo: str
    nivel_efectivo: int
    envio: Modo
    # Al 75 % el envío es automático solo si se cumplen las condiciones de preferencia; si no, va a la cola.
    envio_condicionado: bool
    limite_diario: int
    enviados_hoy: int
    cupo_restante: int
    espera_segundos: int
    # Las del Top sin postulación que caben en el cupo de hoy, de mayor a menor puntaje.
    vacantes: list[VacanteCarril]
    # Las que no caben hoy: quedan POTENCIAL para la próxima corrida (D13).
    en_espera: list[str]
    # Ya preparadas (PREPARADA) y a la espera del OK del usuario o de un reintento.
    en_cola: list[VacanteCarril]


class SinCarril(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    motivo: str


class PlanCarriles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generado: datetime
    ranking: str | None
    # Cuántos carriles abrir a la vez (un subagente y una pestaña cada uno); el resto espera su turno.
    en_paralelo: int
    carriles: list[Carril]
    sin_carril: list[SinCarril]


def _dominio(url: str) -> str:
    host = urlsplit(url).netloc.lower().split("@")[-1].split(":")[0]
    return host.removeprefix("www.")


def portal_de(o: Oportunidad, lista: list[FuenteBusqueda]) -> FuenteBusqueda | None:
    """El portal donde se postula, por el dominio del enlace oficial; si no calza, el de portales corporativos."""
    host = _dominio(o.url)
    activas = [f for f in lista if f.activa]
    for f in activas:
        base = _dominio(f.url) if f.url else ""
        if base and (host == base or host.endswith("." + base)):
            return f
    return next((f for f in activas if f.tipo == "corporativa"), None)


def planear(raiz: Path, ahora: datetime | None = None) -> PlanCarriles:
    """Reparte el Top del último ranking en carriles por portal, con el cupo y el nivel de cada uno (B25, D13)."""
    ahora = ahora or datetime.now().astimezone()
    r = ranking.ultimo(raiz)
    if r is None:
        raise CarrilesError("no hay ranking: corre `ranking generar` antes de planear los carriles.")
    config = cargar_configuracion(raiz)
    lista = fuentes.cargar(raiz)
    previas = {p.id: p for p in postulaciones.listar(raiz)}
    intentos = postulaciones.intentos_de_envio(raiz)

    nuevas_por_portal: dict[str, list[VacanteCarril]] = {}
    cola_por_portal: dict[str, list[VacanteCarril]] = {}
    sin_carril: list[SinCarril] = []

    def ubicar(o: Oportunidad, vacante: VacanteCarril, destino: dict[str, list[VacanteCarril]]) -> None:
        fuente = portal_de(o, lista)
        if fuente is None:
            sin_carril.append(SinCarril(id=o.id, motivo=f"ningún portal activo calza con {_dominio(o.url)}"))
        else:
            destino.setdefault(fuente.nombre, []).append(vacante)

    for entrada in r.top:
        o = oportunidades.cargar(raiz, entrada.id)
        previa = previas.get(entrada.id)
        if o.estado != "POTENCIAL":
            sin_carril.append(SinCarril(id=o.id, motivo=f"la oportunidad está {o.estado}"))
        elif previa is not None:
            sin_carril.append(SinCarril(id=o.id, motivo=f"ya está {previa.estado}"))
        else:
            vacante = VacanteCarril(
                id=o.id,
                posicion=entrada.posicion,
                empresa=o.empresa,
                cargo=o.cargo,
                url=o.url,
                total=entrada.total,
            )
            ubicar(o, vacante, nuevas_por_portal)
    for previa in previas.values():
        if previa.estado == "PREPARADA":
            o = oportunidades.cargar(raiz, previa.id)
            if o.estado in ("CERRADO", "DESCARTADO"):
                continue
            ubicar(
                o,
                VacanteCarril(id=o.id, empresa=o.empresa, cargo=o.cargo, url=o.url),
                cola_por_portal,
            )

    carriles = []
    for nombre in [
        *nuevas_por_portal,
        *(n for n in cola_por_portal if n not in nuevas_por_portal),
    ]:
        fuente = next(f for f in lista if f.nombre == nombre)
        nivel = autonomia.nivel_efectivo(config.autonomia, config.compuerta, fuente)
        limite, hechos = autonomia.cupo_diario(intentos, config.compuerta, fuente, ahora)
        cupo = max(0, limite - hechos)
        nuevas = nuevas_por_portal.get(nombre, [])
        _, espera = autonomia.limites_de_envio(raiz, config.compuerta, fuente, ahora)
        carriles.append(
            Carril(
                portal=nombre,
                riesgo=fuente.riesgo,
                nivel_efectivo=nivel,
                envio=autonomia.MATRIZ[nivel]["envio"],
                envio_condicionado=nivel == 75,
                limite_diario=limite,
                enviados_hoy=hechos,
                cupo_restante=cupo,
                espera_segundos=espera,
                vacantes=nuevas[:cupo],
                en_espera=[v.id for v in nuevas[cupo:]],
                en_cola=cola_por_portal.get(nombre, []),
            )
        )
    return PlanCarriles(
        generado=ahora,
        ranking=r.generado.isoformat(),
        en_paralelo=config.compuerta.carriles_en_paralelo,
        carriles=carriles,
        sin_carril=sin_carril,
    )
