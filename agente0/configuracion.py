import os
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from agente0.datos import ARCHIVO_CONFIGURACION, cargar_configuracion
from agente0.esquemas import Configuracion

ARCHIVO_AUTONOMIA = "configuracion/autonomia.jsonl"
# Mapas con claves libres: un cambio los reemplaza completos; el resto de los bloques se fusiona clave a clave.
MAPAS = {"criterios", "tope_por_riesgo", "topes_por_portal"}


class ConfiguracionError(ValueError):
    pass


class CambioAutonomia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: datetime
    de: int
    a: int
    # Texto de la confirmación explícita del usuario tras el aviso de D12 (obligatoria al activar 100 %).
    confirmacion: str | None = None


def _fusionar(actual: dict, cambios: dict) -> dict:
    fusion = dict(actual)
    for clave, valor in cambios.items():
        if isinstance(valor, dict) and isinstance(actual.get(clave), dict) and clave not in MAPAS:
            fusion[clave] = _fusionar(actual[clave], valor)
        else:
            fusion[clave] = valor
    return fusion


def aplicar(actual: Configuracion, cambios: dict) -> tuple[Configuracion, list[str]]:
    """La configuración que resulta de un cambio parcial, validada y sin escribir nada, con sus advertencias."""
    nueva = Configuracion.model_validate(_fusionar(actual.model_dump(mode="json"), cambios))
    advertencias = []
    if "autonomia" in cambios and nueva.autonomia != cambios["autonomia"]:
        advertencias.append(f"autonomía {cambios['autonomia']} redondeada hacia abajo a {nueva.autonomia} % (D12).")
    if nueva.autonomia >= 75:
        advertencias += _listas_vacias(nueva)
    return nueva, advertencias


def editar(
    raiz: Path, cambios: dict, confirmacion: str | None = None, ahora: datetime | None = None
) -> tuple[Configuracion, list[str]]:
    """Aplica un cambio parcial a la configuración sin tocar código (U4). Devuelve la vigente y las advertencias."""
    actual = cargar_configuracion(raiz)
    nueva, advertencias = aplicar(actual, cambios)
    if nueva.autonomia == 100 and actual.autonomia != 100 and not (confirmacion or "").strip():
        raise ConfiguracionError(
            "activar 100 % exige mostrar el aviso de D12 (`autonomia aviso 100`) y la confirmación explícita del usuario."
        )

    destino = raiz / ARCHIVO_CONFIGURACION
    temporal = destino.with_name(destino.name + ".tmp")
    temporal.write_text(nueva.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.replace(temporal, destino)
    if nueva.autonomia != actual.autonomia:
        _registrar_cambio_de_autonomia(
            raiz,
            CambioAutonomia(
                fecha=ahora or datetime.now().astimezone(),
                de=actual.autonomia,
                a=nueva.autonomia,
                confirmacion=(confirmacion or "").strip() or None,
            ),
        )
    return nueva, advertencias


def _listas_vacias(config: Configuracion) -> list[str]:
    c = config.compuerta
    avisos = []
    if "seniority" in c.condiciones_preferencia and not c.seniority_permitido:
        avisos.append("seniority_permitido está vacío: al 75 % nada se enviará solo hasta que lo definas.")
    if "ubicacion" in c.condiciones_preferencia and not c.ubicaciones_permitidas:
        avisos.append("ubicaciones_permitidas está vacío: al 75 % nada se enviará solo hasta que lo definas.")
    return avisos


def _registrar_cambio_de_autonomia(raiz: Path, cambio: CambioAutonomia) -> None:
    bitacora = raiz / ARCHIVO_AUTONOMIA
    bitacora.parent.mkdir(parents=True, exist_ok=True)
    with bitacora.open("a", encoding="utf-8") as archivo:
        archivo.write(cambio.model_dump_json() + "\n")
