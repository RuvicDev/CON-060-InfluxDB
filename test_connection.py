"""Prueba de conexión estándar del conector influxdb.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_INFLUXDB_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Verifica las credenciales listando buckets."""
    try:
        from ruvic_influxdb_connector import (
            InfluxDBAuthError,
            InfluxDBClientWrapper,
            InfluxDBDataError,
            InfluxDBNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-influxdb-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-influxdb.git#subdirectory=lib",
        )

    try:
        client = InfluxDBClientWrapper()  # valida config
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except InfluxDBAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except InfluxDBNetworkError as exc:
        return False, f"Error de red: {exc}"
    except InfluxDBDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"
    finally:
        try:
            client.close()
        except Exception:  # noqa: BLE001 - el cierre nunca debe ocultar el resultado real
            pass

    return True, f"Conexión exitosa a {client.config.url}"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
