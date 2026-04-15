import streamlit as st
from supabase import create_client
import pandas as pd

# Configuration de la page
st.set_page_config(page_title="Fuel Finder", layout="centered")

# Initialisation de la connexion Supabase via les Secrets de Streamlit
# On utilise st.secrets pour ne pas afficher tes clés en public
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Les secrets SUPABASE_URL et SUPABASE_KEY ne sont pas configurés.")
    st.stop()

st.title("⛽ Fuel Finder")
st.write("Trouve l'essence la moins chère autour de toi.")

# Barre latérale pour les filtres
with st.sidebar:
    st.header("Réglages")
    type_carbu = st.selectbox("Choisis ton carburant", ["GAZOLE", "E10", "SP98", "SP95", "E85", "GPLC"])
    # Coordonnées par défaut (Lille)
    lat_user = st.number_input("Ta Latitude", value=50.6292, format="%.4f")
    lon_user = st.number_input("Ta Longitude", value=3.0573, format="%.4f")

# Appel de la fonction SQL que tu as créée (RPC)
try:
    # On appelle la fonction SQL "get_stations_proches"
    response = supabase.rpc('get_stations_proches', {
        'user_lat': lat_user,
        'user_lon': lon_user
    }).execute()
    
    df = pd.DataFrame(response.data)

    if not df.empty:
        # Filtrer par type de carburant choisi
        df_filtre = df[df['carburant_nom'] == type_carbu]

        if not df_filtre.empty:
            # 1. Affichage de la carte
            # Streamlit a besoin de colonnes nommées 'latitude' et 'longitude'
            # On va donc renommer ou récupérer les bonnes infos
            st.subheader(f"Stations proches ({type_carbu})")
            
            # Pour la carte, on doit refaire une petite requête pour avoir les coordonnées précises
            # (Ou on modifie la fonction RPC, mais restons simple pour l'instant)
            st.map(df_filtre[['latitude', 'longitude']] if 'latitude' in df_filtre else None)

            # 2. Affichage des prix sous forme de liste
            for _, row in df_filtre.iterrows():
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{row['nom']}**")
                        st.caption(f"{row['adresse']}, {row['ville']}")
                    with col2:
                        st.metric("Prix", f"{row['prix']} €")
                    st.divider()
        else:
            st.warning(f"Pas de {type_carbu} trouvé à proximité immédiate.")
    else:
        st.info("Aucune donnée trouvée. Vérifie que ton robot GitHub a bien rempli Supabase !")

except Exception as e:
    st.error(f"Erreur lors de la récupération des données : {e}")
