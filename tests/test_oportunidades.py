import json

import pytest

from agente0.datos import crear_estructura
from agente0.oportunidades import OportunidadError, cambiar_estado, cargar, evaluar, listar, registrar

URL = "https://empleos.example.com/vacante/123?utm_source=correo"
VIGENCIA = {"verificada_el": "2026-11-19", "fuente": "portal corporativo", "evidencia": "botón Solicitar visible"}
TENGO = ("ajuste_experiencia", "compatibilidad_tecnica", "factibilidad")
QUIERO = ("liderazgo_crecimiento", "remuneracion", "industria_empresa")
FILTROS_DEL_AGENTE = ("modalidad_ubicacion", "seniority", "requisitos_obligatorios", "cargo_mal_fit")


def criterios(tengo: int, quiero: int) -> dict:
    return {k: {"puntaje": tengo if k in TENGO else quiero, "evidencia": f"cita para {k}"} for k in TENGO + QUIERO}


def filtros(**excluyen: str) -> dict:
    return {f: {"excluye": f in excluyen, "motivo": excluyen.get(f, "")} for f in FILTROS_DEL_AGENTE}


def _evaluar(raiz, id_, publicacion="Texto de la vacante.", tengo=80, quiero=60, **kwargs):
    return evaluar(
        raiz,
        id_,
        publicacion,
        criterios(tengo, quiero),
        filtros(),
        "Falta experiencia en el sector.",
        **kwargs,
    )


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    return tmp_path


def _eventos(raiz, id_):
    lineas = (raiz / "oportunidades" / id_ / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(linea)["tipo"] for linea in lineas]


def test_registrar_deja_la_vacante_potencial_con_su_primer_evento(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA, fuentes=[{"nombre": "Portal Acme", "url": URL}])

    assert o.estado == "POTENCIAL"
    assert cargar(raiz, o.id) == o
    assert _eventos(raiz, o.id) == ["REGISTRADA"]


def test_registrar_dos_veces_es_idempotente_y_suma_fuentes_nuevas(raiz):
    primera = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)
    igual = registrar(raiz, "Acme", "Jefe de Datos", "https://empleos.example.com/vacante/123/", VIGENCIA)
    con_fuente = registrar(
        raiz,
        "Acme",
        "Jefe de Datos",
        URL,
        VIGENCIA,
        fuentes=[{"nombre": "Agregador", "url": "https://agregador.example.com/x"}],
    )

    assert igual == primera
    assert [f.nombre for f in con_fuente.fuentes] == ["Agregador"]
    assert _eventos(raiz, primera.id) == ["REGISTRADA", "FUENTE_AGREGADA"]
    assert len(listar(raiz)) == 1


def test_reverificar_actualiza_la_vigencia_y_deja_evento(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)

    nueva = registrar(raiz, "Acme", "Jefe de Datos", URL, {**VIGENCIA, "verificada_el": "2026-11-20"})

    assert str(nueva.vigencia.verificada_el) == "2026-11-20"
    assert _eventos(raiz, o.id) == ["REGISTRADA", "VIGENCIA_VERIFICADA"]


@pytest.mark.parametrize("estado", ["CERRADO", "DESCARTADO"])
def test_registrar_no_resucita_una_vacante_cerrada_o_descartada(raiz, estado):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)
    cambiar_estado(raiz, o.id, estado, "motivo")

    assert registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA).estado == estado


def test_registrar_sin_vigencia_verificada_se_rechaza(raiz):
    with pytest.raises(ValueError):
        registrar(raiz, "Acme", "Jefe de Datos", URL, {"verificada_el": "2026-11-19"})


def test_evaluar_guarda_puntajes_con_su_evidencia_y_la_publicacion_literal(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)

    evaluada = _evaluar(raiz, o.id, publicacion="Buscamos a alguien que lidere datos.")

    assert evaluada.evaluacion.criterios["remuneracion"].puntaje == 60
    assert evaluada.evaluacion.criterios["remuneracion"].evidencia == "cita para remuneracion"
    assert (raiz / "oportunidades" / o.id / "publicacion.txt").read_text() == "Buscamos a alguien que lidere datos."
    assert cargar(raiz, o.id) == evaluada


