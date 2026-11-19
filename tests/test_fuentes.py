import pytest

from agente0.fuentes import agregar, cargar, guardar

LINKEDIN = {"nombre": "LinkedIn Jobs", "tipo": "generalista", "pais": "Chile", "metodo": "navegador", "riesgo": "alto"}
GETONBOARD = {"nombre": "Get on Board", "tipo": "especializada", "pais": "Chile", "metodo": "web", "riesgo": "bajo"}


def test_sin_archivo_la_lista_esta_vacia(tmp_path):
    assert cargar(tmp_path) == []


def test_guardar_y_cargar_conservan_la_lista(tmp_path):
    guardar(tmp_path, [LINKEDIN, GETONBOARD])

    fuentes = cargar(tmp_path)

    assert [(f.nombre, f.metodo, f.riesgo, f.activa, f.url) for f in fuentes] == [
        ("LinkedIn Jobs", "navegador", "alto", True, None),
        ("Get on Board", "web", "bajo", True, None),
    ]


def test_agregar_suma_sin_tocar_las_demas(tmp_path):
    guardar(tmp_path, [LINKEDIN])

    agregar(tmp_path, **GETONBOARD, url="https://www.getonbrd.com")

    assert [f.nombre for f in cargar(tmp_path)] == ["LinkedIn Jobs", "Get on Board"]
    assert cargar(tmp_path)[1].url == "https://www.getonbrd.com"


@pytest.mark.parametrize(
    "fuente",
    [
        {**LINKEDIN, "metodo": "api"},
        {**LINKEDIN, "riesgo": "extremo"},
        {**LINKEDIN, "tipo": "red social"},
        {**LINKEDIN, "limite_diario": 3},
        {k: v for k, v in LINKEDIN.items() if k != "pais"},
    ],
)
def test_una_fuente_invalida_se_rechaza_y_no_toca_el_archivo(tmp_path, fuente):
    guardar(tmp_path, [GETONBOARD])

    with pytest.raises(ValueError):
        agregar(tmp_path, **fuente)

    assert [f.nombre for f in cargar(tmp_path)] == ["Get on Board"]


def test_no_se_repite_el_nombre_de_una_fuente(tmp_path):
    guardar(tmp_path, [LINKEDIN])

    with pytest.raises(ValueError, match="mismo nombre"):
        agregar(tmp_path, **{**LINKEDIN, "nombre": "linkedin jobs"})
