# conector-influxdb

Conector Ruvic para InfluxDB: ejecutar consultas Flux/InfluxQL, listar buckets/measurements, y consultar el esquema de una measurement.

## Capacidades

`execute_query` (Flux o InfluxQL), `list_buckets_or_measurements`, `get_measurement_fields`. Conector de **solo lectura** — no tiene ninguna operación de escritura.

## Instalación

Requiere **Python ≥ 3.10**.

```bash
pip install git+https://github.com/tu-org/conector-influxdb.git#subdirectory=lib
```

Para desarrollo local (editable, en un venv limpio):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_INFLUXDB_URL` / `..._TOKEN` / `..._ORG` | Sí | Datos de conexión (InfluxDB 2.x/Cloud) |
| `RUVIC_INFLUXDB_DEFAULT_BUCKET` | No | Requerido para InfluxQL si no se indica bucket en cada llamada |
| `RUVIC_INFLUXDB_QUERY_LANGUAGE` | No | `"flux"` (default) o `"influxql"` |
| `RUVIC_INFLUXDB_REQUEST_TIMEOUT` | No | Segundos, default `30` |

## Permisos / prerrequisitos en InfluxDB

1. En InfluxDB Cloud/OSS 2.x: **Load Data → API Tokens → Generate API Token**.
2. Elige **"Read"** (no "Read/Write") y acótalo a los buckets específicos que el agente necesita consultar, en vez de un token "All Access".
3. Copia el token generado.

## Cómo correr las pruebas locales

Puedes usar **InfluxDB Cloud** (nivel gratuito) o un contenedor Docker local:

```bash
docker run -d -p 8086:8086 influxdb:2

# Configura la instancia inicial en http://localhost:8086 (usuario, org, bucket)
export RUVIC_INFLUXDB_URL=http://localhost:8086
export RUVIC_INFLUXDB_TOKEN=tu_token
export RUVIC_INFLUXDB_ORG=tu_org

python test_connection.py
python validate_local.py
```

Prueba también el caso de error:

```bash
RUVIC_INFLUXDB_TOKEN=invalido python test_connection.py
# FALLO: Autenticación fallida: ...
```

## Limitaciones conocidas

- No escribe datos — es un conector exclusivamente de consulta.
- El modo InfluxQL requiere indicar explícitamente el `bucket` (equivalente al "database" de InfluxDB 1.x) en cada llamada, o tener uno configurado por defecto.
- `get_measurement_fields` usa el paquete Flux `influxdata/influxdb/schema` — solo funciona en modo Flux (InfluxDB 2.x), no tiene equivalente directo en InfluxQL puro.

## Notas de integración

- El paquete pip es `ruvic-influxdb-connector`; el import name es `ruvic_influxdb_connector`.
- Dependencias externas: `influxdb-client` (librería oficial, para Flux) y `requests` (para el endpoint de compatibilidad InfluxQL).
- Ver `SKILL.md` para los ejemplos de uso que consume el agente.
