import os
import requests
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def fetch_and_update():
    # L'URL exacte que tu as trouvée
    api_url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/records?limit=50"
    
    response = requests.get(api_url)
    data = response.json()
    results = data.get('results', [])
    
    if not results:
        print("Toujours rien. Voici le JSON reçu pour analyse :", data)
        return

    print(f"Connexion réussie ! Traitement de {len(results)} stations...")
    
    for record in results:
        try:
            # On crée un ID unique (Station + Type de Carburant)
            # Note : On utilise .get() pour éviter que le script plante si un champ manque
            row_id = f"{record.get('id')}-{record.get('carburants_nom')}"
            
            station_data = {
                "id": row_id,
                "nom": record.get('nom', 'Station'),
                "adresse": record.get('adresse', ''),
                "ville": record.get('ville', ''),
                "cp": record.get('cp', ''),
                "latitude": record.get('latitude'),
                "longitude": record.get('longitude'),
                "carburant_nom": record.get('carburants_nom', ''),
                "prix": record.get('prix_valeur'),
                "maj": str(record.get('prix_maj', ''))
            }
            # Envoi vers ta table Supabase
            supabase.table("stations_carburant").upsert(station_data).execute()
        except Exception as e:
            print(f"Erreur sur une ligne : {e}")

    print("Base de données mise à jour avec succès.")

if __name__ == "__main__":
    fetch_and_update()
