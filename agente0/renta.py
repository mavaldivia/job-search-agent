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
    monto_exacto: float | None = None  # el bruto sin cerrar, solo cuando `monto` salió cerrado


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


PASOS_CLP = (100_000, 50_000)
# Tolerancia del bruto cerrado respecto del bruto exacto: con 100.000 de paso un bruto de unos 4 MM se mueve hasta 1,3 %.
TOLERANCIA_BRUTO_CERRADO = 0.015


def cerrar_monto(valor: float, piso: float | None = None, techo: float | None = None) -> int:
    """Número cerrado en pesos: el múltiplo de 100.000 más cercano dentro de [piso, techo] y, si no cabe ninguno, de 50.000.

    Si tampoco cabe un múltiplo de 50.000, vale el borde que corresponda (la mínima o el tope ya vienen redondos).
    """
    for paso in PASOS_CLP:
        candidato = int(valor // paso + (valor % paso >= paso / 2)) * paso
        if techo is not None and candidato > techo:
            candidato = int(techo // paso) * paso
        if piso is not None and candidato < piso:
            candidato = -int(-piso // paso) * paso
        if (piso is None or candidato >= piso) and (techo is None or candidato <= techo):
            return candidato
    acotado = min(max(valor, piso if piso is not None else valor), techo if techo is not None else valor)
    return int(round(acotado))


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

    `tasa` son unidades de moneda local por una de la moneda de destino (por ejemplo, pesos por dólar). El bruto de Chile
    en pesos sale cerrado (`cerrar_monto`) dentro de una tolerancia del bruto exacto; el resto, con dos decimales.
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
    elif a_bruto and pais is not None and _pais(pais) == "CL":
        cerrado = cerrar_monto(monto, monto * (1 - TOLERANCIA_BRUTO_CERRADO), monto * (1 + TOLERANCIA_BRUTO_CERRADO))
        return Conversion(
            liquido=liquido, factor=factor, tasa=tasa, monto=float(cerrado), monto_exacto=round(monto, 2)
        )
    return Conversion(liquido=liquido, factor=factor, tasa=tasa, monto=round(monto, 2))


def _pais(pais: str) -> str:
    if len(pais) != 2 or not pais.isalpha():
        raise ValueError(f"el país va con su código de dos letras (por ejemplo CL), no {pais!r}.")
    return pais.upper()
