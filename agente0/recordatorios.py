from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

from agente0.datos import cargar_configuracion
from agente0.revisiones import fecha_onboarding, fecha_ultima_revision

ARCHIVO_RECORDATORIOS = "configuracion/recordatorios.json"
Caso = Literal["experiencia", "cv_base", "configuracion", "terminos"]
CASOS = get_args(Caso)
# Experiencia no se registra aquí: su reloj es la bitácora de revisiones de perfil.
CASOS_CON_REGISTRO = ("cv_base", "configuracion", "terminos")


class EstadoCaso(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ultima_operacion: date | None = None
    ultima_pregunta: datetime | None = None


class Recordatorios(BaseModel):
    model_config = ConfigDict(extra="forbid")

    casos: dict[Caso, EstadoCaso] = Field(default_factory=dict)


class Pendiente(BaseModel):
    caso: Caso
    ultima_operacion: date
    dias_desde: int
    ventana_dias: int


def _cargar(raiz: Path) -> Recordatorios:
    archivo = raiz / ARCHIVO_RECORDATORIOS
    if not archivo.exists():
        return Recordatorios()
    return Recordatorios.model_validate_json(archivo.read_text(encoding="utf-8"))


def _guardar(raiz: Path, recordatorios: Recordatorios) -> None:
    archivo = raiz / ARCHIVO_RECORDATORIOS
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(recordatorios.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _fechas_cv_base(raiz: Path) -> list[date]:
    carpeta = raiz / "cv" / "base"
    fechas = []
    for hijo in carpeta.iterdir() if carpeta.exists() else []:
        try:
            fechas.append(date.fromisoformat(hijo.name))
        except ValueError:
            continue
    return fechas


def fecha_ultima_operacion(raiz: Path, caso: Caso, recordatorios: Recordatorios | None = None) -> date | None:
    if caso == "experiencia":
        return fecha_ultima_revision(raiz)
    registrada = (recordatorios or _cargar(raiz)).casos.get(caso, EstadoCaso()).ultima_operacion
    if caso == "cv_base":
        return max([*_fechas_cv_base(raiz), *([registrada] if registrada else [])], default=None)
    if caso == "terminos":
        # Sin renovación registrada no hay reloj: lo parte la primera búsqueda con términos (B22).
        return registrada
    return registrada or fecha_onboarding(raiz)


def pendientes(raiz: Path, ahora: datetime | None = None) -> list[Pendiente]:
    """Casos con la ventana `X` vencida y sin pregunta en las últimas `repetir_recordatorio_horas`."""
    ahora = ahora or datetime.now()
    configuracion = cargar_configuracion(raiz)
    recordatorios = _cargar(raiz)
    resultado = []
    for caso in CASOS:
        desde = fecha_ultima_operacion(raiz, caso, recordatorios)
        if desde is None:
            continue
        ventana = getattr(configuracion.recordatorios_dias, caso)
        dias = (ahora.date() - desde).days
        ultima_pregunta = recordatorios.casos.get(caso, EstadoCaso()).ultima_pregunta
        if dias < ventana:
            continue
        if ultima_pregunta and ahora - ultima_pregunta < timedelta(hours=configuracion.repetir_recordatorio_horas):
            continue
        resultado.append(Pendiente(caso=caso, ultima_operacion=desde, dias_desde=dias, ventana_dias=ventana))
    return resultado


def registrar_pregunta(raiz: Path, caso: Caso, ahora: datetime | None = None) -> None:
    """Se llama con cualquier respuesta (aceptar o "ahora no"); no toca el reloj de la operación."""
    recordatorios = _cargar(raiz)
    recordatorios.casos.setdefault(caso, EstadoCaso()).ultima_pregunta = ahora or datetime.now()
    _guardar(raiz, recordatorios)


def registrar_operacion(raiz: Path, caso: Caso, hoy: date | None = None) -> None:
    if caso not in CASOS_CON_REGISTRO:
        raise ValueError(f"{caso!r} no se registra aquí: su reloj es la bitácora de revisiones de perfil.")
    recordatorios = _cargar(raiz)
    recordatorios.casos.setdefault(caso, EstadoCaso()).ultima_operacion = hoy or date.today()
    _guardar(raiz, recordatorios)
