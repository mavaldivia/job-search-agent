from datetime import datetime

import pytest

from agente0 import postulaciones
from agente0.datos import ARCHIVO_CONFIGURACION, crear_estructura
from agente0.esquemas import Configuracion
from agente0.oportunidades import cambiar_estado, cargar, evaluar, registrar
from agente0.ranking import generar, ultimo
from tests.test_oportunidades import FILTROS_DEL_AGENTE, VIGENCIA, criterios, filtros

HORA = [datetime(2026, 11, 19, 10, 0, minute) for minute in range(60)]


class Corrida:
    """Genera rankings con una hora distinta cada vez, como pasaría en corridas reales."""

    def __init__(self, raiz):
        self.raiz, self._n = raiz, 0

    def __call__(self):
        self._n += 1
        return generar(self.raiz, ahora=HORA[self._n])


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    return tmp_path


@pytest.fixture
def ranking(raiz):
    return Corrida(raiz)


def configurar(raiz, **priorizacion):
    configuracion = Configuracion.model_validate({"priorizacion": priorizacion})
    (raiz / ARCHIVO_CONFIGURACION).write_text(configuracion.model_dump_json(indent=2), encoding="utf-8")


def url(n: int) -> str:
    return f"https://empleos.example.com/vacante/{n}"


def vacante(raiz, n: int, tengo: int, quiero: int, empresa: str | None = None, **datos) -> str:
    o = registrar(raiz, empresa or f"Empresa {n}", f"Cargo {n}", url(n), VIGENCIA, **datos)
    evaluar(raiz, o.id, f"Publicación {n}", criterios(tengo, quiero), filtros(), f"Brecha de la vacante {n}")
    return o.id


def ids(r):
    return [e.id for e in r.top]


def test_el_top_se_ordena_por_total_y_muestra_cada_eje_por_separado(raiz, ranking):
    a = vacante(raiz, 1, tengo=90, quiero=40)
    b = vacante(raiz, 2, tengo=70, quiero=80)

    r = ranking()

    assert ids(r) == [b, a]
    primera = r.top[0]
    assert (primera.tengo, primera.quiero, primera.total) == (70.0, 80.0, 74.5)
    assert primera.contribuciones["ajuste_experiencia"] == 21.0
    assert primera.contribuciones["remuneracion"] == 12.0
    assert primera.brecha_principal == "Brecha de la vacante 2"
    assert [e.cambio for e in r.top] == ["NUEVA", "NUEVA"]


def test_cumple_umbrales_se_evalua_por_eje_y_no_sobre_el_total(raiz, ranking):
    vacante(raiz, 1, tengo=90, quiero=59)
    vacante(raiz, 2, tengo=70, quiero=60)

    r = {e.cargo: e for e in ranking().top}

    assert r["Cargo 1"].cumple_umbrales is False
    assert r["Cargo 2"].cumple_umbrales is True


def test_el_top_respeta_el_tamano_de_la_configuracion(raiz, ranking):
    configurar(raiz, top=2)
    for n, puntaje in enumerate((50, 90, 70), start=1):
        vacante(raiz, n, tengo=puntaje, quiero=puntaje)

    assert [e.cargo for e in ranking().top] == ["Cargo 2", "Cargo 3"]


def test_cambiar_los_pesos_reordena_sin_reevaluar(raiz, ranking):
    a = vacante(raiz, 1, tengo=100, quiero=0)
    b = vacante(raiz, 2, tengo=0, quiero=100)
    assert ids(ranking()) == [a, b]

    base = Configuracion().priorizacion.model_dump(mode="json")
    for criterio in base["criterios"].values():
        criterio["peso"] = 1 if criterio["eje"] == "tengo" else 10
    configurar(raiz, **base)

    assert ids(ranking()) == [b, a]


def test_una_vacante_sin_evaluacion_vigente_queda_pendiente(raiz, ranking):
    sin_evaluar = registrar(raiz, "Acme", "Sin evaluar", url(50), VIGENCIA).id
    vacante(raiz, 1, tengo=80, quiero=80)

    r = ranking()

    assert r.pendientes == [sin_evaluar]
    assert len(r.top) == 1


def test_renta_publicada_bajo_el_minimo_descarta_con_motivo(raiz, ranking):
    configurar(raiz, renta_minima=3_000_000)
    barata = vacante(raiz, 1, tengo=95, quiero=95, renta_publicada=2_000_000)
    sin_dato = vacante(raiz, 2, tengo=60, quiero=60)

    r = ranking()

    assert ids(r) == [sin_dato]
    assert [(d.id, d.motivo) for d in r.descartadas] == [(barata, "renta publicada 2000000 bajo el mínimo 3000000")]
    assert cargar(raiz, barata).estado == "DESCARTADO"


def test_empresa_excluida_y_filtro_del_agente_descartan(raiz, ranking):
    configurar(raiz, empresas_excluidas=["Empresa Prohibida S.A."])
    excluida = vacante(raiz, 1, tengo=90, quiero=90, empresa="empresa prohibida s.a.")
    o = registrar(raiz, "Acme", "Cargo junior", url(2), VIGENCIA)
    evaluar(raiz, o.id, "Publicación 2", criterios(90, 90), filtros(seniority="cargo de entrada"), "brecha")
    vacante(raiz, 3, tengo=60, quiero=60)

    r = ranking()

    motivos = {d.id: d.motivo for d in r.descartadas}
    assert motivos == {excluida: "empresa excluida", o.id: "seniority: cargo de entrada"}
    assert len(r.top) == 1


