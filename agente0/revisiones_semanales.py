from datetime import date, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

ARCHIVO = "medicion/revisiones_semanales.jsonl"
VENTANA_INICIAL_DIAS = 7


class RevisionSemanalError(ValueError):
    pass


class RevisionSemanal(BaseModel):
    """La revisión semanal de lo enviado (B12): el período cubierto y las horas que el usuario dedicó (D17)."""

    model_config = ConfigDict(extra="forbid")

    registrada: date = Field(default_factory=date.today)
    desde: date
    hasta: date
    horas_esfuerzo: float = Field(ge=0)
    nota: str = ""

    @model_validator(mode="after")
    def _periodo(self) -> "RevisionSemanal":
        if self.hasta < self.desde:
            raise ValueError("`hasta` no puede ser anterior a `desde`.")
        return self


def revisiones(raiz: Path) -> list[RevisionSemanal]:
    archivo = raiz / ARCHIVO
    if not archivo.exists():
        return []
    lineas = [linea for linea in archivo.read_text(encoding="utf-8").splitlines() if linea.strip()]
    return [RevisionSemanal.model_validate_json(linea) for linea in lineas]


def periodo_pendiente(raiz: Path, hoy: date | None = None) -> tuple[date, date]:
    """Desde el día siguiente a la última revisión (o los últimos 7 días si no hay) hasta hoy."""
    hoy = hoy or date.today()
    previas = revisiones(raiz)
    desde = previas[-1].hasta + timedelta(days=1) if previas else hoy - timedelta(days=VENTANA_INICIAL_DIAS - 1)
    return min(desde, hoy), hoy


def registrar(raiz: Path, desde: date, hasta: date, horas_esfuerzo: float, nota: str = "") -> RevisionSemanal:
    """Los períodos no se solapan: las horas de un mismo día no se cuentan dos veces."""
    nueva = RevisionSemanal(desde=desde, hasta=hasta, horas_esfuerzo=horas_esfuerzo, nota=nota)
    for previa in revisiones(raiz):
        if nueva.desde <= previa.hasta and previa.desde <= nueva.hasta:
            raise RevisionSemanalError(
                f"el período {nueva.desde} a {nueva.hasta} se solapa con la revisión "
                f"de {previa.desde} a {previa.hasta}."
            )
    archivo = raiz / ARCHIVO
    archivo.parent.mkdir(parents=True, exist_ok=True)
    with archivo.open("a", encoding="utf-8") as f:
        f.write(nueva.model_dump_json() + "\n")
    return nueva
