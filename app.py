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
    menu_items={"About": "EcoPlein – Trouvez le carburant le moins cher près de vous."}
)

# ─── CSS CUSTOM ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #1a1a2e !important; font-weight: 800 !important; }

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

    [data-testid="stSidebar"] { background: #1a1a2e; }
    [data-testid="stSidebar"] * { color: #f0f0f0 !important; }

    .stLinkButton a {
        background: #2ecc71 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    [data-testid="metric-container"] {
        background: white;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
if "lat_user" not in st.session_state:
    st.session_state.lat_user = None
if "lon_user" not in st.session_state:
    st.session_state.lon_user = None
if "position_label" not in st.session_state:
    st.session_state.position_label = None

# ─── INIT ──────────────────────────────────────────────────────────────────────
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

    # ── GPS ──
    if mode_pos == "GPS (Auto)":
        if st.button("🔄 Actualiser ma position GPS"):
            st.session_state.lat_user = None
            st.session_state.lon_user = None
            st.session_state.position_label = None

        loc = get_geolocation()
        if loc:
            st.session_state.lat_user = loc["coords"]["latitude"]
            st.session_state.lon_user = loc["coords"]["longitude"]

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

            label = st.session_state.position_label
            st.success("✅ " + label)
        else:
            st.info("En attente du signal GPS…")

    # ── Manuel ──
    else:
        adresse_saisie = st.text_input(
            "🔍 Ville ou adresse",
            placeholder="Ex: Lyon, Bordeaux, 75001 Paris…"
        )
        if adresse_saisie:
            with st.spinner("Recherche en cours…"):
                try:
                    location = geolocator.geocode(adresse_saisie, language="fr")
                    if location:
                        st.session_state.lat_user = location.latitude
                        st.session_state.lon_user = location.longitude
                        raw_label = location.address
                        if len(raw_label) > 40:
                            st.session_state.position_label = raw_label[:40] + "…"
                        else:
                            st.session_state.position_label = raw_label
                        st.success("📍 " + st.session_state.position_label)
                    else:
                        st.warning("Adresse introuvable. Essayez d'être plus précis.")
                except Exception as e:
                    st.error("Service indisponible (" + type(e).__name__ + "). Réessayez.")

    st.markdown("---")
    st.caption("EcoPlein v2.0 · Données temps réel")

# ─── ZONE PRINCIPALE ───────────────────────────────────────────────────────────
st.title("⛽ EcoPlein")
st.caption("Les prix carburant les moins chers près de vous, en temps réel.")

# ── ÉTAT VIDE ──
if not st.session_state.lat_user or not st.session_state.lon_user:
    st.markdown("---")
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown("""
        <div style="text-align:center; padding:40px 0; color:#888;">
            <div style="font-size:3rem">🗺️</div>
            <h3 style="color:#444">Où êtes-vous ?</h3>
            <p>Activez le GPS ou saisissez votre adresse<br>dans le menu à gauche.</p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# ── FETCH SUPABASE ──
lat_user = st.session_state.lat_user
lon_user = st.session_state.lon_user

with st.spinner("🔍 Recherche des stations autour de vous…"):
    try:
        response = supabase.rpc("get_stations_proches", {
            "user_lat": lat_user,
            "user_lon": lon_user
        }).execute()
    except Exception as e:
        st.error("❌ Impossible de contacter la base de données (" + type(e).__name__ + ").")
        st.stop()

if not response.data:
    st.info("Aucune station trouvée dans cette zone.")
    st.stop()

df = pd.DataFrame(response.data)

# ── FILTRE CARBURANT ──
df_filtre = df[df["carburant_nom"].str.lower() == type_carbu.lower()].copy()

if df_filtre.empty:
    position_name = st.session_state.position_label or "votre position"
    st.warning("⚠️ Aucune station proposant du **" + type_carbu + "** trouvée autour de **" + position_name + "**.")
    st.stop()

df_filtre = df_filtre.sort_values("prix").reset_index(drop=True)

# ── KPIs ──
nb = len(df_filtre)
plural = "s" if nb > 1 else ""
st.markdown("### " + type_carbu + " — " + str(nb) + " station" + plural + " trouvée" + plural)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💰 Meilleur prix", str(round(df_filtre["prix"].min(), 3)) + " €/L")
with col2:
    st.metric("📏 La plus proche", str(round(df_filtre["distance_km"].min(), 1)) + " km")
with col3:
    st.metric("📊 Prix moyen", str(round(df_filtre["prix"].mean(), 3)) + " €/L")

st.markdown("---")

# ── CARTE PYDECK ──
st.subheader("🗺️ Carte des stations")

prix_min = df_filtre["prix"].min()

df_filtre["color"] = df_filtre["prix"].apply(
    lambda p: [231, 76, 60, 220] if p == prix_min else [46, 204, 113, 200]
)
df_filtre["radius"] = df_filtre["prix"].apply(
    lambda p: 80 if p == prix_min else 50
)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_filtre,
    get_position="[longitude, latitude]",
    get_color="color",
    get_radius="radius",
    pickable=True
)

view_state = pdk.ViewState(
    latitude=df_filtre["latitude"].mean(),
    longitude=df_filtre["longitude"].mean(),
    zoom=12,
    pitch=0
)

tooltip = {
    "html": "<b>{nom}</b><br/>💰 {prix} €/L<br/>📏 {distance_km} km",
    "style": {
        "backgroundColor": "#1a1a2e",
        "color": "white",
        "borderRadius": "8px",
        "padding": "8px"
    }
}

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip,
    map_style="mapbox://styles/mapbox/light-v10"
))

# ── LISTE STATIONS ──
st.subheader("📋 Classement par prix")
st.caption("🔴 Moins cher · 🟢 Autres stations")

for i, row in df_filtre.iterrows():
    is_best = (row["prix"] == prix_min)
    badge = "🥇 MEILLEUR PRIX" if is_best else "#" + str(i + 1)
    card_class = "station-card best" if is_best else "station-card"

    nom = str(row["nom"])
    adresse = str(row["adresse"])
    ville = str(row["ville"])
    prix = str(row["prix"])
    distance = str(round(row["distance_km"], 1))
    lat = str(row["latitude"])
    lon = str(row["longitude"])
    url_maps = "https://www.google.com/maps/search/?api=1&query=" + lat + "," + lon

    col_info, col_btn = st.columns([4, 1])

    with col_info:
        st.markdown(
            '<div class="' + card_class + '">'
            '<div style="display:flex; justify-content:space-between; align-items:center">'
            "<h4>" + nom + ' <small style="color:#999; font-weight:400">' + badge + "</small></h4>"
            '<span class="price">' + prix + " €</span>"
            "</div>"
            '<div class="meta">'
            "📍 " + adresse + ", " + ville + "&nbsp;&nbsp;"
            "📏 <strong>" + distance + " km</strong>"
            "</div>"
            "</div>",
            unsafe_allow_html=True
        )

    with col_btn:
        st.markdown("<div style='margin-top:14px'>", unsafe_allow_html=True)
        st.link_button("🚗 Y aller", url_maps)
        st.markdown("</div>", unsafe_allow_html=True)
