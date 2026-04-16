# ─────────────────────────────────────────────────────────────────────────────
# EcoPlein v6 — Mobile-first · GPS · Navigation · Calculateur · Favoris
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from streamlit_js_eval import streamlit_js_eval, get_geolocation
from geopy.distance import geodesic
import pydeck as pdk
from datetime import datetime, timezone, time
import json, re, math

st.set_page_config(
    page_title="EcoPlein",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# META PWA — "Ajouter à l'écran d'accueil" sur mobile
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#0d1117">
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Espacement global ── */
.block-container { padding-top: .75rem !important; padding-bottom: 1rem !important; }

/* ── Hero card (station la moins chère) ── */
.eco-hero {
  background: linear-gradient(135deg, #0f2417 0%, #1b3a25 100%);
  border: 1.5px solid #2ea043;
  border-radius: 14px;
  padding: 16px 18px;
  margin: 8px 0 12px;
  box-shadow: 0 4px 20px rgba(46,160,67,.25);
}
.eco-hero h3 { color: #3fb950 !important; margin: 0 0 4px; font-size: 1rem; font-weight: 700; }
.eco-hero .sub { color: #8b949e !important; font-size: .8rem; margin: 0; }
@media (prefers-color-scheme: light) {
  .eco-hero { background: linear-gradient(135deg, #dafbe1 0%, #c9f2d3 100%); border-color: #2ea043; }
  .eco-hero h3 { color: #1a7f37 !important; }
  .eco-hero .sub { color: #57606a !important; }
}

/* ── Carte station ── */
.eco-card {
  background:    var(--secondary-background-color);
  color:         var(--text-color);
  border:        1px solid rgba(128,128,128,.18);
  border-radius: 10px;
  padding:       12px 14px;
  margin:        5px 0;
  box-shadow:    0 1px 4px rgba(0,0,0,.12);
  transition:    box-shadow .15s;
}
.eco-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,.22); }
.eco-card h4    { color: var(--text-color) !important; margin: 0 0 2px; font-size: .9rem; font-weight: 600; }
.eco-card .sub  { color: var(--text-color) !important; opacity: .6; font-size: .78rem; margin: 0; }

/* ── Prix ── */
.p-cheap { background:#1b2e23; color:#3fb950 !important; border-radius:20px; padding:3px 12px; font-weight:700; font-size:.95rem; display:inline-block; }
.p-avg   { background:#2d2000; color:#d29922 !important; border-radius:20px; padding:3px 12px; font-weight:700; font-size:.95rem; display:inline-block; }
.p-exp   { background:#2d0f10; color:#f85149 !important; border-radius:20px; padding:3px 12px; font-weight:700; font-size:.95rem; display:inline-block; }
@media (prefers-color-scheme: light) {
  .p-cheap { background:#dafbe1; color:#1a7f37 !important; }
  .p-avg   { background:#fff8c5; color:#9a6700 !important; }
  .p-exp   { background:#ffebe9; color:#cf222e !important; }
}

/* ── Fraîcheur ── */
.f-ok  { color: #3fb950 !important; font-size: .72rem; }
.f-mid { color: #d29922 !important; font-size: .72rem; }
.f-old { color: #f85149 !important; font-size: .72rem; }

/* ── Tendance prix ── */
.trend-up   { color: #f85149 !important; font-size: .78rem; font-weight: 600; }
.trend-down { color: #3fb950 !important; font-size: .78rem; font-weight: 600; }
.trend-flat { color: #8b949e !important; font-size: .78rem; }

/* ── Badges services ── */
.bg-g { background:#1b2e23; color:#3fb950 !important; border-radius:12px; padding:2px 8px; font-size:.68rem; margin:2px 2px 0 0; display:inline-block; }
.bg-b { background:#0c1929; color:#58a6ff !important; border-radius:12px; padding:2px 8px; font-size:.68rem; margin:2px 2px 0 0; display:inline-block; }
.bg-w { background:#161b22; color:#8b949e !important; border-radius:12px; padding:2px 8px; font-size:.68rem; margin:2px 2px 0 0; display:inline-block; }
@media (prefers-color-scheme: light) {
  .bg-g { background:#dafbe1; color:#1a7f37 !important; }
  .bg-b { background:#ddf4ff; color:#0550ae !important; }
  .bg-w { background:#f3f4f6; color:#57606a !important; }
}

/* ── Boutons navigation ── */
.nav-btn {
  display: inline-block;
  text-decoration: none !important;
  border-radius: 8px;
  padding: 5px 11px;
  font-size: .75rem;
  font-weight: 600;
  margin-right: 6px;
  margin-top: 6px;
  transition: opacity .15s;
}
.nav-btn:hover { opacity: .82; text-decoration: none !important; }
.btn-gmaps { background: #4285f4; color: #fff !important; }
.btn-waze  { background: #05c8f7; color: #000 !important; }
.btn-apple { background: #1c1c1e; color: #fff !important; }

/* ── Favoris ── */
.fav-star { cursor:pointer; font-size:1.1rem; }

/* ── Marque ── */
.brand { background:var(--text-color); color:var(--background-color) !important; border-radius:4px; padding:1px 6px; font-size:.65rem; font-weight:700; margin-right:5px; vertical-align:middle; display:inline-block; }

/* ── KPI ── */
.kpi { background:var(--secondary-background-color); border:1px solid rgba(128,128,128,.18); border-radius:10px; padding:10px 8px; text-align:center; }
.kpi-v { font-size:1.3rem; font-weight:700; color:var(--text-color) !important; line-height:1.2; }
.kpi-l { font-size:.67rem; color:var(--text-color) !important; opacity:.5; margin-top:1px; }

/* ── Suggestion adresse ── */
.sug-btn button {
  background: var(--secondary-background-color) !important;
  color: var(--text-color) !important;
  border: 1px solid rgba(128,128,128,.2) !important;
  text-align: left !important;
  font-size: .84rem !important;
  border-radius: 8px !important;
  padding: 8px 12px !important;
}
.sug-btn button:hover { background: var(--primary-color) !important; color: #fff !important; }

/* ── GPS status ── */
.gps-ok   { background:#1b2e23; color:#3fb950 !important; border-radius:8px; padding:10px 14px; font-size:.84rem; margin:6px 0; }
.gps-err  { background:#2d2000; color:#d29922 !important; border-radius:8px; padding:10px 14px; font-size:.84rem; margin:6px 0; }
.gps-fail { background:#2d0f10; color:#f85149 !important; border-radius:8px; padding:10px 14px; font-size:.84rem; margin:6px 0; }
@media (prefers-color-scheme: light) {
  .gps-ok   { background:#dafbe1; color:#1a7f37 !important; }
  .gps-err  { background:#fff8c5; color:#9a6700 !important; }
  .gps-fail { background:#ffebe9; color:#cf222e !important; }
}

/* ── Horaires ── */
.htbl { width:100%; font-size:.77rem; border-collapse:collapse; }
.htbl td { padding:3px 6px; border-bottom:1px solid rgba(128,128,128,.14); color:var(--text-color) !important; }
.htbl tr:last-child td { border-bottom:none; }
.htbl-today { background:rgba(46,160,67,.12) !important; }
.htbl-today td { color:#3fb950 !important; font-weight:600; }

/* ── Calculateur ── */
.calc-box { background:var(--secondary-background-color); border:1px solid rgba(128,128,128,.18); border-radius:10px; padding:12px 14px; margin-top:8px; }
.calc-result { font-size:1.05rem; font-weight:700; color:#58a6ff !important; }

/* ── Légende carte ── */
.map-legend { font-size:.73rem; opacity:.65; color:var(--text-color) !important; margin-top:4px; }

/* ── Badge "Ouvert" ── */
.badge-open   { background:#1b2e23; color:#3fb950 !important; border-radius:10px; padding:1px 8px; font-size:.68rem; font-weight:600; }
.badge-closed { background:#2d0f10; color:#f85149 !important; border-radius:10px; padding:1px 8px; font-size:.68rem; font-weight:600; }
@media (prefers-color-scheme: light) {
  .badge-open   { background:#dafbe1; color:#1a7f37 !important; }
  .badge-closed { background:#ffebe9; color:#cf222e !important; }
}

/* ── Mobile responsive ── */
@media (max-width: 768px) {
  .block-container { padding-left: .5rem !important; padding-right: .5rem !important; }
  .kpi-v { font-size: 1.05rem; }
  .kpi-l { font-size: .63rem; }
  .eco-card { padding: 10px 12px; }
  .eco-card h4 { font-size: .87rem; }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
CARBURANTS = {
    "Gazole": "gazole", "SP95": "sp95", "SP98": "sp98",
    "E10": "e10", "E85": "e85", "GPLc": "gplc",
}

# Ordre critique : du plus spécifique au plus générique
BRANDS = [
    ("TotalEnergies", ["TOTALENERGIES","TOTAL ENERGIES","TOTAL ACCESS","TOTAL-ACCESS"]),
    ("Esso",          ["ESSO"]),
    ("BP",            [" BP ","BP-","\"BP\""]),
    ("Shell",         ["SHELL"]),
    ("Avia",          ["AVIA"]),
    ("Agip",          ["AGIP"]),
    ("Elf",           ["ELF"]),
    ("E.Leclerc",     ["LECLERC"]),
    ("Intermarché",   ["INTERMARCHE","INTERMARCHÉ","MOUSQUETAIRES"]),
    ("Carrefour",     ["CARREFOUR"]),
    ("Super U",       ["SUPER U"]),
    ("Hyper U",       ["HYPER U"]),
    ("Système U",     ["SYSTEME U"]),
    ("Auchan",        ["AUCHAN"]),
    ("Casino",        ["CASINO"]),
    ("Géant",         ["GEANT","GÉANT"]),
    ("Lidl",          ["LIDL"]),
    ("Netto",         ["NETTO"]),
    ("Relais",        ["RELAIS"]),
    ("Total",         ["TOTAL"]),   # EN DERNIER — sinon il capte TotalEnergies
]

# Groupes de marques pour le filtre
BRAND_GROUPS = {
    "Grandes surfaces": ["E.Leclerc","Intermarché","Carrefour","Super U","Hyper U","Système U","Auchan","Casino","Géant","Lidl","Netto"],
    "Pétroliers": ["TotalEnergies","Total","Esso","BP","Shell","Avia","Agip","Elf"],
    "Autoroute / Relais": ["Relais"],
}

SVC = {
    "Automate CB 24/24":("💳","bg-g"),
    "Bornes électriques":("⚡","bg-g"),
    "Boutique alimentaire":("🛒","bg-b"),
    "Lavage automatique":("🚿","bg-b"),
    "Restauration à emporter":("🍔","bg-b"),
    "Restauration sur place":("🍽️","bg-b"),
    "Station de gonflage":("🔧","bg-w"),
    "Toilettes publiques":("🚻","bg-w"),
    "Wifi":("📶","bg-w"),
    "DAB (Distributeur automatique de billets)":("💰","bg-w"),
    "Boutique non alimentaire":("🏪","bg-w"),
    "Piste poids lourds":("🚛","bg-w"),
    "Services réparation / entretien":("🔩","bg-w"),
    "Bar":("☕","bg-b"),
    "Laverie":("🫧","bg-w"),
    "Relais colis":("📦","bg-w"),
    "Location de véhicule":("🚙","bg-w"),
    "Carburant additivé":("⚗️","bg-w"),
    "Vente de gaz domestique (Butane, Propane)":("🔥","bg-w"),
}

JOURS = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
CARTO_DARK  = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
CARTO_LIGHT = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def s(v): return str(v) if v is not None else ""

def sl(v):
    if isinstance(v, list): return v
    if isinstance(v, str):
        try: r = json.loads(v); return r if isinstance(r, list) else []
        except: return []
    return []

def geom_to_latlon(g):
    if isinstance(g, dict): return float(g.get("lat", 0)), float(g.get("lon", 0))
    if isinstance(g, str):
        try: d = json.loads(g); return float(d.get("lat", 0)), float(d.get("lon", 0))
        except: pass
    return 0.0, 0.0

def detect_brand(row):
    txt = f"{s(row.get('enseigne')).upper()} {s(row.get('adresse')).upper()}"
    for name, patterns in BRANDS:
        for p in patterns:
            if p in txt:
                return name
    return s(row.get("enseigne")).title() or None

def freshness(v):
    """Retourne (label, css_class). BUG FIX: gestion timezone correcte."""
    if not v:
        return "?", "f-old"
    try:
        raw = str(v).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        # Si pas de tzinfo, on suppose UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        d = (datetime.now(timezone.utc) - dt).days
        if d == 0: return "🟢 Aujourd'hui", "f-ok"
        if d <= 2: return f"🟡 {d}j", "f-mid"
        return f"🔴 {d}j", "f-old"
    except:
        return "?", "f-old"

def dist_km(a, b, c, d):
    try: return round(geodesic((a, b), (c, d)).km, 1)
    except: return None

def is_open_now(row):
    """Vérifie si la station est ouverte en ce moment selon les horaires."""
    hj = s(row.get("horaires_jour"))
    if not hj:
        return None  # inconnu
    if "Automate-24-24" in hj or row.get("horaires_automate_24_24") == "Oui":
        return True
    today = datetime.now().weekday()
    jour = JOURS[today]
    m = re.search(rf"{jour}(\d{{2}})\.(\d{{2}})-(\d{{2}})\.(\d{{2}})", hj)
    if not m:
        return False
    now = datetime.now().time()
    open_t = time(int(m.group(1)), int(m.group(2)))
    close_t = time(int(m.group(3)), int(m.group(4)))
    return open_t <= now <= close_t

def hours_html(raw):
    hj = s(raw)
    if not hj:
        return "<span style='opacity:.5;font-size:.8rem'>Non renseignés</span>"
    is24 = "Automate-24-24" in hj
    today = datetime.now().weekday()
    rows = ""
    for i, j in enumerate(JOURS):
        m = re.search(rf"{j}(\d{{2}}\.\d{{2}})-(\d{{2}}\.\d{{2}})", hj)
        css = ' class="htbl-today"' if i == today else ""
        h = (f"{m.group(1).replace('.','h')}–{m.group(2).replace('.','h')}"
             if m else ("24h/24" if is24 else "Fermé"))
        rows += f"<tr{css}><td style='width:70px;font-weight:600'>{j[:3]}.</td><td>{h}</td></tr>"
    b = '<span class="bg-g">🕐 Automate 24h/24</span><br>' if is24 else ""
    return f"{b}<table class='htbl'>{rows}</table>"

def nav_buttons_html(lat, lon, label):
    """Génère les boutons de navigation vers la station."""
    q = f"{lat},{lon}"
    name = label.replace('"', '').replace("'", "")
    gmaps = f"https://www.google.com/maps/dir/?api=1&destination={q}"
    waze  = f"https://waze.com/ul?ll={q}&navigate=yes"
    apple = f"http://maps.apple.com/?daddr={q}"
    return (
        f'<a href="{gmaps}" target="_blank" class="nav-btn btn-gmaps">🗺️ Google Maps</a>'
        f'<a href="{waze}"  target="_blank" class="nav-btn btn-waze">🚗 Waze</a>'
        f'<a href="{apple}" target="_blank" class="nav-btn btn-apple"> Apple Plans</a>'
    )

def open_status_html(row):
    status = is_open_now(row)
    if status is True:  return '<span class="badge-open">✅ Ouvert</span>'
    if status is False: return '<span class="badge-closed">❌ Fermé</span>'
    return ""

# ══════════════════════════════════════════════════════════════════════════════
# AUTOCOMPLETE ADRESSE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=30, show_spinner=False)
def search_addresses(q: str):
    if len(q) < 3: return []
    try:
        r = requests.get(
            "https://api-adresse.data.gouv.fr/search/",
            params={"q": q, "limit": 6, "autocomplete": 1},
            timeout=4,
        )
        return [
            {"label": f["properties"]["label"],
             "lat":   f["geometry"]["coordinates"][1],
             "lon":   f["geometry"]["coordinates"][0]}
            for f in r.json().get("features", [])
        ]
    except:
        return []

# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT STATIONS
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def load_stations(_sb, carb_col, lat, lon, radius):
    try:
        r = _sb.rpc("get_stations_proches", {
            "user_lat": lat, "user_lon": lon,
            "carburant_col": carb_col, "radius_km": radius,
        }).execute()
        if r.data:
            df = pd.DataFrame(r.data)
            df.rename(columns={"prix": f"{carb_col}_prix", "prix_maj": f"{carb_col}_maj"}, inplace=True)
            return df, True
    except Exception as e:
        st.caption(f"ℹ️ Requête directe (RPC: {str(e)[:55]})")

    try:
        # BUGFIX: filtre géo approximatif pour éviter de charger toutes les stations
        lat_min, lat_max = lat - radius/111, lat + radius/111
        lon_delta = radius / (111 * math.cos(math.radians(lat)))
        lon_min, lon_max = lon - lon_delta, lon + lon_delta

        r = (_sb.table("stations_carburant")
               .select("*")
               .not_.is_(f"{carb_col}_prix", "null")
               .gte("lat", lat_min).lte("lat", lat_max)
               .gte("lon", lon_min).lte("lon", lon_max)
               .execute())
        return pd.DataFrame(r.data or []), False
    except Exception as e2:
        st.error(f"❌ Supabase: {e2}")
        return pd.DataFrame(), False

# ══════════════════════════════════════════════════════════════════════════════
# FAVORIS (session state)
# ══════════════════════════════════════════════════════════════════════════════
def toggle_fav(station_id):
    favs = st.session_state.get("favorites", set())
    if station_id in favs:
        favs.discard(station_id)
    else:
        favs.add(station_id)
    st.session_state.favorites = favs

def is_fav(station_id):
    return station_id in st.session_state.get("favorites", set())

# ══════════════════════════════════════════════════════════════════════════════
# CALCULATEUR DE PLEIN
# ══════════════════════════════════════════════════════════════════════════════
def render_calculator(prix_min, carb_name):
    """Calculateur interactif dans le sidebar/expander."""
    st.markdown("**⛽ Calculateur de plein**")
    cap = st.slider(
        "Capacité du réservoir (L)",
        min_value=20, max_value=110, value=50, step=5,
        key="tank_cap",
    )
    fill_pct = st.slider(
        "Niveau actuel (% plein)",
        min_value=0, max_value=90, value=20, step=5,
        key="tank_fill",
    )
    litres_needed = cap * (1 - fill_pct / 100)
    cout = litres_needed * prix_min
    st.markdown(
        f'<div class="calc-box">'
        f'<div style="font-size:.8rem;opacity:.7">Litres à faire : <b>{litres_needed:.0f} L</b></div>'
        f'<div class="calc-result">💶 {cout:.2f} € au meilleur prix</div>'
        f'<div style="font-size:.72rem;opacity:.55;margin-top:3px">{carb_name} à {prix_min:.3f} €/L</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# HERO CARD — Station la moins chère
# ══════════════════════════════════════════════════════════════════════════════
def render_hero(row, carb_col, u_lat, u_lon, tank_l=50):
    pc = f"{carb_col}_prix"
    prix = float(row.get(pc, 0))
    d = row.get("distance_km") or dist_km(u_lat, u_lon, *geom_to_latlon(row.get("geom")))
    brand = detect_brand(row)
    b = f'<span class="brand">{brand}</span>' if brand else ""
    lat, lon = row.get("lat", 0), row.get("lon", 0)
    fr, _ = freshness(row.get(f"{carb_col}_maj"))
    open_s = open_status_html(row)
    cout = prix * tank_l

    st.markdown(f"""
<div class="eco-hero">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
    <div style="flex:1;min-width:0">
      <h3>🏆 Moins cher à {d} km</h3>
      <div style="margin:3px 0">{b}{s(row.get('adresse'))}</div>
      <div class="sub">{s(row.get('cp'))} {s(row.get('ville'))} &nbsp;·&nbsp; {fr} &nbsp;·&nbsp; {open_s}</div>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <span style="font-size:1.6rem;font-weight:800;color:#3fb950">{prix:.3f}€</span>
      <div style="font-size:.72rem;color:#8b949e">≈ {cout:.2f}€ / {tank_l}L</div>
    </div>
  </div>
  <div style="margin-top:10px">
    {nav_buttons_html(lat, lon, f"{brand or ''} {s(row.get('adresse'))}")}
  </div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# RENDER CARD
# ══════════════════════════════════════════════════════════════════════════════
def render_card(row, carb_col, u_lat, u_lon, moy, show_nav=True):
    pc = f"{carb_col}_prix"
    prix = row.get(pc)
    if prix is None: return
    pf = float(prix)
    ratio = (pf - moy) / max(abs(moy * .03), .001)
    cls = "p-cheap" if ratio < -.5 else ("p-exp" if ratio > .5 else "p-avg")
    fr, fr_cls = freshness(row.get(f"{carb_col}_maj"))
    d = row.get("distance_km") or dist_km(u_lat, u_lon, *geom_to_latlon(row.get("geom")))
    dist_s = f"📍 {d} km · " if d else ""
    brand = detect_brand(row)
    b = f'<span class="brand">{brand}</span>' if brand else ""

    prio = ["Automate CB 24/24", "Bornes électriques", "Lavage automatique", "Boutique alimentaire", "Wifi"]
    svcs = "".join(
        f'<span class="{SVC[sv][1]}">{SVC[sv][0]} {sv}</span>'
        for sv in sl(row.get("services_service")) if sv in prio and sv in SVC
    )
    if row.get("horaires_automate_24_24") == "Oui":
        svcs = '<span class="bg-g">🕐 24h/24</span>' + svcs

    sav = round((moy - pf) * 50, 2)
    sav_s = (f'<span style="color:#3fb950;font-size:.78rem;font-weight:600">💰 -{sav:.2f}€ vs moy (50L)</span>'
             if sav > .5 else "")

    open_s = open_status_html(row)
    station_id = str(row.get("id", f"{d}_{pf}"))
    fav_icon = "⭐" if is_fav(station_id) else "☆"
    lat, lon = row.get("lat", u_lat), row.get("lon", u_lon)

    st.markdown(f"""
<div class="eco-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
    <div style="flex:1;min-width:0">
      <h4>{b}{s(row.get('adresse'))}</h4>
      <p class="sub">{dist_s}{s(row.get('cp'))} {s(row.get('ville'))} {open_s}</p>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <span class="{cls}">{pf:.3f} €/L</span>
      <br><span class="{fr_cls}">{fr}</span>
    </div>
  </div>
  {f'<div style="margin-top:6px;line-height:1.8">{svcs}</div>' if svcs else ''}
  {f'<div style="margin-top:4px">{sav_s}</div>' if sav_s else ''}
</div>""", unsafe_allow_html=True)

    # Expander avec horaires, services, navigation et favori
    with st.expander("📋 Détails, horaires & navigation"):
        # Favori
        fav_col, _ = st.columns([1, 4])
        with fav_col:
            if st.button(f"{fav_icon} Favori", key=f"fav_{station_id}",
                         use_container_width=True):
                toggle_fav(station_id)
                st.rerun()

        # Navigation
        st.markdown("**🧭 Y aller**")
        st.markdown(nav_buttons_html(lat, lon, f"{brand or ''} {s(row.get('adresse'))}"),
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Horaires**")
            st.markdown(hours_html(row.get("horaires_jour")), unsafe_allow_html=True)
        with c2:
            st.markdown("**Services**")
            all_sv = sl(row.get("services_service"))
            if all_sv:
                st.markdown(
                    "".join(f'<span class="{SVC.get(sv,("","bg-w"))[1]}">'
                            f'{SVC.get(sv,("•","bg-w"))[0]} {sv}</span>' for sv in all_sv),
                    unsafe_allow_html=True)
            else:
                st.caption("Non renseignés")

# ══════════════════════════════════════════════════════════════════════════════
# BLOC LOCALISATION
# ══════════════════════════════════════════════════════════════════════════════
def location_block():
    tabs = st.tabs(["📍 GPS auto", "🔍 Adresse"])

    with tabs[0]:
        st.markdown("<small>Votre navigateur demandera l'autorisation GPS.</small>",
                    unsafe_allow_html=True)
        do_gps = st.button("📡 Me localiser", key="gps_btn",
                           use_container_width=True, type="primary")
        if do_gps or st.session_state.get("gps_asked"):
            st.session_state.gps_asked = True
            with st.spinner("Localisation…"):
                try: loc = get_geolocation()
                except: loc = None
            if loc and isinstance(loc, dict) and loc.get("coords"):
                c = loc["coords"]
                lat, lon = c["latitude"], c["longitude"]
                acc = c.get("accuracy", 0)
                st.session_state.gps_result = (lat, lon)
                st.markdown(f'<div class="gps-ok">✅ ±{acc:.0f}m</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="gps-err">⚠️ GPS indisponible — vérifiez les permissions '
                    'ou utilisez la recherche adresse.</div>', unsafe_allow_html=True)
                if st.button("🔄 Réessayer", key="gps_retry"):
                    st.session_state.gps_asked = True; st.rerun()

        if "gps_result" in st.session_state:
            lat, lon = st.session_state.gps_result
            st.markdown(f'<div class="gps-ok">📍 {lat:.5f}, {lon:.5f}</div>',
                        unsafe_allow_html=True)
            return lat, lon, "Ma position GPS"

    with tabs[1]:
        if "addr_selected" in st.session_state:
            info = st.session_state.addr_selected
            st.markdown(f'<div class="gps-ok">✅ {info["label"]}</div>', unsafe_allow_html=True)
            if st.button("✏️ Changer", key="addr_reset", use_container_width=True):
                del st.session_state.addr_selected; st.rerun()
            return info["lat"], info["lon"], info["label"]

        query = st.text_input("addr_q", "",
                              placeholder="Ex: 18 rue Jules Guesde, Lille",
                              label_visibility="collapsed", key="addr_query_field")
        if query and len(query) >= 3:
            with st.spinner("Suggestions…"):
                suggestions = search_addresses(query)
            if suggestions:
                st.markdown("**Sélectionnez :**")
                for i, sug in enumerate(suggestions):
                    with st.container():
                        st.markdown('<div class="sug-btn">', unsafe_allow_html=True)
                        if st.button(f"📍 {sug['label']}", key=f"sug_{i}",
                                     use_container_width=True):
                            st.session_state.addr_selected = sug; st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            elif len(query) >= 5:
                st.caption("Aucun résultat.")
        elif query:
            st.caption("3 caractères minimum…")

    return None, None, None

# ══════════════════════════════════════════════════════════════════════════════
# SECTION RÉSULTATS
# ══════════════════════════════════════════════════════════════════════════════
def show_results(sb, carb_col, carb_name, user_lat, user_lon,
                 radius, sort_by, filters, is_mobile, tank_cap=50, dark_mode=True):

    with st.spinner(f"Recherche {carb_name} dans {radius} km…"):
        df, via_rpc = load_stations(sb, carb_col, user_lat, user_lon, float(radius))

    if df.empty:
        st.warning("Aucune station trouvée. Augmentez le rayon ou vérifiez la connexion.")
        return

    pc = f"{carb_col}_prix"
    mc = f"{carb_col}_maj"

    if "lat" not in df.columns:
        df[["lat","lon"]] = df["geom"].apply(lambda g: pd.Series(geom_to_latlon(g)))
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)
    df = df[(df["lat"] != 0) & (df["lon"] != 0)]

    if "distance_km" not in df.columns:
        df["distance_km"] = df.apply(
            lambda r: dist_km(user_lat, user_lon, r["lat"], r["lon"]) or 9999, axis=1)

    df = df[df["distance_km"].astype(float) <= radius]
    df = df[df[pc].notna()]
    if df.empty:
        st.warning("Aucune station dans ce rayon."); return

    # ── Filtres ──
    f_24h, f_cb, f_ev, f_wash, f_open, brand_group = filters
    def has(v, x): return x in sl(v)

    if f_24h:  df = df[df["horaires_automate_24_24"] == "Oui"]
    if f_cb:   df = df[df["services_service"].apply(lambda v: has(v, "Automate CB 24/24"))]
    if f_ev:   df = df[df["services_service"].apply(lambda v: has(v, "Bornes électriques"))]
    if f_wash: df = df[df["services_service"].apply(lambda v: has(v, "Lavage automatique"))]
    if f_open: df = df[df.apply(is_open_now, axis=1) == True]

    # Filtre par groupe de marque
    if brand_group and brand_group != "Toutes":
        allowed = BRAND_GROUPS.get(brand_group, [])
        df = df[df.apply(lambda r: detect_brand(dict(r)) in allowed, axis=1)]

    if df.empty:
        st.warning("Aucune station avec ces filtres."); return

    pv = df[pc].astype(float)
    moy = pv.mean(); pmin, pmax = pv.min(), pv.max()

    # ── KPIs ──
    st.caption(f"{'🟢 Temps réel' if via_rpc else '🟡 Direct'} · {len(df)} stations · {carb_name}")
    k1, k2, k3, k4 = st.columns(4)
    eco_50 = round((pmax - pmin) * 50, 2)
    for col, val, lbl, clr in [
        (k1, f"{pmin:.3f}€", f"Min {carb_name}", "#3fb950"),
        (k2, f"{moy:.3f}€",  "Moyenne",          "var(--text-color)"),
        (k3, f"{pmax:.3f}€", "Max",               "#f85149"),
        (k4, f"−{eco_50:.2f}€", f"Éco/{tank_cap}L", "#58a6ff"),
    ]:
        with col:
            # Ajuste l'éco au bon volume de réservoir
            display_val = val if lbl != f"Éco/{tank_cap}L" else f"−{round((pmax-pmin)*tank_cap,2):.2f}€"
            st.markdown(
                f'<div class="kpi"><div class="kpi-v" style="color:{clr}">{display_val}</div>'
                f'<div class="kpi-l">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tri ──
    if   sort_by == "Prix ↑":  df_d = df.sort_values(pc)
    elif sort_by == "Prix ↓":  df_d = df.sort_values(pc, ascending=False)
    elif sort_by == "Récent":  df_d = df.sort_values(mc, ascending=False, na_position="last")
    else:                      df_d = df.sort_values("distance_km")

    # ── Hero card (station la moins chère) ──
    best = df_d[df_d[pc] == pmin].iloc[0] if not df_d.empty else None
    if best is not None and sort_by in ("Distance", "Prix ↑"):
        render_hero(dict(best), carb_col, user_lat, user_lon, tank_cap)

    # ── Carte pydeck ──
    def pcol(p):
        if pd.isna(p): return [128, 128, 128, 150]
        r = (float(p) - pmin) / max(pmax - pmin, .01)
        return [int(220*r), int(180*(1-r)), 40, 220]

    dm = df_d.copy()
    dm["color"] = dm[pc].apply(pcol)
    dm["price_str"] = dm[pc].apply(lambda p: f"{float(p):.3f} €/L")
    dm["brand_str"] = dm.apply(lambda r: detect_brand(dict(r)) or "Station", axis=1)
    for cn in ["adresse", "ville"]:
        if cn not in dm.columns: dm[cn] = ""

    map_style = CARTO_DARK if dark_mode else CARTO_LIGHT
    deck = pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=user_lat, longitude=user_lon, zoom=12, pitch=0),
        layers=[
            pdk.Layer("ScatterplotLayer",
                data=dm[["lat","lon","color","price_str","brand_str","adresse","ville"]],
                get_position=["lon","lat"], get_color="color", get_radius=250,
                pickable=True, auto_highlight=True, highlight_color=[255,200,0,255]),
            pdk.Layer("ScatterplotLayer",
                data=pd.DataFrame([{"lat": user_lat, "lon": user_lon}]),
                get_position=["lon","lat"], get_color=[0,112,243,255],
                get_radius=200, pickable=False),
        ],
        tooltip={
            "html": "<b>{brand_str}</b><br>{adresse}, {ville}<br>"
                    "<span style='font-size:1.1em;font-weight:700'>{price_str}</span>",
            "style": {"backgroundColor":"#0d1117","color":"#e6edf3",
                      "fontSize":"13px","padding":"10px 12px","borderRadius":"6px"},
        },
    )

    legend = ('<div class="map-legend">🟢 Moins cher &nbsp;·&nbsp; '
              '🟡 Moyen &nbsp;·&nbsp; 🔴 Plus cher &nbsp;·&nbsp; 🔵 Vous</div>')

    if is_mobile:
        tab_map, tab_list, tab_favs = st.tabs(["🗺️ Carte", "📋 Stations", "⭐ Favoris"])
        with tab_map:
            st.pydeck_chart(deck, use_container_width=True)
            st.markdown(legend, unsafe_allow_html=True)
        with tab_list:
            st.markdown(f"**{len(df_d)} stations · {sort_by}**")
            for _, row in df_d.head(30).iterrows():
                render_card(dict(row), carb_col, user_lat, user_lon, moy)
        with tab_favs:
            favs = st.session_state.get("favorites", set())
            fav_df = df_d[df_d.apply(lambda r: str(r.get("id","")) in favs, axis=1)]
            if fav_df.empty:
                st.info("⭐ Épinglez vos stations favorites depuis la vue Stations.")
            else:
                for _, row in fav_df.iterrows():
                    render_card(dict(row), carb_col, user_lat, user_lon, moy)
    else:
        mc_col, lc_col = st.columns([1.3, 1])
        with mc_col:
            st.pydeck_chart(deck, use_container_width=True)
            st.markdown(legend, unsafe_allow_html=True)
        with lc_col:
            st.markdown(f"**📋 {len(df_d)} stations · {sort_by}**")
            for _, row in df_d.head(20).iterrows():
                render_card(dict(row), carb_col, user_lat, user_lon, moy)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    sb = get_supabase()

    # Détection viewport + thème (évite le flash en cachant le résultat)
    screen_w = streamlit_js_eval(js_expressions="window.innerWidth", key="vp")
    dark_mode = streamlit_js_eval(
        js_expressions="window.matchMedia('(prefers-color-scheme: dark)').matches",
        key="dark_mode",
    )
    is_mobile = isinstance(screen_w, (int, float)) and screen_w < 768
    use_dark  = dark_mode is not False  # True par défaut

    if is_mobile:
        # ── MOBILE ────────────────────────────────────────────────────────────
        st.markdown("### ⛽ EcoPlein")

        ca, cb = st.columns([3, 1])
        with ca:
            carb_name = st.selectbox("Carburant", list(CARBURANTS.keys()),
                                     label_visibility="collapsed", key="carb_m")
        with cb:
            # Slider plus ergonomique sur mobile
            radius = st.select_slider("km", options=[2,5,10,15,20,30,50], value=10,
                                      label_visibility="collapsed", key="rad_m")
            st.caption(f"📏 {radius}km")

        carb_col = CARBURANTS[carb_name]

        with st.expander("📍 Ma position",
                         expanded=("gps_result" not in st.session_state
                                   and "addr_selected" not in st.session_state)):
            user_lat, user_lon, loc_label = location_block()

        if user_lat is None:
            if "gps_result" in st.session_state:
                user_lat, user_lon = st.session_state.gps_result
            elif "addr_selected" in st.session_state:
                info = st.session_state.addr_selected
                user_lat, user_lon = info["lat"], info["lon"]

        with st.expander("⚙️ Filtres & tri"):
            f1, f2 = st.columns(2)
            with f1:
                f_24h  = st.checkbox("🕐 24h/24",     key="m_24h")
                f_cb   = st.checkbox("💳 CB 24/24",   key="m_cb")
                f_open = st.checkbox("✅ Ouvert now",  key="m_open")
            with f2:
                f_ev   = st.checkbox("⚡ Bornes",      key="m_ev")
                f_wash = st.checkbox("🚿 Lavage",      key="m_wash")
            brand_group = st.selectbox(
                "Marque", ["Toutes"] + list(BRAND_GROUPS.keys()),
                label_visibility="collapsed", key="m_brand",
            )
            sort_by = st.radio("Tri", ["Distance","Prix ↑","Prix ↓","Récent"],
                               horizontal=True, label_visibility="collapsed", key="sort_m")

        # Calculateur compact en mobile
        if st.session_state.get("show_calc"):
            with st.expander("⛽ Calculateur de plein", expanded=True):
                prix_min_est = st.session_state.get("prix_min_cache", 1.8)
                render_calculator(prix_min_est, carb_name)

        if user_lat and user_lon:
            show_results(sb, carb_col, carb_name, user_lat, user_lon,
                         radius, sort_by,
                         (f_24h, f_cb, f_ev, f_wash, f_open, brand_group),
                         True, dark_mode=use_dark)
        else:
            st.info("📍 Ouvrez **Ma position** pour démarrer.")

    else:
        # ── DESKTOP ───────────────────────────────────────────────────────────
        with st.sidebar:
            st.markdown("## ⛽ EcoPlein")
            st.caption("Carburant moins cher près de vous")
            st.divider()

            st.markdown("**Carburant**")
            carb_name = st.selectbox("Carburant", list(CARBURANTS.keys()),
                                     label_visibility="collapsed", key="carb_d")
            carb_col  = CARBURANTS[carb_name]

            st.markdown("**Rayon**")
            radius = st.slider("Rayon", 2, 50, 10, format="%d km",
                               label_visibility="collapsed", key="rad_d")
            st.divider()

            st.markdown("**Ma position**")
            user_lat, user_lon, _ = location_block()
            if user_lat is None:
                if "gps_result" in st.session_state:
                    user_lat, user_lon = st.session_state.gps_result
                elif "addr_selected" in st.session_state:
                    info = st.session_state.addr_selected
                    user_lat, user_lon = info["lat"], info["lon"]
            st.divider()

            st.markdown("**Filtres**")
            f_24h  = st.checkbox("🕐 Automate 24h/24",   key="d_24h")
            f_cb   = st.checkbox("💳 CB 24/24",           key="d_cb")
            f_ev   = st.checkbox("⚡ Bornes électriques", key="d_ev")
            f_wash = st.checkbox("🚿 Lavage automatique", key="d_wash")
            f_open = st.checkbox("✅ Ouvert maintenant",  key="d_open")
            brand_group = st.selectbox("Marque", ["Toutes"] + list(BRAND_GROUPS.keys()),
                                       label_visibility="collapsed", key="d_brand")
            st.divider()

            st.markdown("**Tri**")
            sort_by = st.radio("Tri", ["Distance","Prix ↑","Prix ↓","Récent"],
                               label_visibility="collapsed", key="sort_d")
            st.divider()

            # Calculateur de plein — sidebar desktop
            st.markdown("**⛽ Calculateur de plein**")
            tank_cap = st.slider("Réservoir (L)", 20, 110, 50, 5,
                                 label_visibility="collapsed", key="tank_d")
            fill_pct = st.slider("Niveau actuel (%)", 0, 90, 20, 5,
                                 label_visibility="collapsed", key="fill_d")
            st.session_state.tank_cap  = tank_cap
            st.session_state.fill_pct  = fill_pct
            st.divider()
            st.caption("v6.0 · data.gouv.fr")

        st.markdown("## ⛽ EcoPlein — Carburant le moins cher")

        if not user_lat or not user_lon:
            st.info("📍 Activez le GPS ou entrez une adresse dans la barre latérale.")
            st.pydeck_chart(pdk.Deck(
                map_style=CARTO_DARK if use_dark else CARTO_LIGHT,
                initial_view_state=pdk.ViewState(latitude=46.6, longitude=2.3, zoom=5)))
            return

        tank_cap = st.session_state.get("tank_cap", 50)
        show_results(sb, carb_col, carb_name, user_lat, user_lon,
                     radius, sort_by,
                     (f_24h, f_cb, f_ev, f_wash, f_open, brand_group),
                     False, tank_cap=tank_cap, dark_mode=use_dark)


if __name__ == "__main__":
    main()
