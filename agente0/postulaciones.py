import os
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agente0.esquemas import NIVELES_AUTONOMIA
from agente0.ids import id_postulacion

Estado = Literal["PREPARADA", "ENVIO_INTENTADO", "POSTULADO", "EN_PROCESO", "FINALIZADA"]
Resultado = Literal[
    "oferta_aceptada", "oferta_rechazada_por_usuario", "rechazada_por_empresa", "retirada", "sin_respuesta"
]
TipoEvento = Literal[
    "CAMBIO_ESTADO",
    "PRIMER_CONTACTO_ENTREVISTA",
    "ENTREVISTA_REALIZADA",
    "NUEVA_ETAPA",
    "OFERTA_RECIBIDA",
    "RECHAZO",
    "RETIRO",
    "CIERRE_POR_SILENCIO",
]

# D5: sin retrocesos; la única vuelta es ENVIO_INTENTADO -> PREPARADA si el envío falló sin enviarse (D14).
_TRANSICIONES: dict[str, set[str]] = {
    "PREPARADA": {"ENVIO_INTENTADO"},
    "ENVIO_INTENTADO": {"POSTULADO", "PREPARADA"},
    "POSTULADO": {"EN_PROCESO", "FINALIZADA"},
    "EN_PROCESO": {"EN_PROCESO", "FINALIZADA"},
    "FINALIZADA": set(),
}
# Eventos tipados (D5) que además mueven el estado: tipo -> (estado nuevo, campos que fijan).
_EFECTOS: dict[str, tuple[str, dict[str, str]]] = {
    "PRIMER_CONTACTO_ENTREVISTA": ("EN_PROCESO", {"etapa": "primera entrevista"}),
    "NUEVA_ETAPA": ("EN_PROCESO", {}),
    "RECHAZO": ("FINALIZADA", {"resultado": "rechazada_por_empresa"}),
    "RETIRO": ("FINALIZADA", {"resultado": "retirada"}),
    "CIERRE_POR_SILENCIO": ("FINALIZADA", {"resultado": "sin_respuesta"}),
}
_SOLO_REGISTRO = {"ENTREVISTA_REALIZADA", "OFERTA_RECIBIDA"}
_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class PostulacionError(ValueError):
    pass


class RespuestaEnviada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pregunta: str = Field(min_length=1)
    texto: str = Field(min_length=1)
    respuesta_id: str | None = None
    version: str | None = None


class Envio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    autonomia: int
    aprobacion: str = Field(min_length=1)
    cv: Path
    respuestas: list[RespuestaEnviada] = Field(default_factory=list)

    @field_validator("autonomia")
    @classmethod
    def _nivel_fijo(cls, valor: int) -> int:
        # Se registra el nivel realmente usado: redondear aquí falsearía la traza.
        if valor not in NIVELES_AUTONOMIA:
            raise ValueError(f"autonomia debe ser uno de {NIVELES_AUTONOMIA}.")
        return valor


class Evidencia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["confirmacion_visible", "correo", "verificacion_portal"]
    detalle: str = Field(min_length=1)
    captura: Path | None = None


class Postulacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    empresa: str
    cargo: str
    url: str
    estado: Estado = "PREPARADA"
    etapa: str | None = None
    resultado: Resultado | None = None
    fecha_postulacion: date | None = None
    intentos: int = 0

    @model_validator(mode="after")
    def _coherente(self) -> "Postulacion":
        if self.estado == "EN_PROCESO" and not self.etapa:
            raise ValueError("EN_PROCESO exige etapa.")
        if self.estado == "FINALIZADA" and not self.resultado:
            raise ValueError("FINALIZADA exige resultado.")
        return self


class Evento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    tipo: TipoEvento
    estado: Estado
    detalle: str = ""


def _carpeta(raiz: Path, id_: str) -> Path:
    if not _ID.fullmatch(id_):
        raise PostulacionError(f"ID de postulación inválido: {id_!r}.")
    return raiz / "postulaciones" / id_


def cargar(raiz: Path, id_: str) -> Postulacion:
    archivo = _carpeta(raiz, id_) / "postulacion.json"
    if not archivo.exists():
        raise PostulacionError(f"no existe la postulación {id_}.")
    return Postulacion.model_validate_json(archivo.read_text(encoding="utf-8"))


