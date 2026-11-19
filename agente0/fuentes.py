import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

ARCHIVO = "perfil/fuentes.json"


class FuenteBusqueda(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    tipo: Literal["generalista", "especializada", "corporativa", "headhunter"]
    pais: str = Field(min_length=1)
    # Una fila puede agrupar varios portales (por ejemplo "portales corporativos") y no tener un solo enlace.
    url: str | None = None
    # Cómo se descubren las vacantes (D10); postular siempre es por navegador (D4).
    metodo: Literal["web", "navegador"]
    riesgo: Literal["alto", "medio", "bajo"]
    activa: bool = True


_LISTA = TypeAdapter(list[FuenteBusqueda])


def cargar(raiz: Path) -> list[FuenteBusqueda]:
    archivo = raiz / ARCHIVO
    return _LISTA.validate_json(archivo.read_text(encoding="utf-8")) if archivo.exists() else []


def guardar(raiz: Path, fuentes: list[dict]) -> list[FuenteBusqueda]:
    """Reemplaza la lista completa. Para sumar una fuente que el usuario aprobó, usar `agregar`."""
    validadas = _LISTA.validate_python(fuentes)
    nombres = [f.nombre.casefold() for f in validadas]
    if len(nombres) != len(set(nombres)):
        raise ValueError("hay fuentes con el mismo nombre.")
    archivo = raiz / ARCHIVO
    archivo.parent.mkdir(parents=True, exist_ok=True)
    temporal = archivo.with_name(archivo.name + ".tmp")
    temporal.write_text(_LISTA.dump_json(validadas, indent=2).decode() + "\n", encoding="utf-8")
    os.replace(temporal, archivo)
    return validadas


def agregar(raiz: Path, **fuente) -> list[FuenteBusqueda]:
    actuales = [f.model_dump() for f in cargar(raiz)]
    return guardar(raiz, [*actuales, fuente])
