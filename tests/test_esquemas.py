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
    assert configuracion.posponer_dias == 7
