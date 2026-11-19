import json
import sys
from pathlib import Path

from agente0 import postulaciones, respuestas
from agente0.cv_limites import calibrar, cargar_limites, verificar
from agente0.datos import DatosError, cargar_configuracion, crear_estructura, datos_dir
from agente0.revisiones import Revision, fecha_ultima_revision, registrar_revision

USO = (
    "uso: python -m agente0 init | revision ultima | revision registrar (JSON por stdin)"
    " | cv calibrar <archivo.tex> <paginas> | cv verificar <archivo.tex> <limites.json>"
    " | postulacion crear | postulacion ver|intentar|confirmar|fallido|evento|finalizar <id> (JSON por stdin salvo ver)"
    " | respuestas listar|pendientes | respuestas ver|versiones <categoria> [<variante>]"
    " | respuestas guardar|revisar (JSON por stdin)"
)
ACCIONES_POSTULACION = ("crear", "ver", "intentar", "confirmar", "fallido", "evento", "finalizar")


def main(argv: list[str]) -> int:
    if argv in (["init"], ["revision", "ultima"], ["revision", "registrar"]):
        return _datos(argv)
    if argv[:1] == ["postulacion"] and len(argv) in (2, 3) and argv[1] in ACCIONES_POSTULACION:
        return _postulacion(argv[1], argv[2:])
    if argv[:1] == ["respuestas"] and len(argv) >= 2:
        return _respuestas(argv[1], argv[2:])
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


def _postulacion(accion: str, resto: list[str]) -> int:
    try:
        raiz = datos_dir()
        if (accion == "crear") != (not resto):
            raise ValueError("`crear` no lleva ID; las demás acciones sí.")
        if accion == "ver":
            resultado = postulaciones.cargar(raiz, resto[0])
        else:
            datos = json.loads(sys.stdin.read())
            if accion == "crear":
                resultado = postulaciones.crear(raiz, **datos)
            elif accion == "intentar":
                resultado = postulaciones.intentar_envio(raiz, resto[0], postulaciones.Envio.model_validate(datos))
            elif accion == "confirmar":
                resultado = postulaciones.confirmar_envio(raiz, resto[0], postulaciones.Evidencia.model_validate(datos))
            elif accion == "fallido":
                resultado = postulaciones.envio_fallido(raiz, resto[0], **datos)
            elif accion == "evento":
                resultado = postulaciones.registrar_evento(raiz, resto[0], **datos)
            else:
                resultado = postulaciones.finalizar(raiz, resto[0], **datos)
        print(resultado.model_dump_json(indent=2))
    except (DatosError, ValueError, TypeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _respuestas(accion: str, resto: list[str]) -> int:
    try:
        raiz = datos_dir()
        if accion in ("listar", "pendientes") and not resto:
            resultado = respuestas.listar(raiz) if accion == "listar" else respuestas.pendientes(raiz)
        elif accion in ("ver", "versiones") and len(resto) in (1, 2):
            if accion == "ver":
                resultado = respuestas.vigente(raiz, *resto)
            else:
                resultado = respuestas.versiones(raiz, *resto)
        elif accion in ("guardar", "revisar") and not resto:
            datos = json.loads(sys.stdin.read())
            if accion == "guardar":
                resultado = respuestas.guardar(raiz, **datos)
            else:
                respuestas.revisar(raiz, **datos)
                resultado = None
        else:
            print(USO, file=sys.stderr)
            return 2
        if isinstance(resultado, list):
            print(json.dumps([r.model_dump(mode="json") for r in resultado], ensure_ascii=False, indent=2))
        elif resultado is not None:
            print(resultado.model_dump_json(indent=2))
    except (DatosError, ValueError, TypeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
