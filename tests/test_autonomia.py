import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from agente0 import fuentes
from agente0.autonomia import AutonomiaError, Juicios, SolicitudEnvio, evaluar, preparar_envio
from agente0.datos import ARCHIVO_CONFIGURACION, ENV_VAR, REPO, crear_estructura
from agente0.esquemas import Configuracion
from agente0.oportunidades import evaluar as evaluar_vacante
from agente0.oportunidades import observar_renta, registrar
from agente0.postulaciones import Envio, cargar, crear, intentar_envio
from tests.test_oportunidades import criterios, filtros

PORTAL_BAJO, PORTAL_ALTO = "Portal Bajo", "Portal Alto"
COMPUERTA = {"seniority_permitido": ["Lead", "Gerente"], "ubicaciones_permitidas": ["santiago", "remoto_chile"]}
JUICIOS = Juicios.model_validate(
    {
        "seniority": {"valor": "lead", "evidencia": "El cargo dice Lead de Datos."},
        "ubicacion": {"valor": "Remoto_Chile", "evidencia": "Remoto desde Chile."},
        "respuestas_documentadas": {"cumple": True, "evidencia": "Todas salen de la biblioteca."},
        "cv_auditado": {"cumple": True, "evidencia": "Auditoría de veracidad aprobada."},
    }
)


def _ahora() -> datetime:
    return datetime.now().astimezone()


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    fuentes.guardar(
        tmp_path,
        [
            {"nombre": PORTAL_BAJO, "tipo": "generalista", "pais": "Chile", "metodo": "web", "riesgo": "bajo"},
            {"nombre": PORTAL_ALTO, "tipo": "generalista", "pais": "Chile", "metodo": "navegador", "riesgo": "alto"},
        ],
    )
    return tmp_path


def configurar(raiz, autonomia: int, compuerta: dict | None = None, **priorizacion):
    configuracion = Configuracion.model_validate(
        {"autonomia": autonomia, "compuerta": {**COMPUERTA, **(compuerta or {})}, "priorizacion": priorizacion}
    )
    (raiz / ARCHIVO_CONFIGURACION).write_text(configuracion.model_dump_json(indent=2), encoding="utf-8")


def vacante(
    raiz, n: int = 1, empresa: str = "Acme", tengo: int = 80, quiero: int = 70, verificada: date | None = None, **datos
):
    vigencia = {
        "verificada_el": (verificada or date.today()).isoformat(),
        "fuente": "portal",
        "evidencia": "botón visible",
    }
    o = registrar(raiz, empresa, f"Cargo {n}", f"https://empleos.example.com/vacante/{n}", vigencia, **datos)
    evaluar_vacante(raiz, o.id, f"Publicación {n}", criterios(tengo, quiero), filtros(), "Brecha.")
    return o.id


def estado(decision, nombre: str) -> str:
    return next(c.resultado for c in decision.condiciones if c.nombre == nombre)


def enviar(raiz, tmp_path, id_: str, portal: str) -> None:
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"%PDF-1.4")
    intentar_envio(raiz, id_, Envio(autonomia=0, aprobacion="usuario", cv=cv, portal=portal))


@pytest.mark.parametrize(
    "nivel, esperado",
    [
        (0, ("aprobar", "aprobar", "aprobar", "aprobar")),
        (25, ("aprobar", "aprobar", "automatico", "aprobar")),
        (50, ("automatico", "aprobar_nuevas", "automatico", "aprobar")),
        (75, ("automatico", "automatico", "automatico", "automatico")),
        (100, ("automatico", "automatico", "automatico", "automatico")),
    ],
)
def test_la_matriz_por_nivel_sigue_a_d12(raiz, nivel, esperado):
    configurar(raiz, nivel)
    decision = evaluar(raiz, vacante(raiz), PORTAL_BAJO, JUICIOS)

    assert decision.bloqueos == []
    assert tuple(decision.acciones[a] for a in ("cv", "respuestas", "formulario", "envio")) == esperado
    assert decision.nivel_configurado == decision.nivel_efectivo == nivel


def test_al_75_una_condicion_de_preferencia_incumplida_manda_el_envio_a_la_cola(raiz):
    configurar(raiz, 75)
    juicios = Juicios.model_validate({**JUICIOS.model_dump(), "seniority": {"valor": "Senior IC", "evidencia": "IC."}})

    decision = evaluar(raiz, vacante(raiz), PORTAL_BAJO, juicios)

    assert estado(decision, "seniority") == "no_cumple"
    assert decision.acciones["envio"] == "aprobar"
    assert decision.acciones["formulario"] == "automatico"
    assert any(m.startswith("seniority") for m in decision.motivos)
    assert decision.bloqueos == []


