import os
import requests
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def fetch_and_update():
    # On prend 100 stations pour tester
    api_url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-carburants-en-france-flux-instantane-v2/records?limit=100"
    
    response = requests.get(api_url)
    if response.status_code != 200:
        print("Erreur API Gouvernement")
        return

    data = response.json()
    results = data.get('results', [])
    
    for record in results:
        # On vérifie que les données essentielles existent
        if record.get('id') and record.get('prix_valeur'):
            station_data = {
                "id": f"{record.get('id')}-{record.get('carburants_nom')}",
                "nom": record.get('nom', 'Inconnu'),
                "adresse": record.get('adresse', ''),
                "ville": record.get('ville', ''),
                "cp": record.get('cp', ''),
                "latitude": record.get('latitude'),
                "longitude": record.get('longitude'),
                "carburant_nom": record.get('carburants_nom', 'Inconnu'),
                "prix": float(record.get('prix_valeur')),
                "maj": str(record.get('prix_maj'))
            }
            # Envoi vers Supabase
            supabase.table("stations_carburant").upsert(station_data).execute()

    print(f"Terminé ! {len(results)} lignes envoyées.")

if __name__ == "__main__":
    fetch_and_update()
