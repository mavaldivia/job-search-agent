import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

CARPETA = "respuestas"
ARCHIVO_REVISIONES = "respuestas/revisiones.jsonl"
_SLUG = r"[a-z0-9]+(-[a-z0-9]+)*"
_ARCHIVO = re.compile(r"v(\d{3,})_(\d{4}-\d{2}-\d{2})\.md")

Tipo = Literal["hecho", "narrativa"]
Autor = Literal["usuario", "agente"]
Resultado = Literal["aprobada", "rechazada", "editada"]


class RespuestaError(ValueError):
    pass


class SinRespuestaConfirmada(RespuestaError):
    pass


class Respuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Categoría, variante, versión y fecha salen de la ruta y del nombre del archivo, que ya los fijan.
    categoria: str = Field(pattern=_SLUG)
    variante: str | None = Field(default=None, pattern=_SLUG)
    version: int = Field(ge=1)
    fecha: date
    tipo: Tipo
    aprobada_por: Autor
    fuente: str = ""
    notas: str = ""
    texto: str = Field(min_length=1)

    @computed_field
    @property
    def id(self) -> str:
        return f"{self.categoria}.{self.variante}" if self.variante else self.categoria

    @computed_field
    @property
    def etiqueta_version(self) -> str:
        return f"v{self.version:03d}"

    @field_validator("fuente", "notas")
    @classmethod
    def _una_linea(cls, valor: str) -> str:
        # El encabezado es de una clave por línea: un salto de línea lo corrompería.
        if "\n" in valor:
            raise ValueError("debe ir en una sola línea.")
        return valor.strip()

    @model_validator(mode="after")
    def _agente_con_fuente(self) -> "Respuesta":
        if self.aprobada_por == "agente" and not self.fuente:
            raise ValueError("una respuesta guardada por el agente exige fuente (datos confirmados del perfil).")
        return self


class RevisionRespuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha: date = Field(default_factory=date.today)
    id: str
    version: int = Field(ge=1)
    resultado: Resultado


def _carpeta(raiz: Path, categoria: str, variante: str | None = None) -> Path:
    for parte in (categoria, variante):
        if parte is not None and not re.fullmatch(_SLUG, parte):
            raise RespuestaError(f"nombre inválido: {parte!r} (minúsculas, números y guiones).")
    carpeta = raiz / CARPETA / categoria
    return carpeta / variante if variante else carpeta


def _leer(archivo: Path, categoria: str, variante: str | None) -> Respuesta:
    nombre = _ARCHIVO.fullmatch(archivo.name)
    lineas = archivo.read_text(encoding="utf-8").split("\n")
    if lineas[0] != "---" or "---" not in lineas[1:]:
        raise RespuestaError(f"{archivo}: falta el encabezado.")
    fin = lineas.index("---", 1)
    campos = dict(linea.partition(": ")[::2] for linea in lineas[1:fin] if linea.strip())
    return Respuesta(
        categoria=categoria,
        variante=variante,
        version=int(nombre[1]),
        fecha=date.fromisoformat(nombre[2]),
        texto="\n".join(lineas[fin + 1 :]).strip(),
        **campos,
    )


def _serializar(respuesta: Respuesta) -> str:
    encabezado = [f"tipo: {respuesta.tipo}", f"aprobada_por: {respuesta.aprobada_por}"]
    if respuesta.fuente:
        encabezado.append(f"fuente: {respuesta.fuente}")
    if respuesta.notas:
        encabezado.append(f"notas: {respuesta.notas}")
    return "\n".join(["---", *encabezado, "---", "", respuesta.texto, ""])


def versiones(raiz: Path, categoria: str, variante: str | None = None) -> list[Respuesta]:
    """Historial completo de un ID, de la más antigua a la más nueva, incluidas las rechazadas."""
    carpeta = _carpeta(raiz, categoria, variante)
    if not carpeta.is_dir():
        return []
    archivos = [a for a in carpeta.iterdir() if a.is_file() and _ARCHIVO.fullmatch(a.name)]
    return sorted((_leer(a, categoria, variante) for a in archivos), key=lambda r: r.version)


def _revisiones(raiz: Path) -> list[RevisionRespuesta]:
    archivo = raiz / ARCHIVO_REVISIONES
    if not archivo.exists():
        return []
    lineas = archivo.read_text(encoding="utf-8").splitlines()
    return [RevisionRespuesta.model_validate_json(linea) for linea in lineas if linea.strip()]


def _anotar(raiz: Path, revision: RevisionRespuesta) -> None:
    archivo = raiz / ARCHIVO_REVISIONES
    archivo.parent.mkdir(parents=True, exist_ok=True)
    with archivo.open("a", encoding="utf-8") as salida:
        salida.write(revision.model_dump_json() + "\n")