def test_al_75_un_juicio_que_falta_cuenta_como_no_cumplido(raiz):
    configurar(raiz, 75)
    juicios = Juicios.model_validate({**JUICIOS.model_dump(), "ubicacion": None})

    decision = evaluar(raiz, vacante(raiz), PORTAL_BAJO, juicios)

    assert estado(decision, "ubicacion") == "no_evaluada"
    assert decision.acciones["envio"] == "aprobar"


def test_sin_listas_configuradas_nada_se_envia_solo_al_75(raiz):
    configurar(raiz, 75, {"seniority_permitido": [], "ubicaciones_permitidas": []})

    decision = evaluar(raiz, vacante(raiz), PORTAL_BAJO, JUICIOS)

    assert (estado(decision, "seniority"), estado(decision, "ubicacion")) == ("no_cumple", "no_cumple")
    assert decision.acciones["envio"] == "aprobar"


def test_al_100_las_condiciones_de_preferencia_no_rigen_pero_las_vigentes_si(raiz):
    configurar(raiz, 100)
    juicios = Juicios.model_validate({**JUICIOS.model_dump(), "seniority": {"valor": "Senior IC", "evidencia": "IC."}})

    decision = evaluar(raiz, vacante(raiz, tengo=10), PORTAL_BAJO, juicios)

    assert decision.acciones["envio"] == "automatico"
    assert {c.resultado for c in decision.condiciones if c.tipo == "preferencia"} == {"no_aplica"}
    assert len([c for c in decision.condiciones if c.tipo == "vigente"]) == 5


def test_una_condicion_desactivada_no_bloquea_el_auto_envio(raiz):
    configurar(raiz, 75, {"condiciones_preferencia": ["seniority", "ubicacion", "sin_proceso_activo", "renta_minima"]})

    decision = evaluar(raiz, vacante(raiz, tengo=10), PORTAL_BAJO, JUICIOS)

    assert estado(decision, "umbral_match") == "no_aplica"
    assert decision.acciones["envio"] == "automatico"


@pytest.mark.parametrize("tengo, quiero, esperado", [(70, 60, "cumple"), (69, 60, "no_cumple"), (70, 59, "no_cumple")])
def test_el_umbral_de_match_se_mide_por_eje(raiz, tengo, quiero, esperado):
    configurar(raiz, 75)

    decision = evaluar(raiz, vacante(raiz, tengo=tengo, quiero=quiero), PORTAL_BAJO, JUICIOS)

    assert estado(decision, "umbral_match") == esperado
    assert (decision.acciones["envio"] == "automatico") == (esperado == "cumple")


def test_la_renta_publicada_bajo_el_minimo_manda_el_envio_a_la_cola(raiz):
    configurar(raiz, 75, renta_minima=3_800_000)

    bajo = evaluar(raiz, vacante(raiz, 1, renta_publicada=3_000_000), PORTAL_BAJO, JUICIOS)
    sin_dato = evaluar(raiz, vacante(raiz, 2), PORTAL_BAJO, JUICIOS)

    assert (estado(bajo, "renta_minima"), bajo.acciones["envio"]) == ("no_cumple", "aprobar")
    assert (estado(sin_dato, "renta_minima"), sin_dato.acciones["envio"]) == ("cumple", "automatico")


@pytest.mark.parametrize(
    "acepta, avisa, esperado",
    [
        (3_200, 3_400, "cumple"),
        (3_000, 3_100, "cumple"),
        (2_800, 2_900, "no_cumple"),
        (None, 2_900, "no_cumple"),
        (None, 3_400, "no_cumple"),
    ],
)
def test_el_tope_observado_en_el_formulario_decide_la_condicion_de_renta(raiz, acepta, avisa, esperado):
    configurar(raiz, 75, renta_minima=3_000_000)
    id_ = vacante(raiz)
    observar_renta(
        raiz,
        id_,
        unidad="USD bruto mensual",
        minima_equivalente=3_000,
        acepta_hasta=acepta,
        avisa_desde=avisa,
        evidencia="El portal avisó al declarar un monto mayor.",
    )

    decision = evaluar(raiz, id_, PORTAL_BAJO, JUICIOS)

    assert (estado(decision, "renta_minima"), decision.acciones["envio"]) == (
        esperado,
        "automatico" if esperado == "cumple" else "aprobar",
    )


