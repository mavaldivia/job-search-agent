"""Gasto de tokens por sesión y por etapa, desde los transcripts locales de Claude Code."""

import json
import os
import re
from datetime import datetime
from pathlib import Path

SIN_ETAPA = "sin skill"
COMANDOS_DEL_CLI = {"clear", "compact", "config", "context", "effort", "exit", "fast", "model", "resume", "usage"}
COMANDO = re.compile(r"\s*(?:<command-message>.{0,60}?</command-message>\s*)?<command-name>/?([\w:-]+)<", re.S)


def carpeta_transcripts(repo: Path) -> Path:
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return base / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo))


def equivalente(uso: dict) -> float:
    """Tokens ponderados respecto de uno de entrada; aproximado, no es lo que descuenta el plan."""
    escritura = uso.get("cache_creation_input_tokens", 0)
    una_hora = (uso.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
    return (
        uso.get("input_tokens", 0)
        + 2 * una_hora
        + 1.25 * (escritura - una_hora)
        + 0.1 * uso.get("cache_read_input_tokens", 0)
        + 5 * uso.get("output_tokens", 0)
    )


def _lineas(archivo: Path):
    with archivo.open(encoding="utf-8", errors="ignore") as contenido:
        for linea in contenido:
            try:
                yield json.loads(linea)
            except json.JSONDecodeError:
                continue  # la sesión en curso puede tener la última línea a medio escribir


def _recorrer(archivo: Path, skills: set[str], etapa: str):
    """Devuelve los turnos (etapa, equivalente, contexto) y la etapa en que se lanzó cada subagente."""
    turnos, lanzados, vistos = [], {}, set()
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
        if uso and mensaje.get("id") not in vistos:
            vistos.add(mensaje.get("id"))
            contexto = sum(
                uso.get(c, 0) for c in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
            )
            if contexto:
                turnos.append((etapa, equivalente(uso), contexto))
        for bloque in contenido if isinstance(contenido, list) else []:
            if bloque.get("type") != "tool_use":
                continue
            if bloque.get("name") == "Skill" and bloque["input"].get("skill") in skills:
                etapa = bloque["input"]["skill"]
            elif bloque.get("name") in ("Agent", "Task"):
                lanzados[bloque["id"]] = etapa
    return turnos, lanzados


def _millones(valor: float) -> float:
    return round(valor / 1e6, 2)


def _resumir(turnos: list) -> dict:
    return {
        "turnos": len(turnos),
        "contexto_max_k": round(max(t[2] for t in turnos) / 1000),
        "equivalente_m": _millones(sum(t[1] for t in turnos)),
    }


def resumir_sesion(archivo: Path, skills: set[str]) -> dict | None:
    turnos, lanzados = _recorrer(archivo, skills, SIN_ETAPA)
    if not turnos:
        return None
    etapas: dict[str, float] = {}
    for etapa, gasto, _ in turnos:
        etapas[etapa] = etapas.get(etapa, 0) + gasto
    subagentes = []
    for hijo in sorted((archivo.with_suffix("") / "subagents").glob("agent-*.jsonl")):
        meta_archivo = hijo.with_suffix(".meta.json")
        meta = json.loads(meta_archivo.read_text(encoding="utf-8")) if meta_archivo.exists() else {}
        etapa = lanzados.get(meta.get("toolUseId"), SIN_ETAPA)
        propios, _ = _recorrer(hijo, skills, etapa)
        if not propios:
            continue
        gasto = sum(t[1] for t in propios)
        etapas[etapa] = etapas.get(etapa, 0) + gasto
        subagentes.append((gasto, {"descripcion": meta.get("description", hijo.stem), **_resumir(propios)}))
    principal = sum(t[1] for t in turnos)
    hijos = sum(gasto for gasto, _ in subagentes)
    inicio = next(linea["timestamp"] for linea in _lineas(archivo) if linea.get("timestamp"))
    return {
        "sesion": archivo.stem[:8],
        "fecha": datetime.fromisoformat(inicio).astimezone().date().isoformat(),
        "equivalente_m": _millones(principal + hijos),
        "principal": {"contexto_inicial_k": round(turnos[0][2] / 1000), **_resumir(turnos)},
        "subagentes": {
            "cantidad": len(subagentes),
            "equivalente_m": _millones(hijos),
            "mayores": [datos for _, datos in sorted(subagentes, key=lambda s: -s[0])[:3]],
        },
        "etapas_m": {e: _millones(g) for e, g in sorted(etapas.items(), key=lambda par: -par[1])},
    }


def ultimas_sesiones(repo: Path, cantidad: int = 1) -> list[dict]:
    """Las sesiones más recientes del proyecto, la última al final."""
    carpeta = carpeta_transcripts(repo)
    archivos = sorted(carpeta.glob("*.jsonl"), key=lambda a: a.stat().st_mtime, reverse=True)
    if not archivos:
        raise ValueError(f"no hay transcripts en {carpeta}")
    skills = {
        s.parent.name for base in (repo / ".claude", Path.home() / ".claude") for s in base.glob("skills/*/SKILL.md")
    }
    sesiones = []
    for archivo in archivos:
        sesion = resumir_sesion(archivo, skills)
        if sesion:
            sesiones.append(sesion)
        if len(sesiones) == cantidad:
            break
    return sesiones[::-1]
