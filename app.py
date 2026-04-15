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

# ─── CSS — approche chirurgicale sans sélecteur div global ─────────────────────
st.markdown("""
<style>
    /* ── Global ── */
    .stApp { background-color: #f8f9fa; }

    /* ── Sidebar : fond sombre SANS toucher aux divs génériques ── */
    [data-testid="stSidebar"] { background-color: #1a1a2e !important; }
    [data-testid="stSidebar"] .stMarkdown p    { color: #f0f0f0 !important; }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3   { color: #f0f0f0 !important; }
    [data-testid="stSidebar"] .stMarkdown small { color: #cccccc !important; }
    [data-testid="stSidebar"] label             { color: #f0f0f0 !important; }
    [data-testid="stSidebar"] .stSelectbox > div > div { color: #f0f0f0 !important; }
    [data-testid="stSidebar"] .stRadio span     { color: #f0f0f0 !important; }
    [data-testid="stSidebar"] .stButton button  { color: #1a1a2e !important; }
    [data-testid="stSidebar"] hr                { border-color: #3a3a5e !important; }

    /* ── Zone principale : forcer texte sombre ── */
    [data-testid="stMainBlockContainer"] p,
    [data-testid="stMainBlockContainer"] span,
    [data-testid="stMainBlockContainer"] label,
    [data-testid="stMainBlockContainer"] h1,
    [data-testid="stMainBlockContainer"] h2,
    [data-testid="stMainBlockContainer"] h3,
    [data-testid="stMainBlockContainer"] h4 { color: #1a1a2e !important; }

    /* ── Métriques ── */
    [data-testid="metric-container"] {
        background: white !important;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    [data-testid="stMetricValue"]  { color: #1a1a2e !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"]  { color: #555555 !important; }

    /* ── Cards stations ── */
    .station-card {
        background: white;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        border-left: 4px solid #2ecc71;
        color: #1a1a2e;
    }
    .station-card.best {
        border-left: 4px solid #e74c3c;
        background: #fff9f9;
    }
    .card-nom    { margin: 0 0 4px 0; font-size: 1rem; font-weight: 700; color: #1a1a2e; }
    .card-prix   { font-size: 1.4rem; font-weight: 800; color: #e74c3c; white-space: nowrap; }
    .card-meta   { font-size: 0.85rem; color: #555555; margin-top: 4px; }

    /* ── Prix autres carburants ── */
    .prix-autres { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .prix-tag {
        background: #f0f4f8;
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 0.8rem;
        color: #333333;
        border: 1px solid #dde3ea;
    }

    /* ── Services ── */
    .services-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
    .service-badge {
        background: #eaf6f0;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.75rem;
        color: #1a7a45;
        border: 1px solid #b8dfc9;
    }
    .automate-badge {
        background: #e8f1fb;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.75rem;
        color: #1a5a9a;
        border: 1px solid #b8cfe8;
    }

    /* ── Bouton Y aller ── */
    .stLinkButton a {
        background: #2ecc71 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
for key in ["lat_user", "lon_user", "position_label"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─── INIT ──────────────────────────────────────────────────────────────────────
geolocator = Nominatim(user_agent="ecoplein_app_v2")
url  = st.secrets["SUPABASE_URL"]
key  = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ─── FAMILLES CARBURANTS ───────────────────────────────────────────────────────
FAMILLES = {
    "E10":    ["SP95", "SP98", "E85"],
    "SP95":   ["E10",  "SP98", "E85"],
    "SP98":   ["E10",  "SP95", "E85"],
    "E85":    ["E10",  "SP95", "SP98"],
    "Gazole": ["GPLC"],
    "GPLC":   ["Gazole"],
}

ICONES_SERVICES = {
    "toilettes": "🚻", "boutique": "🛒", "lavage": "🚿",
    "restaurant": "🍽️", "wifi": "📶", "gonflage": "🔧",
    "dab": "💳", "handicap": "♿", "gaz": "🔵",
    "automate": "🤖", "poids lourds": "🚛", "bar": "☕",
    "air": "🌬️", "aspirateur": "🧹",
}

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def safe(val, default=""):
    """Convertit toute valeur pandas/None en string propre."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    s = str(val).strip()
    return default if s.lower() in ("none", "nan", "nat") else s


def html_prix_autres(nom, ville, df_complet, type_carbu):
    carbus = FAMILLES.get(type_carbu, [])
    if not carbus:
        return ""
    try:
        df_st = df_complet[
            (df_complet["nom"] == nom) &
            (df_complet["ville"] == ville)
        ]
        tags = []
        for c in carbus:
            match = df_st[df_st["carburant_nom"].str.lower() == c.lower()]
            if not match.empty:
                p = safe(match.iloc[0]["prix"])
                if p:
                    tags.append(
                        '<span class="prix-tag">' + c + ' : <strong>' + p + ' €</strong></span>'
                    )
        if not tags:
            return ""
        return '<div class="prix-autres">' + "".join(tags) + "</div>"
    except Exception:
        return ""


def html_services(services_str, automate_24_24):
    try:
        badges = []
        a = safe(automate_24_24)
        if a and a.lower() not in ("non", "false", "0", ""):
            badges.append('<span class="automate-badge">🤖 Automate 24h/24</span>')

        s = safe(services_str)
        if s:
            items = [x.strip() for x in s.split(",") if x.strip() and x.strip().lower() not in ("none","nan")]
            for item in items[:8]:
                icone = ""
                for k, ico in ICONES_SERVICES.items():
                    if k in item.lower():
                        icone = ico + " "
                        break
                badges.append('<span class="service-badge">' + icone + item + "</span>")

        if not badges:
            return ""
        return '<div class="services-row">' + "".join(badges) + "</div>"
    except Exception:
        return ""


def build_card_html(row, card_class, badge, df_complet, type_carbu):
    """Construit le HTML complet d'une card station. Isolé pour try/except propre."""
    nom      = safe(row.get("nom"),      "Station")
    adresse  = safe(row.get("adresse"),  "")
    ville    = safe(row.get("ville"),    "")
    cp       = safe(row.get("cp"),       "")
    dept     = safe(row.get("departement"), "")
    prix_val = safe(row.get("prix"),     "—")
    dist_raw = row.get("distance_km")
    distance = str(round(float(dist_raw), 1)) if dist_raw is not None else "—"

    # Adresse complète
    loc = adresse
    if cp and ville:
        loc += ", " + cp + " " + ville
    elif ville:
        loc += ", " + ville
    if dept and dept.lower() not in ville.lower():
        loc += " (" + dept + ")"

    h_autres = html_prix_autres(row.get("nom"), row.get("ville"), df_complet, type_carbu)
    h_svc    = html_services(row.get("services"), row.get("automate_24_24"))

    return (
        '<div class="' + card_class + '">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">'
        '<p class="card-nom">' + nom + ' <small style="color:#999;font-weight:400">' + badge + "</small></p>"
        '<span class="card-prix">' + prix_val + " €</span>"
        "</div>"
        '<div class="card-meta">📍 ' + loc + "&nbsp;&nbsp;📏 <strong>" + distance + " km</strong></div>"
        + h_autres
        + h_svc
        + "</div>"
    )

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
        "Mode", ["GPS (Auto)", "Adresse (Manuel)"],
        label_visibility="collapsed"
    )

    if mode_pos == "GPS (Auto)":
        if st.button("🔄 Actualiser ma position GPS"):
            st.session_state.lat_user      = None
            st.session_state.lon_user      = None
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
                    city = rev.raw.get("address", {}).get("city", "") if rev else ""
                    st.session_state.position_label = city or "Position GPS détectée"
                except Exception:
                    st.session_state.position_label = "Position GPS détectée"
            st.success("✅ " + st.session_state.position_label)
        else:
            st.info("En attente du signal GPS…")

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
                        raw = location.address
                        st.session_state.position_label = raw[:40] + "…" if len(raw) > 40 else raw
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

