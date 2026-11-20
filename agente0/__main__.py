import json
import sys
from pathlib import Path

from agente0 import autonomia, configuracion, fuentes, oportunidades, postulaciones, ranking, recordatorios, respuestas
from agente0.cv_limites import calibrar, cargar_limites, verificar
from agente0.datos import DatosError, cargar_configuracion, crear_estructura, datos_dir
from agente0.revisiones import Revision, fecha_ultima_revision, registrar_revision

USO = (
    "uso: python -m agente0 init | configuracion ver | revision ultima | revision registrar (JSON por stdin)"
    " | recordatorio pendientes | recordatorio preguntado|operacion <experiencia|cv_base|configuracion>"
    " | cv calibrar <archivo.tex> <paginas> | cv verificar <archivo.tex> <limites.json>"
    " | postulacion crear | postulacion ver|intentar|confirmar|fallido|evento|recompensar|finalizar <id> (JSON por stdin salvo ver y recompensar)"
    " | respuestas listar|pendientes | respuestas ver|versiones <categoria> [<variante>]"
    " | respuestas guardar|revisar (JSON por stdin)"
    " | oportunidad registrar (JSON por stdin) | oportunidad listar [ESTADO] | oportunidad ver <id>"
    " | oportunidad evaluar|estado <id> (JSON por stdin)"
    " | ranking generar|ultimo | fuentes listar | fuentes guardar|agregar (JSON por stdin)"
    " | autonomia evaluar <id> (JSON por stdin: portal, juicios) | autonomia matriz [nivel] | autonomia aviso <nivel>"
    " | configuracion editar (JSON por stdin: cambios, confirmacion)"
)
ACCIONES_POSTULACION = ("crear", "ver", "intentar", "confirmar", "fallido", "evento", "recompensar", "finalizar")


