from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NIVELES_AUTONOMIA = (0, 25, 50, 75, 100)

Eje = Literal["tengo", "quiero"]
FiltroExcluyente = Literal[
    "renta", "modalidad_ubicacion", "seniority", "empresa_excluida", "requisitos_obligatorios", "cargo_mal_fit"
]
FILTROS_EXCLUYENTES = get_args(FiltroExcluyente)


class RecordatoriosDias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiencia: int = Field(default=15, gt=0)
    cv_base: int = Field(default=30, gt=0)
    configuracion: int = Field(default=60, gt=0)


class Criterio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eje: Eje
    peso: int = Field(gt=0)


def _criterios_d11() -> dict[str, Criterio]:
    return {
        "ajuste_experiencia": Criterio(eje="tengo", peso=30),
        "compatibilidad_tecnica": Criterio(eje="tengo", peso=20),
        "factibilidad": Criterio(eje="tengo", peso=5),
        "liderazgo_crecimiento": Criterio(eje="quiero", peso=20),
        "remuneracion": Criterio(eje="quiero", peso=15),
        "industria_empresa": Criterio(eje="quiero", peso=10),
    }


class UmbralesMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tengo: int = Field(default=70, ge=0, le=100)
    quiero: int = Field(default=60, ge=0, le=100)


class Priorizacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterios: dict[str, Criterio] = Field(default_factory=_criterios_d11)
    umbrales: UmbralesMatch = Field(default_factory=UmbralesMatch)
    top: int = Field(default=10, gt=0)
    ventana_dias: int = Field(default=30, gt=0)
    filtros_activos: list[FiltroExcluyente] = Field(default_factory=lambda: list(FILTROS_EXCLUYENTES))
    # Mismo monto, moneda y período que la renta publicada que se registra en la evidencia de cada vacante.
    renta_minima: int | None = Field(default=None, gt=0)
    empresas_excluidas: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ambos_ejes_tienen_criterios(self) -> "Priorizacion":
        for eje in get_args(Eje):
            if not any(c.eje == eje for c in self.criterios.values()):
                raise ValueError(f"el eje {eje!r} necesita al menos un criterio.")
        return self


class Configuracion(BaseModel):
    # extra="forbid": el archivo se edita a mano y un nombre mal escrito no debe ignorarse en silencio.
    model_config = ConfigDict(extra="forbid")

    autonomia: int = Field(default=0, ge=0, le=100)
    recordatorios_dias: RecordatoriosDias = Field(default_factory=RecordatoriosDias)
    posponer_dias: int = Field(default=7, gt=0)
    priorizacion: Priorizacion = Field(default_factory=Priorizacion)

    @field_validator("autonomia")
    @classmethod
    def _redondear_hacia_abajo(cls, valor: int) -> int:
        return max(n for n in NIVELES_AUTONOMIA if n <= valor)
