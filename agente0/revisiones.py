import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ARCHIVO_REVISIONES = "perfil/revisiones_perfil.jsonl"
_ONBOARDING = re.compile(r"^onboarding_completo:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)


class Cambio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # La bitácora es append-only: una sección mal escrita quedaría para siempre.
    seccion: str = Field(pattern=r"^([EIC]\d{1,2}[a-z]?|diario)$")
    resumen: str = Field(min_length=1)


class Revision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date = Field(default_factory=date.today)
    modo: Literal["cuentame", "preguntame"]
    cambios: list[Cambio] = Field(default_factory=list)


def registrar_revision(raiz: Path, revision: Revision) -> None:
    bitacora = raiz / ARCHIVO_REVISIONES
    bitacora.parent.mkdir(parents=True, exist_ok=True)
    with bitacora.open("a", encoding="utf-8") as archivo:
        archivo.write(revision.model_dump_json() + "\n")


def fecha_ultima_revision(raiz: Path) -> date | None:
    """Última revisión registrada; sin bitácora, la fecha de `onboarding_completo` en perfil/perfil.md."""
    bitacora = raiz / ARCHIVO_REVISIONES
    if bitacora.exists():
        lineas = [linea for linea in bitacora.read_text(encoding="utf-8").splitlines() if linea.strip()]
        if lineas:
            return Revision.model_validate_json(lineas[-1]).fecha
    perfil = raiz / "perfil" / "perfil.md"
    if perfil.exists():
        coincidencia = _ONBOARDING.search(perfil.read_text(encoding="utf-8"))
        if coincidencia:
            return date.fromisoformat(coincidencia.group(1))
    return None
