import sys
from pathlib import Path

from agente0.cv_limites import calibrar, cargar_limites, verificar
from agente0.datos import DatosError, cargar_configuracion, crear_estructura, datos_dir
from agente0.revisiones import Revision, fecha_ultima_revision, registrar_revision

USO = (
    "uso: python -m agente0 init | revision ultima | revision registrar (JSON por stdin)"
    " | cv calibrar <archivo.tex> <paginas> | cv verificar <archivo.tex> <limites.json>"
)


def main(argv: list[str]) -> int:
    if argv in (["init"], ["revision", "ultima"], ["revision", "registrar"]):
        return _datos(argv)
    if len(argv) == 4 and argv[:2] == ["cv", "calibrar"] and argv[3].isdigit():
        print(calibrar(Path(argv[2]).read_text(encoding="utf-8"), int(argv[3])).model_dump_json(indent=2))
        return 0
    if len(argv) == 4 and argv[:2] == ["cv", "verificar"]:
        problemas = verificar(Path(argv[2]), cargar_limites(Path(argv[3])))
        for problema in problemas:
            print(problema)
        return 1 if problemas else 0
    print(USO, file=sys.stderr)
    return 2


def _datos(argv: list[str]) -> int:
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
