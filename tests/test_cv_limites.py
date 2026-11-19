import json
import os
import shutil
import subprocess
import sys

import pytest

from agente0.cv_limites import CABECERA, Limites, calibrar, medir, verificar, verificar_texto
from agente0.datos import REPO

TEX = r"""\documentclass[a4paper]{article}
\usepackage{fontspec}
\usepackage{hyperref}
\newcommand{\seccion}[1]{\par\textbf{#1}\par}
\newcommand{\cargo}[3]{\par\textbf{#1} | #2\par #3\par}
\begin{document}
% este comentario no cuenta
\fontsize{19}{22}\selectfont Ana Pérez \href{mailto:a@b.cl}{a@b.cl}\par
\seccion{PERFIL}
Analista con experiencia en datos.\par
\seccion{EXPERIENCIA}
\cargo{Analista}{Acme S.A.}{Enero 2020 -- Actualidad}
\begin{itemize}
\item Primera viñeta con una mejora del 50 \% medida.
\item Segunda viñeta.
\end{itemize}
\end{document}
"""

necesita_tectonic = pytest.mark.skipif(
    any(shutil.which(h) is None for h in ("tectonic", "pdfinfo", "pdffonts", "pdftotext")),
    reason="faltan tectonic o poppler",
)


def test_medir_cuenta_texto_visible_por_seccion_y_bloque():
    medidas = medir(TEX)

    assert list(medidas) == [CABECERA, "PERFIL", "EXPERIENCIA"]
    assert medidas[CABECERA].caracteres == len("Ana Pérez a@b.cl")
    assert medidas["PERFIL"].caracteres == len("Analista con experiencia en datos.")
    experiencia = medidas["EXPERIENCIA"]
    assert experiencia.bloques == 3
    assert experiencia.bloque_max == len("Primera viñeta con una mejora del 50 % medida.")


def test_el_mismo_texto_pasa_sus_propios_limites():
    assert verificar_texto(TEX, calibrar(TEX, paginas=1)) == []


def test_calibrar_da_holgura_sobre_lo_medido():
    medida = medir(TEX)["PERFIL"]
    limite = calibrar(TEX, paginas=1, tolerancia=0.5).secciones["PERFIL"]

    assert limite.caracteres > medida.caracteres


def test_un_bloque_mas_largo_un_bloque_extra_o_una_seccion_nueva_se_rechazan():
    limites = calibrar(TEX, paginas=1, tolerancia=0)

    mas_largo = TEX.replace("Segunda viñeta.", "Segunda viñeta " + "muy larga " * 20)
    assert any("bloque más largo" in p for p in verificar_texto(mas_largo, limites))

    extra = TEX.replace("\\end{itemize}", "\\item Una tercera.\n\\end{itemize}")
    assert any("bloques" in p for p in verificar_texto(extra, limites))

    nueva = TEX.replace("\\end{document}", "\\seccion{HOBBIES}\nLeer.\\par\n\\end{document}")
    assert any("HOBBIES" in p for p in verificar_texto(nueva, limites))


@necesita_tectonic
def test_un_cv_correcto_compila_y_pasa_las_revisiones_del_pdf(tmp_path):
    archivo = tmp_path / "cv.tex"
    archivo.write_text(TEX, encoding="utf-8")

    assert verificar(archivo, calibrar(TEX, paginas=1)) == []


@necesita_tectonic
def test_un_pdf_con_mas_paginas_de_las_esperadas_se_rechaza(tmp_path):
    archivo = tmp_path / "cv.tex"
    archivo.write_text(TEX.replace("\\end{itemize}", "\\end{itemize}\\newpage Otra página.\\newpage Y otra."), encoding="utf-8")

    problemas = verificar(archivo, calibrar(TEX, paginas=1, tolerancia=10))

    assert any("3 páginas" in p for p in problemas)


CAJAS = r"""\documentclass{article}
\usepackage[paperwidth=576pt,paperheight=768pt,margin=0pt]{geometry}
\usepackage{fontspec}
\usepackage{tikz}
\makeatletter
\newcommand{\bloque}[6]{%
  \node[anchor=north west,inner sep=0,outer sep=0,text width=\dimexpr#4pt*3/4\relax,align=flush left,font=\normalfont]
    (blq#1) at (#2,-#3) {#6};%
  \pgfpointdiff{\pgfpointanchor{blq#1}{south}}{\pgfpointanchor{blq#1}{north}}%
  \dimen0=\pgf@y
  \ifdim\dimen0>\dimexpr#5pt*3/4\relax
    \PackageWarning{cv}{Desborde del bloque #1: \the\dimen0}%
  \fi
}
\makeatother
\begin{document}
\begin{tikzpicture}[remember picture,overlay,x=.75pt,y=.75pt,shift={(current page.north west)}]
\bloque{perfil}{20}{20}{200}{ALTO}{Texto de prueba que se ajusta solo dentro de su caja de ancho fijo y que ocupa varias líneas para medir el alto del bloque.}
\end{tikzpicture}
\null
\end{document}
"""


@necesita_tectonic
def test_un_bloque_de_caja_que_no_cabe_en_su_alto_se_rechaza(tmp_path):
    limites = Limites(paginas=1)
    archivo = tmp_path / "visual.tex"

    archivo.write_text(CAJAS.replace("ALTO", "200"), encoding="utf-8")
    assert verificar(archivo, limites) == []

    archivo.write_text(CAJAS.replace("ALTO", "20"), encoding="utf-8")
    assert verificar(archivo, limites) == ["el bloque perfil no cabe en su alto"]


def test_cli_calibra_y_verifica_un_cv(tmp_path):
    archivo = tmp_path / "cv.tex"
    archivo.write_text(TEX, encoding="utf-8")
    env = {k: v for k, v in os.environ.items()}

    calibracion = subprocess.run(
        [sys.executable, "-m", "agente0", "cv", "calibrar", str(archivo), "1"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    assert calibracion.returncode == 0
    assert json.loads(calibracion.stdout)["paginas"] == 1

    uso = subprocess.run([sys.executable, "-m", "agente0", "cv", "calibrar"], cwd=REPO, capture_output=True, text=True)
    assert uso.returncode == 2
