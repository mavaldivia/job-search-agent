import json
import os
import subprocess
import sys

import pytest

from agente0 import fuentes
from agente0.datos import ENV_VAR, REPO, crear_estructura
from agente0.esquemas import FILTROS_EXCLUYENTES
from agente0.oportunidades import cambiar_estado, cargar
from agente0.oportunidades import evaluar as evaluar_vacante
from agente0.ranking import generar
from agente0.simulacion import simular
from tests.test_autonomia import PORTAL_ALTO, PORTAL_BAJO, configurar, vacante
from tests.test_oportunidades import QUIERO, TENGO, criterios, filtros

EN_BAJO = {"fuentes": [{"nombre": PORTAL_BAJO, "url": "https://portal.example.com/bajo"}]}
EN_ALTO = {"fuentes": [{"nombre": PORTAL_ALTO, "url": "https://portal.example.com/alto"}]}


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


def fila(simulacion, id_):
    return next(f for f in simulacion.filas if f.id == id_)


def archivos(raiz) -> dict:
    return {str(p.relative_to(raiz)): p.read_bytes() for p in sorted(raiz.rglob("*")) if p.is_file()}


def test_simular_no_escribe_nada_ni_cambia_estados(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, **EN_BAJO)
    generar(raiz)
    antes = archivos(raiz)

    simular(raiz, {"autonomia": 100, "priorizacion": {"renta_minima": 9_000_000, "umbrales": {"tengo": 99}}})

    assert archivos(raiz) == antes
    assert cargar(raiz, id_).estado == "POTENCIAL"


def test_bajar_el_umbral_pasa_una_vacante_de_la_cola_al_auto_envio(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, tengo=64, quiero=70, **EN_BAJO)

    f = fila(simular(raiz, {"priorizacion": {"umbrales": {"tengo": 60}}}), id_)

    assert (f.actual.cumple_umbrales, f.actual.destino) == (False, "cola")
    assert "umbral_match" in f.actual.motivos[0] and "tengo 64.0 (mínimo 70)" in f.actual.motivos[0]
    assert (f.hipotetica.cumple_umbrales, f.hipotetica.destino) == (True, "auto_condicionado")
    assert f.cambios == ["destino: cola -> auto_condicionado", "umbrales: no cumple -> cumple"]


def test_subir_el_umbral_saca_una_vacante_del_auto_envio(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, tengo=80, quiero=70, **EN_BAJO)

    f = fila(simular(raiz, {"priorizacion": {"umbrales": {"quiero": 90}}}), id_)

    assert (f.actual.destino, f.hipotetica.destino) == ("auto_condicionado", "cola")


@pytest.mark.parametrize(
    "nivel, destino", [(0, "cola"), (25, "cola"), (50, "cola"), (75, "auto_condicionado"), (100, "auto")]
)
def test_el_nivel_hipotetico_sigue_la_matriz_de_d12(raiz, nivel, destino):
    configurar(raiz, 0)
    id_ = vacante(raiz, 1, **EN_BAJO)

    simulacion = simular(raiz, {"autonomia": nivel})

    assert fila(simulacion, id_).hipotetica.destino == destino
    assert (simulacion.nivel_actual, simulacion.nivel_hipotetico) == (0, nivel)


def test_al_100_las_condiciones_de_preferencia_no_frenan_aunque_los_umbrales_no_se_cumplan(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, tengo=40, quiero=40, **EN_BAJO)

    f = fila(simular(raiz, {"autonomia": 100}), id_)

    assert (f.actual.destino, f.hipotetica.destino, f.hipotetica.cumple_umbrales) == ("cola", "auto", False)


def test_un_nivel_intermedio_se_redondea_y_la_simulacion_lo_avisa(raiz):
    configurar(raiz, 0)

    simulacion = simular(raiz, {"autonomia": 60})

    assert simulacion.nivel_hipotetico == 50
    assert any("redondeada hacia abajo a 50" in a for a in simulacion.advertencias)


def test_el_tope_del_portal_de_riesgo_alto_limita_el_nivel_y_se_puede_simular_su_cambio(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, **EN_ALTO)

    f = fila(simular(raiz, {"compuerta": {"tope_por_riesgo": {"alto": 75}}}), id_)

    assert (f.actual.destino, f.actual.nivel_efectivo) == ("cola", 50)
    assert f.actual.motivos[0].startswith("nivel limitado a 50 %")
    assert (f.hipotetica.destino, f.hipotetica.nivel_efectivo) == ("auto_condicionado", 75)


