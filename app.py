import streamlit as st
from supabase import create_client
import pandas as pd
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim # Pour transformer l'adresse en GPS

# Config
st.set_page_config(page_title="EcoPlein", layout="centered", page_icon="⛽")
geolocator = Nominatim(user_agent="ecoplein_app")

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("⛽ EcoPlein")

# --- BARRE LATÉRALE ---
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
            st.success("GPS Connecté")
    else:
        adresse_saisie = st.text_input("Tape ton adresse ou ville :", "Lille, France")
        if adresse_saisie:
            location = geolocator.geocode(adresse_saisie)
            if location:
                lat_user = location.latitude
                lon_user = location.longitude
                st.success(f"C'est parti pour {location.address[:30]}...")

# --- AFFICHAGE PRINCIPAL ---
if lat_user and lon_user:
    # 1. On montre où l'app pense que tu es
    st.info(f"Position définie sur : {lat_user:.4f}, {lon_user:.4f}")
    
    # 2. Appel Supabase
    try:
        response = supabase.rpc('get_stations_proches', {
            'user_lat': lat_user,
            'user_lon': lon_user
        }).execute()
        
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            df_filtre = df[df['carburant_nom'] == type_carbu].copy()
            
            if not df_filtre.empty:
                # Affichage d'une carte de confirmation
                st.write("### Stations autour de toi")
                # On prépare les données pour la carte Streamlit
                map_data = df_filtre[['latitude', 'longitude']].rename(columns={'latitude': 'lat', 'longitude': 'lon'})
                st.map(map_data)

                # Liste détaillée
                for _, row in df_filtre.iterrows():
                    with st.expander(f"💰 {row['prix']}€ - {row['nom']}"):
                        st.write(f"📍 {row['adresse']}, {row['ville']}")
                        st.write(f"📏 Distance : **{round(row['distance_km'], 1)} km**")
                        url_maps = f"https://www.google.com/maps/search/?api=1&query={row['latitude']},{row['longitude']}"
                        st.link_button("Y aller 🚗", url_maps)
            else:
                st.warning("Aucune station trouvée pour ce carburant ici.")
    except Exception as e:
        st.error(f"Erreur technique : {e}")
else:
    st.warning("En attente de ta position...")
