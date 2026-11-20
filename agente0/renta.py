import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from agente0.datos import cargar_configuracion

ARCHIVO_FACTORES = "configuracion/renta_factores.json"


class FactorNoVigente(ValueError):
    pass


class FactorBruto(BaseModel):
    """Resultado de investigar el paso de líquido a bruto en un país, con lo que hace falta para auditarlo."""

    model_config = ConfigDict(extra="forbid")

    investigado: date
    liquido_referencia: float = Field(gt=0)
    factor: float = Field(ge=1)
    supuestos: str = Field(min_length=1)
    fuentes: list[str] = Field(min_length=1)


class Conversion(BaseModel):
    liquido: float
    factor: float | None
    tasa: float | None
    monto: float


def _cargar(raiz: Path) -> dict[str, FactorBruto]:
    archivo = raiz / ARCHIVO_FACTORES
    if not archivo.exists():
        return {}
    crudo = json.loads(archivo.read_text(encoding="utf-8"))
    return {pais: FactorBruto.model_validate(factor) for pais, factor in crudo.items()}


def guardar_factor(raiz: Path, pais: str, factor: FactorBruto) -> None:
    pais = _pais(pais)
    factores = _cargar(raiz)
    factores[pais] = factor
    archivo = raiz / ARCHIVO_FACTORES
    archivo.parent.mkdir(parents=True, exist_ok=True)
    crudo = {p: f.model_dump(mode="json") for p, f in factores.items()}
    archivo.write_text(json.dumps(crudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def factor_vigente(raiz: Path, pais: str, liquido: float, hoy: date | None = None) -> FactorBruto:
    """El factor guardado si sirve para este monto hoy; si no, `FactorNoVigente` con el motivo (hay que investigarlo)."""
    pais = _pais(pais)
    factor = _cargar(raiz).get(pais)
    if factor is None:
        raise FactorNoVigente(f"no hay factor líquido a bruto guardado para {pais}: investígalo y guárdalo.")
    parametros = cargar_configuracion(raiz).conversion_renta
    dias = ((hoy or date.today()) - factor.investigado).days
    if dias >= parametros.vigencia_factor_dias:
        raise FactorNoVigente(
            f"el factor de {pais} se investigó hace {dias} días (vigencia {parametros.vigencia_factor_dias}): investígalo de nuevo."
        )
    distancia = abs(liquido - factor.liquido_referencia) / factor.liquido_referencia * 100
    if distancia > parametros.banda_monto_pct:
        raise FactorNoVigente(
            f"el factor de {pais} se calculó para un líquido de {factor.liquido_referencia:,.0f} y {liquido:,.0f} "
            f"difiere {distancia:.1f} % (banda {parametros.banda_monto_pct:g} %): investígalo para este monto."
        )
    return factor


def convertir(
    raiz: Path,
    liquido: float,
    *,
    pais: str | None = None,
    a_bruto: bool = False,
    tasa: float | None = None,
    hoy: date | None = None,
) -> Conversion:
    """Dos pasos independientes sobre un líquido en moneda local: pasar a bruto (factor guardado) y/o a otra moneda.

    `tasa` son unidades de moneda local por una de la moneda de destino (por ejemplo, pesos por dólar).
    """
    if liquido <= 0 or (tasa is not None and tasa <= 0):
        raise ValueError("el líquido y la tasa deben ser positivos.")
    if not a_bruto and tasa is None:
        raise ValueError("no hay nada que convertir: pide el paso a bruto, una tasa de cambio o ambos.")
    factor = None
    monto = liquido
    if a_bruto:
        if pais is None:
            raise ValueError("pasar a bruto exige el país.")
        factor = factor_vigente(raiz, pais, liquido, hoy).factor
        monto *= factor
    if tasa is not None:
        monto /= tasa
    return Conversion(liquido=liquido, factor=factor, tasa=tasa, monto=round(monto, 2))


def _pais(pais: str) -> str:
    if len(pais) != 2 or not pais.isalpha():
        raise ValueError(f"el país va con su código de dos letras (por ejemplo CL), no {pais!r}.")
    return pais.upper()
