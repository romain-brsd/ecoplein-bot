import streamlit as st
from supabase import create_client
import pandas as pd
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import time

# Config
st.set_page_config(page_title="EcoPlein", layout="centered", page_icon="⛽")
geolocator = Nominatim(user_agent="ecoplein_final_app")

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("⛽ EcoPlein")

with st.sidebar:
    st.header("⚙️ Configuration")
    # Liste simplifiée pour correspondre à ta base
    type_carbu = st.selectbox("Carburant", ["Gazole", "E10", "SP98", "SP95", "E85", "GPLC"])
    st.write("---")
    mode_pos = st.radio("Ma position :", ["📍 GPS (Auto)", "🔍 Adresse (Manuel)"])
    
    lat_user, lon_user = None, None

    if mode_pos == "📍 GPS (Auto)":
        loc = get_geolocation()
        if loc:
            lat_user = loc['coords']['latitude']
            lon_user = loc['coords']['longitude']
            st.success("GPS Connecté")
    else:
        adresse_saisie = st.text_input("Tape ton adresse (ex: Lille) :", "")
        if adresse_saisie:
            try:
                location = geolocator.geocode(adresse_saisie)
                if location:
                    lat_user = location.latitude
                    lon_user = location.longitude
                    st.success(f"Position : {location.address[:20]}...")
            except:
                st.error("Service indisponible, réessaie.")

# --- AFFICHAGE ---
if lat_user and lon_user:
    try:
        # Appel du RPC (la fonction SQL de calcul de distance)
        response = supabase.rpc('get_stations_proches', {
            'user_lat': lat_user,
            'user_lon': lon_user
        }).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # FILTRE : On compare en mettant tout en minuscule pour éviter les erreurs
            df_filtre = df[df['carburant_nom'].str.lower() == type_carbu.lower()].copy()
            
            if not df_filtre.empty:
                st.write(f"### Top stations {type_carbu} à proximité")
                
                # Carte
                map_data = df_filtre[['latitude', 'longitude']].rename(columns={'latitude': 'lat', 'longitude': 'lon'})
                st.map(map_data)

                # Liste
                for _, row in df_filtre.iterrows():
                    with st.expander(f"💰 {row['prix']}€ - {row['nom']}"):
                        st.write(f"📍 {row['adresse']}, {row['ville']}")
                        st.write(f"📏 Distance : **{round(row['distance_km'], 1)} km**")
                        # Lien Google Maps corrigé avec les coordonnées divisées
                        url_maps = f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}"
                        st.link_button("Y aller 🚗", url_maps)
            else:
                st.warning(f"Aucune station n'a de {type_carbu} actuellement autour de Lille.")
        else:
            st.info("Aucune donnée reçue de la base.")
            
    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.warning("Position non détectée. Utilise la recherche manuelle à gauche.")
