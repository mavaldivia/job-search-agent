"""Guardia de privacidad: lo versionado en este repo público no puede llevar datos del usuario.

Los valores sensibles se sacan de los datos privados (`$AGENTE0_DATOS`) cada vez que se revisa, así que
nada personal vive en el repo. Los hallazgos dicen archivo, línea y tipo, nunca el valor.
"""

import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from agente0.datos import DatosError, datos_dir

LISTA = "privacidad.txt"  # en los datos del usuario: una cadena por línea que nunca debe llegar al repo
MIN_LARGO = 5

RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b")
CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TELEFONO = re.compile(r"\+?56[\s-]?9[\s-]?\d{4}[\s-]?\d{4}")
NACIMIENTO = re.compile(r"nacimiento\D{0,25}(\d{1,4})[-/](\d{1,2})[-/](\d{1,4})", re.IGNORECASE)
DIRECCION = re.compile(r"direcci[oó]n:\s*([^,.\n]+)", re.IGNORECASE)
NOMBRE = re.compile(r"##\s*E1[^\n]*\n+([^\n]+)")
LINKEDIN = re.compile(r"linkedin\.com/in/([\w-]+)", re.IGNORECASE)
GITHUB = re.compile(r"github\.com/([\w-]+)", re.IGNORECASE)
MONTO = re.compile(r"\b\d{1,3}(?:\.\d{3}){1,2}\b|\b\d{6,8}\b")
COMANDO_GIT = re.compile(r"\bgit\s+(?:-\S+\s+)*(?:commit|push)\b")


@dataclass(frozen=True)
class Hallazgo:
    archivo: str
    linea: int
    tipo: str

    def __str__(self) -> str:
        return f"{self.archivo}:{self.linea}: {self.tipo}"


def _textos(raiz: Path, patrones: tuple[str, ...]) -> list[str]:
    return [a.read_text(encoding="utf-8", errors="ignore") for p in patrones for a in sorted(raiz.glob(p))]


def _fechas(d: str, m: str, a: str) -> set[str]:
    anio, dia = (d, a) if len(d) == 4 else (a, d)
    dia, mes = dia.zfill(2), m.zfill(2)
    return {f"{dia}-{mes}-{anio}", f"{anio}-{mes}-{dia}", f"{dia}/{mes}/{anio}"}


def valores_sensibles(raiz: Path) -> dict[str, str]:
    """Valor sensible (en minúsculas) -> tipo, a partir de los datos del usuario."""
    personales = _textos(raiz, ("perfil/*.md", "respuestas/*/*.md"))
    encontrados: dict[str, str] = {}

    def sumar(valor: str, tipo: str) -> None:
        valor = valor.strip().lower()
        if len(valor) >= MIN_LARGO:
            encontrados.setdefault(valor, tipo)

    for texto in personales:
        for rut in RUT.findall(texto):
            limpio = rut.replace(".", "")
            for variante in (rut, limpio, limpio.replace("-", "")):
                sumar(variante, "RUT")
        for correo in CORREO.findall(texto):
            sumar(correo, "correo")
        for telefono in TELEFONO.findall(texto):
            digitos = re.sub(r"\D", "", telefono)
            for variante in (telefono, digitos, f"+{digitos}"):
                sumar(variante, "teléfono")
        for partes in NACIMIENTO.findall(texto):
            for fecha in _fechas(*partes):
                sumar(fecha, "fecha de nacimiento")
        for direccion in DIRECCION.findall(texto):
            sumar(direccion, "dirección")
        for nombre in NOMBRE.findall(texto):
            sumar(nombre, "nombre completo")
        for usuario in LINKEDIN.findall(texto) + GITHUB.findall(texto):
            sumar(usuario, "usuario de LinkedIn o GitHub")
    montos = _textos(raiz, ("respuestas/renta*/*.md", "configuracion/configuracion.json"))
    planilla = raiz / "postulaciones.csv"
    if planilla.exists():
        with planilla.open(encoding="utf-8-sig", newline="") as f:
            montos += [
                f"{fila.get('renta_clp_liquida', '')} {fila.get('renta_declarada', '')}" for fila in csv.DictReader(f)
            ]
    for texto in montos:
        for monto in MONTO.findall(texto):
            sumar(monto, "monto de renta")
            sumar(monto.replace(".", ""), "monto de renta")
    lista = raiz / LISTA
    if lista.exists():
        for linea in lista.read_text(encoding="utf-8").splitlines():
            if linea.strip() and not linea.lstrip().startswith("#"):
                sumar(linea, f"cadena de {LISTA}")
    return encontrados


def _archivos(repo: Path) -> list[Path]:
    salida = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=repo,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return [repo / nombre for nombre in salida.split("\0") if nombre and (repo / nombre).is_file()]


def revisar_texto(texto: str, etiqueta: str, valores: dict[str, str]) -> list[Hallazgo]:
    hallazgos = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        minuscula = linea.lower()
        for tipo in sorted({t for v, t in valores.items() if v in minuscula}):
            hallazgos.append(Hallazgo(etiqueta, numero, tipo))
    return hallazgos


def revisar(repo: Path, raiz: Path) -> list[Hallazgo]:
    """Busca los valores sensibles del usuario en cada archivo versionado o por versionar."""
    valores = valores_sensibles(raiz)
    hallazgos: list[Hallazgo] = []
    for archivo in _archivos(repo):
        try:
            texto = archivo.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hallazgos += revisar_texto(texto, str(archivo.relative_to(repo)), valores)
    return hallazgos


def ejecutar(repo: Path, desde_hook: bool) -> int:
    """`privacidad` revisa el repo; con `--hook` lee el evento de Claude Code y solo actúa ante git commit o push."""
    comando = ""
    if desde_hook:
        try:
            comando = json.load(sys.stdin).get("tool_input", {}).get("command", "")
        except (json.JSONDecodeError, AttributeError):
            return 0
        if not COMANDO_GIT.search(comando):
            return 0
    try:
        raiz = datos_dir()
    except DatosError as error:
        if desde_hook:
            print(f"privacidad: revisión omitida ({error})", file=sys.stderr)
            return 0
        print(f"error: {error}", file=sys.stderr)
        return 1
    hallazgos = revisar(repo, raiz)
    if comando:
        hallazgos += revisar_texto(comando, "(comando de git)", valores_sensibles(raiz))
    if not hallazgos:
        print("privacidad: sin datos del usuario en lo versionado")
        return 0
    print(
        "privacidad: hay datos del usuario en lo que iría al repo público; cámbialos por valores inventados:",
        file=sys.stderr,
    )
    for hallazgo in hallazgos:
        print(f"  {hallazgo}", file=sys.stderr)
    return 2 if desde_hook else 1