def main(argv: list[str]) -> int:
    if argv in (["init"], ["configuracion", "ver"], ["revision", "ultima"], ["revision", "registrar"]):
        return _datos(argv)
    if argv[:1] == ["recordatorio"]:
        return _recordatorio(argv[1:])
    if argv[:1] == ["postulacion"] and len(argv) in (2, 3) and argv[1] in ACCIONES_POSTULACION:
        return _postulacion(argv[1], argv[2:])
    if argv[:1] == ["respuestas"] and len(argv) >= 2:
        return _respuestas(argv[1], argv[2:])
    if argv[:1] == ["oportunidad"] and len(argv) >= 2:
        return _oportunidad(argv[1], argv[2:])
    if argv[:2] == ["autonomia", "evaluar"] and len(argv) == 3:
        return _autonomia_evaluar(argv[2])
    if argv[:2] in (["autonomia", "matriz"], ["autonomia", "aviso"]) and len(argv) <= 3:
        return _autonomia_texto(argv[1], argv[2:])
    if argv == ["configuracion", "editar"]:
        return _configuracion_editar()
    if argv[:1] in (["ranking"], ["fuentes"]) and len(argv) == 2:
        return _ranking_o_fuentes(argv[0], argv[1])
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
        elif argv == ["configuracion", "ver"]:
            print(cargar_configuracion(datos_dir()).model_dump_json(indent=2))
        elif argv == ["revision", "ultima"]:
            print(fecha_ultima_revision(datos_dir()) or "sin_revision")
        else:
            registrar_revision(datos_dir(), Revision.model_validate_json(sys.stdin.read()))
    except (DatosError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _recordatorio(resto: list[str]) -> int:
    try:
        raiz = datos_dir()
        if resto == ["pendientes"]:
            vencidos = [p.model_dump(mode="json") for p in recordatorios.pendientes(raiz)]
            print(json.dumps(vencidos, ensure_ascii=False, indent=2))
        elif len(resto) == 2 and resto[0] == "preguntado" and resto[1] in recordatorios.CASOS:
            recordatorios.registrar_pregunta(raiz, resto[1])
        elif len(resto) == 2 and resto[0] == "operacion" and resto[1] in recordatorios.CASOS:
            recordatorios.registrar_operacion(raiz, resto[1])
        else:
            print(USO, file=sys.stderr)
            return 2
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
        elif accion == "recompensar":
            resultado = postulaciones.recompensar(raiz, resto[0], cargar_configuracion(raiz).recompensa_primer_contacto)
        else:
            datos = json.loads(sys.stdin.read())
            if accion == "crear":
                resultado = postulaciones.crear(raiz, **datos)
            elif accion == "intentar":
                solicitud = autonomia.SolicitudEnvio.model_validate(datos)
                resultado = postulaciones.intentar_envio(
                    raiz, resto[0], autonomia.preparar_envio(raiz, resto[0], solicitud)
                )
            elif accion == "confirmar":
                resultado = postulaciones.confirmar_envio(raiz, resto[0], postulaciones.Evidencia.model_validate(datos))
            elif accion == "fallido":
                resultado = postulaciones.envio_fallido(raiz, resto[0], **datos)
            elif accion == "evento":
                if isinstance(datos, dict) and datos.get("tipo") == "PRIMER_CONTACTO_ENTREVISTA":
                    datos["valor_recompensa"] = cargar_configuracion(raiz).recompensa_primer_contacto
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


def _imprimir(resultado) -> None:
    if isinstance(resultado, list):
        print(json.dumps([r.model_dump(mode="json") for r in resultado], ensure_ascii=False, indent=2))
    elif resultado is not None:
        print(resultado.model_dump_json(indent=2))


def _oportunidad(accion: str, resto: list[str]) -> int:
    try:
        raiz = datos_dir()
        if accion == "listar" and len(resto) <= 1:
            resultado = oportunidades.listar(raiz, *resto)
        elif accion == "ver" and len(resto) == 1:
            resultado = oportunidades.cargar(raiz, resto[0])
        elif accion == "registrar" and not resto:
            resultado = oportunidades.registrar(raiz, **json.loads(sys.stdin.read()))
        elif accion == "evaluar" and len(resto) == 1:
            resultado = oportunidades.evaluar(raiz, resto[0], **json.loads(sys.stdin.read()))
        elif accion == "estado" and len(resto) == 1:
            resultado = oportunidades.cambiar_estado(raiz, resto[0], **json.loads(sys.stdin.read()))
        else:
            print(USO, file=sys.stderr)
            return 2
        _imprimir(resultado)
    except (DatosError, ValueError, TypeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _autonomia_evaluar(id_: str) -> int:
    try:
        datos = json.loads(sys.stdin.read())
        juicios = autonomia.Juicios.model_validate(datos.get("juicios") or {})
        _imprimir(autonomia.evaluar(datos_dir(), id_, datos["portal"], juicios))
    except (DatosError, ValueError, TypeError, KeyError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _autonomia_texto(accion: str, resto: list[str]) -> int:
    try:
        if resto and not resto[0].isdigit():
            raise ValueError(f"el nivel debe ser un número, no {resto[0]!r}.")
        nivel = int(resto[0]) if resto else None
        if accion == "aviso":
            if nivel is None:
                raise ValueError("`aviso` exige el nivel.")
            lineas = autonomia.aviso(datos_dir(), nivel)
        else:
            lineas = autonomia.vista_previa(nivel)
        print("\n".join(lineas))
    except (DatosError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _configuracion_editar() -> int:
    try:
        datos = json.loads(sys.stdin.read())
        nueva, advertencias = configuracion.editar(datos_dir(), datos["cambios"], datos.get("confirmacion"))
        print(
            json.dumps(
                {"configuracion": nueva.model_dump(mode="json"), "advertencias": advertencias},
                ensure_ascii=False,
                indent=2,
            )
        )
    except (DatosError, ValueError, TypeError, KeyError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def _ranking_o_fuentes(grupo: str, accion: str) -> int:
    try:
        raiz = datos_dir()
        if (grupo, accion) == ("ranking", "generar"):
            resultado = ranking.generar(raiz)
        elif (grupo, accion) == ("ranking", "ultimo"):
            resultado = ranking.ultimo(raiz)
            if resultado is None:
                print("sin_ranking")
                return 0
        elif (grupo, accion) == ("fuentes", "listar"):
            resultado = fuentes.cargar(raiz)
        elif (grupo, accion) == ("fuentes", "guardar"):
            resultado = fuentes.guardar(raiz, json.loads(sys.stdin.read()))
        elif (grupo, accion) == ("fuentes", "agregar"):
            resultado = fuentes.agregar(raiz, **json.loads(sys.stdin.read()))
        else:
            print(USO, file=sys.stderr)
            return 2
        _imprimir(resultado)
    except (DatosError, ValueError, TypeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
