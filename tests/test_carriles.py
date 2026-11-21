import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

import pytest

from agente0 import fuentes
from agente0.carriles import CarrilesError, planear, portal_de
from agente0.datos import ARCHIVO_CONFIGURACION, ENV_VAR, REPO, crear_estructura
from agente0.esquemas import Configuracion
from agente0.oportunidades import cargar as cargar_oportunidad
from agente0.oportunidades import evaluar, registrar
from agente0.postulaciones import Envio, Evidencia, confirmar_envio, crear, envio_fallido, intentar_envio
from agente0.ranking import generar
from tests.test_oportunidades import criterios, filtros

FUENTES = [
    {
        "nombre": "Portal A",
        "tipo": "generalista",
        "pais": "Chile",
        "url": "https://www.portal-a.example.com",
        "metodo": "web",
        "riesgo": "bajo",
    },
    {
        "nombre": "Portal B",
        "tipo": "generalista",
        "pais": "Chile",
        "url": "https://portal-b.example.com",
        "metodo": "navegador",
        "riesgo": "alto",
    },
]
CORPORATIVO = {
    "nombre": "Portales corporativos",
    "tipo": "corporativa",
    "pais": "Chile",
    "metodo": "navegador",
    "riesgo": "medio",
}


def _ahora() -> datetime:
    return datetime.now().astimezone()


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    fuentes.guardar(tmp_path, FUENTES)
    return tmp_path


def configurar(raiz, autonomia: int, compuerta: dict | None = None):
    configuracion = Configuracion.model_validate({"autonomia": autonomia, "compuerta": compuerta or {}})
    (raiz / ARCHIVO_CONFIGURACION).write_text(configuracion.model_dump_json(indent=2), encoding="utf-8")


def vacante(raiz, n: int, url: str, tengo: int = 80, empresa: str | None = None) -> str:
    vigencia = {
        "verificada_el": date.today().isoformat(),
        "fuente": "portal",
        "evidencia": "botón visible",
    }
    o = registrar(raiz, empresa or f"Empresa {n}", f"Cargo {n}", url, vigencia)
    evaluar(raiz, o.id, f"Publicación {n}", criterios(tengo, 70), filtros(), "Brecha.")
    return o.id


def enviar(raiz, tmp_path, id_: str, portal: str) -> None:
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"%PDF-1.4")
    intentar_envio(raiz, id_, Envio(autonomia=0, aprobacion="usuario", cv=cv, portal=portal))


def carril(plan, portal: str):
    return next(c for c in plan.carriles if c.portal == portal)


def test_el_top_se_reparte_en_carriles_por_el_dominio_del_enlace_oficial(raiz):
    a1 = vacante(raiz, 1, "https://portal-a.example.com/empleo/1", tengo=90)
    b1 = vacante(raiz, 2, "https://empleos.portal-b.example.com/job/2", tengo=85)
    a2 = vacante(raiz, 3, "https://www.portal-a.example.com/empleo/3", tengo=80)
    generar(raiz)

    plan = planear(raiz)

    assert [c.portal for c in plan.carriles] == ["Portal A", "Portal B"]
    assert [v.id for v in carril(plan, "Portal A").vacantes] == [a1, a2]
    assert [v.id for v in carril(plan, "Portal B").vacantes] == [b1]
    assert plan.sin_carril == []


def test_un_enlace_de_otro_dominio_va_a_portales_corporativos_y_sin_ese_portal_queda_sin_carril(
    raiz,
):
    id_ = vacante(raiz, 1, "https://careers.acme.example.org/job/1")
    generar(raiz)

    sin_corporativo = planear(raiz)
    fuentes.agregar(raiz, **CORPORATIVO)
    con_corporativo = planear(raiz)

    assert [s.id for s in sin_corporativo.sin_carril] == [id_] and sin_corporativo.carriles == []
    assert [v.id for v in carril(con_corporativo, "Portales corporativos").vacantes] == [id_]


def test_una_fuente_inactiva_no_recibe_carril(raiz):
    fuentes.guardar(raiz, [{**FUENTES[0], "activa": False}, FUENTES[1]])
    o = vacante(raiz, 1, "https://portal-a.example.com/empleo/1")

    assert portal_de(cargar_oportunidad(raiz, o), fuentes.cargar(raiz)) is None


def test_el_cupo_del_dia_acota_las_vacantes_del_carril_y_el_resto_queda_en_espera(raiz, tmp_path):
    configurar(raiz, 0, {"pausa_minutos": 0, "limites_diarios": {"alto": 2}})
    previas = [vacante(raiz, n, f"https://portal-b.example.com/job/{n}", tengo=60) for n in (1, 2)]
    for n, id_ in enumerate(previas, start=1):
        crear(raiz, f"Empresa {n}", f"Cargo {n}", f"https://portal-b.example.com/job/{n}")
        enviar(raiz, tmp_path, id_, "Portal B")
    nuevas = [vacante(raiz, n, f"https://portal-b.example.com/job/{n}", tengo=90) for n in (3, 4)]
    generar(raiz)

    c = carril(planear(raiz), "Portal B")

    assert (c.limite_diario, c.enviados_hoy, c.cupo_restante) == (2, 2, 0)
    assert c.vacantes == [] and c.en_espera == nuevas


