"""Cliente para consultar series de tiempo en InfluxDB.

Capacidades:
- execute_query():                ejecutar una consulta Flux o InfluxQL.
- list_buckets_or_measurements():  listar los buckets del proyecto, o las
                                    measurements dentro de un bucket.
- get_measurement_fields():        consultar los campos (fields) y tags
                                    de una measurement específica.

Este conector es de solo lectura por diseño — no expone ninguna
operación de escritura (no hay `write_query` ni similar), solo consulta.

Autenticación: token de InfluxDB, enviado en el header `Authorization:
Token <token>`. Las credenciales SIEMPRE provienen de variables de
entorno RUVIC_INFLUXDB_* (ver config.InfluxDBConfig.from_env). Prohibido
hardcodearlas.
"""

from __future__ import annotations

from typing import Any

import requests
from influxdb_client import InfluxDBClient
from influxdb_client.rest import ApiException
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from .config import InfluxDBConfig
from .exceptions import (
    InfluxDBAuthError,
    InfluxDBDataError,
    InfluxDBNetworkError,
)
from .logging_utils import get_logger


class InfluxDBClientWrapper:
    """Cliente de InfluxDB autenticado con un token.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_INFLUXDB_* (comportamiento
            estándar en el runtime de la plataforma).

    Ejemplo:
        >>> client = InfluxDBClientWrapper()  # lee RUVIC_INFLUXDB_* del entorno
        >>> client.list_buckets_or_measurements()
        [{'name': 'sensores', 'id': '...'}, ...]
    """

    def __init__(self, config: InfluxDBConfig | None = None) -> None:
        self.config = config or InfluxDBConfig.from_env()
        self._logger = get_logger()
        self._client: InfluxDBClient | None = None

    # ------------------------------------------------------------------ #
    # Cliente subyacente (creado una sola vez, perezosamente)
    # ------------------------------------------------------------------ #

    def _get_client(self) -> InfluxDBClient:
        if self._client is not None:
            return self._client
        self._client = InfluxDBClient(
            url=self.config.url,
            token=self.config.token,
            org=self.config.org,
            timeout=self.config.timeout * 1000,  # esta librería espera milisegundos
        )
        return self._client

    def _translate_error(self, exc: Exception, context: str) -> Exception:
        if isinstance(exc, ApiException):
            if exc.status in (401, 403):
                return InfluxDBAuthError(
                    f"Permisos insuficientes en {context} (HTTP {exc.status}): {exc.reason}"
                )
            if exc.status == 404:
                return InfluxDBDataError(f"No encontrado en {context}: {exc.reason}")
            return InfluxDBDataError(f"Error de InfluxDB en {context} (HTTP {exc.status}): {exc.reason}")
        if isinstance(exc, (Timeout, RequestsConnectionError)):
            return InfluxDBNetworkError(f"Error de red en {context}: {exc}")
        return InfluxDBNetworkError(f"Error inesperado en {context}: {exc}")

    # ------------------------------------------------------------------ #
    # Ping / prueba de conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica las credenciales listando buckets (barato)."""
        self.list_buckets_or_measurements()
        self._logger.info("Ping exitoso a InfluxDB (%s)", self.config.url)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: ejecutar una consulta Flux o InfluxQL
    # ------------------------------------------------------------------ #

    def execute_query(
        self,
        query: str,
        language: str | None = None,
        bucket: str | None = None,
        max_results: int = 1000,
    ) -> dict[str, Any]:
        """Ejecuta una consulta Flux o InfluxQL.

        Args:
            query: la consulta a ejecutar, en el lenguaje indicado.
            language: "flux" o "influxql". Si se omite, usa el lenguaje
                por defecto configurado en el conector.
            bucket: requerido solo en modo InfluxQL (equivalente al
                "database" de InfluxDB 1.x). En modo Flux, el bucket se
                especifica dentro de la propia consulta.
            max_results: máximo de filas a retornar (default 1000).

        Returns:
            Dict con "rows" (lista de dicts) y "count".

        Ejemplo:
            >>> client.execute_query('from(bucket:"sensores") |> range(start:-1h) |> limit(n:5)')
            {'rows': [...], 'count': 5}
        """
        if not query or not query.strip():
            raise InfluxDBDataError("La consulta no puede estar vacía.")

        lang = (language or self.config.query_language).lower()
        if lang == "flux":
            return self._execute_flux(query, max_results)
        if lang == "influxql":
            effective_bucket = bucket or self.config.default_bucket
            if not effective_bucket:
                raise InfluxDBDataError(
                    "El modo InfluxQL requiere indicar 'bucket' (equivalente a 'database' "
                    "en InfluxDB 1.x), o configurar un bucket por defecto en el conector."
                )
            return self._execute_influxql(query, effective_bucket, max_results)
        raise InfluxDBDataError(f"Lenguaje de consulta inválido: {lang!r}. Usa 'flux' o 'influxql'.")

    def _execute_flux(self, query: str, max_results: int) -> dict[str, Any]:
        client = self._get_client()
        try:
            tables = client.query_api().query(query, org=self.config.org)
        except ApiException as exc:
            raise self._translate_error(exc, "execute_query (Flux)") from exc
        except (Timeout, RequestsConnectionError) as exc:
            raise self._translate_error(exc, "execute_query (Flux)") from exc

        rows: list[dict[str, Any]] = []
        for table in tables:
            for record in table.records:
                rows.append(dict(record.values))
                if len(rows) >= max_results:
                    break
            if len(rows) >= max_results:
                break

        self._logger.info("execute_query (Flux): %d fila(s)", len(rows))
        return {"rows": rows, "count": len(rows)}

    def _execute_influxql(self, query: str, bucket: str, max_results: int) -> dict[str, Any]:
        url = f"{self.config.url}/query"
        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Token {self.config.token}"},
                params={"db": bucket, "q": query},
                timeout=self.config.timeout,
            )
        except Timeout as exc:
            raise InfluxDBNetworkError(f"Tiempo de espera agotado en {url}.") from exc
        except RequestsConnectionError as exc:
            raise InfluxDBNetworkError(f"No se pudo conectar a {url}: {exc}") from exc
        except RequestException as exc:
            raise InfluxDBNetworkError(f"Error de red: {exc}") from exc

        if resp.status_code != 200:
            if resp.status_code in (401, 403):
                raise InfluxDBAuthError(f"Permisos insuficientes en InfluxQL: {resp.text[:300]}")
            raise InfluxDBDataError(f"Error de InfluxQL (HTTP {resp.status_code}): {resp.text[:300]}")

        payload = resp.json()
        rows: list[dict[str, Any]] = []
        for result in payload.get("results", []):
            for series in result.get("series", []):
                columns = series.get("columns", [])
                for values in series.get("values", []):
                    rows.append(dict(zip(columns, values)))
                    if len(rows) >= max_results:
                        break
                if len(rows) >= max_results:
                    break
            if len(rows) >= max_results:
                break

        self._logger.info("execute_query (InfluxQL): %d fila(s)", len(rows))
        return {"rows": rows, "count": len(rows)}

    # ------------------------------------------------------------------ #
    # Capacidad 2: listar buckets o measurements
    # ------------------------------------------------------------------ #

    def list_buckets_or_measurements(self, bucket: str | None = None) -> list[Any]:
        """Lista los buckets del proyecto, o las measurements dentro de un bucket.

        Args:
            bucket: si se omite, lista los buckets del proyecto. Si se
                indica, lista las measurements dentro de ese bucket.

        Returns:
            Si `bucket` es None: lista de dicts con "name" e "id".
            Si `bucket` se indica: lista de nombres de measurement (str).

        Ejemplo:
            >>> client.list_buckets_or_measurements()
            [{'name': 'sensores', 'id': '...'}]
            >>> client.list_buckets_or_measurements("sensores")
            ['temperatura', 'humedad']
        """
        client = self._get_client()
        if bucket is None:
            try:
                result = client.buckets_api().find_buckets()
            except ApiException as exc:
                raise self._translate_error(exc, "list_buckets_or_measurements") from exc
            buckets = [{"name": b.name, "id": b.id} for b in (result.buckets or [])]
            self._logger.info("list_buckets_or_measurements: %d bucket(s)", len(buckets))
            return buckets

        query = f'import "influxdata/influxdb/schema"\nschema.measurements(bucket: "{bucket}")'
        try:
            tables = client.query_api().query(query, org=self.config.org)
        except ApiException as exc:
            raise self._translate_error(exc, f"list_buckets_or_measurements({bucket!r})") from exc

        measurements = [record.get_value() for table in tables for record in table.records]
        self._logger.info(
            "list_buckets_or_measurements(%s): %d measurement(s)", bucket, len(measurements)
        )
        return measurements

    # ------------------------------------------------------------------ #
    # Capacidad 3: consultar el esquema de una measurement
    # ------------------------------------------------------------------ #

    def get_measurement_fields(self, bucket: str, measurement: str) -> dict[str, list[str]]:
        """Consulta los campos (fields) y tags de una measurement.

        Args:
            bucket: bucket donde vive la measurement.
            measurement: nombre de la measurement a inspeccionar.

        Returns:
            Dict con "fields" (nombres de campos numéricos/valores) y
            "tags" (nombres de etiquetas indexadas).

        Ejemplo:
            >>> client.get_measurement_fields("sensores", "temperatura")
            {'fields': ['valor'], 'tags': ['ubicacion', 'sensor_id']}
        """
        if not bucket or not measurement:
            raise InfluxDBDataError("bucket y measurement no pueden estar vacíos.")

        client = self._get_client()
        fields_query = (
            'import "influxdata/influxdb/schema"\n'
            f'schema.measurementFieldKeys(bucket: "{bucket}", measurement: "{measurement}")'
        )
        tags_query = (
            'import "influxdata/influxdb/schema"\n'
            f'schema.measurementTagKeys(bucket: "{bucket}", measurement: "{measurement}")'
        )
        try:
            field_tables = client.query_api().query(fields_query, org=self.config.org)
            tag_tables = client.query_api().query(tags_query, org=self.config.org)
        except ApiException as exc:
            raise self._translate_error(exc, f"get_measurement_fields({measurement!r})") from exc

        fields = [r.get_value() for t in field_tables for r in t.records]
        tags = [
            r.get_value() for t in tag_tables for r in t.records
            if r.get_value() and not r.get_value().startswith("_")
        ]

        result = {"fields": fields, "tags": tags}
        self._logger.info("get_measurement_fields %s: %s", measurement, result)
        return result

    def close(self) -> None:
        """Cierra la conexión subyacente."""
        if self._client is not None:
            self._client.close()
            self._client = None
