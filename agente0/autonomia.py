import math
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from agente0 import fuentes, oportunidades, postulaciones
from agente0.datos import cargar_configuracion
from agente0.esquemas import CONDICIONES_PREFERENCIA, Compuerta, Priorizacion, Riesgo
from agente0.fuentes import FuenteBusqueda
from agente0.ids import slug_empresa
from agente0.oportunidades import Oportunidad
from agente0.postulaciones import Accion, Condicion, Envio, Modo, RespuestaEnviada
from agente0.ranking import puntuar

# D12: la matriz de permisos por acción y nivel. Al 75 % el envío es automático solo si se cumplen las
# condiciones de preferencia; al 100 % solo rigen las reglas siempre vigentes.
MATRIZ: dict[int, dict[Accion, Modo]] = {
    0: {"cv": "aprobar", "respuestas": "aprobar", "formulario": "aprobar", "envio": "aprobar"},
    25: {"cv": "aprobar", "respuestas": "aprobar", "formulario": "automatico", "envio": "aprobar"},
    50: {"cv": "automatico", "respuestas": "aprobar_nuevas", "formulario": "automatico", "envio": "aprobar"},
    75: {"cv": "automatico", "respuestas": "automatico", "formulario": "automatico", "envio": "automatico"},
    100: {"cv": "automatico", "respuestas": "automatico", "formulario": "automatico", "envio": "automatico"},
}


class AutonomiaError(ValueError):
    pass


class JuicioValor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valor: str = Field(min_length=1)
    evidencia: str = Field(min_length=1)


class JuicioBool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cumple: bool
    evidencia: str = Field(min_length=1)


class Juicios(BaseModel):
    """Lo que solo el agente puede calificar al leer la vacante y su propio trabajo; el código decide el resto."""

    model_config = ConfigDict(extra="forbid")

    seniority: JuicioValor | None = None
    ubicacion: JuicioValor | None = None
    respuestas_documentadas: JuicioBool | None = None
    cv_auditado: JuicioBool | None = None


class SolicitudEnvio(BaseModel):
    """Lo que entrega el agente al congelar un envío; el nivel, las condiciones y las acciones los fija el código."""

    model_config = ConfigDict(extra="forbid")

    portal: str = Field(min_length=1)
    cv: Path
    juicios: Juicios = Field(default_factory=Juicios)
    respuestas: list[RespuestaEnviada] = Field(default_factory=list)
    # Quién aprobó y qué, en el chat. Obligatoria cuando la compuerta pide aprobar el envío.
    aprobacion: str | None = None


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oportunidad: str
    portal: str
    riesgo: Riesgo
    nivel_configurado: int
    nivel_efectivo: int
    condiciones: list[Condicion]
    # Lo que impide continuar con esta postulación ahora; no es lo mismo que pedir aprobación.
    bloqueos: list[str]
    acciones: dict[Accion, Modo]
    # Por qué el envío no es automático aunque el nivel lo permitiría.
    motivos: list[str]
    espera_segundos: int = 0


def evaluar(
    raiz: Path, id_: str, portal: str, juicios: Juicios | None = None, ahora: datetime | None = None
) -> Decision:
    """Compuerta de autonomía (D12): qué se hace solo y qué se aprueba, con cada condición y su resultado."""
    ahora = ahora or datetime.now().astimezone()
    config = cargar_configuracion(raiz)
    compuerta = config.compuerta
    o = oportunidades.cargar(raiz, id_)
    fuente = _fuente(raiz, portal)
    nivel = nivel_efectivo(config.autonomia, compuerta, fuente)
    todas = postulaciones.listar(raiz)
    juicios = juicios or Juicios()

    vigentes = _vigentes(o, config.priorizacion, todas, juicios, ahora)
    preferencias = evaluar_preferencias(o, config.priorizacion, compuerta, todas, juicios, nivel)
    condiciones = vigentes + preferencias

    acciones, motivos_envio = acciones_de_envio(nivel, preferencias, compuerta, fuente, o)
    motivos = []
    if nivel < config.autonomia:
        motivos.append(f"nivel limitado a {nivel} % por el tope de {fuente.nombre} (riesgo {fuente.riesgo})")
    motivos += motivos_envio

    bloqueos = [f"{c.nombre}: {c.detalle}" for c in vigentes if c.resultado != "cumple"]
    bloqueo_limites, espera = _limites(raiz, compuerta, fuente, ahora)
    return Decision(
        oportunidad=id_,
        portal=fuente.nombre,
        riesgo=fuente.riesgo,
        nivel_configurado=config.autonomia,
        nivel_efectivo=nivel,
        condiciones=condiciones,
        bloqueos=bloqueos + bloqueo_limites,
        acciones=acciones,
        motivos=motivos,
        espera_segundos=espera,
    )


