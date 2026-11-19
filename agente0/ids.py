import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit

PARAMETROS_DE_SEGUIMIENTO = {"trk", "trackingid", "refid", "fbclid", "gclid"}


def _slug(texto: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")[:30].strip("-")


def slug_empresa(empresa: str) -> str:
    return _slug(empresa)


def _url_canonica(url: str) -> str:
    partes = urlsplit(url.strip())
    consulta = sorted(
        (k, v)
        for k, v in parse_qsl(partes.query)
        if not k.lower().startswith("utm_") and k.lower() not in PARAMETROS_DE_SEGUIMIENTO
    )
    return f"{partes.scheme.lower()}://{partes.netloc.lower()}{partes.path.rstrip('/')}?{urlencode(consulta)}"


def id_postulacion(empresa: str, cargo: str, url: str) -> str:
    """ID estable: la misma vacante da el mismo ID aunque se detecte otro día o con parámetros de seguimiento."""
    slug_empresa, slug_cargo = _slug(empresa), _slug(cargo)
    if not slug_empresa or not slug_cargo or not url.strip():
        raise ValueError("empresa, cargo y url son obligatorios para generar el ID.")
    huella = hashlib.sha256(_url_canonica(url).encode()).hexdigest()[:6]
    return f"{slug_empresa}-{slug_cargo}-{huella}"
