import pytest

from agente0.ids import id_postulacion

URL = "https://www.laborum.cl/empleos/jefe-de-analytics-123456.html"


def test_el_id_es_legible_y_determinista():
    id_ = id_postulacion("Acme S.A.", "Jefe de Analítica", URL)
    assert id_.startswith("acme-s-a-jefe-de-analitica-")
    assert id_ == id_postulacion("Acme S.A.", "Jefe de Analítica", URL)


def test_seguimiento_mayusculas_y_barra_final_no_cambian_el_id():
    base = id_postulacion("Acme", "Head of Data", "https://x.cl/job/1")
    con_ruido = id_postulacion("Acme", "Head of Data", "HTTPS://X.cl/job/1/?utm_source=a&trk=b#detalle")
    assert base == con_ruido


def test_urls_distintas_dan_ids_distintos_aunque_empresa_y_cargo_coincidan():
    uno = id_postulacion("Acme", "Head of Data", "https://x.cl/jobs?id=1")
    dos = id_postulacion("Acme", "Head of Data", "https://x.cl/jobs?id=2")
    assert uno != dos


@pytest.mark.parametrize("empresa, cargo, url", [("", "Cargo", URL), ("Empresa", "  ", URL), ("Empresa", "Cargo", "")])
def test_faltan_datos_obligatorios(empresa, cargo, url):
    with pytest.raises(ValueError):
        id_postulacion(empresa, cargo, url)
