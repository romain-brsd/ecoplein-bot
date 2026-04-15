import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

API_BASE = (
    "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "prix-des-carburants-en-france-flux-instantane-v2/records"
)

BATCH_SIZE = 500
PAGE_SIZE = 100


def to_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def fetch_all_records():
    all_records = []
    offset = 0

    while True:
        url = f"{API_BASE}?limit={PAGE_SIZE}&offset={offset}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        payload = response.json()
        results = payload.get("results", [])

        if not results:
            break

        all_records.extend(results)
        offset += len(results)

        total_count = payload.get("total_count", 0)
        if offset >= total_count:
            break

    return all_records


def build_station_row(record):
    latitude = record.get("latitude")
    longitude = record.get("longitude")
    geom = record.get("geom")

    if not geom and latitude is not None and longitude is not None:
        try:
            geom = {
                "lat": float(latitude) / 100000.0,
                "lon": float(longitude) / 100000.0,
            }
        except Exception:
            geom = None

    return {
        "id": str(record.get("id")),
        "enseigne": record.get("enseigne"),
        "adresse": record.get("adresse", ""),
        "ville": record.get("ville", ""),
        "cp": str(record.get("cp") or ""),
        "pop": record.get("pop") or "R",
        "departement": record.get("departement", ""),
        "region": record.get("region", ""),
        "geom": geom,

        "horaires_jour": record.get("horaires_jour"),
        "horaires_automate_24_24": record.get("horaires_automate_24_24") or "Non",

        "services_service": record.get("services_service") or [],
        "carburants_disponibles": record.get("carburants_disponibles") or [],
        "carburants_indisponibles": record.get("carburants_indisponibles") or [],
        "carburants_rupture_temporaire": record.get("carburants_rupture_temporaire") or "",
        "carburants_rupture_definitive": record.get("carburants_rupture_definitive") or "",

        "gazole_prix": to_float(record.get("gazole_prix")),
        "gazole_maj": record.get("gazole_maj"),
        "sp95_prix": to_float(record.get("sp95_prix")),
        "sp95_maj": record.get("sp95_maj"),
        "sp98_prix": to_float(record.get("sp98_prix")),
        "sp98_maj": record.get("sp98_maj"),
        "e10_prix": to_float(record.get("e10_prix")),
        "e10_maj": record.get("e10_maj"),
        "e85_prix": to_float(record.get("e85_prix")),
        "e85_maj": record.get("e85_maj"),
        "gplc_prix": to_float(record.get("gplc_prix")),
        "gplc_maj": record.get("gplc_maj"),
    }


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def fetch_and_update():
    records = fetch_all_records()
    rows = [build_station_row(record) for record in records if record.get("id")]

    total = 0
    for batch in chunked(rows, BATCH_SIZE):
        supabase.table("stations_carburant").upsert(
            batch,
            on_conflict="id"
        ).execute()
        total += len(batch)

    print(f"Base synchronisée avec succès : {total} stations upsertées.")


if __name__ == "__main__":
    fetch_and_update()
