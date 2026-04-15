import streamlit as st
from supabase import create_client
import pandas as pd
from streamlit_js_eval import get_geolocation

# 1. Configuration de la page (Doit être la première commande Streamlit)
st.set_page_config(page_title="EcoPlein - Ton essence moins chère", layout="centered", page_icon="⛽")

# 2. Connexion à Supabase via les Secrets
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Erreur de configuration : Vérifie tes Secrets Streamlit (URL et KEY).")
    st.stop()

# 3. Titre et Design
st.title("⛽ EcoPlein")
st.subheader("Les stations les plus proches en temps réel")

# 4. Barre latérale (Sidebar) pour les réglages
with st.sidebar:
    st.header("⚙️ Réglages")
    type_carbu = st.selectbox(
        "Quel carburant cherches-tu ?", 
        ["GAZOLE", "E10", "SP98", "SP95", "E85", "GPLC"]
    )
    
    st.write("---")
    st.write("📍 **Géolocalisation**")
    # Tentative de récupération de la position réelle
    loc = get_geolocation()
    
    if loc:
        lat_user = loc['coords']['latitude']
        lon_user = loc['coords']['longitude']
        st.success("Position détectée ✅")
    else:
        st.info("Clique sur 'Autoriser' ou utilise Lille par défaut.")
        # Coordonnées par défaut (Lille)
        lat_user = 50.6292
        lon_user = 3.0573

# 5. Récupération des données via la fonction RPC de Supabase
try:
    # On appelle ta fonction SQL personnalisée
    response = supabase.rpc('get_stations_proches', {
        'user_lat': lat_user,
        'user_lon': lon_user
    }).execute()
    
    data = response.data

    if data:
        df = pd.DataFrame(data)
        
        # On filtre selon le carburant choisi
        df_filtre = df[df['carburant_nom'] == type_carbu].copy()

        if not df_filtre.empty:
            # Calcul pour la carte (Streamlit a besoin des noms 'lat' et 'lon')
            # Note : On récupère les coordonnées d'origine depuis la table via le RPC
            # Si le RPC ne renvoie pas lat/lon, on affiche juste la liste.
            
            # Affichage de la liste des stations
            st.write(f"### Top des stations ({type_carbu})")
            
            for index, row in df_filtre.iterrows():
                with st.expander(f"💰 {row['prix']}€ - {row['nom']}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**Adresse :** {row['adresse']}")
                        st.write(f"**Ville :** {row['ville']}")
                    with col2:
                        st.metric("Distance", f"{round(row['distance_km'], 1)} km")
                    
                    # Petit bouton pour ouvrir dans Google Maps
                    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={row['nom']} {row['adresse']} {row['ville']}"
                    st.link_button("Y aller 🚗", google_maps_url)
        else:
            st.warning(f"Aucun prix récent trouvé pour le {type_carbu} à proximité.")
    else:
        st.info("Recherche de stations en cours...")

except Exception as e:
    st.error(f"Oups ! Une erreur est survenue : {e}")

# Pied de page
st.write("---")
st.caption("Données : prix-carburants.gouv.fr | Mis à jour automatiquement par ton robot GitHub.")