def test_el_tope_observado_prevalece_sobre_la_renta_publicada_y_usa_la_minima_configurada_sin_equivalente(raiz):
    configurar(raiz, 75, renta_minima=3_000_000)
    id_ = vacante(raiz, renta_publicada=5_000_000)
    observar_renta(
        raiz, id_, unidad="CLP líquido mensual", acepta_hasta=2_500_000, avisa_desde=2_700_000, evidencia="Aviso."
    )

    decision = evaluar(raiz, id_, PORTAL_BAJO, JUICIOS)

    assert (estado(decision, "renta_minima"), decision.acciones["envio"]) == ("no_cumple", "aprobar")


def test_una_observacion_nueva_reemplaza_a_la_anterior_y_deja_el_evento(raiz):
    id_ = vacante(raiz)
    observar_renta(raiz, id_, unidad="USD bruto mensual", avisa_desde=3_400, evidencia="Primer aviso.")
    o = observar_renta(
        raiz, id_, unidad="USD bruto mensual", acepta_hasta=3_200, avisa_desde=3_400, evidencia="Acotado."
    )

    eventos = (raiz / "oportunidades" / id_ / "eventos.jsonl").read_text(encoding="utf-8").splitlines()

    assert o.renta_observada.acepta_hasta == 3_200
    assert [json.loads(e)["tipo"] for e in eventos].count("RENTA_OBSERVADA") == 2


@pytest.mark.parametrize("datos", [{}, {"acepta_hasta": 3_500, "avisa_desde": 3_400}])
def test_la_renta_observada_exige_un_tope_coherente(raiz, datos):
    id_ = vacante(raiz)

    with pytest.raises(ValidationError):
        observar_renta(raiz, id_, unidad="USD bruto mensual", evidencia="Aviso.", **datos)


def test_un_proceso_activo_en_la_misma_empresa_manda_el_envio_a_la_cola(raiz, tmp_path):
    configurar(raiz, 75)
    otra = vacante(raiz, 1, empresa="Acme")
    crear(raiz, "Acme", "Cargo 1", "https://empleos.example.com/vacante/1")

    decision = evaluar(raiz, vacante(raiz, 2, empresa="Acme"), PORTAL_BAJO, JUICIOS)

    assert estado(decision, "sin_proceso_activo") == "no_cumple"
    assert otra in next(c.detalle for c in decision.condiciones if c.nombre == "sin_proceso_activo")
    assert decision.acciones["envio"] == "aprobar"


@pytest.mark.parametrize("nivel", [0, 50, 100])
def test_una_regla_siempre_vigente_incumplida_bloquea_en_todo_nivel(raiz, nivel):
    configurar(raiz, nivel, empresas_excluidas=["Acme"])

    decision = evaluar(raiz, vacante(raiz, empresa="Acme"), PORTAL_BAJO, JUICIOS)

    assert estado(decision, "empresa_no_excluida") == "no_cumple"
    assert len(decision.bloqueos) == 1 and decision.bloqueos[0].startswith("empresa_no_excluida")


def test_la_vigencia_debe_estar_verificada_hoy(raiz):
    configurar(raiz, 100)
    ayer = vacante(raiz, verificada=date.today() - timedelta(days=1))

    decision = evaluar(raiz, ayer, PORTAL_BAJO, JUICIOS)

    assert estado(decision, "vigencia_hoy") == "no_cumple"
    assert decision.bloqueos and decision.bloqueos[0].startswith("vigencia_hoy")


@pytest.mark.parametrize("juicio", ["cv_auditado", "respuestas_documentadas"])
def test_sin_el_juicio_del_agente_o_con_un_no_se_bloquea(raiz, juicio):
    configurar(raiz, 100)
    id_ = vacante(raiz)

    falta = evaluar(raiz, id_, PORTAL_BAJO, Juicios.model_validate({**JUICIOS.model_dump(), juicio: None}))
    niega = evaluar(
        raiz,
        id_,
        PORTAL_BAJO,
        Juicios.model_validate(
            {**JUICIOS.model_dump(), juicio: {"cumple": False, "evidencia": "Hay una pregunta nueva."}}
        ),
    )

    assert (estado(falta, juicio), estado(niega, juicio)) == ("no_evaluada", "no_cumple")
    assert falta.bloqueos and niega.bloqueos


def test_una_vacante_ya_postulada_se_bloquea_y_una_preparada_no(raiz, tmp_path):
    configurar(raiz, 100)
    id_ = vacante(raiz)
    crear(raiz, "Acme", "Cargo 1", "https://empleos.example.com/vacante/1")
    preparada = evaluar(raiz, id_, PORTAL_BAJO, JUICIOS)
    enviar(raiz, tmp_path, id_, PORTAL_BAJO)

    intentada = evaluar(raiz, id_, PORTAL_BAJO, JUICIOS)

    assert estado(preparada, "no_postulada_antes") == "cumple"
    assert estado(intentada, "no_postulada_antes") == "no_cumple"
    assert intentada.bloqueos[0].startswith("no_postulada_antes")


