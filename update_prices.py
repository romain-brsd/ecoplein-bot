import os
import requests
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def fetch_and_update():
    api_url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records?limit=100"
    response = requests.get(api_url)
    results = response.json().get('results', [])
    
    carburants_map = {
        'gazole': 'Gazole',
        'sp95': 'SP95',
        'sp98': 'SP98',
        'e10': 'E10',
        'e85': 'E85',
        'gplc': 'GPLc'
    }
    
    count = 0
    for record in results:
        station_id = record.get('id')
        # On prépare les infos communes
        base_info = {
            "nom": record.get('nom', 'Station'),
            "adresse": record.get('adresse', ''),
            "ville": record.get('ville', ''),
            "cp": record.get('cp', ''),
            "departement": record.get('departement', ''),
            "region": record.get('region', ''),
            "latitude": record.get('latitude'),
            "longitude": record.get('longitude'),
            "automate_24_24": record.get('horaires_automate_24_24', 'Non'),
            "services": ", ".join(record.get('services_service', [])) if record.get('services_service') else ""
        }
        
        for key_prefix, display_name in carburants_map.items():
            prix = record.get(f'{key_prefix}_prix')
            # On vérifie aussi si le carburant est marqué en rupture
            rupture_type = record.get(f'{key_prefix}_rupture_type')
            
            if prix is not None or rupture_type is not None:
                unique_id = f"{station_id}-{key_prefix}"
                
                station_data = {
                    **base_info,
                    "id": unique_id,
                    "carburant_nom": display_name,
                    "prix": float(prix) if prix else None,
                    "maj": str(record.get(f'{key_prefix}_maj', '')),
                    "en_rupture": True if rupture_type else False
                }
                
                try:
                    supabase.table("stations_carburant").upsert(station_data).execute()
                    count += 1
                except Exception as e:
                    continue

    print(f"Base complétée avec succès : {count} entrées enrichies.")

if __name__ == "__main__":
    fetch_and_update()
