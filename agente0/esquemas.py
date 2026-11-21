from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NIVELES_AUTONOMIA = (0, 25, 50, 75, 100)

Eje = Literal["tengo", "quiero"]
FiltroExcluyente = Literal[
    "renta", "modalidad_ubicacion", "seniority", "empresa_excluida", "requisitos_obligatorios", "cargo_mal_fit"
]
FILTROS_EXCLUYENTES = get_args(FiltroExcluyente)
Riesgo = Literal["alto", "medio", "bajo"]
CondicionPreferencia = Literal["seniority", "ubicacion", "umbral_match", "sin_proceso_activo", "renta_minima"]
CONDICIONES_PREFERENCIA = get_args(CondicionPreferencia)


class RecordatoriosDias(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiencia: int = Field(default=15, gt=0)
    cv_base: int = Field(default=30, gt=0)
    configuracion: int = Field(default=60, gt=0)
    # B22: los nombres de los cargos cambian rápido en el mercado, así que los términos de búsqueda se renuevan antes.
    terminos: int = Field(default=15, gt=0)


class ConversionRenta(BaseModel):
    """Cuándo se reutiliza el factor líquido a bruto guardado (B17) en vez de investigarlo de nuevo."""

    model_config = ConfigDict(extra="forbid")

    vigencia_factor_dias: int = Field(default=30, gt=0)
    # El impuesto es progresivo: el factor solo vale cerca del líquido con que se calculó.
    banda_monto_pct: float = Field(default=10, ge=0)


class Mercado(BaseModel):
    """B24: vigencia de la tabla de mercado y qué percentil se propone como renta según la modalidad."""

    model_config = ConfigDict(extra="forbid")

    vigencia_dias: int = Field(default=30, gt=0)
    percentil_base: Literal[50, 75, 90] = 75
    percentil_presencial: Literal[50, 75, 90] = 90
    # La unidad en que está expresada `priorizacion.renta_minima`; los rangos en otra unidad piden la mínima convertida.
    unidad_renta_minima: str = Field(default="CLP líquido mensual", min_length=1)
    # Techo de la renta que se propone en los cargos exigentes (nivel Manager o superior con mucha presencialidad o
    # lejos de casa), en la misma unidad que la mínima; sin valor, la propone el mercado sin límite.
    renta_maxima: int | None = Field(default=None, gt=0)
    # Tope en el resto de los cargos; sin valor rige `renta_maxima`.
    renta_tope_general: int | None = Field(default=None, gt=0)
    # Lo que se propone en un cargo general cuando el mercado no publica rango (en los exigentes, `renta_maxima`).
    renta_estandar: int | None = Field(default=None, gt=0)
    # Con mucho fit la propuesta sube de su base al tope del cargo: nada bajo `fit_desde`, el tope desde `fit_pleno`.
    fit_desde: float = Field(default=70, ge=0, le=100)
    fit_pleno: float = Field(default=90, gt=0, le=100)

    @model_validator(mode="after")
    def _escalones_ordenados(self) -> "Mercado":
        if self.fit_desde >= self.fit_pleno:
            raise ValueError("`fit_desde` debe ser menor que `fit_pleno`.")
        escalones = [v for v in (self.renta_estandar, self.renta_tope_general, self.renta_maxima) if v is not None]
        if escalones != sorted(escalones):
            raise ValueError("deben cumplir renta_estandar <= renta_tope_general <= renta_maxima.")
        return self


class TopeCorrida(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paginas: int = Field(gt=0)
    lecturas: int = Field(gt=0)


class Busqueda(BaseModel):
    """Cuánto recorre cada búsqueda según el riesgo de la fuente (D4); valores iniciales a ajustar al iterar."""

    model_config = ConfigDict(extra="forbid")

    # Páginas de resultados y publicaciones leídas por fuente y día. Sin tope para el riesgo que no figura aquí, y sin
    # tope en el primer día de búsqueda de una fuente (primera pasada completa).
    topes_por_riesgo: dict[Riesgo, TopeCorrida] = Field(
        default_factory=lambda: {
            "alto": TopeCorrida(paginas=3, lecturas=10),
            "medio": TopeCorrida(paginas=5, lecturas=25),
        }
    )


class Medicion(BaseModel):
    """D16 y D17: ventanas de medición y umbrales de la recomendación de respuestas; valores iniciales sin validar."""

    model_config = ConfigDict(extra="forbid")

    ventana_semanas: int = Field(default=4, ge=4, le=6)
    # Con menos contactos que esto en una ventana, el reporte dice «sin conclusión».
    minimo_contactos: int = Field(default=5, gt=0)
    # Un uso entra a la tasa de una respuesta cuando se resolvió o pasaron estos días desde el envío (D5).
    dias_para_resolver: int = Field(default=30, gt=0)
    # Tasa suavizada: la base del usuario pesa como estos usos virtuales; se recomienda desde estos usos comparables.
    usos_virtuales: int = Field(default=5, gt=0)
    usos_para_recomendar: int = Field(default=8, gt=0)


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


def _nivel_hacia_abajo(valor: int) -> int:
    return max(n for n in NIVELES_AUTONOMIA if n <= valor)


class LimitesDiarios(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alto: int = Field(default=3, ge=0)
    medio: int = Field(default=5, ge=0)
    bajo: int = Field(default=8, ge=0)


class Compuerta(BaseModel):
    """Parámetros de la compuerta de autonomía (D12 y U4). Los valores iniciales son los de D12."""

    model_config = ConfigDict(extra="forbid")

    limites_diarios: LimitesDiarios = Field(default_factory=LimitesDiarios)
    pausa_minutos: int = Field(default=2, ge=0)
    # B25: portales que se trabajan a la vez (un subagente y una pestaña por portal); dentro de cada uno, en serie.
    carriles_en_paralelo: int = Field(default=4, ge=1)
    # Nivel máximo según el riesgo del portal (U5) y por nombre de portal; este último manda sobre el primero.
    tope_por_riesgo: dict[Riesgo, int] = Field(default_factory=lambda: {"alto": 50})
    topes_por_portal: dict[str, int] = Field(default_factory=dict)
    # Aprobar el envío a mano aunque el nivel sea más alto.
    siempre_aprobar_portales: list[str] = Field(default_factory=list)
    siempre_aprobar_empresas: list[str] = Field(default_factory=list)
    # Quitar una condición de la lista la desactiva; las reglas siempre vigentes de D12 no son configurables.
    condiciones_preferencia: list[CondicionPreferencia] = Field(default_factory=lambda: list(CONDICIONES_PREFERENCIA))
    # Una condición activa con lista vacía no se cumple nunca: sin configurar, nada se envía solo.
    seniority_permitido: list[str] = Field(default_factory=list)
    ubicaciones_permitidas: list[str] = Field(default_factory=list)

    @field_validator("tope_por_riesgo", "topes_por_portal")
    @classmethod
    def _topes_a_nivel_fijo(cls, topes: dict) -> dict:
        if any(not 0 <= valor <= 100 for valor in topes.values()):
            raise ValueError("un tope de nivel va de 0 a 100.")
        return {clave: _nivel_hacia_abajo(valor) for clave, valor in topes.items()}


class Configuracion(BaseModel):
    # extra="forbid": el archivo se edita a mano y un nombre mal escrito no debe ignorarse en silencio.
    model_config = ConfigDict(extra="forbid")

    autonomia: int = Field(default=0, ge=0, le=100)
    recordatorios_dias: RecordatoriosDias = Field(default_factory=RecordatoriosDias)
    repetir_recordatorio_horas: int = Field(default=24, gt=0)
    recompensa_primer_contacto: float = Field(default=1.0, gt=0)
    priorizacion: Priorizacion = Field(default_factory=Priorizacion)
    compuerta: Compuerta = Field(default_factory=Compuerta)
    conversion_renta: ConversionRenta = Field(default_factory=ConversionRenta)
    busqueda: Busqueda = Field(default_factory=Busqueda)
    mercado: Mercado = Field(default_factory=Mercado)
    medicion: Medicion = Field(default_factory=Medicion)

    @field_validator("autonomia")
    @classmethod
    def _redondear_hacia_abajo(cls, valor: int) -> int:
        return _nivel_hacia_abajo(valor)
