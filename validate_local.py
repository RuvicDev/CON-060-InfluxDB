"""Validación local del conector influxdb: ejercita las 3 capacidades.

Requiere las env vars RUVIC_INFLUXDB_* exportadas contra un servidor
InfluxDB real (puedes usar InfluxDB Cloud Free Tier, o un contenedor
Docker local con "docker run -p 8086:8086 influxdb:2").
"""

from ruvic_influxdb_connector import InfluxDBClientWrapper, setup_logging

setup_logging("INFO")
client = InfluxDBClientWrapper()

print("== 1. Listar buckets ==")
buckets = client.list_buckets_or_measurements()
print(f"  {len(buckets)} bucket(s)")
for b in buckets[:5]:
    print(f"    {b}")

if buckets:
    primer_bucket = buckets[0]["name"]
    print(f"== 2. Listar measurements del bucket '{primer_bucket}' ==")
    measurements = client.list_buckets_or_measurements(primer_bucket)
    print(f"  {len(measurements)} measurement(s): {measurements}")

    if measurements:
        print(f"== 3. Consultar el esquema de '{measurements[0]}' ==")
        esquema = client.get_measurement_fields(primer_bucket, measurements[0])
        print(f"  {esquema}")

        print(f"== 4. Ejecutar una consulta Flux simple ==")
        resultado = client.execute_query(
            f'from(bucket: "{primer_bucket}") |> range(start: -30d) |> limit(n: 5)'
        )
        print(f"  {resultado['count']} fila(s)")
else:
    print("== 2, 3, 4. Se omiten (no hay buckets con datos en este proyecto) ==")

client.close()
print("\nValidación completa.")
