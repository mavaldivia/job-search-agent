import json
from datetime import date, datetime, timezone

import pytest

from agente0.busquedas import (
    conocida,
    cupo,
    pendiente,
    registrar_consulta,
    registrar_vista,
    resumen,
    vistas,
)
from agente0.configuracion import editar
from agente0.datos import crear_estructura
from agente0.fuentes import guardar
from agente0.oportunidades import registrar
from tests.test_oportunidades import URL, VIGENCIA

LINKEDIN = {"nombre": "LinkedIn Jobs", "tipo": "generalista", "pais": "Chile", "metodo": "navegador", "riesgo": "alto"}
INDEED = {"nombre": "Indeed Chile", "tipo": "generalista", "pais": "Chile", "metodo": "navegador", "riesgo": "medio"}
GETONBOARD = {"nombre": "Get on Board", "tipo": "especializada", "pais": "Chile", "metodo": "web", "riesgo": "bajo"}
HOY = date(2026, 11, 20)


def al_dia(dia: int, mes: int = 11) -> datetime:
    return datetime(2026, mes, dia, 10, 0, tzinfo=timezone.utc)


def consulta(raiz, fuente="LinkedIn Jobs", texto="Data Science Lead", dia=20, cubre=date(2026, 10, 21), **datos):
    base = {"paginas": 2, "lecturas": 4, "vistas": 40, "nuevas": 3, "cubre_desde": cubre}
    return registrar_consulta(raiz, fuente, texto, ahora=al_dia(dia), **base | datos)


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    guardar(tmp_path, [LINKEDIN, INDEED, GETONBOARD])
    return tmp_path


def test_una_fuente_que_no_esta_en_la_lista_se_rechaza_y_no_deja_rastro(raiz):
    with pytest.raises(ValueError, match="no está en fuentes.json"):
        consulta(raiz, fuente="Portal inventado")

    assert not (raiz / "busquedas" / "registro.jsonl").exists()


def test_el_nombre_de_la_fuente_se_guarda_como_esta_en_la_lista(raiz):
    assert consulta(raiz, fuente="linkedin jobs").fuente == "LinkedIn Jobs"


def test_una_busqueda_no_puede_cubrir_desde_el_futuro(raiz):
    with pytest.raises(ValueError, match="cubre_desde"):
        consulta(raiz, dia=20, cubre=date(2026, 11, 21))


def test_sin_busquedas_previas_queda_pendiente_toda_la_ventana(raiz):
    assert [(t.desde, t.hasta) for t in pendiente(raiz, "LinkedIn Jobs", "Data Science Lead", HOY)] == [
        (date(2026, 10, 21), HOY)
    ]


def test_tras_una_busqueda_completa_solo_queda_pendiente_hoy(raiz):
    consulta(raiz, dia=19, cubre=date(2026, 10, 20))

    tramos = pendiente(raiz, "LinkedIn Jobs", "data science lead", HOY)

    assert [(t.desde, t.hasta) for t in tramos] == [(date(2026, 11, 19), HOY)]


def test_una_busqueda_cortada_deja_pendiente_lo_mas_antiguo_y_lo_publicado_despues(raiz):
    consulta(raiz, dia=18, cubre=date(2026, 11, 10), motivo_corte="tope de páginas")

    tramos = pendiente(raiz, "LinkedIn Jobs", "Data Science Lead", HOY)

    assert [(t.desde, t.hasta) for t in tramos] == [
        (date(2026, 10, 21), date(2026, 11, 9)),
        (date(2026, 11, 18), HOY),
    ]


def test_una_segunda_busqueda_completa_lo_que_la_cortada_dejo(raiz):
    consulta(raiz, dia=18, cubre=date(2026, 11, 10), motivo_corte="tope de páginas")
    consulta(raiz, dia=19, cubre=date(2026, 10, 21))

    tramos = pendiente(raiz, "LinkedIn Jobs", "Data Science Lead", HOY)

    assert [(t.desde, t.hasta) for t in tramos] == [(date(2026, 11, 19), HOY)]


def test_una_variante_nueva_del_cargo_no_hereda_lo_cubierto_por_las_otras(raiz):
    consulta(raiz, dia=19, cubre=date(2026, 10, 20))

    tramos = pendiente(raiz, "LinkedIn Jobs", "Head of Data", HOY)

    assert [(t.desde, t.hasta) for t in tramos] == [(date(2026, 10, 21), HOY)]


def test_lo_cubierto_en_otra_fuente_no_cuenta(raiz):
    consulta(raiz, fuente="Indeed Chile", dia=19, cubre=date(2026, 10, 20))

    assert pendiente(raiz, "LinkedIn Jobs", "Data Science Lead", HOY)[0].desde == date(2026, 10, 21)


def test_el_primer_dia_de_una_fuente_no_tiene_tope(raiz):
    consulta(raiz, dia=20, paginas=12, lecturas=60)

    c = cupo(raiz, "LinkedIn Jobs", HOY)

    assert (c.primera_pasada, c.paginas_restantes, c.lecturas_restantes) == (True, None, None)
    assert (c.paginas_usadas_hoy, c.lecturas_usadas_hoy) == (12, 60)


