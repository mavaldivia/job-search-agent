import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agente0 import oportunidades, ranking
from agente0.datos import cargar_configuracion
from agente0.ids import slug_empresa

ARCHIVO_RANGOS = "configuracion/mercado_rangos.json"
Presencialidad = Literal["remota", "hibrida", "alta", "total"]


class MercadoError(ValueError):
    pass


class SinRango(MercadoError):
    pass


class FuenteMercado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    url: str = Field(min_length=1)
    dato: str = Field(min_length=1)


class RangoMercado(BaseModel):
    """B24: lo que paga el mercado por un rol y seniority, con las fuentes de cada cifra. Sin fuente no se usa."""

    model_config = ConfigDict(extra="forbid")

    rol: str = Field(min_length=1)
    seniority: str = Field(min_length=1)
    mercado: str = Field(min_length=1)
    unidad: str = Field(min_length=1)
    empresa: str | None = None
    p50: int = Field(gt=0)
    p75: int = Field(gt=0)
    # Muchas guías publican hasta el percentil 75; sin p90 publicado no se inventa uno.
    p90: int | None = Field(default=None, gt=0)
    confianza: Literal["alta", "media", "baja"]
    metodo: str = Field(min_length=1)
    fuentes: list[FuenteMercado] = Field(min_length=1)
    investigado: date

    @model_validator(mode="after")
    def _percentiles_ordenados(self) -> "RangoMercado":
        if not self.p50 <= self.p75 <= (self.p90 or self.p75):
            raise ValueError("los percentiles deben cumplir p50 <= p75 <= p90.")
        return self

    def clave(self) -> tuple[str, str, str, str]:
        return (
            self.rol.casefold(),
            self.seniority.casefold(),
            self.mercado.casefold(),
            slug_empresa(self.empresa) if self.empresa else "",
        )


class RangoListado(BaseModel):
    rango: RangoMercado
    dias: int
    vigente: bool


class Solicitud(BaseModel):
    """Lo que aporta el agente, con evidencia: a qué rol, seniority y mercado corresponde la vacante y su presencialidad."""

    model_config = ConfigDict(extra="forbid")

    rol: str = Field(min_length=1)
    seniority: str = Field(min_length=1)
    mercado: str = Field(min_length=1)
    presencialidad: Presencialidad
    lejos_de_casa: bool = False
    evidencia: str = Field(min_length=1)
    minima_equivalente: int | None = Field(default=None, gt=0)
    maxima_equivalente: int | None = Field(default=None, gt=0)
    tope_general_equivalente: int | None = Field(default=None, gt=0)
    aplicar: bool = False


class Propuesta(BaseModel):
    origen: Literal["mercado", "estandar"]
    escalon: Literal["general", "exigente"]
    percentil: int | None
    valor_mercado: int | None
    minima: int | None
    maxima: int | None = None  # el tope que rige en este cargo, no siempre `mercado.renta_maxima`
    monto: int
    subida_a_minima: bool
    bajada_a_maxima: bool = False
    fit: float | None = None
    subida_por_fit: int = 0
    unidad: str
    investigado: date | None
    confianza: str | None
    fuentes: list[str]
    nota: str | None = None


class Cuadre(BaseModel):
    resultado: Literal["cuadra", "omitir", "sin_dato"]
    referencia: int | None
    detalle: str


class Evaluacion(BaseModel):
    propuesta: Propuesta
    cuadre: Cuadre
    sugerida: int
    descartada: bool = False


def _cargar(raiz: Path) -> list[RangoMercado]:
    archivo = raiz / ARCHIVO_RANGOS
    if not archivo.exists():
        return []
    return [RangoMercado.model_validate(r) for r in json.loads(archivo.read_text(encoding="utf-8"))]