def test_una_excepcion_por_empresa_manda_el_envio_a_la_cola(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, empresa="Acme", **EN_BAJO)

    f = fila(simular(raiz, {"compuerta": {"siempre_aprobar_empresas": ["Acme"]}}), id_)

    assert (f.actual.destino, f.hipotetica.destino) == ("auto_condicionado", "cola")
    assert "excepción de la configuración" in f.hipotetica.motivos[0]


def test_la_renta_minima_saca_la_vacante_por_el_filtro_o_la_manda_a_la_cola_sin_el_filtro(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, renta_publicada=3_000_000, **EN_BAJO)

    con_filtro = fila(simular(raiz, {"priorizacion": {"renta_minima": 3_500_000}}), id_)
    sin_filtro = fila(
        simular(
            raiz,
            {
                "priorizacion": {
                    "renta_minima": 3_500_000,
                    "filtros_activos": [f for f in FILTROS_EXCLUYENTES if f != "renta"],
                }
            },
        ),
        id_,
    )

    assert con_filtro.hipotetica.destino == "fuera"
    assert "renta publicada 3000000 bajo el mínimo 3500000" in con_filtro.hipotetica.motivos[0]
    assert sin_filtro.hipotetica.destino == "cola"
    assert "renta_minima" in sin_filtro.hipotetica.motivos[0]


def test_sin_renta_publicada_la_renta_minima_no_mueve_nada(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, **EN_BAJO)

    f = fila(simular(raiz, {"priorizacion": {"renta_minima": 9_000_000}}), id_)

    assert f.cambios == []


def test_los_pesos_cambian_el_orden_del_top(raiz):
    configurar(raiz, 0)
    de_tengo = vacante(raiz, 1, tengo=90, quiero=50, **EN_BAJO)
    de_quiero = vacante(raiz, 2, tengo=50, quiero=90, **EN_BAJO)
    pesos = {k: {"eje": "tengo" if k in TENGO else "quiero", "peso": 5 if k in TENGO else 50} for k in TENGO + QUIERO}

    simulacion = simular(raiz, {"priorizacion": {"criterios": pesos}})

    assert [fila(simulacion, i).actual.posicion for i in (de_tengo, de_quiero)] == [1, 2]
    assert [fila(simulacion, i).hipotetica.posicion for i in (de_tengo, de_quiero)] == [2, 1]
    assert fila(simulacion, de_quiero).cambios == ["Top: puesto 2 -> puesto 1"]
    assert [f.id for f in simulacion.filas] == [de_quiero, de_tengo]


def test_un_top_mas_chico_deja_vacantes_fuera_del_top(raiz):
    configurar(raiz, 0)
    mejor, peor = vacante(raiz, 1, tengo=90, **EN_BAJO), vacante(raiz, 2, tengo=60, **EN_BAJO)

    simulacion = simular(raiz, {"priorizacion": {"top": 1}})

    assert (fila(simulacion, mejor).hipotetica.posicion, fila(simulacion, peor).hipotetica.posicion) == (1, None)
    assert fila(simulacion, peor).cambios == ["Top: puesto 2 -> fuera del Top"]


def test_una_lista_permitida_vacia_manda_el_envio_a_la_cola_y_lo_dice(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, **EN_BAJO)

    f = fila(simular(raiz, {"compuerta": {"seniority_permitido": []}}), id_)

    assert f.hipotetica.destino == "cola"
    assert "seniority: la configuración no define seniority permitida" in f.hipotetica.motivos


def test_un_cargo_de_mal_fit_sigue_frenando_por_seniority_aunque_se_desactive_su_filtro(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, **EN_BAJO)
    evaluar_vacante(raiz, id_, "Otro texto", criterios(80, 70), filtros(cargo_mal_fit="es de ventas"), "Brecha.")

    f = fila(simular(raiz, {"priorizacion": {"filtros_activos": ["renta"]}}), id_)

    assert (f.actual.destino, f.hipotetica.destino) == ("fuera", "cola")
    assert "cargo de mal fit: es de ventas" in f.hipotetica.motivos[0]