def test_desde_el_segundo_dia_rige_el_tope_del_riesgo_menos_lo_usado_hoy(raiz):
    consulta(raiz, dia=19)
    consulta(raiz, dia=20, paginas=2, lecturas=4)
    consulta(raiz, texto="Head of Data", dia=20, paginas=1, lecturas=3)

    c = cupo(raiz, "LinkedIn Jobs", HOY)

    assert (c.primera_pasada, c.riesgo, c.paginas_restantes, c.lecturas_restantes) == (False, "alto", 0, 3)


def test_el_tope_de_riesgo_medio_es_distinto_y_el_bajo_no_tiene(raiz):
    consulta(raiz, fuente="Indeed Chile", dia=19)
    consulta(raiz, fuente="Get on Board", dia=19)

    medio, bajo = cupo(raiz, "Indeed Chile", HOY), cupo(raiz, "Get on Board", HOY)

    assert (medio.paginas_restantes, medio.lecturas_restantes) == (5, 25)
    assert (bajo.paginas_restantes, bajo.lecturas_restantes) == (None, None)


def test_el_tope_se_edita_en_la_configuracion_sin_tocar_codigo(raiz):
    consulta(raiz, dia=19)

    editar(raiz, {"busqueda": {"topes_por_riesgo": {"alto": {"paginas": 8, "lecturas": 40}}}})

    c = cupo(raiz, "LinkedIn Jobs", HOY)
    assert (c.paginas_restantes, c.lecturas_restantes) == (8, 40)


def test_quitar_un_riesgo_de_los_topes_lo_deja_sin_tope(raiz):
    consulta(raiz, dia=19)

    editar(raiz, {"busqueda": {"topes_por_riesgo": {"medio": {"paginas": 5, "lecturas": 25}}}})

    assert cupo(raiz, "LinkedIn Jobs", HOY).paginas_restantes is None


def test_el_resumen_trae_la_ultima_busqueda_de_cada_fuente(raiz):
    consulta(raiz, dia=18)
    consulta(raiz, texto="Head of Data", dia=19)
    consulta(raiz, fuente="Indeed Chile", dia=17)

    r = {x.fuente: (x.ultima_busqueda, x.consultas_distintas) for x in resumen(raiz)}

    assert r == {
        "LinkedIn Jobs": (date(2026, 11, 19), 2),
        "Indeed Chile": (date(2026, 11, 17), 1),
        "Get on Board": (None, 0),
    }


def test_una_vacante_conocida_se_reconoce_por_enlace_aunque_cambien_los_parametros(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)

    c = conocida(raiz, url="https://empleos.example.com/vacante/123/")

    assert (c.origen, c.coincide_por, c.id, c.estado) == ("OPORTUNIDAD", "url", o.id, "POTENCIAL")


def test_la_misma_vacante_en_otra_fuente_se_reconoce_por_empresa_y_cargo(raiz):
    o = registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)

    c = conocida(raiz, url="https://www.linkedin.com/jobs/view/999", empresa="ACME", cargo="jefe de datos")

    assert (c.origen, c.coincide_por, c.id) == ("OPORTUNIDAD", "empresa_y_cargo", o.id)


def test_un_cargo_distinto_de_la_misma_empresa_no_es_la_misma_vacante(raiz):
    registrar(raiz, "Acme", "Jefe de Datos", URL, VIGENCIA)

    assert conocida(raiz, empresa="Acme", cargo="Gerente de Datos") is None


def test_una_vista_descartada_a_simple_vista_se_reconoce_y_guarda_su_motivo(raiz):
    registrar_vista(
        raiz,
        "LinkedIn Jobs",
        empresa="Beta",
        cargo="Gerente de Ventas",
        url="https://www.linkedin.com/jobs/view/1?trk=abc",
        motivo="mal fit declarado: ventas puras",
        ahora=al_dia(20),
    )

    c = conocida(raiz, url="https://www.linkedin.com/jobs/view/1")

    assert (c.origen, c.coincide_por, c.detalle) == ("VISTA", "url", "mal fit declarado: ventas puras")
    assert [v.cargo for v in vistas(raiz)] == ["Gerente de Ventas"]


def test_conocida_exige_enlace_o_empresa_y_cargo(raiz):
    with pytest.raises(ValueError, match="url"):
        conocida(raiz, empresa="Acme")


def test_el_registro_solo_se_agrega_y_mezcla_busquedas_y_vistas(raiz):
    consulta(raiz, dia=19)
    registrar_vista(raiz, "Indeed Chile", empresa="B", cargo="C", url="https://x.example/1", motivo="m")
    consulta(raiz, dia=20)

    lineas = (raiz / "busquedas" / "registro.jsonl").read_text(encoding="utf-8").splitlines()

    assert [json.loads(linea)["tipo"] for linea in lineas] == ["CONSULTA", "VISTA", "CONSULTA"]