def test_los_envios_de_otro_portal_no_gastan_el_cupo_ni_la_pausa_del_carril(raiz, tmp_path):
    configurar(raiz, 0)
    en_a = vacante(raiz, 1, "https://portal-a.example.com/empleo/1")
    crear(raiz, "Empresa 1", "Cargo 1", "https://portal-a.example.com/empleo/1")
    enviar(raiz, tmp_path, en_a, "Portal A")
    vacante(raiz, 2, "https://portal-b.example.com/job/2")
    vacante(raiz, 3, "https://portal-a.example.com/empleo/3")
    generar(raiz)

    plan = planear(raiz)

    assert (
        carril(plan, "Portal A").enviados_hoy,
        carril(plan, "Portal A").espera_segundos > 0,
    ) == (1, True)
    assert (
        carril(plan, "Portal B").enviados_hoy,
        carril(plan, "Portal B").espera_segundos,
    ) == (0, 0)
    assert planear(raiz, ahora=_ahora() + timedelta(minutes=3)).carriles[0].espera_segundos == 0


@pytest.mark.parametrize("autonomia, nivel", [(0, 0), (50, 50), (75, 50), (100, 50)])
def test_el_tope_del_portal_de_riesgo_alto_manda_sobre_el_nivel_configurado(raiz, autonomia, nivel):
    configurar(raiz, autonomia)
    vacante(raiz, 1, "https://portal-b.example.com/job/1")
    generar(raiz)

    c = carril(planear(raiz), "Portal B")

    assert (c.nivel_efectivo, c.envio, c.envio_condicionado) == (
        nivel,
        "aprobar",
        False,
    )


def test_al_75_el_envio_de_un_portal_sin_tope_es_automatico_pero_condicionado(raiz):
    configurar(raiz, 75)
    vacante(raiz, 1, "https://portal-a.example.com/empleo/1")
    generar(raiz)

    c = carril(planear(raiz), "Portal A")

    assert (c.nivel_efectivo, c.envio, c.envio_condicionado) == (75, "automatico", True)


def test_las_preparadas_van_a_la_cola_y_las_ya_enviadas_quedan_fuera(raiz, tmp_path):
    configurar(raiz, 50, {"pausa_minutos": 0})
    preparada = vacante(raiz, 1, "https://portal-a.example.com/empleo/1", tengo=90)
    enviada = vacante(raiz, 2, "https://portal-a.example.com/empleo/2", tengo=85)
    nueva = vacante(raiz, 3, "https://portal-a.example.com/empleo/3", tengo=80)
    crear(raiz, "Empresa 1", "Cargo 1", "https://portal-a.example.com/empleo/1")
    crear(raiz, "Empresa 2", "Cargo 2", "https://portal-a.example.com/empleo/2")
    enviar(raiz, tmp_path, enviada, "Portal A")
    confirmar_envio(raiz, enviada, Evidencia(tipo="confirmacion_visible", detalle="Gracias"))
    generar(raiz)

    c = carril(planear(raiz), "Portal A")

    assert [v.id for v in c.en_cola] == [preparada]
    assert [v.id for v in c.vacantes] == [nueva]


def test_un_envio_fallido_vuelve_a_la_cola_del_carril(raiz, tmp_path):
    configurar(raiz, 0, {"pausa_minutos": 0})
    id_ = vacante(raiz, 1, "https://portal-a.example.com/empleo/1")
    crear(raiz, "Empresa 1", "Cargo 1", "https://portal-a.example.com/empleo/1")
    enviar(raiz, tmp_path, id_, "Portal A")
    envio_fallido(raiz, id_, "timeout sin envío")
    generar(raiz)

    c = carril(planear(raiz), "Portal A")

    assert [v.id for v in c.en_cola] == [id_] and c.vacantes == []


def test_sin_ranking_se_pide_generarlo(raiz):
    with pytest.raises(CarrilesError, match="ranking generar"):
        planear(raiz)


def test_cuantos_carriles_van_a_la_vez_sale_de_la_configuracion(raiz):
    configurar(raiz, 0, {"carriles_en_paralelo": 2})
    vacante(raiz, 1, "https://portal-a.example.com/empleo/1")
    generar(raiz)

    assert planear(raiz).en_paralelo == 2


def test_el_cli_entrega_el_plan_en_json(raiz):
    vacante(raiz, 1, "https://portal-a.example.com/empleo/1")
    generar(raiz)
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}

    resultado = subprocess.run(
        [sys.executable, "-m", "agente0", "carriles"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert json.loads(resultado.stdout)["carriles"][0]["portal"] == "Portal A"