def _guardar(carpeta: Path, postulacion: Postulacion, evento: Evento) -> None:
    with (carpeta / "eventos.jsonl").open("a", encoding="utf-8") as archivo:
        archivo.write(evento.model_dump_json() + "\n")
    temporal = carpeta / "postulacion.json.tmp"
    temporal.write_text(postulacion.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.replace(temporal, carpeta / "postulacion.json")


def _mover(raiz: Path, id_: str, nuevo: str, tipo: str, detalle: str = "", **cambios) -> Postulacion:
    actual = cargar(raiz, id_)
    if nuevo not in _TRANSICIONES[actual.estado]:
        raise PostulacionError(f"{id_}: {actual.estado} no pasa a {nuevo}.")
    postulacion = Postulacion.model_validate({**actual.model_dump(), "estado": nuevo, **cambios})
    _guardar(_carpeta(raiz, id_), postulacion, Evento(tipo=tipo, estado=nuevo, detalle=detalle))
    return postulacion


def _exigir(postulacion: Postulacion, estado: str) -> None:
    if postulacion.estado != estado:
        raise PostulacionError(f"{postulacion.id}: está {postulacion.estado}, se requiere {estado}.")


def _congelar(carpeta: Path) -> None:
    # Solo lectura: la instantánea no se reescribe por accidente; la carpeta sigue abierta para sumar la evidencia.
    for archivo in carpeta.iterdir():
        archivo.chmod(0o444)


def crear(raiz: Path, empresa: str, cargo: str, url: str) -> Postulacion:
    id_ = id_postulacion(empresa, cargo, url)
    carpeta = _carpeta(raiz, id_)
    try:
        carpeta.mkdir(parents=True)
    except FileExistsError:
        raise PostulacionError(f"{id_} ya existe: no se crea de nuevo ni se reenvía sin instrucción expresa.") from None
    postulacion = Postulacion(id=id_, empresa=empresa, cargo=cargo, url=url)
    _guardar(carpeta, postulacion, Evento(tipo="CAMBIO_ESTADO", estado="PREPARADA", detalle="creada"))
    return postulacion


def intentar_envio(raiz: Path, id_: str, envio: Envio) -> Postulacion:
    """Congela lo que se envía (CV, respuestas literales, autonomía y aprobación) y pasa a ENVIO_INTENTADO."""
    actual = cargar(raiz, id_)
    _exigir(actual, "PREPARADA")
    if not envio.cv.is_file():
        raise PostulacionError(f"el CV {envio.cv} no existe.")
    intento = actual.intentos + 1
    destino = _carpeta(raiz, id_) / "instantanea" / f"{intento:03d}"
    destino.mkdir(parents=True)
    copia = destino / f"cv{envio.cv.suffix}"
    shutil.copyfile(envio.cv, copia)
    (destino / "envio.json").write_text(
        envio.model_copy(update={"cv": Path(copia.name)}).model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    _congelar(destino)
    return _mover(raiz, id_, "ENVIO_INTENTADO", "CAMBIO_ESTADO", f"intento {intento}", intentos=intento)


def confirmar_envio(raiz: Path, id_: str, evidencia: Evidencia) -> Postulacion:
    """POSTULADO solo con evidencia (D14): la guarda junto a la instantánea del intento confirmado."""
    actual = cargar(raiz, id_)
    _exigir(actual, "ENVIO_INTENTADO")
    destino = _carpeta(raiz, id_) / "instantanea" / f"{actual.intentos:03d}"
    nombre_captura = None
    if evidencia.captura is not None:
        if not evidencia.captura.is_file():
            raise PostulacionError(f"la captura {evidencia.captura} no existe.")
        nombre_captura = f"captura{evidencia.captura.suffix}"
        shutil.copyfile(evidencia.captura, destino / nombre_captura)
    with (destino / "evidencia.json").open("x", encoding="utf-8") as archivo:
        archivo.write(evidencia.model_copy(update={"captura": nombre_captura}).model_dump_json(indent=2) + "\n")
    _congelar(destino)
    return _mover(raiz, id_, "POSTULADO", "CAMBIO_ESTADO", evidencia.tipo, fecha_postulacion=date.today())


def envio_fallido(raiz: Path, id_: str, detalle: str) -> Postulacion:
    """El envío falló sin enviarse (D14): vuelve a PREPARADA; el próximo intento crea otra instantánea."""
    return _mover(raiz, id_, "PREPARADA", "CAMBIO_ESTADO", detalle)


def registrar_evento(raiz: Path, id_: str, tipo: str, detalle: str = "", etapa: str | None = None) -> Postulacion:
    actual = cargar(raiz, id_)
    if tipo in _SOLO_REGISTRO:
        _exigir(actual, "EN_PROCESO")
        estado, cambios = "EN_PROCESO", {}
    elif tipo in _EFECTOS:
        estado, cambios = _EFECTOS[tipo]
        if tipo == "PRIMER_CONTACTO_ENTREVISTA":
            # Solo desde POSTULADO: un segundo aviso no puede crear otro hito (regla 6 de CLAUDE.md).
            _exigir(actual, "POSTULADO")
        if tipo == "NUEVA_ETAPA":
            if not etapa:
                raise PostulacionError("NUEVA_ETAPA exige etapa.")
            cambios = {"etapa": etapa}
    else:
        raise PostulacionError(f"tipo de evento no válido: {tipo!r}.")
    return _mover(raiz, id_, estado, tipo, detalle, **cambios)


def finalizar(raiz: Path, id_: str, resultado: str, detalle: str = "") -> Postulacion:
    return _mover(raiz, id_, "FINALIZADA", "CAMBIO_ESTADO", detalle, resultado=resultado)
