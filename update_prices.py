import os
import requests
from supabase import create_client

# Connexion sécurisée via les secrets que tu viens de remplir
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def fetch_and_update():
    # On récupère les 100 dernières mises à jour du gouvernement
    api_url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-carburants-en-france-flux-instantane-v2/records?limit=100"
    
    try:
        response = requests.get(api_url)
        data = response.json()

        for record in data.get('results', []):
            # Préparation des données pour Supabase
            station_data = {
                "id": f"{record.get('id')}-{record.get('carburants_nom')}",
                "nom": record.get('nom'),
                "adresse": record.get('adresse'),
                "ville": record.get('ville'),
                "cp": record.get('cp'),
                "latitude": record.get('latitude'),
                "longitude": record.get('longitude'),
                "carburant_nom": record.get('carburants_nom'),
                "prix": record.get('prix_valeur'),
                "maj": record.get('prix_maj')
            }
            
            # Envoi : si la station existe déjà, il met à jour le prix, sinon il la crée
            supabase.table("stations_carburant").upsert(station_data).execute()

        print(f"Succès : {len(data.get('results', []))} stations traitées.")
    except Exception as e:
        print(f"Erreur : {e}")

if __name__ == "__main__":
    fetch_and_update()
