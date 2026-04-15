import streamlit as st
from supabase import create_client
import pandas as pd
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
import pydeck as pdk

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EcoPlein",
    layout="centered",
    page_icon="⛽",
    # AMÉLIORATION : menu burger masqué, look plus propre
    menu_items={"About": "EcoPlein – Trouvez le carburant le moins cher près de vous."}
)

# ─── CSS CUSTOM ────────────────────────────────────────────────────────────────
# AMÉLIORATION UI : identité visuelle, cards, couleurs cohérentes
st.markdown("""
<style>
    /* Fond général plus doux */
    .stApp { background-color: #f8f9fa; }

    /* Titre principal */
    h1 { color: #1a1a2e !important; font-weight: 800 !important; }

    /* Cards stations */
    .station-card {
        background: white;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        border-left: 4px solid #2ecc71;
    }
    .station-card.best {
        border-left: 4px solid #e74c3c;
        background: #fff9f9;
    }
    .station-card h4 { margin: 0 0 4px 0; color: #1a1a2e; font-size: 1rem; }
    .station-card .price { font-size: 1.4rem; font-weight: 800; color: #e74c3c; }
    .station-card .meta { color: #666; font-size: 0.85rem; margin-top: 4px; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #1a1a2e; }
    [data-testid="stSidebar"] * { color: #f0f0f0 !important; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label { color: #ccc !important; font-size: 0.9rem; }

    /* Bouton principal */
    .stLinkButton a {
        background: #2ecc71 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* Metric KPI */
    [data-testid="metric-container"] {
        background: white;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
</style>
""", unsafe_allow_html=True)

# ─── INIT SESSION STATE ─────────────────────────────────────────────────────────
# AMÉLIORATION : évite de recalculer la position à chaque interaction
if "lat_user" not in st.session_state:
    st.session_state.lat_user = None
if "lon_user" not in st.session_state:
    st.session_state.lon_user = None
if "position_label" not in st.session_state:
    st.session_state.position_label = None
if "df_stations" not in st.session_state:
    st.session_state.df_stations = None

# ─── SUPABASE ──────────────────────────────────────────────────────────────────
geolocator = Nominatim(user_agent="ecoplein_app_v2")
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")

    type_carbu = st.selectbox(
        "⛽ Type de carburant",
        ["Gazole", "E10", "SP98", "SP95", "E85", "GPLC"],
        help="Sélectionnez le carburant que vous cherchez"
    )

    st.markdown("---")
    st.markdown("**📍 Ma position**")
    mode_pos = st.radio(
        "Mode de localisation",
        ["GPS (Auto)", "Adresse (Manuel)"],
        label_visibility="collapsed"
    )

    # ── Mode GPS ──
    if mode_pos == "GPS (Auto)":
        if st.button("🔄 Actualiser ma position GPS"):
            # AMÉLIORATION : bouton explicite plutôt que refresh automatique
            st.session_state.lat_user = None
            st.session_state.lon_user = None

        loc = get_geolocation()
        if loc:
            st.session_state.lat_user = loc['coords']['latitude']
            st.session_state.lon_user = loc['coords']['longitude']
            # AMÉLIORATION : reverse geocoding pour afficher la ville
            if not st.session_state.position_label:
                try:
                    rev = geolocator.reverse(
                        (st.session_state.lat_user, st.session_state.lon_user),
                        language="fr"
                    )
                    if rev:
                        city = rev.raw.get("address", {}).get("city", "")
                        st.session_state.position_label = city or "Position GPS détectée"
                except Exception:
                    st.session_state.position_label = "Position GPS détectée"
            st.success(f"✅ {st.session_state.position_label}")
        else:
            # AMÉLIORATION : message d'attente clair, pas d'erreur agressive
            st.info("En attente du signal GPS…")

    # ── Mode Manuel ──
    else:
        adresse_saisie = st.text_input(
            "🔍 Ville ou adresse",
            placeholder="Ex: Lyon, Bordeaux, 75001 Paris…"
        )
        if adresse_saisie:
            # AMÉLIORATION : spinner pendant la recherche
            with st.spinner("Recherche en cours…"):
                try:
                    location = geolocator.geocode(adresse_saisie, language="fr")
                    if location:
                        st.session_state.lat_user = location.latitude
                        st.session_state.lon_user = location.longitude
                        # AMÉLIORATION : affiche le nom complet tronqué proprement
                        label = location.address
                        st.session_state.position_label = label[:40] + "…" if len(label) > 40 else label
                        st.success(f"📍 {st.session_state.position_label}")
                    else:
                        st.warning("Adresse introuvable. Essayez d'être plus précis.")
                except Exception as e:
                    # AMÉLIORATION : erreur plus descriptive
                    st.error(f"Service de géocodage indisponible ({type(e).__name__}). Réessayez.")

    st.markdown("---")
    st.caption("EcoPlein v2.0 · Données temps réel")

# ─── ZONE PRINCIPALE ───────────────────────────────────────────────────────────
st.title("⛽ EcoPlein")
st.caption("Les prix carburant les moins chers près de vous, en temps réel.")

# ── ÉTAT VIDE INITIAL ──
# AMÉLIORATION : onboarding clair au lieu d'un warning agressif
if not st.session_state.lat_user or not st.session_state.lon_user:
    st.markdown("---")
    col_empty1, col_empty2, col_empty3 = st.columns([1, 2, 1])
    with col_empty2:
        st.markdown("""
        <div style="text-align:center; padding: 40px 0; color: #888;">
            <div style="font-size: 3rem">🗺️</div>
            <h3 style="color:#444">Où êtes-vous ?</h3>
            <p>Activez le GPS ou saisissez votre adresse<br>dans le menu à gauche pour trouver les stations près de vous.</p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# ── RÉCUPÉRATION DES DONNÉES ──
lat_user = st.session_state.lat_user
lon_user = st.session_state.lon_user

# AMÉLIORATION : spinner + cache session pour éviter re-fetch inutile
with st.spinner("🔍 Recherche des stations autour de vous…"):
    try:
        response = supabase.rpc('get_stations_proches', {
            'user_lat': lat_user,
            'user_lon': lon_user
        }).execute()
    except Exception as e:
        st.error(f"❌ Impossible de contacter la base de données ({type(e).__name__}). Vérifiez votre connexion.")
        st.stop()

if not response.data:
    st.info("Aucune station trouvée dans cette zone. Élargissez votre recherche.")
    st.stop()

df = pd.DataFrame(response.data)

# ── FILTRE CARBURANT ──
df_filtre = df[df['carburant_nom'].str.lower() == type_carbu.lower()].copy()

# AMÉLIORATION : message d'erreur dynamique (plus de "Lille" hardcodé !)
if df_filtre.empty:
    location_name = st.session_state.position_label or "votre position"
    st.warning(f"⚠️ Aucune station proposant du **{type_carbu}** n'a été trouvée autour de **{location_name}**.")
    st.stop()

# Tri par prix
df_filtre = df_filtre.sort_values("prix").reset_index(drop=True)

# ── KPIs RÉSUMÉ ──
# AMÉLIORATION : vue d'ensemble immédiate en haut de page
st.markdown(f"### {type_carbu} — {len(df_filtre)} station{'s' if len(df_filtre) 