def _vigente_exacta(raiz: Path, categoria: str, variante: str | None) -> Respuesta | None:
    rechazadas = {(r.id, r.version) for r in _revisiones(raiz) if r.resultado == "rechazada"}
    candidatas = [r for r in versiones(raiz, categoria, variante) if (r.id, r.version) not in rechazadas]
    return candidatas[-1] if candidatas else None


def vigente(raiz: Path, categoria: str, variante: str | None = None) -> Respuesta:
    """Variante de la familia de la vacante; si no hay, la general; si no hay ninguna, hay que pedir intervención."""
    for candidata in ([variante, None] if variante else [None]):
        respuesta = _vigente_exacta(raiz, categoria, candidata)
        if respuesta:
            return respuesta
    familia = f" (variante {variante})" if variante else ""
    raise SinRespuestaConfirmada(
        f"{categoria}{familia}: sin respuesta confirmada; pedir intervención o, si el perfil la respalda, guardarla."
    )


def _ids(raiz: Path) -> list[tuple[str, str | None]]:
    """Cada categoría y cada una de sus variantes, como (categoria, variante)."""
    base = raiz / CARPETA
    if not base.is_dir():
        return []
    resultado: list[tuple[str, str | None]] = []
    for categoria in sorted(p for p in base.iterdir() if p.is_dir()):
        familias = sorted(p.name for p in categoria.iterdir() if p.is_dir())
        resultado += [(categoria.name, variante) for variante in (None, *familias)]
    return resultado


def listar(raiz: Path) -> list[Respuesta]:
    """Respuesta vigente de cada categoría y de cada una de sus variantes."""
    vigentes = (_vigente_exacta(raiz, categoria, variante) for categoria, variante in _ids(raiz))
    return [respuesta for respuesta in vigentes if respuesta]


def _sin_revisar(raiz: Path, respuestas: list[Respuesta]) -> list[Respuesta]:
    revisadas = {(r.id, r.version) for r in _revisiones(raiz)}
    return [r for r in respuestas if r.aprobada_por == "agente" and (r.id, r.version) not in revisadas]


def pendientes(raiz: Path) -> list[Respuesta]:
    """Versiones que guardó el agente y el usuario aún no revisa."""
    return [r for categoria, variante in _ids(raiz) for r in _sin_revisar(raiz, versiones(raiz, categoria, variante))]


def guardar(
    raiz: Path,
    categoria: str,
    texto: str,
    tipo: Tipo,
    aprobada_por: Autor,
    variante: str | None = None,
    fuente: str = "",
    notas: str = "",
    fecha: date | None = None,
) -> Respuesta:
    """Crea la versión siguiente de un ID. Las versiones son inmutables: editar es guardar otra."""
    previas = versiones(raiz, categoria, variante)
    if previas and previas[-1].tipo != tipo:
        raise RespuestaError(f"{previas[-1].id} es de tipo {previas[-1].tipo}: no se mezcla con {tipo}.")
    if previas and aprobada_por == "agente":
        raise RespuestaError(f"{previas[-1].id} ya tiene versiones: el agente no edita, lo hace el usuario (D9).")
    respuesta = Respuesta(
        categoria=categoria,
        variante=variante,
        version=previas[-1].version + 1 if previas else 1,
        fecha=fecha or date.today(),
        tipo=tipo,
        aprobada_por=aprobada_por,
        fuente=fuente,
        notas=notas,
        texto=texto.strip(),
    )
    carpeta = _carpeta(raiz, categoria, variante)
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"{respuesta.etiqueta_version}_{respuesta.fecha.isoformat()}.md"
    with archivo.open("x", encoding="utf-8") as salida:
        salida.write(_serializar(respuesta))
    archivo.chmod(0o444)
    if aprobada_por == "usuario":
        # Una versión del usuario reemplaza a las del agente que seguían sin revisar.
        for anterior in _sin_revisar(raiz, previas):
            _anotar(raiz, RevisionRespuesta(id=anterior.id, version=anterior.version, resultado="editada"))
    return respuesta


def revisar(raiz: Path, categoria: str, version: int, resultado: Resultado, variante: str | None = None) -> None:
    """El usuario aprueba o rechaza una versión del agente; una rechazada deja de ser vigente."""
    if resultado == "editada":
        raise RespuestaError("`editada` se registra sola al guardar la versión del usuario.")
    objetivo = next((r for r in versiones(raiz, categoria, variante) if r.version == version), None)
    if objetivo is None:
        raise RespuestaError(f"no existe la versión {version} de {categoria}.")
    if not _sin_revisar(raiz, [objetivo]):
        raise RespuestaError(f"{objetivo.id} v{version:03d} no es una versión del agente pendiente de revisión.")
    _anotar(raiz, RevisionRespuesta(id=objetivo.id, version=version, resultado=resultado))
