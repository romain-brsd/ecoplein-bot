# ─────────────────────────────────────────────────────────────────────────────
# EcoPlein v2.1 — app.py
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
from supabase import create_client
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import pydeck as pdk
from datetime import datetime, timezone
import json
import re

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="EcoPlein",
    page_icon="⛽",
    layout="wide",
    menu_items={"About": "EcoPlein v2.1 — Données gouvernementales temps réel"}
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0d1117 !important; }
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] .stMarkdown small,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stRadio span,
[data-testid="stSidebar"] .stCheckbox span,
[data-testid="stSidebar"] .stSlider span { color: #e6edf3 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #161b22 !important; color: #e6edf3 !important;
    border: 1px solid #30363d !important; }
[data-testid="stSidebar"] .stTextInput > div > div > input {
    background-color: #161b22 !important; color: #e6edf3 !important;
    border: 1px solid #30363d !important; }
[data-testid="stSidebar"] hr { border-color: #21262d !important; margin: 10px 0 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #238636, #2ea043) !important;
    color: #fff !important; border: none !important;
    border-radius: 6px !important; font-weight: 600 !important; width: 100% !important; }
[data-testid="stMainBlockContainer"] { background-color: #f6f8fa !important; padding-top: 1.2rem !important; }

/* Cards */
.eco-card { background:#fff; border:1px solid #d0d7de; border-radius:8px; padding:14px 16px;
    margin:6px 0; color:#24292f !important; box-shadow:0 1px 3px rgba(31,35,40,.06);
    transition:box-shadow .15s; }
.eco-card:hover { box-shadow:0 4px 12px rgba(31,35,40,.12); }
.eco-card h4  { color:#24292f !important; margin:0 0 5px; font-size:.95rem; font-weight:600; }
.eco-card .addr { color:#57606a !important; font-size:.82rem; margin:0; }

/* Prix */
.prix-cheap { display:inline-block; background:#dafbe1; color:#1a7f37 !important;
    border-radius:20px; padding:4px 14px; font-weight:700; font-size:1.1rem; }
.prix-avg   { display:inline-block; background:#fff8c5; color:#9a6700 !important;
    border-radius:20px; padding:4px 14px; font-weight:700; font-size:1.1rem; }
.prix-exp   { display:inline-block; background:#ffebe9; color:#cf222e !important;
    border-radius:20px; padding:4px 14px; font-weight:700; font-size:1.1rem; }

/* Fraîcheur */
.fr-today  { color:#1a7f37 !important; font-size:.78rem; }
.fr-recent { color:#9a6700 !important; font-size:.78rem; }
.fr-old    { color:#cf222e !important; font-size:.78rem; }

/* Marque */
.brand-tag { display:inline-block; background:#0d1117; color:#e6edf3 !important;
    border-radius:4px; padding:2px 9px; font-size:.72rem; font-weight:700;
    letter-spacing:.03em; margin-right:6px; vertical-align:middle; }

/* Services */
.svc-g { display:inline-block; background:#dafbe1; color:#1a7f37 !important;
    border-radius:12px; padding:2px 8px; font-size:.72rem; margin:2px 2px 0 0; }
.svc-b { display:inline-block; background:#ddf4ff; color:#0550ae !important;
    border-radius:12px; padding:2px 8px; font-size:.72rem; margin:2px 2px 0 0; }

/* Ruptures */
.rup-t { background:#fff8c5; color:#9a6700 !important; border-radius:4px;
    padding:2px 8px; font-size:.72rem; margin:2px 2px 0 0; display:inline-block; }
.rup-d { background:#ffebe9; color:#cf222e !important; border-radius:4px;
    padding:2px 8px; font-size:.72rem; margin:2px 2px 0 0; display:inline-block; }

/* KPIs */
.kpi { background:#fff; border:1px solid #d0d7de; border-radius:8px;
    padding:14px 12px; text-align:center; color:#24292f !important; }
.kpi-v { font-size:1.7rem; font-weight:700; color:#24292f !important; line-height:1.2; }
.kpi-l { font-size:.78rem; color:#57606a !important; margin-top:2px; }

/* GPS */
.gps-ok   { background:#dafbe1; color:#1a7f37 !important; border-radius:6px;
    padding:8px 12px; font-size:.85rem; margin-top:8px; }
.gps-wait { background:#fff8c5; color:#9a6700 !important; border-radius:6px;
    padding:8px 12px; font-size:.85rem; margin-top:8px; }

/* Horaires */
.htbl { width:100%; font-size:.8rem; border-collapse:collapse; }
.htbl td { padding:3px 8px; border-bottom:1px solid #d0d7de; color:#24292f; }
.htbl tr:last-child td { border-bottom:none; }
.htbl .d { font-weight:600; width:85px; }
.htbl-today { background:#dafbe1 !important; }

.saving { color:#1a7f37 !important; font-size:.82rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
CARBURANTS = {
    "Gazole": "gazole",
    "SP95":   "sp95",
    "SP98":   "sp98",
    "E10":    "e10",
    "E85":    "e85",
    "GPLc":   "gplc",
}

BRANDS = [
    ("TotalEnergies", ["TOTALENERGIES", "TOTAL ENERGIES", "TOTAL ACCESS"]),
    ("Total",         ["TOTAL"]),
    ("Esso",          ["ESSO"]),
    ("BP",            [" BP ", "BP-"]),
    ("Shell",         ["SHELL"]),
    ("Avia",          ["AVIA"]),
    ("Agip",          ["AGIP"]),
    ("Elf",           ["ELF"]),
    ("Dyneff",        ["DYNEFF"]),
    ("E.Leclerc",     ["LECLERC"]),
    ("Intermarché",   ["INTERMARCHE", "INTERMARCHÉ", "MOUSQUETAIRES"]),
    ("Carrefour",     ["CARREFOUR"]),
    ("Super U",       ["SUPER U", "SUPERMARCHE U", "SUPERMARCHÉ U"]),
    ("Hyper U",       ["HYPER U"]),
    ("Système U",     ["SYSTEME U", "SYSTÈME U"]),
    ("Auchan",        ["AUCHAN"]),
    ("Casino",        ["CASINO"]),
    ("Géant",         ["GEANT", "GÉANT"]),
    ("Lidl",          ["LIDL"]),
    ("Netto",         ["NETTO"]),
    ("Vito",          ["VITO"]),
    ("DKV",           ["DKV"]),
    ("Relais",        ["RELAIS"]),
]

SERVICES_MAP = {
    "Automate CB 24/24":                         ("💳", "svc-g"),
    "Bornes électriques":                        ("⚡", "svc-g"),
    "Boutique alimentaire":                      ("🛒", "svc-b"),
    "Boutique non alimentaire":                  ("🏪", "svc-b"),
    "Lavage automatique":                        ("🚗", "svc-b"),
    "Lavage manuel":                             ("🧹", "svc-b"),
    "Station de gonflage":                       ("🔧", "svc-b"),
    "Toilettes publiques":                       ("🚻", "svc-b"),
    "Restauration à emporter":                   ("🍔", "svc-b"),
    "Restauration sur place":                    ("🍽️", "svc-b"),
    "Piste poids lourds":                        ("🚛", "svc-b"),
    "DAB (Distributeur automatique de billets)": ("💰", "svc-b"),
    "Services réparation / entretien":           ("🔩", "svc-b"),
    "Carburant additivé":                        ("⚗️", "svc-b"),
    "Location de véhicule":                      ("🚙", "svc-b"),
    "Vente de gaz domestique (Butane, Propane)": ("🔥", "svc-b"),
    "Bar":                                       ("☕", "svc-b"),
    "Wifi":                                      ("📶", "svc-b"),
    "Laverie":                                   ("🫧", "svc-b"),
    "Relais colis":                              ("📦", "svc-b"),
}

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def safe_str(v) -> str:
    return str(v) if v is not None else ""

def safe_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            p = json.loads(v)
            return p if isinstance(p, list) else []
        except Exception:
            return []
    return []

def extract_geom(geom) -> tuple[float, float]:
    if isinstance(geom, dict):
        return float(geom.get("lat", 0)), float(geom.get("lon", 0))
    if isinstance(geom, str):
        try:
            d = json.loads(geom)
            return float(d.get("lat", 0)), float(d.get("lon", 0))
        except Exception:
            pass
    return 0.0, 0.0

def detect_brand(row: dict) -> str | None:
    enseigne = safe_str(row.get("enseigne"))
    text = f"{enseigne.upper()} {safe_str(row.get('adresse')).upper()} {safe_str(row.get('ville')).upper()}"
    for brand_name, patterns in BRANDS:
        for p in patterns:
            if p in text:
                return brand_name
    return enseigne.title() if enseigne else None

def freshness(maj_val) -> tuple[str, str]:
    if not maj_val:
        return "❓ Inconnu", "fr-old"
    try:
        maj = datetime.fromisoformat(str(maj_val).replace("Z", "+00:00"))
        if maj.tzinfo is None:
            maj = maj.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - maj).days
        if days == 0:   return "🟢 Aujourd'hui", "fr-today"
        if days <= 2:   return f"🟡 {days}j",     "fr-recent"
        if days <= 7:   return f"🔴 {days}j",     "fr-old"
        return f"⚠️ {days}j — périmé", "fr-old"
    except Exception:
        return "❓", "fr-old"

def hours_html(horaires_jour) -> str:
    hj = safe_str(horaires_jour)
    if not hj:
        return "<span style='color:#57606a;font-size:.83rem'>Non renseignés</span>"
    is_24h    = "Automate-24-24" in hj
    today_idx = datetime.now().weekday()
    rows = ""
    for i, jour in enumerate(JOURS):
        m = re.search(rf"{jour}(\d{{2}}\.\d{{2}})-(\d{{2}}\.\d{{2}})", hj)
        css = ' class="htbl-today"' if i == today_idx else ""
        if m:
            h = f"{m.group(1).replace('.','h')} – {m.group(2).replace('.','h')}"
        elif is_24h and not re.search(rf"{jour}\d", hj):
            h = "24h/24 (automate)"
        else:
            h = "Fermé"
        rows += f"<tr{css}><td class='d'>{jour[:3]}.</td><td>{h}</td></tr>"
    badge = '<span class="svc-g">🕐 Automate 24h/24</span>' if is_24h else ""
    return f"{badge}<br><table class='htbl'>{rows}</table>"

def dist_km(lat1, lon1, lat2, lon2) -> float | None:
    try:
        return round(geodesic((lat1, lon1), (lat2, lon2)).km, 1)
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT — RPC avec fallback direct
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def load_stations(_sb, carburant_col: str, lat: float, lon: float, radius: float):
    """Essaie la RPC, retombe sur table directe si indisponible."""
    try:
        resp = _sb.rpc("get_stations_proches", {
            "user_lat":      lat,
            "user_lon":      lon,
            "carburant_col": carburant_col,
            "radius_km":     radius,
        }).execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            df.rename(columns={
                "prix":    f"{carburant_col}_prix",
                "prix_maj": f"{carburant_col}_maj",
            }, inplace=True)
            return df, True
    except Exception as e:
        st.caption(f"⚠️ RPC indisponible, requête directe. ({e})")

    try:
        prix_col = f"{carburant_col}_prix"
        resp = _sb.table("stations_carburant") \
                  .select("*") \
                  .not_.is_(prix_col, "null") \
                  .execute()
        return pd.DataFrame(resp.data or []), False
    except Exception as e2:
        st.error(f"Erreur Supabase : {e2}")
        return pd.DataFrame(), False

# ══════════════════════════════════════════════════════════════════════════════
# RENDU CARTE STATION
# ══════════════════════════════════════════════════════════════════════════════
def render_card(row: dict, carburant_col: str, user_lat: float, user_lon: float,
                moyenne: float):
    prix_col = f"{carburant_col}_prix"
    maj_col  = f"{carburant_col}_maj"
    prix = row.get(prix_col)
    if prix is None:
        return

    # Prix class
    ratio = (float(prix) - moyenne) / max(abs(moyenne * 0.03), 0.001)
    prix_cls = "prix-cheap" if ratio < -0.5 else ("prix-exp" if ratio > 0.5 else "prix-avg")

    # Fraîcheur
    fr_lbl, fr_cls = freshness(row.get(maj_col))

    # Distance
    d = row.get("distance_km")
    if d is None:
        lat, lon = extract_geom(row.get("geom"))
        d = dist_km(user_lat, user_lon, lat, lon)
    dist_str = f"📍 {d} km" if d else ""

    # Marque
    brand = detect_brand(row)
    brand_html = f'<span class="brand-tag">{brand}</span>' if brand else ""

    # Type autoroute
    pop_badge = '<span class="svc-b">🛣️ Autoroute</span>' if row.get("pop") == "A" else ""

    # Services prioritaires
    priority = ["Automate CB 24/24", "Bornes électriques", "Lavage automatique",
                "Boutique alimentaire", "Wifi"]
    svcs_html = ""
    for svc in safe_list(row.get("services_service")):
        if svc in priority and svc in SERVICES_MAP:
            icon, cls = SERVICES_MAP[svc]
            svcs_html += f'<span class="{cls}">{icon} {svc}</span>'
    if row.get("horaires_automate_24_24") == "Oui":
        svcs_html = '<span class="svc-g">🕐 24h/24</span>' + svcs_html

    # Ruptures
    rup = ""
    if safe_str(row.get("carburants_rupture_temporaire")):
        rup += f'<span class="rup-t">⏳ {row["carburants_rupture_temporaire"]}</span>'
    if safe_str(row.get("carburants_rupture_definitive")):
        rup += f'<span class="rup-d">🚫 {row["carburants_rupture_definitive"]}</span>'

    # Économie
    saving = round((moyenne - float(prix)) * 50, 2)
    sav_html = (f'<span class="saving">💰 -{saving:.2f}€ vs moyenne (plein 50L)</span>'
                if saving > 0.5 else "")

    adresse = safe_str(row.get("adresse"))
    ville   = safe_str(row.get("ville"))
    cp      = safe_str(row.get("cp"))

    st.markdown(f"""
    <div class="eco-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
        <div style="flex:1;min-width:0">
          <h4>{brand_html}{adresse}</h4>
          <p class="addr">{cp} {ville}&nbsp;·&nbsp;{dist_str}</p>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <span class="{prix_cls}">{float(prix):.3f} €/L</span>
          <br><span class="{fr_cls}">{fr_lbl}</span>
        </div>
      </div>
      <div style="margin-top:8px;line-height:1.9">{pop_badge}{svcs_html}</div>
      {f'<div style="margin-top:5px">{sav_html}</div>' if sav_html else ''}
      {f'<div style="margin-top:4px">{rup}</div>' if rup else ''}
    </div>""", unsafe_allow_html=True)

    with st.expander("📋 Horaires & services complets"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🕐 Horaires**")
            st.markdown(hours_html(row.get("horaires_jour")), unsafe_allow_html=True)
        with c2:
            st.markdown("**🔧 Services**")
            all_svcs = safe_list(row.get("services_service"))
            if all_svcs:
                s = "".join(
                    f'<span class="{SERVICES_MAP.get(sv, ("•","svc-b"))[1]}">'
                    f'{SERVICES_MAP.get(sv, ("•","svc-b"))[0]} {sv}</span>'
                    for sv in all_svcs
                )
                st.markdown(s, unsafe_allow_html=True)
            else:
                st.caption("Non renseignés")

            dispo   = safe_list(row.get("carburants_disponibles"))
            indispo = safe_list(row.get("carburants_indisponibles"))
            if dispo or indispo:
                st.markdown("**⛽ Carburants**")
                c  = "".join(f'<span class="svc-g">✅ {x}</span>' for x in dispo)
                c += "".join(f'<span class="rup-d">🚫 {x}</span>' for x in indispo)
                st.markdown(c, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
def main():
    sb = get_supabase()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⛽ EcoPlein")
        st.markdown('<small style="color:#8b949e">Carburant moins cher près de vous</small>',
                    unsafe_allow_html=True)
        st.markdown("---")

        st.markdown("**🔴 Carburant**")
        carb_name = st.selectbox("c", list(CARBURANTS.keys()), label_visibility="collapsed")
        carb_col  = CARBURANTS[carb_name]

        st.markdown("---")
        st.markdown("**📏 Rayon**")
        radius = st.slider("r", 2, 50, 10, label_visibility="collapsed", format="%d km")

        st.markdown("---")
        st.markdown("**📍 Position**")
        mode = st.radio("m", ["GPS (Auto)", "Adresse (Manuel)"], label_visibility="collapsed")

        user_lat = user_lon = None

        if mode == "GPS (Auto)":
            if st.button("🔄 Actualiser GPS"):
                st.session_state.pop("gps", None)
            if "gps" not in st.session_state:
                loc = get_geolocation()
                if loc and loc.get("coords"):
                    st.session_state.gps = loc
            if "gps" in st.session_state:
                c = st.session_state.gps["coords"]
                user_lat, user_lon = c["latitude"], c["longitude"]
                st.markdown(
                    f'<div class="gps-ok">✅ Position détectée<br>'
                    f'<small>{user_lat:.5f}, {user_lon:.5f}</small></div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="gps-wait">⏳ En attente GPS…<br>'
                    '<small>Autorisez la géolocalisation</small></div>',
                    unsafe_allow_html=True)
        else:
            addr = st.text_input("a", placeholder="Ex: 15 rue de la Paix, Lyon",
                                 label_visibility="collapsed")
            if addr and st.button("🔍 Géolocaliser"):
                with st.spinner("Recherche…"):
                    try:
                        loc = Nominatim(user_agent="ecoplein_v2").geocode(addr + ", France")
                        if loc:
                            user_lat, user_lon = loc.latitude, loc.longitude
                            st.session_state.mloc = (user_lat, user_lon)
                            st.success(f"✅ {loc.address[:50]}…")
                        else:
                            st.error("Adresse introuvable")
                    except Exception as e:
                        st.error(str(e))
            if "mloc" in st.session_state and not user_lat:
                user_lat, user_lon = st.session_state.mloc

        st.markdown("---")
        st.markdown("**🔧 Filtres**")
        f_24h  = st.checkbox("🕐 Automate 24h/24")
        f_cb   = st.checkbox("💳 CB 24/24")
        f_ev   = st.checkbox("⚡ Bornes électriques")
        f_wash = st.checkbox("🚗 Lavage auto")
        f_shop = st.checkbox("🛒 Boutique alim.")
        f_dab  = st.checkbox("💰 DAB")

        st.markdown("---")
        st.markdown("**📊 Tri**")
        sort_by = st.selectbox("s",
            ["Distance", "Prix croissant", "Prix décroissant", "Mise à jour récente"],
            label_visibility="collapsed")

        st.markdown("---")
        st.markdown('<small style="color:#8b949e">v2.1 · data.gouv.fr</small>',
                    unsafe_allow_html=True)

    # ── Main ──────────────────────────────────────────────────────────────────
    st.markdown("## ⛽ EcoPlein — Carburant le moins cher près de vous")

    if not user_lat or not user_lon:
        st.info("📍 Activez le GPS ou entrez une adresse dans la barre latérale.")
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v10",
            initial_view_state=pdk.ViewState(latitude=46.6, longitude=2.3, zoom=5)))
        return

    with st.spinner(f"Recherche stations {carb_name}…"):
        df, via_rpc = load_stations(sb, carb_col, user_lat, user_lon, float(radius))

    if df.empty:
        st.warning("Aucune station trouvée. Vérifiez la connexion ou augmentez le rayon.")
        return

    prix_col = f"{carb_col}_prix"
    maj_col  = f"{carb_col}_maj"

    # Coordonnées
    if "lat" not in df.columns:
        df[["lat", "lon"]] = df["geom"].apply(lambda g: pd.Series(extract_geom(g)))
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)
    df = df[(df["lat"] != 0) & (df["lon"] != 0)]

    # Distance si absente (fallback direct)
    if "distance_km" not in df.columns:
        df["distance_km"] = df.apply(
            lambda r: dist_km(user_lat, user_lon, r["lat"], r["lon"]) or 9999, axis=1)
    df = df[df["distance_km"].astype(float) <= radius]
    df = df[df[prix_col].notna()]

    if df.empty:
        st.warning("Aucune station avec prix dans ce rayon.")
        return

    # Filtres services
    def has(v, s): return s in safe_list(v)
    if f_24h:  df = df[df["horaires_automate_24_24"] == "Oui"]
    if f_cb:   df = df[df["services_service"].apply(lambda v: has(v, "Automate CB 24/24"))]
    if f_ev:   df = df[df["services_service"].apply(lambda v: has(v, "Bornes électriques"))]
    if f_wash: df = df[df["services_service"].apply(lambda v: has(v, "Lavage automatique"))]
    if f_shop: df = df[df["services_service"].apply(lambda v: has(v, "Boutique alimentaire"))]
    if f_dab:  df = df[df["services_service"].apply(
                   lambda v: has(v, "DAB (Distributeur automatique de billets)"))]

    if df.empty:
        st.warning("Aucune station ne correspond aux filtres.")
        return

    # Stats
    pv       = df[prix_col].astype(float)
    moyenne  = pv.mean()
    pmin, pmax = pv.min(), pv.max()
    eco_max  = round((pmax - pmin) * 50, 2)

    src = "🟢 RPC" if via_rpc else "🟡 Direct"
    st.caption(f"{src} · {len(df)} stations · rayon {radius} km")

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    for col, val, label, color in [
        (k1, pmin,    f"Prix min {carb_name}",         "#1a7f37"),
        (k2, moyenne, "Prix moyen",                    "#24292f"),
        (k3, pmax,    "Prix max",                      "#cf222e"),
        (k4, None,    f"{len(df)} stations · -{eco_max:.2f}€/50L", "#0550ae"),
    ]:
        with col:
            val_str = f"{val:.3f} €" if val is not None else str(len(df))
            st.markdown(
                f'<div class="kpi"><div class="kpi-v" style="color:{color}">{val_str}</div>'
                f'<div class="kpi-l">{label}</div></div>',
                unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tri
    if sort_by == "Prix croissant":
        df_d = df.sort_values(prix_col)
    elif sort_by == "Prix décroissant":
        df_d = df.sort_values(prix_col, ascending=False)
    elif sort_by == "Mise à jour récente":
        df_d = df.sort_values(maj_col, ascending=False, na_position="last")
    else:
        df_d = df.sort_values("distance_km")

    # Carte + Liste
    mc, lc = st.columns([1.3, 1])

    with mc:
        def pcol(p):
            if pd.isna(p): return [128,128,128,160]
            r = (float(p) - pmin) / max(pmax - pmin, 0.01)
            return [int(220*r), int(180*(1-r)), 40, 210]

        dm = df_d.copy()
        dm["color"]     = dm[prix_col].apply(pcol)
        dm["price_str"] = dm[prix_col].apply(lambda p: f"{float(p):.3f} €/L")
        dm["brand_str"] = dm.apply(lambda r: detect_brand(dict(r)) or "Station", axis=1)

        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v10",
            initial_view_state=pdk.ViewState(
                latitude=user_lat, longitude=user_lon, zoom=12),
            layers=[
                pdk.Layer("ScatterplotLayer",
                    data=dm[["lat","lon","color","price_str","brand_str","adresse","ville"]],
                    get_position=["lon","lat"], get_color="color", get_radius=250,
                    pickable=True, auto_highlight=True, highlight_color=[255,200,0,255]),
                pdk.Layer("ScatterplotLayer",
                    data=[{"lat": user_lat, "lon": user_lon}],
                    get_position=["lon","lat"], get_color=[0,112,243,255],
                    get_radius=180, pickable=False),
            ],
            tooltip={
                "html": "<b>{brand_str}</b><br>{adresse}, {ville}<br>"
                        "<span style='font-size:1.1em;font-weight:700'>{price_str}</span>",
                "style": {"backgroundColor":"#0d1117","color":"#e6edf3",
                          "fontSize":"13px","padding":"10px 12px","borderRadius":"6px"}
            }
        ))
        st.markdown(
            '<div style="display:flex;gap:16px;font-size:.8rem;color:#57606a;margin-top:4px">'
            '<span>🟢 Moins cher</span><span>🟡 Moyen</span>'
            '<span>🔴 Plus cher</span><span>🔵 Vous</span></div>',
            unsafe_allow_html=True)

    with lc:
        n = len(df_d)
        st.markdown(f"**📋 {n} station{'s' if n > 1 else ''} — {sort_by}**")
        for _, row in df_d.head(20).iterrows():
            render_card(dict(row), carb_col, user_lat, user_lon, moyenne)
        if n > 20:
            st.info(f"20/20 affichées · Réduisez le rayon pour plus de précision")


if __name__ == "__main__":
    main()
