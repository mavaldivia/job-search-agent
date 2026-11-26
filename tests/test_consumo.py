import json

import pytest

from agente0.__main__ import main
from agente0.consumo import carpeta_transcripts, ultimas_sesiones
from agente0.datos import REPO

# Transcripts inventados: solo reproducen la forma de los de Claude Code.
USO = {
    "input_tokens": 1000,
    "cache_creation_input_tokens": 100_000,
    "cache_creation": {"ephemeral_1h_input_tokens": 100_000},
    "cache_read_input_tokens": 1_000_000,
    "output_tokens": 19_800,
}  # equivalente: 1.000 + 200.000 + 100.000 + 99.000 = 0,4 M


def _turno(id_, *bloques):
    return {
        "type": "assistant",
        "timestamp": "2030-01-15T15:00:00.000Z",
        "message": {"id": id_, "usage": USO, "content": list(bloques)},
    }


def _escribir(archivo, lineas):
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text("".join(json.dumps(linea) + "\n" for linea in lineas), encoding="utf-8")


@pytest.fixture
def transcripts(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    carpeta = carpeta_transcripts(REPO)
    comando = "<command-message>todos</command-message>\n<command-name>/todos</command-name>"
    skill = {"type": "tool_use", "id": "a", "name": "Skill", "input": {"skill": "postular"}}
    ajena = {"type": "tool_use", "id": "b", "name": "Skill", "input": {"skill": "ayuda-del-navegador"}}
    agente = {"type": "tool_use", "id": "c", "name": "Agent", "input": {}}
    _escribir(
        carpeta / "sesion01.jsonl",
        [
            {"type": "user", "timestamp": "2030-01-15T15:00:00.000Z", "message": {"content": comando}},
            _turno("m1", {"type": "text", "text": "hola"}),
            _turno("m1", skill),
            _turno("m2", ajena),
            _turno("m3", agente),
        ],
    )
    hijo = carpeta / "sesion01" / "subagents" / "agent-1.jsonl"
    _escribir(hijo, [_turno("s1")])
    hijo.with_suffix(".meta.json").write_text(json.dumps({"toolUseId": "c", "description": "vacante inventada"}))
    return carpeta


def test_gasto_por_sesion_y_etapa(transcripts):
    [sesion] = ultimas_sesiones(REPO)
    assert sesion["fecha"] == "2030-01-15"
    assert sesion["principal"]["turnos"] == 3
    assert sesion["principal"]["contexto_max_k"] == 1101
    assert sesion["equivalente_m"] == 1.6
    assert sesion["etapas_m"] == {"postular": 1.2, "todos": 0.4}
    assert sesion["subagentes"]["mayores"][0]["descripcion"] == "vacante inventada"


def test_comando(transcripts, capsys):
    assert main(["consumo"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["sesion"] == "sesion01"
    assert main(["consumo", "0"]) == 2


def test_sin_transcripts(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert main(["consumo"]) == 1
    assert "no hay transcripts" in capsys.readouterr().err