def test_el_tope_por_riesgo_limita_el_nivel_en_portales_de_riesgo_alto(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz)

    alto = evaluar(raiz, id_, PORTAL_ALTO, JUICIOS)
    bajo = evaluar(raiz, id_, PORTAL_BAJO, JUICIOS)

    assert (alto.nivel_configurado, alto.nivel_efectivo) == (75, 50)
    assert alto.acciones["envio"] == "aprobar" and alto.acciones["respuestas"] == "aprobar_nuevas"
    assert any("limitado a 50" in m for m in alto.motivos)
    assert bajo.nivel_efectivo == 75 and bajo.acciones["envio"] == "automatico"


def test_el_tope_por_portal_manda_sobre_el_de_riesgo(raiz):
    configurar(raiz, 75, {"topes_por_portal": {"portal alto": 100, "Portal Bajo": 25}})
    id_ = vacante(raiz)

    assert evaluar(raiz, id_, PORTAL_ALTO, JUICIOS).nivel_efectivo == 75
    assert evaluar(raiz, id_, PORTAL_BAJO, JUICIOS).nivel_efectivo == 25


@pytest.mark.parametrize(
    "compuerta", [{"siempre_aprobar_portales": ["portal bajo"]}, {"siempre_aprobar_empresas": ["ACME"]}]
)
def test_las_excepciones_exigen_aprobar_el_envio_aunque_el_nivel_sea_100(raiz, compuerta):
    configurar(raiz, 100, compuerta)

    decision = evaluar(raiz, vacante(raiz), PORTAL_BAJO, JUICIOS)

    assert decision.acciones["envio"] == "aprobar"
    assert decision.acciones["formulario"] == "automatico"
    assert any("excepción" in m for m in decision.motivos)


def test_un_portal_fuera_de_las_fuentes_se_rechaza(raiz):
    configurar(raiz, 75)

    with pytest.raises(AutonomiaError, match="no está en las fuentes"):
        evaluar(raiz, vacante(raiz), "Portal Desconocido", JUICIOS)


def test_el_limite_diario_por_riesgo_bloquea_el_envio_siguiente(raiz, tmp_path):
    configurar(raiz, 0, {"pausa_minutos": 0})
    for n in range(3):
        id_ = vacante(raiz, n)
        crear(raiz, "Acme", f"Cargo {n}", f"https://empleos.example.com/vacante/{n}")
        enviar(raiz, tmp_path, id_, PORTAL_ALTO)
    nueva = vacante(raiz, 9, empresa="Otra")

    en_alto = evaluar(raiz, nueva, PORTAL_ALTO, JUICIOS)
    en_bajo = evaluar(raiz, nueva, PORTAL_BAJO, JUICIOS)
    al_dia_siguiente = evaluar(raiz, nueva, PORTAL_ALTO, JUICIOS, ahora=_ahora() + timedelta(days=1))

    assert any(b.startswith("límite diario: 3 de 3") for b in en_alto.bloqueos)
    assert en_bajo.bloqueos == []
    assert not any(b.startswith("límite diario") for b in al_dia_siguiente.bloqueos)


def test_la_pausa_entre_envios_se_mide_por_portal(raiz, tmp_path):
    configurar(raiz, 0)
    id_ = vacante(raiz, 1)
    crear(raiz, "Acme", "Cargo 1", "https://empleos.example.com/vacante/1")
    enviar(raiz, tmp_path, id_, PORTAL_ALTO)
    nueva = vacante(raiz, 2, empresa="Otra")

    mismo_portal = evaluar(raiz, nueva, PORTAL_ALTO, JUICIOS)
    otro_portal = evaluar(raiz, nueva, PORTAL_BAJO, JUICIOS)
    despues = evaluar(raiz, nueva, PORTAL_ALTO, JUICIOS, ahora=_ahora() + timedelta(minutes=3))

    assert 0 < mismo_portal.espera_segundos <= 120
    assert any(b.startswith("pausa entre envíos") for b in mismo_portal.bloqueos)
    assert otro_portal.espera_segundos == 0 and otro_portal.bloqueos == []
    assert despues.espera_segundos == 0 and despues.bloqueos == []


def solicitud(tmp_path, juicios: Juicios = JUICIOS, **extra) -> SolicitudEnvio:
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"%PDF-1.4")
    return SolicitudEnvio(portal=PORTAL_BAJO, cv=cv, juicios=juicios, **extra)


