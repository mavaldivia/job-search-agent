from pydantic import BaseModel, ConfigDict, Field, field_validator

NIVELES_AUTONOMIA = (0, 25, 50, 75, 100)


class RecordatoriosDias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiencia: int = Field(default=15, gt=0)
    cv_base: int = Field(default=30, gt=0)
    configuracion: int = Field(default=60, gt=0)


class Configuracion(BaseModel):
    # extra="forbid": el archivo se edita a mano y un nombre mal escrito no debe ignorarse en silencio.
    model_config = ConfigDict(extra="forbid")

    autonomia: int = Field(default=0, ge=0, le=100)
    recordatorios_dias: RecordatoriosDias = Field(default_factory=RecordatoriosDias)
    posponer_dias: int = Field(default=7, gt=0)

    @field_validator("autonomia")
    @classmethod
    def _redondear_hacia_abajo(cls, valor: int) -> int:
        return max(n for n in NIVELES_AUTONOMIA if n <= valor)
