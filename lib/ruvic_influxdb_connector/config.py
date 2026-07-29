"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_INFLUXDB_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_INFLUXDB_"

_VALID_LANGUAGES = ("flux", "influxql")


@dataclass(frozen=True)
class InfluxDBConfig:
    """Parámetros de conexión a un servidor InfluxDB."""

    url: str
    token: str
    org: str
    default_bucket: str = ""
    query_language: str = "flux"
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "InfluxDBConfig":
        """Construye la configuración desde las variables RUVIC_INFLUXDB_*.

        Raises:
            ValueError: si falta URL, TOKEN u ORG, o QUERY_LANGUAGE no es válido.
        """
        url = os.environ.get(f"{ENV_PREFIX}URL", "").strip()
        token = os.environ.get(f"{ENV_PREFIX}TOKEN", "").strip()
        org = os.environ.get(f"{ENV_PREFIX}ORG", "").strip()

        missing = [
            name for name, val in (
                (f"{ENV_PREFIX}URL", url),
                (f"{ENV_PREFIX}TOKEN", token),
                (f"{ENV_PREFIX}ORG", org),
            ) if not val
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector influxdb: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )

        query_language = os.environ.get(f"{ENV_PREFIX}QUERY_LANGUAGE", "flux").strip().lower()
        if query_language not in _VALID_LANGUAGES:
            raise ValueError(
                f"{ENV_PREFIX}QUERY_LANGUAGE inválido: {query_language!r}. "
                f"Debe ser uno de: {', '.join(_VALID_LANGUAGES)}."
            )

        return cls(
            url=url.rstrip("/"),
            token=token,
            org=org,
            default_bucket=os.environ.get(f"{ENV_PREFIX}DEFAULT_BUCKET", "").strip(),
            query_language=query_language,
            timeout=int(os.environ.get(f"{ENV_PREFIX}REQUEST_TIMEOUT", "30")),
        )
