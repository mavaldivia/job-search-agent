"""Gasto por sesión, etapa y tipo de proceso, desde los transcripts locales de Claude Code."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from statistics import median

SIN_ETAPA = "sin skill"
COMANDOS_DEL_CLI = {"clear", "compact", "config", "context", "effort", "exit", "fast", "model", "resume", "usage"}
COMANDO = re.compile(r"\s*(?:<command-message>.{0,60}?</command-message>\s*)?<command-name>/?([\w:-]+)<", re.S)
# USD de lista por millón de tokens: entrada, escritura de caché 5 min, escritura 1 h, lectura de caché, salida.
# No es lo que descuenta el plan; sirve para comparar procesos y modelos.
PRECIOS = {
    "claude-sonnet-5-5": (2, 2.5, 4, 0.10, 10),
    "claude-opus-5-5": (4, 5, 8, 0.20, 20),
    "claude-haiku-5-5": (0.10, 0.125, 0.20, 0.01, 0.50),
}
HAIKU_SOBRE_100K = (0.50, 0.625, 1, 0.05, 2.50)
# Por la descripción con que se lanza cada subagente.
PROCESOS = (
    ("buscar vacantes (1 fuente)", r"^(Búsqueda|Buscar)"),
    ("sueldos (1 rol y mercado)", r"^(Sueldos|Investigar sueldos)"),
    ("revisar CV", r"Revisor|Revisión|Revisar"),
    ("adaptar CV", r"CV adaptado|Adaptar CV"),
    ("preparar postulación", r"Carril|Preparar post|Reconocer"),
)
CONFIRMACION = re.compile(r"agente0 postulacion confirmar\s+\"?([a-z0-9-]{12,})")
INICIO_POSTULACION = re.compile(r"/cv/|autonomia evaluar|postulacion crear|\"postular\"|\"adaptar_cv\"")


def carpeta_transcripts(repo: Path) -> Path:
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return base / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo))


def costo(uso: dict, modelo: str | None) -> float:
    entrada, lectura = uso.get("input_tokens", 0), uso.get("cache_read_input_tokens", 0)
    escritura = uso.get("cache_creation_input_tokens", 0)
    una_hora = (uso.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
    precio = PRECIOS.get(modelo, PRECIOS["claude-sonnet-5-5"])
    if modelo == "claude-haiku-5-5" and entrada + escritura + lectura > 100_000:
        precio = HAIKU_SOBRE_100K
    cantidades = (entrada, escritura - una_hora, una_hora, lectura, uso.get("output_tokens", 0))
    return sum(c * p for c, p in zip(cantidades, precio)) / 1e6


def _lineas(archivo: Path):
    with archivo.open(encoding="utf-8", errors="ignore") as contenido:
        for linea in contenido:
            try:
                yield json.loads(linea)
            except json.JSONDecodeError:
                continue  # la sesión en curso puede tener la última línea a medio escribir


def _recorrer(archivo: Path, skills: set[str], etapa: str):
    """Devuelve los turnos y, por cada subagente lanzado, la etapa y el turno que lo lanzó."""
    turnos, lanzados, indice = [], {}, {}
    for linea in _lineas(archivo):
        mensaje = linea.get("message")
        if not isinstance(mensaje, dict):
            continue
        contenido = mensaje.get("content")
        if linea.get("type") == "user" and isinstance(contenido, str):
            comando = COMANDO.match(contenido)
            if comando and comando[1] not in COMANDOS_DEL_CLI:
                etapa = comando[1]
        uso = mensaje.get("usage")
        # Un mismo mensaje ocupa una línea por bloque y todas repiten su `usage`.
        if uso and mensaje.get("id") not in indice:
            contexto = sum(
                uso.get(c, 0) for c in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
            )
            if contexto:
                indice[mensaje.get("id")] = len(turnos)
                usd = costo(uso, mensaje.get("model"))
                turnos.append({"etapa": etapa, "usd": usd, "contexto": contexto, "usos": []})
        for bloque in contenido if isinstance(contenido, list) else []:
            if bloque.get("type") != "tool_use":
                continue
            nombre, argumentos = bloque.get("name"), bloque.get("input", {})
            posicion = indice.get(mensaje.get("id"))
            if posicion is not None:
                texto = argumentos.get("command") or json.dumps(argumentos, ensure_ascii=False)
                turnos[posicion]["usos"].append(f"{nombre} {texto}")
            if nombre == "Skill" and argumentos.get("skill") in skills:
                etapa = argumentos["skill"]
            elif nombre in ("Agent", "Task"):
                lanzados[bloque["id"]] = (etapa, posicion)
    return turnos, lanzados


def _leer_sesion(archivo: Path, skills: set[str]):
    turnos, lanzados = _recorrer(archivo, skills, SIN_ETAPA)
    subagentes = []
    for hijo in sorted((archivo.with_suffix("") / "subagents").glob("agent-*.jsonl")):
        meta_archivo = hijo.with_suffix(".meta.json")
        meta = json.loads(meta_archivo.read_text(encoding="utf-8")) if meta_archivo.exists() else {}
        etapa, posicion = lanzados.get(meta.get("toolUseId"), (SIN_ETAPA, None))
        propios, _ = _recorrer(hijo, skills, etapa)
        if propios:
            datos = {"descripcion": meta.get("description", hijo.stem), "etapa": etapa, "turno": posicion}
            subagentes.append({**datos, "turnos": propios, "usd": _total(propios)})
    return turnos, subagentes


def _total(turnos: list) -> float:
    return sum(t["usd"] for t in turnos)


def _resumir(turnos: list) -> dict:
    return {
        "turnos": len(turnos),
        "contexto_max_k": round(max(t["contexto"] for t in turnos) / 1000),
        "usd": round(_total(turnos), 2),
    }


def _sumar_etapas(etapas: dict, turnos: list, subagentes: list) -> None:
    for turno in turnos:
        etapas[turno["etapa"]] = etapas.get(turno["etapa"], 0) + turno["usd"]
    for hijo in subagentes:
        etapas[hijo["etapa"]] = etapas.get(hijo["etapa"], 0) + hijo["usd"]


def _ordenar(etapas: dict) -> dict:
    return {e: round(g, 2) for e, g in sorted(etapas.items(), key=lambda par: -par[1])}


def resumir_sesion(archivo: Path, skills: set[str]) -> dict | None:
    turnos, subagentes = _leer_sesion(archivo, skills)
    if not turnos:
        return None
    etapas: dict[str, float] = {}
    _sumar_etapas(etapas, turnos, subagentes)
    principal, hijos = _total(turnos), sum(s["usd"] for s in subagentes)
    inicio = next(linea["timestamp"] for linea in _lineas(archivo) if linea.get("timestamp"))
    mayores = sorted(subagentes, key=lambda s: -s["usd"])[:3]
    return {
        "sesion": archivo.stem[:8],
        "fecha": datetime.fromisoformat(inicio).astimezone().date().isoformat(),
        "usd": round(principal + hijos, 2),
        "principal": {"contexto_inicial_k": round(turnos[0]["contexto"] / 1000), **_resumir(turnos)},
        "subagentes": {
            "cantidad": len(subagentes),
            "usd": round(hijos, 2),
            "mayores": [{"descripcion": s["descripcion"], **_resumir(s["turnos"])} for s in mayores],
        },
        "etapas_usd": _ordenar(etapas),
    }


def _sesiones(repo: Path) -> tuple[list[Path], set[str]]:
    carpeta = carpeta_transcripts(repo)
    archivos = sorted(carpeta.glob("*.jsonl"), key=lambda a: a.stat().st_mtime, reverse=True)
    if not archivos:
        raise ValueError(f"no hay transcripts en {carpeta}")
    bases = (repo / ".claude", Path.home() / ".claude")
    return archivos, {s.parent.name for base in bases for s in base.glob("skills/*/SKILL.md")}


def ultimas_sesiones(repo: Path, cantidad: int = 1) -> list[dict]:
    """Las sesiones más recientes del proyecto, la última al final."""
    archivos, skills = _sesiones(repo)
    sesiones = []
    for archivo in archivos:
        sesion = resumir_sesion(archivo, skills)
        if sesion:
            sesiones.append(sesion)
        if len(sesiones) == cantidad:
            break
    return sesiones[::-1]


def _postulaciones(turnos: list, subagentes: list, datos: Path):
    """Por cada envío confirmado: portal, preguntas del formulario y gasto desde que se empezó la vacante."""
    corte = 0
    for i, turno in enumerate(turnos):
        for uso in turno["usos"]:
            confirmado = CONFIRMACION.search(uso)
            if not confirmado:
                continue
            id_ = confirmado[1]
            envios = sorted((datos / "postulaciones" / id_ / "instantanea").glob("*/envio.json"))
            if not envios:
                continue
            inicio = next(
                (
                    j
                    for j in range(corte, i + 1)
                    if any(id_ in u and INICIO_POSTULACION.search(u) for u in turnos[j]["usos"])
                ),
                i,
            )
            envio = json.loads(envios[-1].read_text(encoding="utf-8"))
            gasto = _total(turnos[inicio : i + 1])
            gasto += sum(s["usd"] for s in subagentes if s["turno"] is not None and inicio <= s["turno"] <= i)
            yield envio.get("portal") or "sin portal", len(envio.get("respuestas", [])), gasto
            corte = i + 1


def _estadistica(grupos: dict) -> dict:
    return {
        nombre: {
            "n": len(v),
            "usd_mediana": round(median(v), 2),
            "usd_min": round(min(v), 2),
            "usd_max": round(max(v), 2),
        }
        for nombre, v in sorted(grupos.items(), key=lambda par: -sum(par[1]))
    }


def por_proceso(repo: Path, datos: Path | None = None) -> dict:
    """Costo unitario de cada tipo de proceso en todo el historial; las postulaciones piden los datos del usuario."""
    archivos, skills = _sesiones(repo)
    procesos, portales, tamanos, etapas = {}, {}, {}, {}
    for archivo in archivos:
        turnos, subagentes = _leer_sesion(archivo, skills)
        _sumar_etapas(etapas, turnos, subagentes)
        for hijo in subagentes:
            nombre = next((n for n, patron in PROCESOS if re.search(patron, hijo["descripcion"])), "otros")
            procesos.setdefault(nombre, []).append(hijo["usd"])
        for portal, preguntas, gasto in _postulaciones(turnos, subagentes, datos) if datos else ():
            tamano = "sin preguntas" if not preguntas else "1 a 5" if preguntas <= 5 else "6 o más"
            portales.setdefault(portal, []).append(gasto)
            tamanos.setdefault(tamano, []).append(gasto)
    return {
        "subagentes": _estadistica(procesos),
        "postulacion_por_portal": _estadistica(portales),
        "postulacion_por_preguntas": _estadistica(tamanos),
        "etapas_usd": _ordenar(etapas),
    }