def _fuente(raiz: Path, portal: str) -> FuenteBusqueda:
    for fuente in fuentes.cargar(raiz):
        if fuente.nombre.casefold() == portal.strip().casefold():
            return fuente
    raise AutonomiaError(
        f"el portal {portal!r} no está en las fuentes del usuario: agrégalo (con su aprobación) con `fuentes agregar`."
    )


def nivel_efectivo(autonomia: int, compuerta: Compuerta, fuente: FuenteBusqueda) -> int:
    por_portal = {nombre.casefold(): tope for nombre, tope in compuerta.topes_por_portal.items()}
    tope = por_portal.get(fuente.nombre.casefold(), compuerta.tope_por_riesgo.get(fuente.riesgo, 100))
    return min(autonomia, tope)


def acciones_de_envio(
    nivel: int, preferencias: list[Condicion], compuerta: Compuerta, fuente: FuenteBusqueda, o: Oportunidad
) -> tuple[dict[Accion, Modo], list[str]]:
    """La matriz de D12 para el nivel y por qué el envío no es automático aunque el nivel lo permitiría."""
    acciones = dict(MATRIZ[nivel])
    motivos = []
    if nivel == 75:
        for c in preferencias:
            if c.resultado in ("no_cumple", "no_evaluada"):
                acciones["envio"] = "aprobar"
                motivos.append(f"{c.nombre}: {c.detalle}")
    if _siempre_aprobar(compuerta, fuente, o):
        acciones["envio"] = "aprobar"
        motivos.append("excepción de la configuración: este portal o empresa se aprueba a mano")
    return acciones, motivos


def _siempre_aprobar(compuerta: Compuerta, fuente: FuenteBusqueda, o: Oportunidad) -> bool:
    portales = {p.casefold() for p in compuerta.siempre_aprobar_portales}
    empresas = {slug_empresa(e) for e in compuerta.siempre_aprobar_empresas}
    return fuente.nombre.casefold() in portales or slug_empresa(o.empresa) in empresas


def _vigentes(
    o: Oportunidad, prio: Priorizacion, todas: list[postulaciones.Postulacion], juicios: Juicios, ahora: datetime
) -> list[Condicion]:
    previa = next((p for p in todas if p.id == o.id), None)
    hoy = ahora.astimezone().date()

    if o.estado in ("CERRADO", "DESCARTADO"):
        vigencia = ("no_cumple", f"la oportunidad está {o.estado}")
    elif o.vigencia.verificada_el != hoy:
        vigencia = ("no_cumple", f"verificada el {o.vigencia.verificada_el}, no hoy")
    else:
        vigencia = ("cumple", f"verificada hoy en {o.vigencia.fuente}")

    if previa is None or (previa.estado == "PREPARADA" and previa.intentos == 0):
        antes = ("cumple", "sin envíos previos")
    elif previa.estado == "PREPARADA":
        antes = ("cumple", f"reintento tras {previa.intentos} envío(s) fallido(s): verificar que no se envió")
    else:
        antes = ("no_cumple", f"ya está {previa.estado}")

    excluida = slug_empresa(o.empresa) in {slug_empresa(e) for e in prio.empresas_excluidas}
    empresa = ("no_cumple", f"{o.empresa} está excluida") if excluida else ("cumple", "no excluida")

    return [
        Condicion(nombre="vigencia_hoy", tipo="vigente", resultado=vigencia[0], detalle=vigencia[1]),
        Condicion(nombre="no_postulada_antes", tipo="vigente", resultado=antes[0], detalle=antes[1]),
        Condicion(nombre="empresa_no_excluida", tipo="vigente", resultado=empresa[0], detalle=empresa[1]),
        _juicio_bool("cv_auditado", juicios.cv_auditado),
        _juicio_bool("respuestas_documentadas", juicios.respuestas_documentadas),
    ]


def _juicio_bool(nombre: str, juicio: JuicioBool | None) -> Condicion:
    if juicio is None:
        return Condicion(nombre=nombre, tipo="vigente", resultado="no_evaluada", detalle="falta el juicio del agente")
    return Condicion(
        nombre=nombre, tipo="vigente", resultado="cumple" if juicio.cumple else "no_cumple", detalle=juicio.evidencia
    )


