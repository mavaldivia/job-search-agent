import sys

from agente0.datos import DatosError, cargar_configuracion, crear_estructura, datos_dir
from agente0.revisiones import Revision, fecha_ultima_revision, registrar_revision

USO = "uso: python -m agente0 init | revision ultima | revision registrar (JSON por stdin)"


def main(argv: list[str]) -> int:
    if argv not in (["init"], ["revision", "ultima"], ["revision", "registrar"]):
        print(USO, file=sys.stderr)
        return 2
    try:
        if argv == ["init"]:
            raiz = datos_dir(debe_existir=False)
            crear_estructura(raiz)
            cargar_configuracion(raiz)
            print(raiz)
        elif argv == ["revision", "ultima"]:
            print(fecha_ultima_revision(datos_dir()) or "sin_revision")
        else:
            registrar_revision(datos_dir(), Revision.model_validate_json(sys.stdin.read()))
    except (DatosError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
