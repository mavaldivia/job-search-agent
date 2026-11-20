import os
from pathlib import Path

from agente0.esquemas import Configuracion

ENV_VAR = "AGENTE0_DATOS"
DIRECTORIOS = (
    "perfil",
    "configuracion",
    "cv/base",
    "respuestas",
    "oportunidades",
    "busquedas",
    "ranking",
    "postulaciones",
    "origen",
    "respaldos",
)
ARCHIVO_CONFIGURACION = "configuracion/configuracion.json"
REPO = Path(__file__).resolve().parent.parent


class DatosError(Exception):
    pass


def datos_dir(*, debe_existir: bool = True) -> Path:
    valor = os.environ.get(ENV_VAR)
    if not valor:
        raise DatosError(
            f"{ENV_VAR} no está definida: indica la carpeta de datos del usuario (sugerida: Agente0_datos/<usuario>, junto al repo)."
        )
    raiz = Path(valor).expanduser().resolve()
    if raiz == REPO or REPO in raiz.parents:
        raise DatosError(f"{raiz} está dentro del repo: los datos del usuario van fuera (D3).")
    if debe_existir and not raiz.is_dir():
        raise DatosError(f"{raiz} no existe: ejecuta `python -m agente0 init`.")
    return raiz


def crear_estructura(raiz: Path) -> None:
    for directorio in DIRECTORIOS:
        (raiz / directorio).mkdir(parents=True, exist_ok=True)
    configuracion = raiz / ARCHIVO_CONFIGURACION
    if not configuracion.exists():
        configuracion.write_text(Configuracion().model_dump_json(indent=2) + "\n", encoding="utf-8")


def cargar_configuracion(raiz: Path) -> Configuracion:
    return Configuracion.model_validate_json((raiz / ARCHIVO_CONFIGURACION).read_text(encoding="utf-8"))
