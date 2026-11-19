import json
import os
import subprocess
import sys

import pytest

from agente0.datos import ENV_VAR, REPO
from agente0.postulaciones import (
    Envio,
    Evidencia,
    PostulacionError,
    RespuestaEnviada,
    cargar,
    confirmar_envio,
    crear,
    envio_fallido,
    finalizar,
    intentar_envio,
    recompensar,
    registrar_evento,
)

URL = "https://portal.example.com/empleo/123?utm_source=correo"


def _cli(raiz, *args: str, entrada: str = "") -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}
    return subprocess.run(
        [sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, input=entrada, capture_output=True, text=True
    )


def _envio(tmp_path, autonomia: int = 0) -> Envio:
    cv = tmp_path / "cv_adaptado.pdf"
    cv.write_bytes(b"%PDF-1.4 contenido")
    return Envio(
        autonomia=autonomia,
        aprobacion="usuario, paso a paso",
        cv=cv,
        respuestas=[
            RespuestaEnviada(pregunta="Pretensión de renta", texto="Texto literal", respuesta_id="H3", version="v002")
        ],
    )


def _eventos(raiz, id_):
    lineas = (raiz / "postulaciones" / id_ / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(linea) for linea in lineas]


def _postulada(raiz, tmp_path):
    id_ = crear(raiz, "Acme", "Jefe de Datos", URL).id
    intentar_envio(raiz, id_, _envio(tmp_path))
    confirmar_envio(raiz, id_, Evidencia(tipo="confirmacion_visible", detalle="Postulación enviada, folio 987"))
    return id_


def test_crear_deja_la_postulacion_preparada_con_su_primer_evento(tmp_path):
    postulacion = crear(tmp_path, "Acme", "Jefe de Datos", URL)

    assert postulacion.estado == "PREPARADA"
    assert cargar(tmp_path, postulacion.id) == postulacion
    assert [e["tipo"] for e in _eventos(tmp_path, postulacion.id)] == ["CAMBIO_ESTADO"]


def test_la_misma_vacante_no_se_crea_dos_veces(tmp_path):
    crear(tmp_path, "Acme", "Jefe de Datos", URL)

    with pytest.raises(PostulacionError, match="ya existe"):
        crear(tmp_path, "Acme", "Jefe de Datos", "https://portal.example.com/empleo/123/")


def test_flujo_completo_hasta_finalizar_con_historial_de_transiciones(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)
    assert cargar(tmp_path, id_).fecha_postulacion is not None

    registrar_evento(tmp_path, id_, "PRIMER_CONTACTO_ENTREVISTA", "Correo de la reclutadora")
    assert cargar(tmp_path, id_).etapa == "primera entrevista"
    registrar_evento(tmp_path, id_, "ENTREVISTA_REALIZADA")
    registrar_evento(tmp_path, id_, "NUEVA_ETAPA", etapa="entrevista técnica")
    registrar_evento(tmp_path, id_, "OFERTA_RECIBIDA")
    final = finalizar(tmp_path, id_, "oferta_rechazada_por_usuario", "Renta bajo el mínimo")

    assert (final.estado, final.etapa, final.resultado) == (
        "FINALIZADA",
        "entrevista técnica",
        "oferta_rechazada_por_usuario",
    )
    assert [e["estado"] for e in _eventos(tmp_path, id_)] == [
        "PREPARADA",
        "ENVIO_INTENTADO",
        "POSTULADO",
        "EN_PROCESO",
        "EN_PROCESO",
        "EN_PROCESO",
        "EN_PROCESO",
        "EN_PROCESO",
        "FINALIZADA",
    ]


def test_la_instantanea_guarda_lo_enviado_y_queda_de_solo_lectura(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)
    intento = tmp_path / "postulaciones" / id_ / "instantanea" / "001"

    envio = json.loads((intento / "envio.json").read_text(encoding="utf-8"))
    assert envio["autonomia"] == 0
    assert envio["aprobacion"] == "usuario, paso a paso"
    assert envio["cv"] == "cv.pdf"
    assert envio["respuestas"][0] == {
        "pregunta": "Pretensión de renta",
        "texto": "Texto literal",
        "respuesta_id": "H3",
        "version": "v002",
    }
    assert (intento / "cv.pdf").read_bytes() == b"%PDF-1.4 contenido"
    assert json.loads((intento / "evidencia.json").read_text(encoding="utf-8"))["detalle"].endswith("folio 987")
    with pytest.raises(PermissionError):
        (intento / "envio.json").write_text("{}", encoding="utf-8")


def test_la_captura_de_evidencia_se_copia_a_la_instantanea(tmp_path):
    id_ = crear(tmp_path, "Acme", "Jefe de Datos", URL).id
    intentar_envio(tmp_path, id_, _envio(tmp_path))
    captura = tmp_path / "pantalla.png"
    captura.write_bytes(b"png")

    confirmar_envio(tmp_path, id_, Evidencia(tipo="correo", detalle="Correo de acuse", captura=captura))

    intento = tmp_path / "postulaciones" / id_ / "instantanea" / "001"
    assert (intento / "captura.png").read_bytes() == b"png"
    assert json.loads((intento / "evidencia.json").read_text(encoding="utf-8"))["captura"] == "captura.png"


def test_envio_fallido_vuelve_a_preparada_y_el_reintento_conserva_el_primer_intento(tmp_path):
    id_ = crear(tmp_path, "Acme", "Jefe de Datos", URL).id
    intentar_envio(tmp_path, id_, _envio(tmp_path))
    envio_fallido(tmp_path, id_, "El portal pidió CAPTCHA antes de enviar")
    assert cargar(tmp_path, id_).estado == "PREPARADA"

    intentar_envio(tmp_path, id_, _envio(tmp_path, autonomia=25))

    base = tmp_path / "postulaciones" / id_ / "instantanea"
    assert sorted(p.name for p in base.iterdir()) == ["001", "002"]
    assert json.loads((base / "001" / "envio.json").read_text(encoding="utf-8"))["autonomia"] == 0
    assert json.loads((base / "002" / "envio.json").read_text(encoding="utf-8"))["autonomia"] == 25


def test_una_postulacion_ya_postulada_no_se_reenvia(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)

    with pytest.raises(PostulacionError, match="POSTULADO"):
        intentar_envio(tmp_path, id_, _envio(tmp_path))


def test_no_hay_postulado_sin_envio_intentado_ni_evidencia(tmp_path):
    id_ = crear(tmp_path, "Acme", "Jefe de Datos", URL).id

    with pytest.raises(PostulacionError):
        confirmar_envio(tmp_path, id_, Evidencia(tipo="correo", detalle="x"))
    with pytest.raises(ValueError):
        Evidencia(tipo="correo", detalle="")
    assert cargar(tmp_path, id_).estado == "PREPARADA"


def test_el_primer_contacto_no_se_registra_dos_veces(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)
    registrar_evento(tmp_path, id_, "PRIMER_CONTACTO_ENTREVISTA")

    with pytest.raises(PostulacionError):
        registrar_evento(tmp_path, id_, "PRIMER_CONTACTO_ENTREVISTA")
    assert len(_eventos(tmp_path, id_)) == 5


def _premios(raiz, id_):
    return [e for e in _eventos(raiz, id_) if e["tipo"] == "RECOMPENSA"]


def test_el_primer_contacto_crea_un_solo_premio_ligado_a_lo_enviado(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)

    registrar_evento(tmp_path, id_, "PRIMER_CONTACTO_ENTREVISTA", "Correo de la reclutadora")

    assert cargar(tmp_path, id_).estado == "EN_PROCESO"
    assert [e["tipo"] for e in _eventos(tmp_path, id_)][-2:] == ["PRIMER_CONTACTO_ENTREVISTA", "RECOMPENSA"]
    (premio,) = _premios(tmp_path, id_)
    assert premio["recompensa"] == {
        "hito": "PRIMER_CONTACTO_ENTREVISTA",
        "valor": 1.0,
        "intento": 1,
        "respuestas": [{"respuesta_id": "H3", "version": "v002"}],
    }


def test_repetir_el_aviso_o_reprocesar_el_hito_no_duplica_el_premio(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)
    registrar_evento(tmp_path, id_, "PRIMER_CONTACTO_ENTREVISTA")

    with pytest.raises(PostulacionError):
        registrar_evento(tmp_path, id_, "PRIMER_CONTACTO_ENTREVISTA")
    premio = recompensar(tmp_path, id_)

    assert premio.tipo == "RECOMPENSA"
    assert len(_premios(tmp_path, id_)) == 1
    assert len(_eventos(tmp_path, id_)) == 5


def test_un_premio_que_quedo_sin_escribir_se_recupera_una_sola_vez(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)
    registrar_evento(tmp_path, id_, "PRIMER_CONTACTO_ENTREVISTA")
    archivo = tmp_path / "postulaciones" / id_ / "eventos.jsonl"
    sin_premio = archivo.read_text(encoding="utf-8").splitlines()[:-1]
    archivo.write_text("\n".join(sin_premio) + "\n", encoding="utf-8")
    assert _premios(tmp_path, id_) == []

    recompensar(tmp_path, id_)
    recompensar(tmp_path, id_)

    assert len(_premios(tmp_path, id_)) == 1


def test_sin_primer_contacto_no_hay_premio(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)

    with pytest.raises(PostulacionError, match="nada que premiar"):
        recompensar(tmp_path, id_)
    assert _premios(tmp_path, id_) == []


def test_rechazo_y_silencio_no_generan_premio(tmp_path):
    rechazada = _postulada(tmp_path, tmp_path)
    registrar_evento(tmp_path, rechazada, "RECHAZO")
    callada = crear(tmp_path, "Beta", "Analista", "https://portal.example.com/empleo/456").id
    intentar_envio(tmp_path, callada, _envio(tmp_path))
    confirmar_envio(tmp_path, callada, Evidencia(tipo="correo", detalle="Correo de confirmación"))
    registrar_evento(tmp_path, callada, "CIERRE_POR_SILENCIO")

    assert _premios(tmp_path, rechazada) == []
    assert _premios(tmp_path, callada) == []


def test_el_premio_liga_las_respuestas_del_intento_confirmado_y_no_las_de_otros(tmp_path):
    id_ = crear(tmp_path, "Acme", "Jefe de Datos", URL).id
    intentar_envio(tmp_path, id_, _envio(tmp_path))
    envio_fallido(tmp_path, id_, "El portal no respondió")
    segundo = _envio(tmp_path).model_copy(
        update={
            "respuestas": [
                RespuestaEnviada(pregunta="Pretensión de renta", texto="Texto nuevo", respuesta_id="H3", version="v003"),
                RespuestaEnviada(pregunta="Por qué te interesa", texto="Texto libre sin ID"),
            ]
        }
    )
    intentar_envio(tmp_path, id_, segundo)
    confirmar_envio(tmp_path, id_, Evidencia(tipo="confirmacion_visible", detalle="folio 2"))

    registrar_evento(tmp_path, id_, "PRIMER_CONTACTO_ENTREVISTA")

    (premio,) = _premios(tmp_path, id_)
    assert premio["recompensa"]["intento"] == 2
    assert premio["recompensa"]["respuestas"] == [{"respuesta_id": "H3", "version": "v003"}]


def test_eventos_que_no_corresponden_al_estado_se_rechazan(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)

    with pytest.raises(PostulacionError):
        registrar_evento(tmp_path, id_, "ENTREVISTA_REALIZADA")
    with pytest.raises(PostulacionError, match="etapa"):
        registrar_evento(tmp_path, id_, "NUEVA_ETAPA")
    with pytest.raises(PostulacionError, match="no válido"):
        registrar_evento(tmp_path, id_, "CAMBIO_ESTADO")


def test_rechazo_finaliza_y_una_finalizada_no_se_mueve(tmp_path):
    id_ = _postulada(tmp_path, tmp_path)

    final = registrar_evento(tmp_path, id_, "RECHAZO", "Correo de la empresa")

    assert (final.estado, final.resultado) == ("FINALIZADA", "rechazada_por_empresa")
    with pytest.raises(PostulacionError):
        registrar_evento(tmp_path, id_, "RETIRO")


def test_la_autonomia_registrada_debe_ser_un_nivel_fijo(tmp_path):
    with pytest.raises(ValueError):
        _envio(tmp_path, autonomia=30)


def test_cv_inexistente_no_deja_instantanea_a_medias(tmp_path):
    id_ = crear(tmp_path, "Acme", "Jefe de Datos", URL).id

    with pytest.raises(PostulacionError, match="no existe"):
        intentar_envio(tmp_path, id_, Envio(autonomia=0, aprobacion="usuario", cv=tmp_path / "falta.pdf"))

    assert not (tmp_path / "postulaciones" / id_ / "instantanea").exists()
    assert cargar(tmp_path, id_).estado == "PREPARADA"


@pytest.mark.parametrize("id_", ["../afuera", "A/b", "", "acme..x"])
def test_id_con_ruta_se_rechaza(tmp_path, id_):
    with pytest.raises(PostulacionError, match="inválido"):
        cargar(tmp_path, id_)


def test_cli_recorre_el_flujo_y_rechaza_el_reenvio(tmp_path):
    raiz = tmp_path / "datos"
    raiz.mkdir()
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"pdf")
    creada = _cli(raiz, "postulacion", "crear", entrada=json.dumps({"empresa": "Acme", "cargo": "Jefe", "url": URL}))
    assert creada.returncode == 0, creada.stderr
    id_ = json.loads(creada.stdout)["id"]

    intento = _cli(
        raiz,
        "postulacion",
        "intentar",
        id_,
        entrada=json.dumps({"autonomia": 0, "aprobacion": "usuario", "cv": str(cv)}),
    )
    confirmacion = _cli(
        raiz,
        "postulacion",
        "confirmar",
        id_,
        entrada=json.dumps({"tipo": "confirmacion_visible", "detalle": "folio 1"}),
    )
    ver = _cli(raiz, "postulacion", "ver", id_)
    reenvio = _cli(
        raiz,
        "postulacion",
        "intentar",
        id_,
        entrada=json.dumps({"autonomia": 0, "aprobacion": "usuario", "cv": str(cv)}),
    )

    assert intento.returncode == 0, intento.stderr
    assert confirmacion.returncode == 0, confirmacion.stderr
    assert json.loads(ver.stdout)["estado"] == "POSTULADO"
    assert reenvio.returncode == 1
    assert "POSTULADO" in reenvio.stderr


