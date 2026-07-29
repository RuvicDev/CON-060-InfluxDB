"""Excepciones propias del conector InfluxDB.

Separan los tipos de fallo que el usuario debe distinguir: configuración
inválida, autenticación, red, y datos (bucket/measurement inexistente,
consulta Flux/InfluxQL inválida).
"""


class InfluxDBConnectorError(Exception):
    """Error base del conector."""


class InfluxDBConfigError(InfluxDBConnectorError):
    """Configuración inválida: falta un campo requerido."""


class InfluxDBAuthError(InfluxDBConnectorError):
    """Token inválido o revocado, o sin permisos suficientes."""


class InfluxDBNetworkError(InfluxDBConnectorError):
    """No se pudo alcanzar el servidor InfluxDB (DNS, timeout, red)."""


class InfluxDBDataError(InfluxDBConnectorError):
    """La operación es válida pero el bucket/measurement no existe, o la
    consulta Flux/InfluxQL es inválida."""
