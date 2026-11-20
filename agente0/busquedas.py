import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from agente0 import fuentes, oportunidades
from agente0.datos import cargar_configuracion
from agente0.esquemas import Riesgo
from agente0.ids import normalizar, url_canonica

ARCHIVO = "busquedas/registro.jsonl"


class Consulta(BaseModel):
    """Una búsqueda hecha en una fuente. Solo se agrega al registro, nunca se edita."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["CONSULTA"] = "CONSULTA"
    fecha: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    fuente: str = Field(min_length=1)
    consulta: str = Field(min_length=1)
    paginas: int = Field(ge=0)
    # Publicaciones leídas completas, no resultados de listado.
    lecturas: int = Field(ge=0)
    vistas: int = Field(ge=0)
    nuevas: int = Field(ge=0)
    # Todo lo publicado desde esta fecha hasta la víspera de `fecha` quedó revisado. Si la búsqueda se cortó, es la
    # publicación más antigua a la que llegó; el listado debe ir de lo más nuevo a lo más antiguo.
    cubre_desde: date
    motivo_corte: str | None = None

    @model_validator(mode="after")
    def _coherente(self) -> "Consulta":
        if self.cubre_desde > self.fecha.date():
            raise ValueError("`cubre_desde` no puede ser posterior a la fecha de la búsqueda.")
        return self


class Vista(BaseModel):
    """Una vacante descartada a simple vista por el listado, sin leer la publicación ni puntuarla."""

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["VISTA"] = "VISTA"
    fecha: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    fuente: str = Field(min_length=1)
    empresa: str = Field(min_length=1)
    cargo: str = Field(min_length=1)
    url: str = Field(min_length=1)
    motivo: str = Field(min_length=1)


class Tramo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desde: date
    hasta: date


class Cupo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fuente: str
    riesgo: Riesgo
    # El primer día de búsqueda de una fuente no tiene tope: se recorre completa para poblar la base.
    primera_pasada: bool
    paginas_usadas_hoy: int
    lecturas_usadas_hoy: int
    # None: sin tope.
    paginas_restantes: int | None
    lecturas_restantes: int | None


class ResumenFuente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fuente: str
    riesgo: Riesgo
    activa: bool
    ultima_busqueda: date | None
    consultas_distintas: int


class Conocida(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origen: Literal["OPORTUNIDAD", "VISTA"]
    coincide_por: Literal["url", "empresa_y_cargo"]
    id: str | None = None
    estado: str | None = None
    detalle: str = ""


_REGISTRO = TypeAdapter(list[Annotated[Consulta | Vista, Field(discriminator="tipo")]])


def _leer(raiz: Path) -> list[Consulta | Vista]:
    archivo = raiz / ARCHIVO
    if not archivo.exists():
        return []
    return _REGISTRO.validate_python(
        [json.loads(linea) for linea in archivo.read_text(encoding="utf-8").splitlines() if linea]
    )


def _agregar(raiz: Path, entrada: Consulta | Vista) -> None:
    archivo = raiz / ARCHIVO
    archivo.parent.mkdir(parents=True, exist_ok=True)
    with archivo.open("a", encoding="utf-8") as f:
        f.write(entrada.model_dump_json() + "\n")


def _fuente(raiz: Path, nombre: str) -> fuentes.FuenteBusqueda:
    for f in fuentes.cargar(raiz):
        if f.nombre.casefold() == nombre.strip().casefold():
            return f
    raise ValueError(f"la fuente {nombre!r} no está en fuentes.json: agrégala con el usuario antes de buscar en ella.")


def _consultas(raiz: Path, fuente: str) -> list[Consulta]:
    return [e for e in _leer(raiz) if isinstance(e, Consulta) and e.fuente == fuente]


def registrar_consulta(raiz: Path, fuente: str, consulta: str, ahora: datetime | None = None, **datos) -> Consulta:
    entrada = Consulta(
        **({"fecha": ahora} if ahora else {}), fuente=_fuente(raiz, fuente).nombre, consulta=consulta.strip(), **datos
    )
    _agregar(raiz, entrada)
    return entrada


def registrar_vista(raiz: Path, fuente: str, ahora: datetime | None = None, **datos) -> Vista:
    entrada = Vista(**({"fecha": ahora} if ahora else {}), fuente=_fuente(raiz, fuente).nombre, **datos)
    _agregar(raiz, entrada)
    return entrada


def vistas(raiz: Path) -> list[Vista]:
    return [e for e in _leer(raiz) if isinstance(e, Vista)]


def pendiente(raiz: Path, fuente: str, consulta: str, hoy: date | None = None) -> list[Tramo]:
    """Fechas de publicación que esa consulta aún no revisó en esa fuente, dentro de la ventana de D10 (inclusive).
    Cada búsqueda cubre de `cubre_desde` hasta la víspera de su fecha; hoy siempre queda pendiente porque aún pueden
    salir publicaciones. Una consulta nueva (otra variante del cargo) no hereda lo cubierto por las anteriores."""
    hoy = hoy or date.today()
    clave = normalizar(consulta)
    ventana = cargar_configuracion(raiz).priorizacion.ventana_dias
    dia = timedelta(days=1)
    cubiertos = sorted(
        (c.cubre_desde, c.fecha.date() - dia)
        for c in _consultas(raiz, _fuente(raiz, fuente).nombre)
        if normalizar(c.consulta) == clave and c.cubre_desde <= c.fecha.date() - dia
    )
    tramos, cursor = [], hoy - timedelta(days=ventana)
    for desde, hasta in cubiertos:
        if hasta < cursor:
            continue
        if desde > cursor:
            tramos.append(Tramo(desde=cursor, hasta=desde - dia))
        cursor = hasta + dia
    if cursor <= hoy:
        tramos.append(Tramo(desde=cursor, hasta=hoy))
    return tramos


def cupo(raiz: Path, fuente: str, hoy: date | None = None) -> Cupo:
    hoy = hoy or date.today()
    f = _fuente(raiz, fuente)
    previas = _consultas(raiz, f.nombre)
    de_hoy = [c for c in previas if c.fecha.date() == hoy]
    paginas, lecturas = sum(c.paginas for c in de_hoy), sum(c.lecturas for c in de_hoy)
    primera = all(c.fecha.date() >= hoy for c in previas)
    tope = None if primera else cargar_configuracion(raiz).busqueda.topes_por_riesgo.get(f.riesgo)
    return Cupo(
        fuente=f.nombre,
        riesgo=f.riesgo,
        primera_pasada=primera,
        paginas_usadas_hoy=paginas,
        lecturas_usadas_hoy=lecturas,
        paginas_restantes=max(tope.paginas - paginas, 0) if tope else None,
        lecturas_restantes=max(tope.lecturas - lecturas, 0) if tope else None,
    )


def resumen(raiz: Path) -> list[ResumenFuente]:
    registro = [e for e in _leer(raiz) if isinstance(e, Consulta)]
    resultado = []
    for f in fuentes.cargar(raiz):
        propias = [c for c in registro if c.fuente == f.nombre]
        resultado.append(
            ResumenFuente(
                fuente=f.nombre,
                riesgo=f.riesgo,
                activa=f.activa,
                ultima_busqueda=max((c.fecha.date() for c in propias), default=None),
                consultas_distintas=len({normalizar(c.consulta) for c in propias}),
            )
        )
    return resultado


def conocida(raiz: Path, url: str | None = None, empresa: str | None = None, cargo: str | None = None) -> Conocida | None:
    """Si la vacante ya está en las oportunidades o entre las vistas: por enlace, o por empresa y cargo (la misma
    vacante en otra fuente trae otro enlace). Es una pista para el agente, que compara y decide."""
    if not url and not (empresa and cargo):
        raise ValueError("indica `url` o `empresa` y `cargo`.")
    canonica = url_canonica(url) if url else None
    par = (normalizar(empresa), normalizar(cargo)) if empresa and cargo else None

    def coincidencia(enlaces: list[str], e: str, c: str) -> Literal["url", "empresa_y_cargo"] | None:
        if canonica and canonica in {url_canonica(u) for u in enlaces}:
            return "url"
        return "empresa_y_cargo" if par and par == (normalizar(e), normalizar(c)) else None

    for o in oportunidades.listar(raiz):
        por = coincidencia([o.url, *(f.url for f in o.fuentes)], o.empresa, o.cargo)
        if por:
            return Conocida(origen="OPORTUNIDAD", coincide_por=por, id=o.id, estado=o.estado, detalle=o.motivo or "")
    for v in vistas(raiz):
        por = coincidencia([v.url], v.empresa, v.cargo)
        if por:
            return Conocida(origen="VISTA", coincide_por=por, detalle=v.motivo)
    return None