def test_evaluar_la_misma_publicacion_no_cambia_el_puntaje(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)
    primera = _evaluar(raiz, o.id, publicacion="Texto  de la\nvacante.", tengo=80)

    de_nuevo = _evaluar(raiz, o.id, publicacion="Texto de la vacante.", tengo=40)

    assert de_nuevo == primera
    assert _eventos(raiz, o.id) == ["REGISTRADA", "EVALUADA"]


def test_evaluar_con_publicacion_distinta_o_forzada_si_cambia_el_puntaje(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)
    _evaluar(raiz, o.id, tengo=80)

    con_evidencia_nueva = _evaluar(raiz, o.id, publicacion="Ahora piden liderar 20 personas.", tengo=50)
    forzada = _evaluar(raiz, o.id, publicacion="Ahora piden liderar 20 personas.", tengo=30, forzar=True)

    assert con_evidencia_nueva.evaluacion.criterios["ajuste_experiencia"].puntaje == 50
    assert forzada.evaluacion.criterios["ajuste_experiencia"].puntaje == 30


def test_evaluar_exige_los_criterios_de_la_configuracion(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)
    incompletos = {k: v for k, v in criterios(80, 60).items() if k != "factibilidad"}

    with pytest.raises(OportunidadError, match="factibilidad"):
        evaluar(raiz, o.id, "Texto.", incompletos, filtros(), "brecha")


@pytest.mark.parametrize(
    "filtros_agente, dicho",
    [
        ({k: v for k, v in filtros().items() if k != "seniority"}, "seniority"),
        ({**filtros(), "renta": {"excluye": False}}, "renta"),
    ],
)
def test_evaluar_exige_exactamente_los_filtros_que_califica_el_agente(raiz, filtros_agente, dicho):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)

    with pytest.raises(OportunidadError, match=dicho):
        evaluar(raiz, o.id, "Texto.", criterios(80, 60), filtros_agente, "brecha")


def test_un_filtro_que_excluye_exige_motivo(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)

    with pytest.raises(ValueError, match="motivo"):
        evaluar(raiz, o.id, "Texto.", criterios(80, 60), {**filtros(), "seniority": {"excluye": True}}, "brecha")


def test_evaluar_solo_vale_para_vacantes_potenciales(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)
    cambiar_estado(raiz, o.id, "CERRADO", "ya no recibe postulaciones")

    with pytest.raises(OportunidadError, match="CERRADO"):
        _evaluar(raiz, o.id)


def test_cerrar_y_descartar_exigen_motivo(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)

    with pytest.raises(ValueError, match="motivo"):
        cambiar_estado(raiz, o.id, "DESCARTADO")


def test_cerrado_es_terminal_y_descartado_solo_vuelve_por_rescate(raiz):
    cerrada = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)
    cambiar_estado(raiz, cerrada.id, "CERRADO", "cerrada en la fuente oficial")
    with pytest.raises(OportunidadError, match="no pasa"):
        cambiar_estado(raiz, cerrada.id, "POTENCIAL")

    descartada = registrar(raiz, "Beta", "Gerente", "https://empleos.example.com/vacante/9", VIGENCIA)
    cambiar_estado(raiz, descartada.id, "DESCARTADO", "decisión del usuario")
    rescatada = cambiar_estado(raiz, descartada.id, "POTENCIAL")

    assert rescatada.estado == "POTENCIAL"
    assert rescatada.rescatada is True
    assert rescatada.motivo is None


def test_saltar_una_vacante_en_postulacion_la_devuelve_a_potencial(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)
    cambiar_estado(raiz, o.id, "EN_POSTULACION")

    assert cambiar_estado(raiz, o.id, "POTENCIAL").rescatada is False
