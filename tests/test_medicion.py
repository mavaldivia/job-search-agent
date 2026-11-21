import json
import os
import subprocess
import sys
from datetime import date, timedelta

import pytest

from agente0 import configuracion, fuentes
from agente0.datos import ENV_VAR, REPO, crear_estructura
from agente0.medicion import respuestas, ventanas
from agente0.postulaciones import (
    Envio,
    Evidencia,
    RespuestaEnviada,
    confirmar_envio,
    crear,
    intentar_envio,
    registrar_evento,
)
from agente0.resumen import resumir
from agente0.revisiones_semanales import RevisionSemanalError, periodo_pendiente, registrar, revisiones

HOY = date(2026, 12, 20)


@pytest.fixture
def raiz(tmp_path):
    crear_estructura(tmp_path)
    fuentes.guardar(
        tmp_path, [{"nombre": "Portal", "tipo": "generalista", "pais": "Chile", "metodo": "web", "riesgo": "bajo"}]
    )
    return tmp_path


def postular(raiz, n: int, enviada: date, pares=(), contacto=False, aprobacion="usuario", nivel=0) -> str:
    """Una postulación confirmada el día `enviada`, con las respuestas de la biblioteca indicadas."""
    cv = raiz / "cv.pdf"
    cv.write_bytes(b"%PDF-1.4")
    p = crear(raiz, f"Empresa {n}", f"Cargo {n}", f"https://empleos.example.com/{n}")
    envio = Envio(
        autonomia=nivel,
        aprobacion=aprobacion,
        cv=cv,
        portal="Portal",
        nivel_efectivo=nivel,
        respuestas=[
            RespuestaEnviada(pregunta=f"P{i}", texto="Texto.", respuesta_id=rid, version=version)
            for i, (rid, version) in enumerate(pares)
        ],
    )
    intentar_envio(raiz, p.id, envio)
    confirmar_envio(raiz, p.id, Evidencia(tipo="confirmacion_visible", detalle="Gracias por postular"))
    archivo = raiz / "postulaciones" / p.id / "postulacion.json"
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    datos["fecha_postulacion"] = enviada.isoformat()
    archivo.write_text(json.dumps(datos), encoding="utf-8")
    if contacto:
        registrar_evento(raiz, p.id, "PRIMER_CONTACTO_ENTREVISTA")
    return p.id


def medir(raiz, **cambios):
    configuracion.editar(raiz, {"medicion": cambios})


def test_el_resumen_cuenta_lo_enviado_en_el_periodo_y_como_se_resolvio(raiz):
    hoy = date.today()
    postular(raiz, 1, hoy, aprobacion="automático: nivel 75 %, condiciones de la compuerta evaluadas", nivel=75)
    postular(raiz, 2, hoy)
    en_cola = crear(raiz, "Empresa 3", "Cargo 3", "https://empleos.example.com/3")

    r = resumir(raiz, hoy - timedelta(days=6), hoy)

    assert (len(r.enviadas), r.automaticas, r.aprobadas) == (2, 1, 1)
    assert r.por_portal == {"Portal": 2}
    assert r.en_cola == [en_cola.id] and r.por_verificar == []
    assert r.revision_anterior is None


def test_el_resumen_deja_fuera_lo_de_otros_periodos_y_marca_lo_por_verificar(raiz):
    hoy = date.today()
    postular(raiz, 1, hoy)
    cv = raiz / "cv.pdf"
    sin_confirmar = crear(raiz, "Empresa 2", "Cargo 2", "https://empleos.example.com/2")
    intentar_envio(raiz, sin_confirmar.id, Envio(autonomia=0, aprobacion="usuario", cv=cv, portal="Portal"))

    semana_pasada = resumir(raiz, hoy - timedelta(days=20), hoy - timedelta(days=10))

    assert semana_pasada.enviadas == [] and semana_pasada.oportunidades_nuevas == 0
    assert semana_pasada.por_verificar == [sin_confirmar.id]


def test_los_primeros_contactos_y_otros_hitos_se_cuentan_en_su_periodo(raiz):
    hoy = date.today()
    con_contacto = postular(raiz, 1, hoy, contacto=True)
    rechazada = postular(raiz, 2, hoy)
    registrar_evento(raiz, rechazada, "RECHAZO")

    r = resumir(raiz, hoy, hoy)

    assert r.primeros_contactos == [con_contacto]
    assert r.otros_hitos == {"RECHAZO": 1}


def test_el_cambio_de_autonomia_del_periodo_aparece_en_el_resumen(raiz):
    configuracion.editar(raiz, {"autonomia": 25})

    r = resumir(raiz, date.today(), date.today())

    assert [(c.de, c.a) for c in r.cambios_de_autonomia] == [(0, 25)] and r.autonomia == 25


def test_el_periodo_pendiente_parte_el_dia_siguiente_a_la_ultima_revision(raiz):
    assert periodo_pendiente(raiz, HOY) == (HOY - timedelta(days=6), HOY)

    registrar(raiz, HOY - timedelta(days=10), HOY - timedelta(days=4), 6.5, "semana tranquila")

    assert periodo_pendiente(raiz, HOY) == (HOY - timedelta(days=3), HOY)
    assert revisiones(raiz)[0].horas_esfuerzo == 6.5


def test_las_revisiones_no_se_solapan_ni_aceptan_horas_negativas(raiz):
    registrar(raiz, date(2026, 12, 1), date(2026, 12, 7), 5)

    with pytest.raises(RevisionSemanalError, match="se solapa"):
        registrar(raiz, date(2026, 12, 7), date(2026, 12, 14), 5)
    with pytest.raises(ValueError):
        registrar(raiz, date(2026, 12, 8), date(2026, 12, 14), -1)
    with pytest.raises(ValueError, match="anterior"):
        registrar(raiz, date(2026, 12, 14), date(2026, 12, 8), 1)
    assert len(revisiones(raiz)) == 1