def test_una_vacante_descartada_por_un_filtro_reaparece_si_se_desactiva_el_filtro(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, **EN_BAJO)
    evaluar_vacante(raiz, id_, "Otro texto", criterios(80, 70), filtros(requisitos_obligatorios="pide X"), "Brecha.")
    generar(raiz)
    assert cargar(raiz, id_).estado == "DESCARTADO"
    sin_filtro = {
        "priorizacion": {"filtros_activos": [f for f in FILTROS_EXCLUYENTES if f != "requisitos_obligatorios"]}
    }

    f = fila(simular(raiz, sin_filtro), id_)

    assert f.referencial
    assert (f.actual.destino, f.hipotetica.destino) == ("fuera", "auto_condicionado")
    assert "requisitos_obligatorios: pide X" in f.actual.motivos[0]


def test_las_vacantes_en_postulacion_son_referenciales_y_las_cerradas_no_salen(raiz):
    configurar(raiz, 75)
    postulada, cerrada, abierta = (vacante(raiz, n, **EN_BAJO) for n in (1, 2, 3))
    cambiar_estado(raiz, postulada, "EN_POSTULACION", "ya existe una postulación")
    cambiar_estado(raiz, cerrada, "CERRADO", "la vacante cerró")

    simulacion = simular(raiz, {})

    assert {f.id: f.referencial for f in simulacion.filas} == {postulada: True, abierta: False}


def test_un_criterio_nuevo_deja_las_evaluaciones_sin_vigencia(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, **EN_BAJO)
    pesos = {k: {"eje": "tengo" if k in TENGO else "quiero", "peso": 10} for k in TENGO + QUIERO}
    pesos["criterio_nuevo"] = {"eje": "quiero", "peso": 10}

    f = fila(simular(raiz, {"priorizacion": {"criterios": pesos}}), id_)

    assert f.hipotetica.destino == "sin_evaluacion"
    assert f.hipotetica.quiero is None


def test_una_vacante_sin_portal_en_las_fuentes_avisa_y_se_supone_sin_tope(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1)

    simulacion = simular(raiz, {})

    assert fila(simulacion, id_).actual.destino == "auto_condicionado"
    assert any(id_ in a and "sin portal" in a for a in simulacion.advertencias)


def test_con_varios_portales_se_usa_el_de_tope_mas_bajo(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, fuentes=[*EN_BAJO["fuentes"], *EN_ALTO["fuentes"]])

    f = fila(simular(raiz, {}), id_)

    assert (f.actual.destino, f.actual.nivel_efectivo) == ("cola", 50)


def test_un_cambio_invalido_se_rechaza_igual_que_en_configuracion_editar(raiz):
    configurar(raiz, 75)

    with pytest.raises(ValueError):
        simular(raiz, {"priorizacion": {"umbrales": {"tengo": 140}}})
    with pytest.raises(ValueError):
        simular(raiz, {"nombre_mal_escrito": 1})


def test_lo_que_no_se_simula_va_en_cada_resultado(raiz):
    configurar(raiz, 75)

    simulacion = simular(raiz, {})

    assert len(simulacion.no_simulado) == 3 and "seniority y ubicación" in simulacion.no_simulado[0]


def test_cli_simula_sin_tocar_la_configuracion(raiz):
    configurar(raiz, 75)
    id_ = vacante(raiz, 1, tengo=64, **EN_BAJO)
    antes = archivos(raiz)
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}

    resultado = subprocess.run(
        [sys.executable, "-m", "agente0", "simulacion"],
        cwd=REPO,
        env=env,
        input=json.dumps({"cambios": {"priorizacion": {"umbrales": {"tengo": 60}}}}),
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    salida = json.loads(resultado.stdout)
    assert salida["filas"][0]["id"] == id_
    assert salida["filas"][0]["hipotetica"]["destino"] == "auto_condicionado"
    assert archivos(raiz) == antes


def test_cli_rechaza_la_entrada_sin_cambios(raiz):
    configurar(raiz, 75)
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}

    resultado = subprocess.run(
        [sys.executable, "-m", "agente0", "simulacion"], cwd=REPO, env=env, input="{}", capture_output=True, text=True
    )

    assert resultado.returncode == 1
    assert resultado.stdout == "" and resultado.stderr.startswith("error:")
