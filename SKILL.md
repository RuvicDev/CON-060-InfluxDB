---
name: influxdb
description: "Usa la librería ruvic_influxdb_connector para consultar series de tiempo en InfluxDB (solo lectura) - ejecutar una consulta Flux o InfluxQL (execute_query), listar los buckets del proyecto o las measurements dentro de un bucket (list_buckets_or_measurements), y consultar los campos/tags de una measurement (get_measurement_fields). Úsala cuando el usuario pida consultar métricas, series de tiempo, o explorar qué datos existen en InfluxDB. Conector de solo lectura, sin operaciones de escritura."
triggers:
- influxdb
- flux
- influxql
- series de tiempo
- buckets influxdb
---

# Conector InfluxDB (ruvic_influxdb_connector)

Librería Python de **solo lectura** para consultar InfluxDB, autenticada con un token de API. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-influxdb.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `influxdb` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_INFLUXDB_URL` / `..._TOKEN` / `..._ORG` | Siempre requeridas |
| `RUVIC_INFLUXDB_DEFAULT_BUCKET` | (opcional) requerido para InfluxQL si no se pasa `bucket` en cada llamada |
| `RUVIC_INFLUXDB_QUERY_LANGUAGE` | (opcional) `"flux"` o `"influxql"`, default `"flux"` |
| `RUVIC_INFLUXDB_REQUEST_TIMEOUT` | (opcional) segundos, default `30` |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

El código generado **NUNCA** usa nombres de variable con segmento de alias (`_DEFAULT_`, `_TEST_`, `_PRODUCCION_`, etc.) — siempre `{ENV_PREFIX}{CAMPO}` tal cual, sin importar cuántas instancias de este conector haya configuradas. Esto aplica salvo que dichos nombres aparezcan explícitamente en una sección autogenerada al final de este skill.

## Conexión (siempre igual)

```python
from ruvic_influxdb_connector import InfluxDBClientWrapper

client = InfluxDBClientWrapper()  # lee RUVIC_INFLUXDB_* del entorno automáticamente
```

## Capacidad 1 — Ejecutar una consulta Flux o InfluxQL

```python
# Flux (por defecto)
resultado = client.execute_query('''
    from(bucket: "sensores")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "temperatura")
    |> limit(n: 20)
''')
for fila in resultado["rows"]:
    print(fila)

# InfluxQL (requiere indicar el bucket)
resultado = client.execute_query(
    "SELECT * FROM temperatura WHERE time > now() - 1h LIMIT 20",
    language="influxql", bucket="sensores",
)
```

## Capacidad 2 — Listar buckets o measurements

```python
buckets = client.list_buckets_or_measurements()
for b in buckets:
    print(b["name"])

measurements = client.list_buckets_or_measurements("sensores")
print(measurements)  # ['temperatura', 'humedad', ...]
```

## Capacidad 3 — Consultar el esquema de una measurement

```python
esquema = client.get_measurement_fields("sensores", "temperatura")
print(f"Campos: {esquema['fields']}, Tags: {esquema['tags']}")
```

## Manejo de errores

```python
from ruvic_influxdb_connector import InfluxDBAuthError, InfluxDBNetworkError, InfluxDBDataError

try:
    client.execute_query('from(bucket:"sensores") |> range(start:-1h)')
except InfluxDBAuthError:
    print("Token inválido o permisos insuficientes — revisa la configuración del conector")
except InfluxDBNetworkError:
    print("No se pudo conectar a InfluxDB — revisa la red")
except InfluxDBDataError as e:
    print(f"Error de datos: {e}")  # ej. bucket no encontrado, consulta inválida
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_INFLUXDB_*` (el constructor de `InfluxDBClientWrapper` ya lo hace).
2. Nunca imprimas `RUVIC_INFLUXDB_TOKEN` en logs ni en la salida.
3. Usa `range()` en las consultas Flux para acotar el intervalo de tiempo — evita traer todo el histórico sin necesidad.
4. Si vas a ejecutar InfluxQL, siempre indica `bucket` explícitamente (o confirma que hay uno por defecto configurado).
5. No intentes escribir datos: este conector no tiene ninguna operación de escritura.