def test_sin_envios_confirmados_no_hay_ventanas(raiz):
    r = ventanas(raiz, HOY)

    assert (r.linea_base, r.ventanas, r.comparaciones) == (None, [], [])


def test_las_ventanas_agrupan_los_envios_por_fecha_y_con_pocos_contactos_no_concluyen(raiz):
    inicio = HOY - timedelta(weeks=5)
    postular(raiz, 1, inicio, contacto=True)
    postular(raiz, 2, inicio + timedelta(days=3))
    postular(raiz, 3, inicio + timedelta(weeks=4, days=1))

    r = ventanas(raiz, HOY)

    primera, segunda = r.ventanas
    assert (primera.envios, primera.contactos, primera.tasa_contacto) == (2, 1, 0.5)
    assert (segunda.envios, segunda.contactos, segunda.completa) == (1, 0, False)
    assert primera.completa and primera.conclusion == "sin_conclusion"
    assert "sin conclusión" in r.comparaciones[0].lectura
    assert r.comparaciones[0].tasa_contacto_dif is None


def test_con_el_minimo_de_contactos_se_compara_contra_la_linea_base_y_se_usan_las_horas(raiz):
    medir(raiz, minimo_contactos=1)
    inicio = HOY - timedelta(weeks=5)
    postular(raiz, 1, inicio, contacto=True)
    postular(raiz, 2, inicio + timedelta(days=1))
    postular(raiz, 3, inicio + timedelta(weeks=4), contacto=True)
    registrar(raiz, inicio, inicio + timedelta(days=6), 5)
    registrar(raiz, inicio + timedelta(days=7), inicio + timedelta(days=13), 5)
    registrar(raiz, inicio + timedelta(weeks=4), inicio + timedelta(weeks=4, days=6), 2)

    r = ventanas(raiz, HOY)

    primera, segunda = r.ventanas
    assert (primera.horas_esfuerzo, primera.contactos_por_hora) == (10, 0.1)
    assert (segunda.horas_esfuerzo, segunda.contactos_por_hora) == (2, 0.5)
    assert r.comparaciones[0].tasa_contacto_dif == 0.5
    assert r.comparaciones[0].contactos_por_hora_dif == 0.4
    assert "no prueba" in r.comparaciones[0].lectura


def test_una_ventana_sin_revision_semanal_no_inventa_horas(raiz):
    postular(raiz, 1, HOY - timedelta(days=3), contacto=True)

    ventana = ventanas(raiz, HOY).ventanas[0]

    assert (ventana.horas_esfuerzo, ventana.contactos_por_hora) == (None, None)


def test_la_madurez_de_una_ventana_espera_los_dias_para_resolver(raiz):
    inicio = HOY - timedelta(weeks=9)
    postular(raiz, 1, inicio)

    primera = ventanas(raiz, HOY).ventanas[0]
    reciente = ventanas(raiz, inicio + timedelta(weeks=4, days=10)).ventanas[0]

    assert primera.madura is True and reciente.madura is False


def test_las_respuestas_se_suavizan_hacia_la_base_y_con_pocos_usos_solo_se_muestran(raiz):
    medir(raiz, usos_virtuales=2, usos_para_recomendar=3)
    viejo = HOY - timedelta(days=40)
    A, B = ("H1", "v001"), ("N1", "v002")
    for n in range(1, 5):
        postular(raiz, n, viejo, pares=[A], contacto=n <= 3)
    postular(raiz, 5, viejo, pares=[B], contacto=False)
    postular(raiz, 6, viejo, pares=[B], contacto=False)

    r = respuestas(raiz, HOY)

    assert (r.usos_totales, r.contactos_totales, r.tasa_base) == (6, 3, 0.5)
    a, b = r.respuestas
    assert (a.respuesta_id, a.usos, a.contactos, a.tasa_suavizada) == ("H1", 4, 3, 0.6667)
    assert (a.marca, a.recomendar) == ("sobre_la_base", True)
    assert (b.respuesta_id, b.usos, b.tasa_suavizada, b.marca, b.recomendar) == ("N1", 2, 0.25, "pocos_datos", False)


def test_un_envio_reciente_sin_resolver_no_entra_a_la_tasa_de_las_respuestas(raiz):
    postular(raiz, 1, HOY - timedelta(days=3), pares=[("H1", "v001")])
    postular(raiz, 2, HOY - timedelta(days=3), pares=[("H1", "v001")], contacto=True)

    r = respuestas(raiz, HOY)

    assert (r.usos_totales, r.contactos_totales) == (1, 1)
    assert r.respuestas[0].usos == 1


def test_el_cli_registra_la_revision_y_reporta(raiz):
    env = {k: v for k, v in os.environ.items() if k != ENV_VAR} | {ENV_VAR: str(raiz)}

    def cli(*args, entrada=""):
        return subprocess.run(
            [sys.executable, "-m", "agente0", *args], cwd=REPO, env=env, input=entrada, capture_output=True, text=True
        )

    revisado = cli("resumen", "revisado", entrada=json.dumps({"horas_esfuerzo": 4, "nota": "ok"}))
    repetido = cli("resumen", "revisado", entrada=json.dumps({"horas_esfuerzo": 4, "desde": date.today().isoformat()}))
    semanal = cli("resumen", "semanal")
    medicion = cli("medicion", "ventanas")

    assert revisado.returncode == 0, revisado.stderr
    assert repetido.returncode == 1 and "se solapa" in repetido.stderr
    assert json.loads(semanal.stdout)["revision_anterior"]["horas_esfuerzo"] == 4
    assert json.loads(medicion.stdout)["ventanas"] == []
