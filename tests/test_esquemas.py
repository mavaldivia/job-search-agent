import pytest
from pydantic import ValidationError

from agente0.esquemas import Configuracion


@pytest.mark.parametrize("valor, esperado", [(0, 0), (24, 0), (25, 25), (60, 50), (99, 75), (100, 100)])
def test_autonomia_se_redondea_hacia_abajo_al_nivel_fijo(valor, esperado):
    assert Configuracion(autonomia=valor).autonomia == esperado


@pytest.mark.parametrize("valor", [-1, 101])
def test_autonomia_fuera_de_rango_se_rechaza(valor):
    with pytest.raises(ValidationError):
        Configuracion(autonomia=valor)


def test_valores_por_defecto_son_los_de_d15():
    configuracion = Configuracion()
    assert configuracion.autonomia == 0
    assert configuracion.recordatorios_dias.model_dump() == {"experiencia": 15, "cv_base": 30, "configuracion": 60}
    assert configuracion.repetir_recordatorio_horas == 24


def test_priorizacion_parte_con_los_valores_de_d11_y_u4():
    p = Configuracion().priorizacion
    peso_por_eje = {eje: sum(c.peso for c in p.criterios.values() if c.eje == eje) for eje in ("tengo", "quiero")}
    assert peso_por_eje == {"tengo": 55, "quiero": 45}
    assert (p.umbrales.tengo, p.umbrales.quiero) == (70, 60)
    assert (p.top, p.ventana_dias, p.renta_minima, p.empresas_excluidas) == (10, 30, None, [])
    assert len(p.filtros_activos) == 6


def test_configuracion_sin_bloque_de_priorizacion_carga_con_los_valores_iniciales():
    assert Configuracion.model_validate_json('{"autonomia": 25}').priorizacion == Configuracion().priorizacion


def test_priorizacion_editada_a_mano_sobrevive_al_ciclo_json():
    cruda = Configuracion().model_dump(mode="json")
    cruda["priorizacion"]["top"] = 5
    cruda["priorizacion"]["criterios"]["remuneracion"]["peso"] = 25
    cruda["priorizacion"]["renta_minima"] = 3_000_000

    p = Configuracion.model_validate(cruda).priorizacion

    assert (p.top, p.criterios["remuneracion"].peso, p.renta_minima) == (5, 25, 3_000_000)


@pytest.mark.parametrize(
    "cambio",
    [
        {"criterios": {"solo_tengo": {"eje": "tengo", "peso": 10}}},
        {"criterios": {"x": {"eje": "otro", "peso": 10}, "y": {"eje": "quiero", "peso": 10}}},
        {"criterios": {"a": {"eje": "tengo", "peso": 0}, "b": {"eje": "quiero", "peso": 10}}},
        {"filtros_activos": ["inventado"]},
        {"top": 0},
        {"topp": 5},
    ],
)
def test_priorizacion_invalida_se_rechaza(cambio):
    with pytest.raises(ValidationError):
        Configuracion.model_validate({"priorizacion": cambio})