def evaluar_preferencias(
    o: Oportunidad,
    prio: Priorizacion,
    compuerta: Compuerta,
    todas: list[postulaciones.Postulacion],
    juicios: Juicios,
    nivel: int,
) -> list[Condicion]:
    evaluadores = {
        "seniority": lambda: _seniority(o, juicios.seniority, compuerta.seniority_permitido),
        "ubicacion": lambda: _por_lista(juicios.ubicacion, compuerta.ubicaciones_permitidas, "ubicación"),
        "umbral_match": lambda: _umbral(o, prio),
        "sin_proceso_activo": lambda: _sin_proceso_activo(o, todas),
        "renta_minima": lambda: _renta(o, prio),
    }
    condiciones = []
    for nombre in CONDICIONES_PREFERENCIA:
        if nombre not in compuerta.condiciones_preferencia:
            resultado, detalle = "no_aplica", "desactivada en la configuración"
        elif nivel == 100:
            resultado, detalle = "no_aplica", "no rige al 100 %"
        else:
            resultado, detalle = evaluadores[nombre]()
        condiciones.append(Condicion(nombre=nombre, tipo="preferencia", resultado=resultado, detalle=detalle))
    return condiciones


def _por_lista(juicio: JuicioValor | None, permitidos: list[str], etiqueta: str) -> tuple[str, str]:
    if juicio is None:
        return "no_evaluada", f"falta el juicio de {etiqueta}"
    if not permitidos:
        return "no_cumple", f"la configuración no define {etiqueta} permitida"
    ok = juicio.valor.strip().casefold() in {p.strip().casefold() for p in permitidos}
    return ("cumple" if ok else "no_cumple"), f"{juicio.valor}: {juicio.evidencia}"


def _seniority(o: Oportunidad, juicio: JuicioValor | None, permitidos: list[str]) -> tuple[str, str]:
    resultado, detalle = _por_lista(juicio, permitidos, "seniority")
    mal_fit = o.evaluacion.filtros.get("cargo_mal_fit") if o.evaluacion else None
    if resultado == "cumple" and mal_fit is not None and mal_fit.excluye:
        return "no_cumple", f"cargo de mal fit: {mal_fit.motivo}"
    return resultado, detalle


def _umbral(o: Oportunidad, prio: Priorizacion) -> tuple[str, str]:
    if o.evaluacion is None or set(o.evaluacion.criterios) != set(prio.criterios):
        return "no_evaluada", "la vacante no tiene una evaluación vigente"
    quiero, tengo, _, _ = puntuar(o, prio)
    ok = tengo >= prio.umbrales.tengo and quiero >= prio.umbrales.quiero
    return (
        "cumple" if ok else "no_cumple",
        f"tengo {tengo} (mínimo {prio.umbrales.tengo}), quiero {quiero} (mínimo {prio.umbrales.quiero})",
    )


def _sin_proceso_activo(o: Oportunidad, todas: list[postulaciones.Postulacion]) -> tuple[str, str]:
    activas = [
        p.id
        for p in todas
        if p.id != o.id and slug_empresa(p.empresa) == slug_empresa(o.empresa) and p.estado != "FINALIZADA"
    ]
    return (
        ("no_cumple", f"proceso activo en la empresa: {', '.join(activas)}")
        if activas
        else ("cumple", "sin procesos activos")
    )


def _renta(o: Oportunidad, prio: Priorizacion) -> tuple[str, str]:
    if prio.renta_minima is None:
        return "cumple", "sin renta mínima configurada"
    if (obs := o.renta_observada) is not None:
        minima = obs.minima_equivalente or prio.renta_minima
        # Solo un valor visto sin aviso prueba que el portal acepta la mínima; el resto va a la cola.
        ok = obs.acepta_hasta is not None and obs.acepta_hasta >= minima
        return ("cumple" if ok else "no_cumple"), (
            f"tope observado en el formulario: acepta hasta {obs.acepta_hasta}, avisa desde {obs.avisa_desde} "
            f"({obs.unidad}); mínimo {minima}"
        )
    if o.renta_publicada is None:
        return "cumple", "la publicación no trae renta"
    ok = o.renta_publicada >= prio.renta_minima
    return ("cumple" if ok else "no_cumple"), f"renta publicada {o.renta_publicada}, mínimo {prio.renta_minima}"


def _limites(raiz: Path, compuerta: Compuerta, fuente: FuenteBusqueda, ahora: datetime) -> tuple[list[str], int]:
    """D12 y D4: tope de envíos por día en el portal y pausa entre envíos, sin ráfagas."""
    intentos = postulaciones.intentos_de_envio(raiz)
    hoy = ahora.astimezone().date()
    en_portal = [
        i
        for i in intentos
        if i.portal and i.portal.casefold() == fuente.nombre.casefold() and i.momento.astimezone().date() == hoy
    ]
    limite = getattr(compuerta.limites_diarios, fuente.riesgo)
    bloqueos = []
    if len(en_portal) >= limite:
        bloqueos.append(f"límite diario: {len(en_portal)} de {limite} envíos hoy en {fuente.nombre}")
    espera = 0
    if intentos:
        transcurrido = (ahora - max(i.momento for i in intentos)).total_seconds()
        espera = max(0, math.ceil(compuerta.pausa_minutos * 60 - transcurrido))
        if espera:
            bloqueos.append(f"pausa entre envíos: faltan {espera} s")
    return bloqueos, espera