def test_cli_premia_una_vez_con_el_valor_de_la_configuracion(tmp_path):
    raiz = tmp_path / "datos"
    raiz.mkdir()
    assert _cli(raiz, "init").returncode == 0
    configuracion = raiz / "configuracion" / "configuracion.json"
    datos_config = json.loads(configuracion.read_text(encoding="utf-8"))
    configuracion.write_text(json.dumps(datos_config | {"recompensa_primer_contacto": 2.5}), encoding="utf-8")
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"pdf")
    id_ = json.loads(
        _cli(raiz, "postulacion", "crear", entrada=json.dumps({"empresa": "Acme", "cargo": "Jefe", "url": URL})).stdout
    )["id"]
    envio = {
        "autonomia": 0,
        "aprobacion": "usuario",
        "cv": str(cv),
        "respuestas": [{"pregunta": "Renta", "texto": "x", "respuesta_id": "H3", "version": "v001"}],
    }
    _cli(raiz, "postulacion", "intentar", id_, entrada=json.dumps(envio))
    _cli(raiz, "postulacion", "confirmar", id_, entrada=json.dumps({"tipo": "correo", "detalle": "folio 1"}))

    primero = _cli(raiz, "postulacion", "evento", id_, entrada='{"tipo": "PRIMER_CONTACTO_ENTREVISTA"}')
    repetido = _cli(raiz, "postulacion", "evento", id_, entrada='{"tipo": "PRIMER_CONTACTO_ENTREVISTA"}')
    reproceso = _cli(raiz, "postulacion", "recompensar", id_)

    assert primero.returncode == 0, primero.stderr
    assert repetido.returncode == 1
    assert reproceso.returncode == 0, reproceso.stderr
    (premio,) = _premios(raiz, id_)
    assert premio["recompensa"]["valor"] == 2.5
    assert json.loads(reproceso.stdout)["recompensa"]["valor"] == 2.5


def test_cli_con_json_invalido_falla_y_no_escribe(tmp_path):
    raiz = tmp_path / "datos"
    raiz.mkdir()
    creada = _cli(raiz, "postulacion", "crear", entrada=json.dumps({"empresa": "Acme", "cargo": "Jefe", "url": URL}))
    id_ = json.loads(creada.stdout)["id"]

    resultado = _cli(raiz, "postulacion", "evento", id_, entrada='{"tipo": "INVENTADO"}')

    assert resultado.returncode == 1
    assert len((raiz / "postulaciones" / id_ / "eventos.jsonl").read_text(encoding="utf-8").splitlines()) == 1