def test_un_filtro_desactivado_no_descarta(raiz, ranking):
    configurar(
        raiz, filtros_activos=[f for f in ("renta", "empresa_excluida", *FILTROS_DEL_AGENTE) if f != "seniority"]
    )
    o = registrar(raiz, "Acme", "Cargo junior", url(2), VIGENCIA)
    evaluar(
        raiz,
        o.id,
        "Publicación 2",
        criterios(90, 90),
        {k: v for k, v in filtros(seniority="x").items() if k != "seniority"},
        "brecha",
    )

    assert ids(ranking()) == [o.id]


def test_una_vacante_rescatada_no_se_vuelve_a_descartar(raiz, ranking):
    configurar(raiz, renta_minima=3_000_000)
    id_ = vacante(raiz, 1, tengo=90, quiero=90, renta_publicada=2_000_000)
    ranking()
    cambiar_estado(raiz, id_, "POTENCIAL")

    r = ranking()

    assert ids(r) == [id_]
    assert r.descartadas == []


def test_una_vacante_con_postulacion_existente_sale_del_ranking_sin_duplicarse(raiz, ranking):
    ya = vacante(raiz, 1, tengo=90, quiero=90)
    otra = vacante(raiz, 2, tengo=80, quiero=80)
    assert ids(ranking()) == [ya, otra]
    postulaciones.crear(raiz, "Empresa 1", "Cargo 1", url(1))

    r = ranking()

    assert ids(r) == [otra]
    assert [(s.id, s.motivo) for s in r.salidas] == [(ya, "POSTULADA")]
    assert cargar(raiz, ya).estado == "EN_POSTULACION"


def test_proceso_activo_en_la_empresa_descarta_otras_vacantes_de_ella(raiz, ranking):
    postulaciones.crear(raiz, "Acme", "Gerente", url(100))
    otra_de_acme = vacante(raiz, 1, tengo=90, quiero=90, empresa="ACME")
    libre = vacante(raiz, 2, tengo=70, quiero=70)

    r = ranking()

    assert ids(r) == [libre]
    assert [(d.id, d.motivo) for d in r.descartadas] == [(otra_de_acme, "proceso activo en esa empresa")]


def test_dos_corridas_seguidas_dan_la_misma_lista_sin_cambios(raiz, ranking):
    for n, puntaje in enumerate((90, 70, 50), start=1):
        vacante(raiz, n, tengo=puntaje, quiero=puntaje)
    primera = ranking()

    segunda = ranking()

    assert ids(segunda) == ids(primera)
    assert {e.cambio for e in segunda.top} == {"SIN_CAMBIOS"}
    assert segunda.anterior == "2026-11-19T100001"
    assert segunda.salidas == [] and segunda.descartadas == []


def test_una_vacante_nueva_empatada_con_la_ultima_no_entra(raiz, ranking):
    configurar(raiz, top=2)
    a = vacante(raiz, 1, tengo=90, quiero=90)
    b = vacante(raiz, 2, tengo=70, quiero=70)
    ranking()
    vacante(raiz, 3, tengo=70, quiero=70)

    r = ranking()

    assert ids(r) == [a, b]
    assert r.salidas == []


def test_una_vacante_nueva_superior_entra_y_desplaza_a_la_ultima(raiz, ranking):
    configurar(raiz, top=2)
    a = vacante(raiz, 1, tengo=90, quiero=90)
    b = vacante(raiz, 2, tengo=70, quiero=70)
    ranking()
    c = vacante(raiz, 3, tengo=80, quiero=80)

    r = ranking()

    assert ids(r) == [a, c]
    assert {e.id: e.cambio for e in r.top} == {a: "SIN_CAMBIOS", c: "NUEVA"}
    assert [(s.id, s.motivo) for s in r.salidas] == [(b, "DESPLAZADA")]


def test_si_una_sale_por_cierre_las_demas_no_figuran_como_que_suben(raiz, ranking):
    a = vacante(raiz, 1, tengo=90, quiero=90)
    b = vacante(raiz, 2, tengo=80, quiero=80)
    c = vacante(raiz, 3, tengo=70, quiero=70)
    ranking()
    cambiar_estado(raiz, a, "CERRADO", "cerrada en el portal corporativo")

    r = ranking()

    assert ids(r) == [b, c]
    assert {e.cambio for e in r.top} == {"SIN_CAMBIOS"}
    assert [(s.id, s.motivo, s.detalle) for s in r.salidas] == [(a, "CERRADA", "cerrada en el portal corporativo")]


def test_evidencia_nueva_mueve_la_posicion_y_se_declara(raiz, ranking):
    a = vacante(raiz, 1, tengo=90, quiero=90)
    b = vacante(raiz, 2, tengo=80, quiero=80)
    ranking()
    evaluar(raiz, a, "Publicación 1 con nuevas exigencias", criterios(40, 40), filtros(), "Nueva brecha")

    r = ranking()

    assert ids(r) == [b, a]
    assert {e.id: e.cambio for e in r.top} == {b: "SUBE", a: "BAJA"}


def test_una_vacante_que_pasa_a_descartada_sale_con_su_motivo_y_no_se_repite(raiz, ranking):
    a = vacante(raiz, 1, tengo=90, quiero=90)
    vacante(raiz, 2, tengo=80, quiero=80)
    ranking()
    cambiar_estado(raiz, a, "DESCARTADO", "decisión del usuario")

    r = ranking()

    assert [(s.id, s.motivo, s.detalle) for s in r.salidas] == [(a, "DESCARTADA", "decisión del usuario")]
    assert r.descartadas == []


def test_el_ranking_queda_guardado_y_ultimo_devuelve_el_mas_reciente(raiz, ranking):
    assert ultimo(raiz) is None
    vacante(raiz, 1, tengo=90, quiero=90)
    ranking()
    segunda = ranking()

    assert ultimo(raiz) == segunda
    assert len(list((raiz / "ranking").glob("*.json"))) == 2
