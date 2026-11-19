import hashlib
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agente0.datos import cargar_configuracion
from agente0.esquemas import FiltroExcluyente
from agente0.ids import id_postulacion

Estado = Literal["POTENCIAL", "EN_POSTULACION", "CERRADO", "DESCARTADO"]
TipoEvento = Literal["REGISTRADA", "FUENTE_AGREGADA", "VIGENCIA_VERIFICADA", "EVALUADA", "CAMBIO_ESTADO"]

# D5 y D13: saltar una vacante la devuelve a POTENCIAL; DESCARTADO solo vuelve por rescate del usuario (D11).
_TRANSICIONES: dict[str, set[str]] = {
    "POTENCIAL": {"EN_POSTULACION", "CERRADO", "DESCARTADO"},
    "EN_POSTULACION": {"POTENCIAL", "CERRADO", "DESCARTADO"},
    "DESCARTADO": {"POTENCIAL"},
    "CERRADO": set(),
}
# El código los decide con la configuración y las postulaciones; el agente no los califica.
FILTROS_DEL_CODIGO = {"renta", "empresa_excluida"}
_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class OportunidadError(ValueError):
    pass


class Fuente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    url: str = Field(min_length=1)


class Vigencia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verificada_el: date
    fuente: str = Field(min_length=1)
    evidencia: str = Field(min_length=1)


class PuntajeCriterio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    puntaje: int = Field(ge=0, le=100)
    evidencia: str = Field(min_length=1)


class ResultadoFiltro(BaseModel):
    model_config = ConfigDict(extra="forbid")

    excluye: bool
    motivo: str = ""

    @model_validator(mode="after")
    def _excluir_exige_motivo(self) -> "ResultadoFiltro":
        if self.excluye and not self.motivo:
            raise ValueError("un filtro que excluye exige motivo.")
        return self


class Evaluacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date
    huella: str
    criterios: dict[str, PuntajeCriterio]
    filtros: dict[FiltroExcluyente, ResultadoFiltro]
    brecha_principal: str = Field(min_length=1)


