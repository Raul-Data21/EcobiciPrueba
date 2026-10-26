"""Toma UNA foto de station_status de Ecobici y la guarda comprimida.

Uso:  python muestreador_status.py            (una foto)
      python muestreador_status.py --loop 10  (una foto cada 10 min, para correrlo en la laptop)

Salida: data/status/AAAA-MM-DD/HHMM.csv.gz   (hora de CDMX; un archivo por foto)
Se guarda un archivo por foto (y no uno por dia) para que git no guarde
copias repetidas de un archivo que crece.
"""
import argparse, csv, gzip, json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://gbfs.mex.lyftbikes.com/gbfs/en/station_status.json"  # confirmar que es el mismo feed de su station_status.json
CAMPOS = ["num_bikes_available", "num_docks_available", "num_bikes_disabled",
          "num_docks_disabled", "is_installed", "is_renting", "is_returning", "last_reported"]
OUT = Path("data/status")
TZ = ZoneInfo("America/Mexico_City")


def descargar(url=URL, intentos=3):
    for i in range(intentos):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            print(f"intento {i+1} fallo: {e}", file=sys.stderr)
            time.sleep(5)
    raise SystemExit("no se pudo descargar el feed")


def guardar(data, ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    local = ahora.astimezone(TZ)
    estaciones = data["data"]["stations"]
    if len(estaciones) < 100:  # feed raro/vacio: no guardar basura
        raise SystemExit(f"solo {len(estaciones)} estaciones; no guardo")
    carpeta = OUT / local.strftime("%Y-%m-%d")
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / (local.strftime("%H%M") + ".csv.gz")
    with gzip.open(ruta, "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_local", "ts_utc", "station_id"] + CAMPOS)
        for s in estaciones:
            w.writerow([local.strftime("%Y-%m-%d %H:%M:%S"), ahora.strftime("%Y-%m-%d %H:%M:%S"),
                        s["station_id"]] + [s.get(c, "") for c in CAMPOS])
    print(f"{ruta}  ({len(estaciones)} estaciones; feed last_updated={data.get('last_updated')})")
    return ruta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0, help="minutos entre fotos (0 = una sola)")
    a = ap.parse_args()
    while True:
        guardar(descargar())
        if not a.loop:
            break
        time.sleep(a.loop * 60)
