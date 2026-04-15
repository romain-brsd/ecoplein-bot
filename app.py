import streamlit as st
from supabase import create_client
import pandas as pd
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import time

# Config
st.set_page_config(page_title="EcoPlein", layout="centered", page_icon="⛽")

# On change l'User_Agent pour éviter d'être bloqué par le Geocoder
geolocator = Nominatim(user_agent="mon_application_carburant_unique_123")

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("⛽ EcoPlein")

with st.sidebar:
    st.header("⚙️ Configuration")
    type_carbu = st.selectbox("Carburant", ["GAZOLE", "E10", "SP98", "SP95", "E85", "GPLC"])
    st.write("---")
    mode_pos = st.radio("Définir ma position par :", ["📍 GPS (Auto)", "🔍 Adresse (Manuel)"])
    
    lat_user, lon_user = None, None

    if mode_pos == "📍 GPS (Auto)":
        loc = get_geolocation()
        if loc:
            lat_user = loc['coords']['latitude']
            lon_user = loc['coords']['longitude']
    else:
        adresse_saisie = st.text_input("Tape ton adresse ou ville :", "")
        if adresse_saisie:
            try:
                # On ajoute un petit délai pour ne pas brusquer le service gratuit
                time.sleep(1) 
                location = geolocator.geocode(adresse_saisie)
                if location:
                    lat_user = location.latitude
                    lon_user = location.longitude
                    st.success(f"Position : {location.address[:30]}...")
            except:
                st.error("Service de recherche indisponible. Réessaie dans 2 secondes.")

if lat_user and lon_user:
    st.info(f"📍 Position définie sur Lille ({lat_user:.4f}, {lon_user:.4f})")
    
    try:
        response = supabase.rpc('get_stations_proches', {
            'user_lat': lat_user,
            'user_lon': lon_user
        }).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # ASTUCE TEMPORAIRE : Si tes données sont "NC", on les affiche quand même
            # pour que tu puisses voir que la géolocalisation fonctionne.
            mask = (df['carburant_nom'] == type_carbu) | (df['carburant_nom'] == "NC")
            df_filtre = df[mask].copy()
            
            if not df_filtre.empty:
                st.write(f"### Stations proches")
                
                # Carte
                map_data = df_filtre[['latitude', 'longitude']].rename(columns={'latitude': 'lat', 'longitude': 'lon'})
                st.map(map_data)

                for _, row in df_filtre.iterrows():
                    nom_affiche = row['nom'] if row['carburant_nom'] != "NC" else f"{row['nom']} (Carburant NC)"
                    with st.expander(f"💰 {row['prix']}€ - {nom_affiche}"):
                        st.write(f"📍 {row['adresse']}, {row['ville']}")
                        st.write(f"📏 Distance : **{round(row['distance_km'], 1)} km**")
            else:
                st.warning("Aucune station trouvée ici.")
    except Exception as e:
        st.error(f"Erreur Supabase : {e}")