def preparar_envio(raiz: Path, id_: str, solicitud: SolicitudEnvio, ahora: datetime | None = None) -> Envio:
    """Aplica la compuerta antes de congelar (D12): sin bloqueos y, si el envío no es automático, con aprobación."""
    decision = evaluar(raiz, id_, solicitud.portal, solicitud.juicios, ahora)
    if decision.bloqueos:
        raise AutonomiaError(f"{id_}: no se puede enviar ahora: {'; '.join(decision.bloqueos)}.")
    aprobacion = (solicitud.aprobacion or "").strip()
    if decision.acciones["envio"] == "aprobar" and not aprobacion:
        razon = "; ".join(decision.motivos) or f"el nivel {decision.nivel_efectivo} % pide aprobar el envío"
        raise AutonomiaError(f"{id_}: el envío requiere la aprobación del usuario ({razon}).")
    if decision.acciones["envio"] == "automatico":
        automatica = f"automático: nivel {decision.nivel_efectivo} %, condiciones de la compuerta evaluadas"
        aprobacion = f"{automatica}; {aprobacion}" if aprobacion else automatica
    return Envio(
        autonomia=decision.nivel_configurado,
        aprobacion=aprobacion,
        cv=solicitud.cv,
        respuestas=solicitud.respuestas,
        portal=decision.portal,
        nivel_efectivo=decision.nivel_efectivo,
        acciones=decision.acciones,
        condiciones=decision.condiciones,
    )


_MODO = {"aprobar": "tú apruebas", "aprobar_nuevas": "revisas lo nuevo o sensible", "automatico": "automático"}
_PASO = {"cv": "CV", "respuestas": "respuestas", "formulario": "formulario", "envio": "envío"}
_NOTA_ENVIO = {
    75: "automático solo si cumple las condiciones de preferencia; si no, va a la cola de aprobación",
    100: "automático con solo las reglas siempre vigentes",
}


def vista_previa(nivel: int | None = None) -> list[str]:
    """Qué se hace solo y qué se aprueba en cada nivel (D12), para mostrar antes de cambiarlo."""
    if nivel is not None and nivel not in MATRIZ:
        raise AutonomiaError(f"nivel inválido: {nivel}; usa {tuple(MATRIZ)}.")
    lineas = []
    for n in [nivel] if nivel is not None else list(MATRIZ):
        pasos = {a: _MODO[m] for a, m in MATRIZ[n].items()}
        pasos["envio"] = _NOTA_ENVIO.get(n, pasos["envio"])
        lineas.append(f"{n} %: " + "; ".join(f"{_PASO[a]}: {m}" for a, m in pasos.items()))
    return lineas


def aviso(raiz: Path, nivel: int) -> list[str]:
    """El aviso de D12 antes de activar un nivel: qué acciones externas podrá hacer el agente, dónde y con qué límites."""
    config = cargar_configuracion(raiz)
    compuerta = config.compuerta
    lineas = [f"Con el nivel {nivel} %, {vista_previa(nivel)[0]}", "Envíos por portal:"]
    for fuente in fuentes.cargar(raiz):
        if not fuente.activa:
            continue
        efectivo = nivel_efectivo(nivel, compuerta, fuente)
        excepcion = fuente.nombre.casefold() in {p.casefold() for p in compuerta.siempre_aprobar_portales}
        envio = "con tu aprobación" if excepcion or MATRIZ[efectivo]["envio"] == "aprobar" else "automático"
        limite = getattr(compuerta.limites_diarios, fuente.riesgo)
        lineas.append(
            f"- {fuente.nombre} (riesgo {fuente.riesgo}): nivel {efectivo} %, envío {envio}, hasta {limite} por día"
        )
    lineas.append(f"Pausa mínima entre envíos: {compuerta.pausa_minutos} minutos.")
    if compuerta.siempre_aprobar_empresas:
        lineas.append(f"Siempre con tu aprobación: empresas {', '.join(compuerta.siempre_aprobar_empresas)}.")
    lineas.append(
        "Siguen rigiendo en todo nivel: vigencia verificada hoy, vacante no postulada antes, empresa no excluida, "
        "CV auditado, respuestas documentadas y la pausa ante CAPTCHA, login, 2FA, términos o campos imposibles."
    )
    if nivel == 100 and compuerta.condiciones_preferencia:
        lineas.append(f"Dejan de regir: {', '.join(compuerta.condiciones_preferencia)}.")
    return lineas