if not st.session_state.lat_user or not st.session_state.lon_user:
    st.markdown("---")
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("""
        <div style="text-align:center;padding:40px 0">
            <div style="font-size:3rem">🗺️</div>
            <h3 style="color:#444">Où êtes-vous ?</h3>
            <p style="color:#888">Activez le GPS ou saisissez votre adresse dans le menu à gauche.</p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# ── FETCH SUPABASE ──
with st.spinner("🔍 Recherche des stations autour de vous…"):
    try:
        response = supabase.rpc("get_stations_proches", {
            "user_lat": st.session_state.lat_user,
            "user_lon": st.session_state.lon_user
        }).execute()
    except Exception as e:
        st.error("❌ Impossible de contacter la base (" + type(e).__name__ + ").")
        st.stop()

if not response.data:
    st.info("Aucune station trouvée dans cette zone.")
    st.stop()

df_complet = pd.DataFrame(response.data)

# ── FILTRE ──
df_filtre = df_complet[
    df_complet["carburant_nom"].str.lower() == type_carbu.lower()
].copy().sort_values("prix").reset_index(drop=True)

if df_filtre.empty:
    pos = st.session_state.position_label or "votre position"
    st.warning("⚠️ Aucune station proposant du **" + type_carbu + "** trouvée autour de **" + pos + "**.")
    st.stop()

# ── KPIs ──
nb     = len(df_filtre)
plural = "s" if nb > 1 else ""
st.markdown("### " + type_carbu + " — " + str(nb) + " station" + plural + " trouvée" + plural)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("💰 Meilleur prix",  str(round(df_filtre["prix"].min(), 3))  + " €/L")
with c2:
    st.metric("📏 La plus proche", str(round(df_filtre["distance_km"].min(), 1)) + " km")
with c3:
    st.metric("📊 Prix moyen",     str(round(df_filtre["prix"].mean(), 3))  + " €/L")

st.markdown("---")

# ── CARTE ──
st.subheader("🗺️ Carte des stations")

prix_min = df_filtre["prix"].min()
df_filtre["color"]  = df_filtre["prix"].apply(lambda p: [231,76,60,220]  if p == prix_min else [46,204,113,200])
df_filtre["radius"] = df_filtre["prix"].apply(lambda p: 80 if p == prix_min else 50)

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
    zoom=12, pitch=0
)
tooltip = {
    "html": "<b>{nom}</b><br/>💰 {prix} €/L<br/>📏 {distance_km} km",
    "style": {"backgroundColor":"#1a1a2e","color":"white","borderRadius":"8px","padding":"8px"}
}

try:
    st.pydeck_chart(pdk.Deck(
        layers=[layer], initial_view_state=view_state,
        tooltip=tooltip, map_style=pdk.map_styles.CARTO_LIGHT
    ))
except Exception:
    st.map(
        df_filtre[["latitude","longitude"]].rename(columns={"latitude":"lat","longitude":"lon"}),
        zoom=12
    )

# ── LISTE ──
st.subheader("📋 Classement par prix")
st.caption("🔴 Moins cher · 🟢 Autres stations")

for i, row in df_filtre.iterrows():
    is_best    = (row["prix"] == prix_min)
    badge      = "🥇 MEILLEUR PRIX" if is_best else "#" + str(i + 1)
    card_class = "station-card best" if is_best else "station-card"
    lat        = safe(row.get("latitude"))
    lon        = safe(row.get("longitude"))
    url_maps   = "https://www.google.com/maps/search/?api=1&query=" + lat + "," + lon

    col_info, col_btn = st.columns([4, 1])

    with col_info:
        try:
            card_html = build_card_html(row, card_class, badge, df_complet, type_carbu)
        except Exception as e:
            card_html = "<div class='" + card_class + "'><p>" + safe(row.get("nom"), "Station") + " — erreur d'affichage</p></div>"
        st.markdown(card_html, unsafe_allow_html=True)

    with col_btn:
        st.markdown("<div style='margin-top:14px'>", unsafe_allow_html=True)
        st.link_button("🚗 Y aller", url_maps)
        st.markdown("</div>", unsafe_allow_html=True)