def congelado(raiz, id_: str, n: int = 1) -> dict:
    return json.loads(
        (raiz / "postulaciones" / id_ / "instantanea" / f"{n:03d}" / "envio.json").read_text(encoding="utf-8")
    )


def test_el_agente_no_puede_declarar_el_nivel_ni_las_condiciones(tmp_path):
    with pytest.raises(ValidationError):
        SolicitudEnvio.model_validate({"portal": PORTAL_BAJO, "cv": str(tmp_path / "cv.pdf"), "autonomia": 100})


def test_al_0_el_envio_sin_aprobacion_se_rechaza_y_no_deja_instantanea(raiz, tmp_path):
    configurar(raiz, 0)
    id_ = vacante(raiz)
    crear(raiz, "Acme", "Cargo 1", "https://empleos.example.com/vacante/1")

    with pytest.raises(AutonomiaError, match="requiere la aprobación"):
        preparar_envio(raiz, id_, solicitud(tmp_path))

    assert not (raiz / "postulaciones" / id_ / "instantanea").exists()


def test_al_0_con_aprobacion_el_registro_trae_nivel_acciones_y_condiciones(raiz, tmp_path):
    configurar(raiz, 0)
    id_ = vacante(raiz)
    crear(raiz, "Acme", "Cargo 1", "https://empleos.example.com/vacante/1")

    envio = preparar_envio(raiz, id_, solicitud(tmp_path, aprobacion="usuario aprobó CV y textos"))
    intentar_envio(raiz, id_, envio)

    registro = congelado(raiz, id_)
    assert (registro["autonomia"], registro["nivel_efectivo"], registro["portal"]) == (0, 0, PORTAL_BAJO)
    assert registro["aprobacion"] == "usuario aprobó CV y textos"
    assert set(registro["acciones"].values()) == {"aprobar"}
    assert len(registro["condiciones"]) == 10
    assert cargar(raiz, id_).estado == "ENVIO_INTENTADO"


def test_al_75_con_todo_cumplido_el_envio_es_automatico_y_queda_registrado_como_tal(raiz, tmp_path):
    configurar(raiz, 75)
    id_ = vacante(raiz)
    crear(raiz, "Acme", "Cargo 1", "https://empleos.example.com/vacante/1")

    intentar_envio(raiz, id_, preparar_envio(raiz, id_, solicitud(tmp_path)))

    registro = congelado(raiz, id_)
    assert registro["aprobacion"].startswith("automático: nivel 75 %")
    assert registro["acciones"]["envio"] == "automatico"
    assert {c["resultado"] for c in registro["condiciones"]} == {"cumple"}


def test_al_75_con_una_condicion_incumplida_solo_sale_con_aprobacion_del_usuario(raiz, tmp_path):
    configurar(raiz, 75)
    id_ = vacante(raiz, tengo=10)
    crear(raiz, "Acme", "Cargo 1", "https://empleos.example.com/vacante/1")

    with pytest.raises(AutonomiaError, match="umbral_match"):
        preparar_envio(raiz, id_, solicitud(tmp_path))
    envio = preparar_envio(raiz, id_, solicitud(tmp_path, aprobacion="usuario aprobó desde la cola"))

    assert envio.aprobacion == "usuario aprobó desde la cola"
    assert envio.acciones["envio"] == "aprobar"
    assert next(c for c in envio.condiciones if c.nombre == "umbral_match").resultado == "no_cumple"


def test_un_bloqueo_impide_congelar_aunque_el_usuario_apruebe(raiz, tmp_path):
    configurar(raiz, 0)
    id_ = vacante(raiz, verificada=date.today() - timedelta(days=1))
    crear(raiz, "Acme", "Cargo 1", "https://empleos.example.com/vacante/1")

    with pytest.raises(AutonomiaError, match="vigencia_hoy"):
        preparar_envio(raiz, id_, solicitud(tmp_path, aprobacion="usuario"))

    assert (cargar(raiz, id_).estado, cargar(raiz, id_).intentos) == ("PREPARADA", 0)


def test_cli_evalua_la_compuerta_con_los_juicios_del_agente(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz)
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}

    resultado = subprocess.run(
        [sys.executable, "-m", "agente0", "autonomia", "evaluar", id_],
        cwd=REPO,
        env=env,
        input=json.dumps({"portal": PORTAL_BAJO, "juicios": JUICIOS.model_dump()}),
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    decision = json.loads(resultado.stdout)
    assert (decision["nivel_efectivo"], decision["acciones"]["envio"], decision["bloqueos"]) == (75, "automatico", [])
