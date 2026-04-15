import os
import requests
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def fetch_and_update():
    api_url = api_url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-carburants-en-france-flux-instantane-v2/records?limit=100&order_by=prix_maj%20desc"
    response = requests.get(api_url)
    data = response.json()
    results = data.get('results', [])
    
    print(f"Tentative d'envoi de {len(results)} stations...")
    
    for record in results:
        try:
            station_data = {
                "id": f"{record.get('id')}-{record.get('carburants_nom')}",
                "nom": record.get('nom', 'Inconnu'),
                "adresse": record.get('adresse', ''),
                "ville": record.get('ville', ''),
                "cp": record.get('cp', ''),
                "latitude": float(record.get('latitude')) if record.get('latitude') else None,
                "longitude": float(record.get('longitude')) if record.get('longitude') else None,
                "carburant_nom": record.get('carburants_nom', 'Inconnu'),
                "prix": float(record.get('prix_valeur')) if record.get('prix_valeur') else 0,
                "maj": str(record.get('prix_maj'))
            }
            supabase.table("stations_carburant").upsert(station_data).execute()
        except Exception as e:
            print(f"Erreur sur une ligne : {e}")

    print("Processus terminé.")

if __name__ == "__main__":
    fetch_and_update()
