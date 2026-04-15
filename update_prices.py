# ─────────────────────────────────────────────────────────────────────────────
# EcoPlein — update_prices.py
# Script GitHub Actions : synchronise l'API gouvernementale → Supabase
# Env vars requises : SUPABASE_URL, SUPABASE_KEY
# ─────────────────────────────────────────────────────────────────────────────
import os
import requests
from supabase import create_client

# ── Connexion ─────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase     = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Config API ────────────────────────────────────────────────────────────────
API_BASE   = (
    "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
    "prix-des-carburants-en-france-flux-instantane-v2/records"
)
PAGE_SIZE  = 100   # max autorisé par l'API
BATCH_SIZE = 500   # lignes par upsert Supabase


# ── Helpers ───────────────────────────────────────────────────────────────────
def to_float(value):
    """Convertit une valeur en float, retourne None si impossible."""
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def fetch_all_records() -> list[dict]:
    """Télécharge toutes les stations avec pagination automatique."""
    all_records = []
    offset      = 0
    total       = None

    while True:
        resp = requests.get(
            f"{API_BASE}?limit={PAGE_SIZE}&offset={offset}",
            timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()

        if total is None:
            total = payload.get("total_count", 0)
            print(f"📊 {total} stations disponibles dans l'API")

        results = payload.get("results", [])
        if not results:
            break

        all_records.extend(results)
        offset += len(results)
        print(f"  ↳ {offset}/{total} téléchargées…", end="\r")

        if offset >= total:
            break

    print(f"\n✅ {len(all_records)} enregistrements récupérés")
    return all_records


def build_row(record: dict):
    """
    Transforme un enregistrement API en ligne pour stations_carburant.
    Retourne None si l'enregistrement n'a pas d'id valide.
    """
    station_id = record.get("id")
    if not station_id:
        return None

    # ── Coordonnées ──────────────────────────────────────────────────────────
    # L'API v2 fournit un champ geom déjà en WGS84
    # Sinon on convertit latitude/longitude (x100000 → degrés décimaux)
    geom = record.get("geom")
    if not geom:
        lat_raw = record.get("latitude")
        lon_raw = record.get("longitude")
        if lat_raw is not None and lon_raw is not None:
            try:
                geom = {
                    "lat": float(lat_raw) / 100000.0,
                    "lon": float(lon_raw) / 100000.0,
                }
            except (TypeError, ValueError):
                geom = None

    return {
        "id":       str(station_id),

        # ── Infos station ─────────────────────────────────────────────────
        "enseigne": record.get("enseigne"),
        "adresse":  record.get("adresse", ""),
        "ville":    record.get("ville", ""),
        "cp":       str(record.get("cp") or ""),
        "pop":      record.get("pop") or "R",
        "geom":     geom,

        # ── Localisation ─────────────────────────────────────────────────
        "departement": record.get("departement", ""),
        "region":      record.get("region", ""),

        # ── Horaires ─────────────────────────────────────────────────────
        "horaires_jour":           record.get("horaires_jour"),
        "horaires_automate_24_24": record.get("horaires_automate_24_24") or "Non",

        # ── Services ─────────────────────────────────────────────────────
        "services_service": record.get("services_service") or [],

        # ── Disponibilités ───────────────────────────────────────────────
        "carburants_disponibles":         record.get("carburants_disponibles")  or [],
        "carburants_indisponibles":       record.get("carburants_indisponibles") or [],
        "carburants_rupture_temporaire":  record.get("carburants_rupture_temporaire") or "",
        "carburants_rupture_definitive":  record.get("carburants_rupture_definitive") or "",

        # ── Prix par carburant ────────────────────────────────────────────
        "gazole_prix": to_float(record.get("gazole_prix")),
        "gazole_maj":  record.get("gazole_maj"),
        "sp95_prix":   to_float(record.get("sp95_prix")),
        "sp95_maj":    record.get("sp95_maj"),
        "sp98_prix":   to_float(record.get("sp98_prix")),
        "sp98_maj":    record.get("sp98_maj"),
        "e10_prix":    to_float(record.get("e10_prix")),
        "e10_maj":     record.get("e10_maj"),
        "e85_prix":    to_float(record.get("e85_prix")),
        "e85_maj":     record.get("e85_maj"),
        "gplc_prix":   to_float(record.get("gplc_prix")),
        "gplc_maj":    record.get("gplc_maj"),
    }


def chunked(lst: list, size: int):
    """Découpe une liste en sous-listes de taille max `size`."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


# ── Main ──────────────────────────────────────────────────────────────────────
def fetch_and_update():
    # 1. Téléchargement
    records = fetch_all_records()

    # 2. Transformation
    rows = [build_row(r) for r in records]
    rows = [r for r in rows if r is not None]

    # 3. Déduplication par id (évite l'erreur PostgreSQL ON CONFLICT)
    #    L'API peut retourner la même station sur deux pages consécutives
    rows = list({row["id"]: row for row in rows}.values())
    print(f"🔑 {len(rows)} stations uniques après déduplication")

    # 4. Upsert par batches
    total = 0
    for i, batch in enumerate(chunked(rows, BATCH_SIZE)):
        # Déduplication intra-batch par sécurité supplémentaire
        batch = list({row["id"]: row for row in batch}.values())

        supabase.table("stations_carburant").upsert(
            batch,
            on_conflict="id"
        ).execute()

        total += len(batch)
        print(f"  ✅ Batch {i+1} — {total}/{len(rows)} stations upsertées", end="\r")

    print(f"\n🎉 Synchronisation terminée : {total} stations dans Supabase")


if __name__ == "__main__":
    fetch_and_update()
