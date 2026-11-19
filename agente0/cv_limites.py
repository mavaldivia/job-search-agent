"""Límites de tamaño por bloque de un CV en LaTeX y su verificación (decisión B3, 2026-11-18).

La plantilla marca las secciones con `\\seccion{TÍTULO}` y los bloques son viñetas (`\\item`) o
párrafos. Los límites se calibran con el CV base; una variante por vacante debe caber en ellos
con la misma fuente y los mismos márgenes, así que solo cambia el largo del texto.
"""

import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict

TOLERANCIA = 0.05
CABECERA = "(cabecera)"

_COMENTARIO = re.compile(r"(?<!\\)%.*")
_SECCION = re.compile(r"\\seccion\{([^}]*)\}")
_CORTES = re.compile(
    r"\\item\b|\\par\b|\\begin\{itemize\}|\\end\{itemize\}|\\cargo\b|\\newpage|\\vspace\{[^}]*\}|\n\s*\n"
)
# Argumentos que no son texto visible: contarlos inflaría los caracteres.
_ARGS_SIN_TEXTO = re.compile(r"\\fontsize\{[^}]*\}\{[^}]*\}|\\(?:vspace|hspace|color)\*?\{[^}]*\}|\\href\{[^}]*\}")


class Medida(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caracteres: int
    bloque_max: int
    bloques: int


class Limites(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paginas: int
    # Vacío en una plantilla de cajas de alto fijo (la visual): el límite de cada bloque va en la plantilla.
    secciones: dict[str, Medida] = {}


def _limpiar(trozo: str) -> str:
    trozo = _ARGS_SIN_TEXTO.sub(" ", trozo)
    trozo = re.sub(r"\\[a-zA-Z]+\*?", " ", trozo)
    trozo = re.sub(r"\\(.)", r"\1", trozo)
    trozo = trozo.replace("{", " ").replace("}", " ")
    return re.sub(r"\s+", " ", trozo).strip()


def _medir_trozo(trozo: str) -> Medida:
    bloques = [texto for texto in (_limpiar(parte) for parte in _CORTES.split(trozo)) if texto]
    return Medida(
        caracteres=sum(len(b) for b in bloques), bloque_max=max((len(b) for b in bloques), default=0), bloques=len(bloques)
    )


def medir(tex: str) -> dict[str, Medida]:
    cuerpo = tex.split("\\begin{document}", 1)[-1].split("\\end{document}", 1)[0]
    cuerpo = _COMENTARIO.sub("", cuerpo)
    partes = _SECCION.split(cuerpo)
    medidas = {CABECERA: _medir_trozo(partes[0])}
    for nombre, trozo in zip(partes[1::2], partes[2::2]):
        medidas[_limpiar(nombre)] = _medir_trozo(trozo)
    return medidas


def calibrar(tex: str, paginas: int, tolerancia: float = TOLERANCIA) -> Limites:
    def con_holgura(valor: int) -> int:
        return math.ceil(valor * (1 + tolerancia))

    return Limites(
        paginas=paginas,
        secciones={
            nombre: Medida(
                caracteres=con_holgura(m.caracteres), bloque_max=con_holgura(m.bloque_max), bloques=con_holgura(m.bloques)
            )
            for nombre, m in medir(tex).items()
        },
    )


def verificar_texto(tex: str, limites: Limites) -> list[str]:
    if not limites.secciones:
        return []
    problemas = []
    for nombre, medida in medir(tex).items():
        limite = limites.secciones.get(nombre)
        if limite is None:
            problemas.append(f"{nombre}: sección que no está en el CV base")
            continue
        for campo, etiqueta in (("caracteres", "caracteres"), ("bloque_max", "bloque más largo"), ("bloques", "bloques")):
            if getattr(medida, campo) > getattr(limite, campo):
                problemas.append(f"{nombre}: {etiqueta} {getattr(medida, campo)} > límite {getattr(limite, campo)}")
    return problemas


def verificar_pdf(tex_path: Path, paginas: int) -> list[str]:
    herramientas = ("tectonic", "pdfinfo", "pdffonts", "pdftotext")
    faltan = [h for h in herramientas if shutil.which(h) is None]
    if faltan:
        return [f"faltan herramientas para compilar y revisar el PDF: {', '.join(faltan)}"]
    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / tex_path.name
        shutil.copy(tex_path, copia)
        # Sin --print, tectonic no muestra los avisos de paquetes ni los Overfull.
        compilacion = subprocess.run(["tectonic", "--print", copia.name], cwd=tmp, capture_output=True, text=True)
        salida = compilacion.stdout + compilacion.stderr
        if compilacion.returncode != 0:
            errores = [linea for linea in salida.splitlines() if linea.startswith("error:")]
            return ["no compila: " + (errores or salida.strip().splitlines() or ["sin detalle"])[-1]]
        pdf = copia.with_suffix(".pdf")
        problemas = []
        if "Overfull" in salida:
            problemas.append("hay líneas que desbordan el margen (Overfull \\hbox)")
        for nombre in dict.fromkeys(re.findall(r"Desborde del bloque (\S+?):", salida)):
            problemas.append(f"el bloque {nombre} no cabe en su alto")
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        hojas = int(re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE).group(1))
        if hojas != paginas:
            problemas.append(f"el PDF tiene {hojas} páginas y se esperaban {paginas}")
        fuentes = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout.splitlines()[2:]
        for linea in fuentes:
            if not re.search(r"\s(yes)\s+(?:yes|no)\s+(yes)\s+\d+\s+\d+\s*$", linea):
                problemas.append(f"fuente sin incrustar o sin mapa Unicode: {linea.split()[0]}")
        texto = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
        if re.search("[\ufb00-\ufb06\ufffd]", texto):
            problemas.append("el texto extraído trae ligaduras (U+FB00 a U+FB06) o caracteres de reemplazo")
        return problemas


def verificar(tex_path: Path, limites: Limites) -> list[str]:
    problemas = verificar_texto(tex_path.read_text(encoding="utf-8"), limites)
    return problemas + verificar_pdf(tex_path, limites.paginas)


def cargar_limites(ruta: Path) -> Limites:
    return Limites.model_validate(json.loads(ruta.read_text(encoding="utf-8")))
