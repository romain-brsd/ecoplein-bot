import os
import requests
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def fetch_and_update():
    # L'URL que tu as trouvée
    api_url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records?limit=10"
    
    response = requests.get(api_url)
    results = response.json().get('results', [])
    
    if results:
        # On affiche les clés du premier résultat pour vérifier les noms
        print(f"Clés disponibles dans les données : {results[0].keys()}")
    
    for record in results:
        # Ici on adapte selon les noms réels envoyés par l'API
        station_id = record.get('id', 'inconnu')
        carbu_type = record.get('carburants_nom', 'NC')
        
        station_data = {
            "id": f"{station_id}-{carbu_type}",
            "nom": record.get('nom', 'Station'),
            "adresse": record.get('adresse', ''),
            "ville": record.get('ville', ''),
            "cp": record.get('cp', ''),
            "latitude": record.get('latitude'),
            "longitude": record.get('longitude'),
            "carburant_nom": carbu_type,
            "prix": record.get('prix_valeur'), # Si c'est vide, on vérifiera le nom de la clé
            "maj": str(record.get('prix_maj', ''))
        }
        supabase.table("stations_carburant").upsert(station_data).execute()

    print("Mise à jour terminée.")

if __name__ == "__main__":
    fetch_and_update()