class Oportunidad(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    empresa: str
    cargo: str
    url: str
    fuentes: list[Fuente] = Field(default_factory=list)
    estado: Estado = "POTENCIAL"
    motivo: str | None = None
    rescatada: bool = False
    publicada: date | None = None
    cierra_el: date | None = None
    renta_publicada: int | None = Field(default=None, gt=0)
    vigencia: Vigencia
    evaluacion: Evaluacion | None = None

    @model_validator(mode="after")
    def _coherente(self) -> "Oportunidad":
        if self.estado in ("CERRADO", "DESCARTADO") and not self.motivo:
            raise ValueError(f"{self.estado} exige motivo.")
        return self


class Evento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    tipo: TipoEvento
    estado: Estado
    detalle: str = ""


def _carpeta(raiz: Path, id_: str) -> Path:
    if not _ID.fullmatch(id_):
        raise OportunidadError(f"ID de oportunidad inválido: {id_!r}.")
    return raiz / "oportunidades" / id_


def cargar(raiz: Path, id_: str) -> Oportunidad:
    archivo = _carpeta(raiz, id_) / "oportunidad.json"
    if not archivo.exists():
        raise OportunidadError(f"no existe la oportunidad {id_}.")
    return Oportunidad.model_validate_json(archivo.read_text(encoding="utf-8"))


def listar(raiz: Path, estado: Estado | None = None) -> list[Oportunidad]:
    if estado is not None and estado not in get_args(Estado):
        raise OportunidadError(f"estado inválido: {estado!r}; usa {get_args(Estado)}.")
    carpeta = raiz / "oportunidades"
    if not carpeta.is_dir():
        return []
    todas = [cargar(raiz, d.name) for d in sorted(carpeta.iterdir()) if (d / "oportunidad.json").exists()]
    return [o for o in todas if estado is None or o.estado == estado]


def _guardar(carpeta: Path, oportunidad: Oportunidad, *eventos: Evento) -> None:
    with (carpeta / "eventos.jsonl").open("a", encoding="utf-8") as archivo:
        for evento in eventos:
            archivo.write(evento.model_dump_json() + "\n")
    temporal = carpeta / "oportunidad.json.tmp"
    temporal.write_text(oportunidad.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.replace(temporal, carpeta / "oportunidad.json")


def registrar(
    raiz: Path,
    empresa: str,
    cargo: str,
    url: str,
    vigencia: dict,
    fuentes: list[dict] | None = None,
    publicada: date | None = None,
    cierra_el: date | None = None,
    renta_publicada: int | None = None,
) -> Oportunidad:
    """Alta o actualización idempotente. La `url` es la oficial (D10): de ella sale el ID que usará la postulación."""
    id_ = id_postulacion(empresa, cargo, url)
    carpeta = _carpeta(raiz, id_)
    nueva_vigencia = Vigencia.model_validate(vigencia)
    nuevas_fuentes = [Fuente.model_validate(f) for f in fuentes or []]

    if not (carpeta / "oportunidad.json").exists():
        carpeta.mkdir(parents=True, exist_ok=True)
        oportunidad = Oportunidad(
            id=id_,
            empresa=empresa,
            cargo=cargo,
            url=url,
            fuentes=_sin_repetidas([], nuevas_fuentes),
            publicada=publicada,
            cierra_el=cierra_el,
            renta_publicada=renta_publicada,
            vigencia=nueva_vigencia,
        )
        _guardar(
            carpeta,
            oportunidad,
            Evento(tipo="REGISTRADA", estado="POTENCIAL", detalle=f"vigencia en {nueva_vigencia.fuente}"),
        )
        return oportunidad

    actual = cargar(raiz, id_)
    if actual.estado in ("CERRADO", "DESCARTADO"):
        return actual
    fuentes_finales = _sin_repetidas(actual.fuentes, nuevas_fuentes)
    cambios = {
        "fuentes": fuentes_finales,
        "vigencia": nueva_vigencia,
        **{
            k: v
            for k, v in (("publicada", publicada), ("cierra_el", cierra_el), ("renta_publicada", renta_publicada))
            if v is not None
        },
    }
    oportunidad = Oportunidad.model_validate({**actual.model_dump(), **cambios})
    eventos = []
    if len(fuentes_finales) > len(actual.fuentes):
        eventos.append(Evento(tipo="FUENTE_AGREGADA", estado=actual.estado))
    if nueva_vigencia != actual.vigencia:
        eventos.append(Evento(tipo="VIGENCIA_VERIFICADA", estado=actual.estado, detalle=f"en {nueva_vigencia.fuente}"))
    if oportunidad != actual:
        _guardar(carpeta, oportunidad, *eventos)
    return oportunidad


def _sin_repetidas(existentes: list[Fuente], nuevas: list[Fuente]) -> list[Fuente]:
    resultado = list(existentes)
    for fuente in nuevas:
        if all(fuente.url != f.url for f in resultado):
            resultado.append(fuente)
    return resultado


def _huella(publicacion: str) -> str:
    texto = " ".join(publicacion.split())
    if not texto:
        raise OportunidadError("la publicación literal no puede estar vacía: es la evidencia del puntaje.")
    return hashlib.sha256(texto.encode()).hexdigest()[:12]


def evaluar(
    raiz: Path,
    id_: str,
    publicacion: str,
    criterios: dict,
    filtros: dict,
    brecha_principal: str,
    forzar: bool = False,
    fecha: date | None = None,
) -> Oportunidad:
    """D11, estabilidad: si el texto de la publicación no cambió, el puntaje guardado no cambia. `forzar` es para
    cuando cambió el perfil del usuario y la misma publicación debe puntuarse de nuevo."""
    actual = cargar(raiz, id_)
    if actual.estado != "POTENCIAL":
        raise OportunidadError(f"{id_}: está {actual.estado}; solo se evalúa una vacante POTENCIAL.")
    huella = _huella(publicacion)
    if actual.evaluacion and actual.evaluacion.huella == huella and not forzar:
        return actual

    evaluacion = Evaluacion(
        fecha=fecha or date.today(),
        huella=huella,
        criterios=criterios,
        filtros=filtros,
        brecha_principal=brecha_principal,
    )
    _validar_contra_configuracion(raiz, id_, evaluacion)
    oportunidad = actual.model_copy(update={"evaluacion": evaluacion})
    carpeta = _carpeta(raiz, id_)
    (carpeta / "publicacion.txt").write_text(publicacion, encoding="utf-8")
    _guardar(carpeta, oportunidad, Evento(tipo="EVALUADA", estado=actual.estado, detalle=f"huella {huella}"))
    return oportunidad


def _validar_contra_configuracion(raiz: Path, id_: str, evaluacion: Evaluacion) -> None:
    config = cargar_configuracion(raiz).priorizacion
    esperados = set(config.criterios)
    if set(evaluacion.criterios) != esperados:
        faltan, sobran = esperados - set(evaluacion.criterios), set(evaluacion.criterios) - esperados
        raise OportunidadError(
            f"{id_}: criterios distintos a la configuración (faltan {sorted(faltan)}, sobran {sorted(sobran)})."
        )
    del_agente = set(config.filtros_activos) - FILTROS_DEL_CODIGO
    if set(evaluacion.filtros) != del_agente:
        faltan, sobran = del_agente - set(evaluacion.filtros), set(evaluacion.filtros) - del_agente
        raise OportunidadError(
            f"{id_}: los filtros a calificar son {sorted(del_agente)} "
            f"(faltan {sorted(faltan)}, sobran {sorted(sobran)}); "
            f"{sorted(FILTROS_DEL_CODIGO)} los decide el código."
        )


def cambiar_estado(raiz: Path, id_: str, nuevo: Estado, motivo: str = "") -> Oportunidad:
    actual = cargar(raiz, id_)
    if nuevo not in _TRANSICIONES[actual.estado]:
        raise OportunidadError(f"{id_}: {actual.estado} no pasa a {nuevo}.")
    cambios: dict = {"estado": nuevo, "motivo": motivo or None}
    if actual.estado == "DESCARTADO":
        cambios["rescatada"] = True
    oportunidad = Oportunidad.model_validate({**actual.model_dump(), **cambios})
    _guardar(_carpeta(raiz, id_), oportunidad, Evento(tipo="CAMBIO_ESTADO", estado=nuevo, detalle=motivo))
    return oportunidad