def guardar(raiz: Path, rango: RangoMercado) -> None:
    """Alta o reemplazo del rango con la misma clave (rol, seniority, mercado y empresa)."""
    rangos = [r for r in _cargar(raiz) if r.clave() != rango.clave()] + [rango]
    archivo = raiz / ARCHIVO_RANGOS
    archivo.parent.mkdir(parents=True, exist_ok=True)
    crudo = [r.model_dump(mode="json") for r in rangos]
    archivo.write_text(json.dumps(crudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def listar(raiz: Path, hoy: date | None = None) -> list[RangoListado]:
    vigencia = cargar_configuracion(raiz).mercado.vigencia_dias
    hoy = hoy or date.today()
    return [
        RangoListado(rango=r, dias=(hoy - r.investigado).days, vigente=(hoy - r.investigado).days < vigencia)
        for r in _cargar(raiz)
    ]


def buscar(
    raiz: Path, rol: str, seniority: str, mercado: str, empresa: str | None = None, hoy: date | None = None
) -> RangoMercado:
    """El rango vigente de la empresa si existe y, si no, el general; si falta o venció, hay que investigarlo."""
    base = (rol.casefold(), seniority.casefold(), mercado.casefold())
    candidatos = [e for e in listar(raiz, hoy) if e.rango.clave()[:3] == base]
    if not candidatos:
        raise SinRango(f"no hay rango de mercado para {rol} / {seniority} / {mercado}: investígalo y guárdalo.")
    vigentes = [e.rango for e in candidatos if e.vigente]
    if not vigentes:
        dias = min(e.dias for e in candidatos)
        raise MercadoError(f"el rango de {rol} / {seniority} / {mercado} se investigó hace {dias} días: investígalo de nuevo.")
    de_la_empresa = [r for r in vigentes if empresa and r.empresa and slug_empresa(r.empresa) == slug_empresa(empresa)]
    generales = [r for r in vigentes if r.empresa is None]
    elegidos = de_la_empresa or generales
    if not elegidos:
        raise MercadoError(f"solo hay rangos de otras empresas para {rol} / {seniority} / {mercado}: investiga el general.")
    return elegidos[0]


def exige_percentil_alto(presencialidad: Presencialidad, lejos_de_casa: bool) -> bool:
    return presencialidad == "total" or (presencialidad == "alta" and lejos_de_casa)


NIVELES_EXIGENTES = ("manager", "head")


def es_exigente(seniority: str, presencialidad: Presencialidad, lejos_de_casa: bool) -> bool:
    """Los cargos de nivel Manager o superior con mucha presencialidad o lejos de casa se piden sobre el tope general."""
    return seniority.casefold() in NIVELES_EXIGENTES and (presencialidad in ("alta", "total") or lejos_de_casa)


def _subida_por_fit(base: int, tope: int | None, fit: float | None, desde: float, pleno: float) -> int:
    """Cuánto sube la propuesta por fit: lineal de `desde` a `pleno`, hasta el tope; en tres cifras significativas."""
    if fit is None or tope is None or base >= tope:
        return 0
    fraccion = min(max((fit - desde) / (pleno - desde), 0), 1)
    sube = base + (tope - base) * fraccion
    redondeado = int(round(sube, 3 - len(str(int(sube)))))
    return max(min(redondeado, tope) - base, 0)


def _cotas(o: oportunidades.Oportunidad, unidad: str, unidad_config: str) -> tuple[int | None, int | None]:
    """(mayor valor aceptado, menor valor que ya excede el tope) de la oferta, en la unidad del rango."""
    obs = o.renta_observada
    if obs is not None and obs.unidad == unidad:
        return obs.acepta_hasta, obs.avisa_desde
    if o.renta_publicada is not None and unidad == unidad_config:
        return o.renta_publicada, o.renta_publicada + 1
    return None, None


def _cuadre(piso: int | None, techo: int | None, referencia: int | None, que: str) -> Cuadre:
    if referencia is None:
        return Cuadre(resultado="sin_dato", referencia=None, detalle="no hay renta mínima configurada en esa unidad")
    if techo is not None and techo <= referencia:
        return Cuadre(
            resultado="omitir",
            referencia=referencia,
            detalle=f"el tope de la oferta queda bajo {que} ({referencia}): excede desde {techo}",
        )
    if piso is not None and piso >= referencia:
        return Cuadre(
            resultado="cuadra", referencia=referencia, detalle=f"la oferta acepta hasta {piso}, sobre {que} ({referencia})"
        )
    return Cuadre(resultado="sin_dato", referencia=referencia, detalle="la oferta no muestra un tope que decida")


def _tope_del_cargo(solicitud: Solicitud, config, exigente: bool, unidad: str) -> int | None:
    m, unidad_config = config.mercado, config.mercado.unidad_renta_minima
    en_general = not exigente and m.renta_tope_general is not None
    tope = m.renta_tope_general if en_general else m.renta_maxima
    if tope is None or unidad == unidad_config:
        return tope
    nombre = "tope_general_equivalente" if en_general else "maxima_equivalente"
    equivalente = getattr(solicitud, nombre)
    if equivalente is None:
        raise MercadoError(f"el rango está en {unidad}: falta `{nombre}`, el tope de renta de este cargo en esa unidad.")
    return equivalente


def evaluar(raiz: Path, id_: str, hoy: date | None = None, **datos) -> Evaluacion:
    """B24: renta propuesta según el escalón del cargo, el mercado y el fit, y si cuadra con el tope de la oferta.

    General: percentil 75 con el tope general (sin rango de mercado, la renta estándar). Exigente (Manager o superior
    con mucha presencialidad o lejos de casa): percentil 90 con `renta_maxima` (sin rango, `renta_maxima`). Con mucho fit
    sube de su base hacia el tope. No cuadrar es omitir la vacante: en cargos 100 % presenciales o lejos de casa,
    cuando el tope de la oferta queda bajo la renta propuesta; en el resto, cuando queda bajo la renta mínima. Con
    `aplicar` la vacante pasa a DESCARTADO con el motivo.
    """
    solicitud = Solicitud.model_validate(datos)
    config = cargar_configuracion(raiz)
    o = oportunidades.cargar(raiz, id_)
    exigente = es_exigente(solicitud.seniority, solicitud.presencialidad, solicitud.lejos_de_casa)
    unidad_config = config.mercado.unidad_renta_minima
    try:
        rango = buscar(raiz, solicitud.rol, solicitud.seniority, solicitud.mercado, o.empresa, hoy)
    except SinRango:
        estandar = config.mercado.renta_maxima if exigente else config.mercado.renta_estandar
        if solicitud.mercado.casefold() != "chile" or estandar is None:
            raise
        rango = None

    unidad = rango.unidad if rango else unidad_config
    if unidad == unidad_config:
        minima = config.priorizacion.renta_minima
    elif solicitud.minima_equivalente is not None:
        minima = solicitud.minima_equivalente
    else:
        raise MercadoError(f"el rango está en {unidad}: falta `minima_equivalente`, la renta mínima en esa unidad.")

    maxima = _tope_del_cargo(solicitud, config, exigente, unidad)
    if maxima is not None and minima is not None and maxima < minima:
        raise MercadoError(f"el techo de renta ({maxima}) queda bajo la renta mínima ({minima}).")

    percentil = valor = None
    nota = "sin rango de mercado: se propone la renta estándar del usuario" if rango is None else None
    if rango is None:
        base = estandar
    else:
        percentil = config.mercado.percentil_presencial if exigente else config.mercado.percentil_base
        valor = getattr(rango, f"p{percentil}")
        if valor is None:
            nota = f"el rango no publica el percentil {percentil}: se usa el 75"
            percentil, valor = 75, rango.p75
        base = valor
    tras_tope = min(base, maxima) if maxima is not None else base
    fit = ranking.puntuar(o, config.priorizacion)[1] if o.evaluacion else None
    sube = _subida_por_fit(tras_tope, maxima, fit, config.mercado.fit_desde, config.mercado.fit_pleno)
    monto = max(tras_tope + sube, minima or 0)
    propuesta = Propuesta(
        origen="mercado" if rango else "estandar",
        escalon="exigente" if exigente else "general",
        percentil=percentil,
        valor_mercado=valor,
        minima=minima,
        maxima=maxima,
        monto=monto,
        subida_a_minima=monto > tras_tope + sube,
        bajada_a_maxima=tras_tope < base,
        fit=fit,
        subida_por_fit=sube,
        unidad=unidad,
        investigado=rango.investigado if rango else None,
        confianza=rango.confianza if rango else None,
        fuentes=[f.url for f in rango.fuentes] if rango else [],
        nota=nota,
    )

    piso, techo = _cotas(o, unidad, unidad_config)
    alto = exige_percentil_alto(solicitud.presencialidad, solicitud.lejos_de_casa)
    cuadre = (
        _cuadre(piso, techo, monto, "la renta propuesta")
        if alto
        else _cuadre(piso, techo, minima, "la renta mínima")
    )
    sugerida = piso if cuadre.resultado == "cuadra" and piso is not None and piso < monto else monto

    descartada = False
    if cuadre.resultado == "omitir" and solicitud.aplicar and o.estado in ("POTENCIAL", "EN_POSTULACION"):
        motivo = f"sin cuadre de renta ({unidad}): {cuadre.detalle}"
        oportunidades.cambiar_estado(raiz, id_, "DESCARTADO", motivo)
        descartada = True
    return Evaluacion(propuesta=propuesta, cuadre=cuadre, sugerida=sugerida, descartada=descartada)
