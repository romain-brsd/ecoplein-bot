import streamlit as st
import pandas as pd
from supabase import create_client
from streamlit_js_eval import streamlit_js_eval, get_geolocation
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import pydeck as pdk
from datetime import datetime, timezone
import json, re, time

st.set_page_config(page_title="EcoPlein", page_icon="⛽", layout="wide",
                   initial_sidebar_state="collapsed",
                   menu_items={"About": "EcoPlein v4.0 — Mobile First"})

# ══════════════════════════════════════════════════════════════════════════════
# PALETTES
# ══════════════════════════════════════════════════════════════════════════════
LIGHT = {
    "--c-bg":"#f6f8fa","--c-sidebar":"#0d1117","--c-card":"#ffffff",
    "--c-card-hover":"#f0f3f6","--c-border":"rgba(31,35,40,.15)",
    "--c-text":"#24292f","--c-muted":"#57606a","--c-faint":"#8c959f",
    "--c-cheap-bg":"#dafbe1","--c-cheap-fg":"#1a7f37",
    "--c-avg-bg":"#fff8c5","--c-avg-fg":"#9a6700",
    "--c-exp-bg":"#ffebe9","--c-exp-fg":"#cf222e",
    "--c-svc-g-bg":"#dafbe1","--c-svc-g-fg":"#1a7f37",
    "--c-svc-b-bg":"#ddf4ff","--c-svc-b-fg":"#0550ae",
    "--c-rup-t-bg":"#fff8c5","--c-rup-t-fg":"#9a6700",
    "--c-rup-d-bg":"#ffebe9","--c-rup-d-fg":"#cf222e",
    "--c-kpi-bg":"#ffffff","--c-brand-bg":"#0d1117","--c-brand-fg":"#e6edf3",
    "--c-saving":"#1a7f37","--c-input-bg":"#ffffff","--c-input-border":"#d0d7de",
    "--shadow":"0 1px 3px rgba(31,35,40,.08)","--shadow-h":"0 4px 14px rgba(31,35,40,.14)",
    "--c-tab-active-bg":"#0d1117","--c-tab-active-fg":"#ffffff",
    "--c-gps-btn":"linear-gradient(135deg,#1f6feb,#388bfd)",
    "--c-search-btn":"linear-gradient(135deg,#238636,#2ea043)",
}
DARK = {
    "--c-bg":"#0d1117","--c-sidebar":"#010409","--c-card":"#161b22",
    "--c-card-hover":"#1c2128","--c-border":"rgba(240,246,252,.1)",
    "--c-text":"#e6edf3","--c-muted":"#8b949e","--c-faint":"#6e7681",
    "--c-cheap-bg":"#1b2e23","--c-cheap-fg":"#3fb950",
    "--c-avg-bg":"#2d2000","--c-avg-fg":"#d29922",
    "--c-exp-bg":"#2d0f10","--c-exp-fg":"#f85149",
    "--c-svc-g-bg":"#1b2e23","--c-svc-g-fg":"#3fb950",
    "--c-svc-b-bg":"#0c1929","--c-svc-b-fg":"#58a6ff",
    "--c-rup-t-bg":"#2d2000","--c-rup-t-fg":"#d29922",
    "--c-rup-d-bg":"#2d0f10","--c-rup-d-fg":"#f85149",
    "--c-kpi-bg":"#161b22","--c-brand-bg":"#e6edf3","--c-brand-fg":"#0d1117",
    "--c-saving":"#3fb950","--c-input-bg":"#161b22","--c-input-border":"#30363d",
    "--shadow":"0 1px 3px rgba(0,0,0,.4)","--shadow-h":"0 4px 14px rgba(0,0,0,.6)",
    "--c-tab-active-bg":"#e6edf3","--c-tab-active-fg":"#0d1117",
    "--c-gps-btn":"linear-gradient(135deg,#1f6feb,#388bfd)",
    "--c-search-btn":"linear-gradient(135deg,#238636,#2ea043)",
}

def inject_theme(mode):
    lv="\n".join(f"  {k}:{v};" for k,v in LIGHT.items())
    dv="\n".join(f"  {k}:{v};" for k,v in DARK.items())
    if   mode=="Clair ☀️":  root=f":root{{{lv}}}"
    elif mode=="Sombre 🌙": root=f":root{{{dv}}}"
    else: root=f":root{{{lv}}} @media(prefers-color-scheme:dark){{:root{{{dv}}}}}"
    st.markdown(f"<style>{root}</style>", unsafe_allow_html=True)

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown("""<style>
/* ── Backgrounds ── */
[data-testid="stAppViewContainer"],
[data-testid="stMainBlockContainer"],.main,.block-container{
  background:var(--c-bg)!important;}
[data-testid="stSidebar"]{background:var(--c-sidebar)!important;}

/* ── Textes principaux ── */
[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3,
[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] .stMarkdown p,
[data-testid="stMainBlockContainer"] small,
[data-testid="stMainBlockContainer"] .stCaption{
  color:var(--c-text)!important;}

/* ── Inputs ── */
input,textarea,.stTextInput input,.stSelectbox>div>div{
  background:var(--c-input-bg)!important;
  color:var(--c-text)!important;
  border-color:var(--c-input-border)!important;}
input::placeholder,textarea::placeholder{color:var(--c-faint)!important;}

/* ── Selectbox dropdown ── */
[data-baseweb="select"] [data-testid="stMarkdownContainer"],
[data-baseweb="popover"]{
  background:var(--c-card)!important;color:var(--c-text)!important;}
[role="listbox"],[role="option"]{
  background:var(--c-card)!important;color:var(--c-text)!important;}
[aria-selected="true"]{background:var(--c-card-hover)!important;}

/* ── Slider ── */
[data-testid="stSlider"] span,[data-testid="stSlider"] p{color:var(--c-text)!important;}
[data-testid="stSlider"] [data-baseweb="slider"] div:first-child{
  background:var(--c-border)!important;}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label span{color:var(--c-text)!important;}

/* ── Tabs (mobile navigation) ── */
[data-testid="stTabs"]{background:transparent!important;}
[data-testid="stTabs"] button{
  color:var(--c-muted)!important;
  background:transparent!important;
  border:none!important;
  font-weight:500;font-size:.9rem;padding:10px 16px;
  transition:all .2s;}
[data-testid="stTabs"] button[aria-selected="true"]{
  color:var(--c-text)!important;
  border-bottom:2px solid var(--c-text)!important;
  font-weight:700;}
[data-testid="stTabsContent"]{background:transparent!important;}

/* ── Expander ── */
[data-testid="stExpander"]{
  background:var(--c-card)!important;
  border:1px solid var(--c-border)!important;
  border-radius:8px!important;}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary{color:var(--c-text)!important;}
[data-testid="stExpanderDetails"]{background:var(--c-card)!important;}

/* ── Alerts ── */
[data-testid="stAlert"]{
  background:var(--c-card)!important;
  border-color:var(--c-border)!important;
  color:var(--c-text)!important;}

/* ── Sidebar dark ── */
[data-testid="stSidebar"] *{color:#e6edf3!important;}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] [data-baseweb="select"]>div{
  background:#161b22!important;border-color:#30363d!important;}
[data-testid="stSidebar"] hr{border-color:#21262d!important;margin:8px 0!important;}

/* ── Carte station ── */
.eco-card{
  background:var(--c-card);
  border:1px solid var(--c-border);
  border-radius:10px;padding:14px 16px;margin:6px 0;
  box-shadow:var(--shadow);transition:box-shadow .15s,background .2s;}
.eco-card:hover{background:var(--c-card-hover);box-shadow:var(--shadow-h);}
.eco-card h4{color:var(--c-text)!important;margin:0 0 4px;font-size:.95rem;font-weight:600;line-height:1.3;}
.eco-card .addr{color:var(--c-muted)!important;font-size:.8rem;margin:0;line-height:1.4;}

/* ── Prix ── */
.prix-cheap{display:inline-block;background:var(--c-cheap-bg);color:var(--c-cheap-fg)!important;border-radius:20px;padding:4px 14px;font-weight:700;font-size:1.05rem;}
.prix-avg  {display:inline-block;background:var(--c-avg-bg);  color:var(--c-avg-fg)!important;  border-radius:20px;padding:4px 14px;font-weight:700;font-size:1.05rem;}
.prix-exp  {display:inline-block;background:var(--c-exp-bg);  color:var(--c-exp-fg)!important;  border-radius:20px;padding:4px 14px;font-weight:700;font-size:1.05rem;}
.fr-today {color:var(--c-cheap-fg)!important;font-size:.75rem;}
.fr-recent{color:var(--c-avg-fg)!important;  font-size:.75rem;}
.fr-old   {color:var(--c-exp-fg)!important;  font-size:.75rem;}

/* ── Badges ── */
.brand-tag{display:inline-block;background:var(--c-brand-bg);color:var(--c-brand-fg)!important;border-radius:4px;padding:2px 8px;font-size:.7rem;font-weight:700;letter-spacing:.03em;margin-right:6px;vertical-align:middle;}
.svc-g{display:inline-block;background:var(--c-svc-g-bg);color:var(--c-svc-g-fg)!important;border-radius:12px;padding:2px 8px;font-size:.7rem;margin:2px 2px 0 0;}
.svc-b{display:inline-block;background:var(--c-svc-b-bg);color:var(--c-svc-b-fg)!important;border-radius:12px;padding:2px 8px;font-size:.7rem;margin:2px 2px 0 0;}
.rup-t{display:inline-block;background:var(--c-rup-t-bg);color:var(--c-rup-t-fg)!important;border-radius:4px;padding:2px 8px;font-size:.7rem;margin:2px 2px 0 0;}
.rup-d{display:inline-block;background:var(--c-rup-d-bg);color:var(--c-rup-d-fg)!important;border-radius:4px;padding:2px 8px;font-size:.7rem;margin:2px 2px 0 0;}

/* ── KPI ── */
.kpi{background:var(--c-kpi-bg);border:1px solid var(--c-border);border-radius:10px;padding:14px 10px;text-align:center;}
.kpi-v{font-size:1.5rem;font-weight:700;color:var(--c-text)!important;line-height:1.2;}
.kpi-l{font-size:.72rem;color:var(--c-muted)!important;margin-top:2px;}

/* ── GPS / search box ── */
.loc-box{background:var(--c-card);border:1px solid var(--c-border);border-radius:10px;padding:14px 16px;margin-bottom:12px;}
.loc-box p{color:var(--c-text)!important;margin:0;}
.saving{color:var(--c-saving)!important;font-size:.8rem;font-weight:600;}

/* ── Horaires ── */
.htbl{width:100%;font-size:.78rem;border-collapse:collapse;}
.htbl td{padding:3px 8px;border-bottom:1px solid var(--c-border);color:var(--c-text)!important;}
.htbl tr:last-child td{border-bottom:none;}
.htbl .d{font-weight:600;width:80px;}
.htbl-today{background:var(--c-svc-g-bg)!important;}
.htbl-today td{color:var(--c-svc-g-fg)!important;}

.map-legend{display:flex;gap:12px;flex-wrap:wrap;font-size:.75rem;color:var(--c-muted)!important;margin-top:6px;}

/* ══════════════════════════════════════════════════
   RESPONSIVE MOBILE FIRST
   ══════════════════════════════════════════════════ */

/* Réduire le padding Streamlit par défaut */
.block-container{padding-top:1rem!important;padding-bottom:1rem!important;}

@media(max-width:768px){
  /* Colonnes → pleine largeur */
  [data-testid="stHorizontalBlock"]{flex-direction:column!important;gap:0!important;}
  [data-testid="stHorizontalBlock"]>div{width:100%!important;min-width:100%!important;flex:none!important;}
  /* KPI compact */
  .kpi{padding:10px 6px;} .kpi-v{font-size:1.2rem;} .kpi-l{font-size:.65rem;}
  /* Padding réduit */
  .block-container{padding-left:.75rem!important;padding-right:.75rem!important;}
  /* Carte pleine largeur */
  [data-testid="stDeckGlJsonChart"]{border-radius:10px!important;}
}
@media(max-width:480px){
  .eco-card{padding:10px 12px;}
  .eco-card h4{font-size:.88rem;}
  .kpi-v{font-size:1rem;}
  .block-container{padding-left:.5rem!important;padding-right:.5rem!important;}
}

/* Boutons Streamlit larges */
[data-testid="stButton"]>button{
  border-radius:8px!important;font-weight:600!important;
  transition:all .15s!important;}
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
CARBURANTS = {"⛽ Gazole":"gazole","🟡 SP95":"sp95","🔵 SP98":"sp98",
              "🌿 E10":"e10","♻️ E85":"e85","🔵 GPLc":"gplc"}
BRANDS = [
    ("TotalEnergies",["TOTALENERGIES","TOTAL ENERGIES","TOTAL ACCESS"]),
    ("Total",["TOTAL"]),("Esso",["ESSO"]),("BP",[" BP ","BP-"]),
    ("Shell",["SHELL"]),("Avia",["AVIA"]),("Agip",["AGIP"]),("Elf",["ELF"]),
    ("E.Leclerc",["LECLERC"]),("Intermarché",["INTERMARCHE","INTERMARCHÉ","MOUSQUETAIRES"]),
    ("Carrefour",["CARREFOUR"]),("Super U",["SUPER U","SUPERMARCHE U"]),
    ("Hyper U",["HYPER U"]),("Système U",["SYSTEME U","SYSTÈME U"]),
    ("Auchan",["AUCHAN"]),("Casino",["CASINO"]),("Géant",["GEANT","GÉANT"]),
    ("Lidl",["LIDL"]),("Netto",["NETTO"]),("Relais",["RELAIS"]),
]
SERVICES_MAP = {
    "Automate CB 24/24":("💳","svc-g"),"Bornes électriques":("⚡","svc-g"),
    "Boutique alimentaire":("🛒","svc-b"),"Boutique non alimentaire":("🏪","svc-b"),
    "Lavage automatique":("🚿","svc-b"),"Lavage manuel":("🧹","svc-b"),
    "Station de gonflage":("🔧","svc-b"),"Toilettes publiques":("🚻","svc-b"),
    "Restauration à emporter":("🍔","svc-b"),"Restauration sur place":("🍽️","svc-b"),
    "Piste poids lourds":("🚛","svc-b"),
    "DAB (Distributeur automatique de billets)":("💰","svc-b"),
    "Services réparation / entretien":("🔩","svc-b"),
    "Carburant additivé":("⚗️","svc-b"),"Location de véhicule":("🚙","svc-b"),
    "Vente de gaz domestique (Butane, Propane)":("🔥","svc-b"),
    "Bar":("☕","svc-b"),"Wifi":("📶","svc-b"),"Laverie":("🫧","svc-b"),
    "Relais colis":("📦","svc-b"),
}
JOURS=["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
CARTO_LIGHT="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
CARTO_DARK ="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"],st.secrets["SUPABASE_KEY"])

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def safe_str(v): return str(v) if v is not None else ""
def safe_list(v):
    if v is None: return []
    if isinstance(v,list): return v
    if isinstance(v,str):
        try: p=json.loads(v); return p if isinstance(p,list) else []
        except: return []
    return []
def extract_geom(g):
    if isinstance(g,dict): return float(g.get("lat",0)),float(g.get("lon",0))
    if isinstance(g,str):
        try: d=json.loads(g); return float(d.get("lat",0)),float(d.get("lon",0))
        except: pass
    return 0.0,0.0
def detect_brand(row):
    e=safe_str(row.get("enseigne"))
    t=f"{e.upper()} {safe_str(row.get('adresse')).upper()} {safe_str(row.get('ville')).upper()}"
    for bn,ps in BRANDS:
        for p in ps:
            if p in t: return bn
    return e.title() if e else None
def freshness(v):
    if not v: return "❓","fr-old"
    try:
        maj=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        if maj.tzinfo is None: maj=maj.replace(tzinfo=timezone.utc)
        d=(datetime.now(timezone.utc)-maj).days
        if d==0: return "🟢 Aujourd'hui","fr-today"
        if d<=2: return f"🟡 {d}j","fr-recent"
        if d<=7: return f"🔴 {d}j","fr-old"
        return f"⚠️ {d}j","fr-old"
    except: return "❓","fr-old"
def hours_html(hj_raw):
    hj=safe_str(hj_raw)
    if not hj: return "<span style='color:var(--c-muted);font-size:.8rem'>Non renseignés</span>"
    is_24h="Automate-24-24" in hj; today=datetime.now().weekday(); rows=""
    for i,jour in enumerate(JOURS):
        m=re.search(rf"{jour}(\d{{2}}\.\d{{2}})-(\d{{2}}\.\d{{2}})",hj)
        css=' class="htbl-today"' if i==today else ""
        if m: h=f"{m.group(1).replace('.','h')} – {m.group(2).replace('.','h')}"
        elif is_24h and not re.search(rf"{jour}\d",hj): h="24h/24"
        else: h="Fermé"
        rows+=f"<tr{css}><td class='d'>{jour[:3]}.</td><td>{h}</td></tr>"
    b='<span class="svc-g">🕐 24h/24</span>' if is_24h else ""
    return f"{b}<br><table class='htbl'>{rows}</table>"
def dist_km(a,b,c,d):
    try: return round(geodesic((a,b),(c,d)).km,1)
    except: return None
def geocode_address(addr):
    """Géocode avec fallback et timeout."""
    for attempt in range(2):
        try:
            geolocator=Nominatim(user_agent=f"ecoplein_v4_{attempt}",timeout=8)
            result=geolocator.geocode(addr+", France", exactly_one=True)
            if result: return result.latitude, result.longitude, result.address
            time.sleep(1)
        except Exception as e:
            if attempt==1: raise e
            time.sleep(1)
    return None, None, None

# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def load_stations(_sb, carburant_col, lat, lon, radius):
    try:
        r=_sb.rpc("get_stations_proches",{
            "user_lat":lat,"user_lon":lon,
            "carburant_col":carburant_col,"radius_km":radius}).execute()
        if r.data:
            df=pd.DataFrame(r.data)
            df.rename(columns={"prix":f"{carburant_col}_prix",
                                "prix_maj":f"{carburant_col}_maj"},inplace=True)
            return df,True
    except Exception as e:
        st.caption(f"ℹ️ Mode direct (RPC : {str(e)[:60]})")
    try:
        r=_sb.table("stations_carburant").select("*")\
              .not_.is_(f"{carburant_col}_prix","null").execute()
        return pd.DataFrame(r.data or []),False
    except Exception as e2:
        st.error(f"Erreur Supabase : {e2}"); return pd.DataFrame(),False

# ══════════════════════════════════════════════════════════════════════════════
# BLOC LOCALISATION (commun mobile + desktop)
# ══════════════════════════════════════════════════════════════════════════════
def location_block(compact=False):
    """
    Retourne (user_lat, user_lon) ou (None, None).
    compact=True → version condensée pour mobile.
    """
    user_lat=user_lon=None

    # ── GPS ──────────────────────────────────────────────────────────────────
    if not compact:
        st.markdown("**📍 Ma position**")

    mode_key="loc_mode"
    if mode_key not in st.session_state:
        st.session_state[mode_key]="GPS"

    if compact:
        cols=st.columns([1,1])
        with cols[0]:
            if st.button("📍 GPS",key="gps_tab_btn",use_container_width=True,
                         type="primary" if st.session_state[mode_key]=="GPS" else "secondary"):
                st.session_state[mode_key]="GPS"
                st.session_state.pop("gps",None)
        with cols[1]:
            if st.button("🔍 Adresse",key="addr_tab_btn",use_container_width=True,
                         type="primary" if st.session_state[mode_key]=="Adresse" else "secondary"):
                st.session_state[mode_key]="Adresse"
    else:
        m=st.radio("loc_radio",["GPS (auto)","Adresse manuelle"],
                   index=0 if st.session_state[mode_key]=="GPS" else 1,
                   label_visibility="collapsed",horizontal=True,key="loc_radio_key")
        st.session_state[mode_key]="GPS" if m=="GPS (auto)" else "Adresse"

    # ── Mode GPS ──────────────────────────────────────────────────────────────
    if st.session_state[mode_key]=="GPS":
        # get_geolocation() appelle l'API navigator.geolocation du navigateur
        # On l'appelle à chaque render pour détecter la position
        with st.spinner("🛰️ Localisation en cours…"):
            try:
                loc=get_geolocation()
            except Exception:
                loc=None

        if loc and isinstance(loc,dict) and loc.get("coords"):
            c=loc["coords"]
            user_lat=c.get("latitude")
            user_lon=c.get("longitude")
            acc=c.get("accuracy",0)
            st.session_state.gps_cache=(user_lat,user_lon)
            st.markdown(
                f'<div style="background:var(--c-svc-g-bg);color:var(--c-svc-g-fg);'
                f'border-radius:8px;padding:8px 12px;font-size:.83rem;margin-top:6px">'
                f'✅ Position détectée · précision {acc:.0f}m</div>',
                unsafe_allow_html=True)
        else:
            # Utiliser le cache si disponible
            if "gps_cache" in st.session_state:
                user_lat,user_lon=st.session_state.gps_cache
                st.markdown(
                    '<div style="background:var(--c-avg-bg);color:var(--c-avg-fg);'
                    'border-radius:8px;padding:8px 12px;font-size:.83rem;margin-top:6px">'
                    '⏳ Utilisation dernière position connue</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="background:var(--c-avg-bg);color:var(--c-avg-fg);'
                    'border-radius:8px;padding:8px 12px;font-size:.83rem;margin-top:6px">'
                    '⚠️ GPS non disponible — autorisez la géolocalisation ou utilisez la recherche par adresse</div>',
                    unsafe_allow_html=True)
        if not compact:
            if st.button("🔄 Relancer GPS",key="gps_refresh"):
                st.session_state.pop("gps_cache",None); st.rerun()

    # ── Mode Adresse ──────────────────────────────────────────────────────────
    else:
        addr=st.text_input(
            "addr_input","",
            placeholder="Ex: 18 rue Jules Guesde, Lille",
            label_visibility="collapsed",key="addr_field")

        if addr:
            btn_lbl="🔍 Rechercher" if not compact else "🔍"
            if st.button(btn_lbl,key="geocode_btn",use_container_width=True,type="primary"):
                with st.spinner("Géocodage…"):
                    try:
                        lat,lon,full_addr=geocode_address(addr)
                        if lat:
                            st.session_state.manual_loc=(lat,lon)
                            short=full_addr[:55]+"…" if len(full_addr)>55 else full_addr
                            st.success(f"✅ {short}")
                        else:
                            st.error("❌ Adresse introuvable. Essayez d'être plus précis.")
                    except Exception as e:
                        st.error(f"❌ Erreur : {e}")

        if "manual_loc" in st.session_state:
            user_lat,user_lon=st.session_state.manual_loc
            if not addr:
                st.markdown(
                    '<div style="background:var(--c-svc-g-bg);color:var(--c-svc-g-fg);'
                    'border-radius:8px;padding:8px 12px;font-size:.83rem">'
                    f'✅ {user_lat:.5f}, {user_lon:.5f}</div>',
                    unsafe_allow_html=True)

    return user_lat, user_lon

# ══════════════════════════════════════════════════════════════════════════════
# RENDU CARTE STATION
# ══════════════════════════════════════════════════════════════════════════════
def render_card(row,carb_col,u_lat,u_lon,moy):
    pc=f"{carb_col}_prix"; mc=f"{carb_col}_maj"
    prix=row.get(pc)
    if prix is None: return
    ratio=(float(prix)-moy)/max(abs(moy*.03),.001)
    prix_cls="prix-cheap" if ratio<-.5 else("prix-exp" if ratio>.5 else "prix-avg")
    fr_lbl,fr_cls=freshness(row.get(mc))
    d=row.get("distance_km")
    if d is None:
        la,lo=extract_geom(row.get("geom")); d=dist_km(u_lat,u_lon,la,lo)
    dist_s=f"📍 {d} km" if d else ""
    brand=detect_brand(row)
    b_html=f'<span class="brand-tag">{brand}</span>' if brand else ""
    pop_b='<span class="svc-b">🛣️ Autoroute</span>' if row.get("pop")=="A" else ""
    prio=["Automate CB 24/24","Bornes électriques","Lavage automatique",
          "Boutique alimentaire","Wifi"]
    svcs=""
    for sv in safe_list(row.get("services_service")):
        if sv in prio and sv in SERVICES_MAP:
            ic,cl=SERVICES_MAP[sv]; svcs+=f'<span class="{cl}">{ic} {sv}</span>'
    if row.get("horaires_automate_24_24")=="Oui":
        svcs='<span class="svc-g">🕐 24h/24</span>'+svcs
    rup=""
    if safe_str(row.get("carburants_rupture_temporaire")):
        rup+=f'<span class="rup-t">⏳ {row["carburants_rupture_temporaire"]}</span>'
    if safe_str(row.get("carburants_rupture_definitive")):
        rup+=f'<span class="rup-d">🚫 {row["carburants_rupture_definitive"]}</span>'
    sav=round((moy-float(prix))*50,2)
    sav_h=f'<span class="saving">💰 -{sav:.2f}€ vs moyenne (50L)</span>' if sav>.5 else ""
    st.markdown(f"""
<div class="eco-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
    <div style="flex:1;min-width:0;overflow:hidden">
      <h4>{b_html}{safe_str(row.get('adresse'))}</h4>
      <p class="addr">{safe_str(row.get('cp'))} {safe_str(row.get('ville'))}&nbsp;·&nbsp;{dist_s}</p>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <span class="{prix_cls}">{float(prix):.3f} €/L</span>
      <br><span class="{fr_cls}">{fr_lbl}</span>
    </div>
  </div>
  <div style="margin-top:8px;line-height:1.9">{pop_b}{svcs}</div>
  {f'<div style="margin-top:4px">{sav_h}</div>' if sav_h else ''}
  {f'<div style="margin-top:3px">{rup}</div>' if rup else ''}
</div>""", unsafe_allow_html=True)
    with st.expander("📋 Horaires & services"):
        c1,c2=st.columns(2)
        with c1:
            st.markdown("**🕐 Horaires**")
            st.markdown(hours_html(row.get("horaires_jour")),unsafe_allow_html=True)
        with c2:
            st.markdown("**🔧 Services**")
            all_sv=safe_list(row.get("services_service"))
            if all_sv:
                st.markdown("".join(
                    f'<span class="{SERVICES_MAP.get(sv,("•","svc-b"))[1]}">'
                    f'{SERVICES_MAP.get(sv,("•","svc-b"))[0]} {sv}</span>'
                    for sv in all_sv),unsafe_allow_html=True)
            else: st.caption("Non renseignés")
            di=safe_list(row.get("carburants_disponibles"))
            in_=safe_list(row.get("carburants_indisponibles"))
            if di or in_:
                st.markdown("**⛽ Carburants**")
                st.markdown(
                    "".join(f'<span class="svc-g">✅ {x}</span>' for x in di)+
                    "".join(f'<span class="rup-d">🚫 {x}</span>' for x in in_),
                    unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION RÉSULTATS (partagée mobile + desktop)
# ══════════════════════════════════════════════════════════════════════════════
def results_section(sb,carb_col,carb_name,user_lat,user_lon,radius,
                    sort_by,filters,theme,mobile_tabs=False):
    with st.spinner(f"Recherche {carb_name}…"):
        df,via_rpc=load_stations(sb,carb_col,user_lat,user_lon,float(radius))

    if df.empty:
        st.warning("Aucune station. Vérifiez la connexion ou augmentez le rayon.")
        return

    prix_col=f"{carb_col}_prix"; maj_col=f"{carb_col}_maj"
    if "lat" not in df.columns:
        df[["lat","lon"]]=df["geom"].apply(lambda g:pd.Series(extract_geom(g)))
    df["lat"]=df["lat"].astype(float); df["lon"]=df["lon"].astype(float)
    df=df[(df["lat"]!=0)&(df["lon"]!=0)]
    if "distance_km" not in df.columns:
        df["distance_km"]=df.apply(
            lambda r:dist_km(user_lat,user_lon,r["lat"],r["lon"]) or 9999,axis=1)
    df=df[df["distance_km"].astype(float)<=radius]
    df=df[df[prix_col].notna()]
    if df.empty: st.warning("Aucune station avec prix dans ce rayon."); return

    f_24h,f_cb,f_ev,f_wash,f_shop=filters
    def has(v,s): return s in safe_list(v)
    if f_24h:  df=df[df["horaires_automate_24_24"]=="Oui"]
    if f_cb:   df=df[df["services_service"].apply(lambda v:has(v,"Automate CB 24/24"))]
    if f_ev:   df=df[df["services_service"].apply(lambda v:has(v,"Bornes électriques"))]
    if f_wash: df=df[df["services_service"].apply(lambda v:has(v,"Lavage automatique"))]
    if f_shop: df=df[df["services_service"].apply(lambda v:has(v,"Boutique alimentaire"))]
    if df.empty: st.warning("Aucune station ne correspond aux filtres."); return

    pv=df[prix_col].astype(float)
    moy=pv.mean(); pmin,pmax=pv.min(),pv.max(); eco=round((pmax-pmin)*50,2)

    # KPIs
    src="🟢 Temps réel" if via_rpc else "🟡 Base complète"
    st.caption(f"{src} · {len(df)} station{'s' if len(df)>1 else ''} · {radius} km")
    k1,k2,k3,k4=st.columns(4)
    for col,val,lbl,clr in [
        (k1,f"{pmin:.3f}€",f"Min {carb_name}","var(--c-cheap-fg)"),
        (k2,f"{moy:.3f}€","Moyenne","var(--c-text)"),
        (k3,f"{pmax:.3f}€","Max","var(--c-exp-fg)"),
        (k4,f"-{eco:.2f}€","Économie max/50L","var(--c-svc-b-fg)"),
    ]:
        with col:
            st.markdown(f'<div class="kpi"><div class="kpi-v" style="color:{clr}">{val}</div>'
                        f'<div class="kpi-l">{lbl}</div></div>',unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)

    # Tri
    if   sort_by=="Prix croissant":      df_d=df.sort_values(prix_col)
    elif sort_by=="Prix décroissant":    df_d=df.sort_values(prix_col,ascending=False)
    elif sort_by=="Mise à jour récente": df_d=df.sort_values(maj_col,ascending=False,na_position="last")
    else:                                df_d=df.sort_values("distance_km")

    map_style=CARTO_DARK if theme=="Sombre 🌙" else CARTO_LIGHT

    def pcol(p):
        if pd.isna(p): return [128,128,128,160]
        r=(float(p)-pmin)/max(pmax-pmin,.01)
        return [int(220*r),int(180*(1-r)),40,220]
    dm=df_d.copy()
    dm["color"]=dm[prix_col].apply(pcol)
    dm["price_str"]=dm[prix_col].apply(lambda p:f"{float(p):.3f} €/L")
    dm["brand_str"]=dm.apply(lambda r:detect_brand(dict(r)) or "Station",axis=1)
    for cn in ["adresse","ville"]:
        if cn not in dm.columns: dm[cn]=""
    map_data=dm[["lat","lon","color","price_str","brand_str","adresse","ville"]].copy()
    user_df=pd.DataFrame([{"lat":user_lat,"lon":user_lon}])
    deck=pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(latitude=user_lat,longitude=user_lon,zoom=12,pitch=0),
        layers=[
            pdk.Layer("ScatterplotLayer",data=map_data,
                get_position=["lon","lat"],get_color="color",get_radius=250,
                pickable=True,auto_highlight=True,highlight_color=[255,200,0,255]),
            pdk.Layer("ScatterplotLayer",data=user_df,
                get_position=["lon","lat"],get_color=[0,112,243,255],
                get_radius=180,pickable=False),
        ],
        tooltip={
            "html":"<b>{brand_str}</b><br>{adresse}, {ville}<br>"
                   "<span style='font-size:1.1em;font-weight:700'>{price_str}</span>",
            "style":{"backgroundColor":"#0d1117","color":"#e6edf3",
                     "fontSize":"13px","padding":"10px 12px","borderRadius":"6px"}}
    )

    if mobile_tabs:
        # ── Layout mobile : tabs ──────────────────────────────────────────
        tab_map,tab_list=st.tabs(["🗺️ Carte","📋 Stations"])
        with tab_map:
            st.pydeck_chart(deck,use_container_width=True)
            st.markdown(
                '<div class="map-legend"><span>🟢 Moins cher</span>'
                '<span>🟡 Moyen</span><span>🔴 Plus cher</span>'
                '<span>🔵 Vous</span></div>',unsafe_allow_html=True)
        with tab_list:
            n=len(df_d)
            st.markdown(f"**{n} station{'s' if n>1 else ''} — {sort_by}**")
            for _,row in df_d.head(25).iterrows():
                render_card(dict(row),carb_col,user_lat,user_lon,moy)
            if n>25: st.info("25 premières affichées · Réduisez le rayon")
    else:
        # ── Layout desktop : colonnes ─────────────────────────────────────
        mc,lc=st.columns([1.3,1])
        with mc:
            st.pydeck_chart(deck,use_container_width=True)
            st.markdown(
                '<div class="map-legend"><span>🟢 Moins cher</span>'
                '<span>🟡 Moyen</span><span>🔴 Plus cher</span>'
                '<span>🔵 Vous</span></div>',unsafe_allow_html=True)
        with lc:
            n=len(df_d)
            st.markdown(f"**📋 {n} station{'s' if n>1 else ''} — {sort_by}**")
            for _,row in df_d.head(20).iterrows():
                render_card(dict(row),carb_col,user_lat,user_lon,moy)
            if n>20: st.info("20 premières affichées · Réduisez le rayon")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    sb=get_supabase()

    # Thème
    if "theme" not in st.session_state: st.session_state.theme="Auto 🌓"
    inject_theme(st.session_state.theme)

    # Détection viewport (None au premier rendu → on suppose desktop)
    screen_w=streamlit_js_eval(js_expressions="window.innerWidth",key="vp_w")
    is_mobile=isinstance(screen_w,(int,float)) and screen_w<768

    # ══════════════════════════════════════════════════════════════════════
    # LAYOUT MOBILE
    # ══════════════════════════════════════════════════════════════════════
    if is_mobile:
        # Header compact
        h1,h2=st.columns([3,1])
        with h1: st.markdown("### ⛽ EcoPlein")
        with h2:
            opts=["Auto 🌓","Clair ☀️","Sombre 🌙"]
            tc=st.selectbox("th_m",opts,
                index=opts.index(st.session_state.theme),
                label_visibility="collapsed",key="th_mobile")
            if tc!=st.session_state.theme:
                st.session_state.theme=tc; st.rerun()

        # Carburant + rayon sur une ligne
        c1,c2=st.columns([2,1])
        with c1:
            carb_items=list(CARBURANTS.items())
            carb_labels=[k for k,v in carb_items]
            carb_sel=st.selectbox("carb_m",carb_labels,label_visibility="collapsed",key="carb_mobile")
            carb_col=CARBURANTS[carb_sel]
            carb_name=carb_sel.split(" ",1)[1] if " " in carb_sel else carb_sel
        with c2:
            radius=st.number_input("km_m",min_value=2,max_value=50,value=10,
                                   label_visibility="collapsed",key="radius_mobile",
                                   help="Rayon (km)")
            st.caption(f"📏 {radius} km")

        # Localisation
        with st.expander("📍 Ma position",expanded="gps_cache" not in st.session_state and "manual_loc" not in st.session_state):
            user_lat,user_lon=location_block(compact=True)

        # Si position dispo → récupérer depuis session si location_block renvoie None
        if not user_lat and "gps_cache" in st.session_state:
            user_lat,user_lon=st.session_state.gps_cache
        if not user_lat and "manual_loc" in st.session_state:
            user_lat,user_lon=st.session_state.manual_loc

        # Filtres rapides (inline chips)
        with st.expander("⚙️ Filtres & tri"):
            fc1,fc2=st.columns(2)
            with fc1:
                f_24h =st.checkbox("🕐 24h/24",key="m_24h")
                f_cb  =st.checkbox("💳 CB 24/24",key="m_cb")
                f_ev  =st.checkbox("⚡ Bornes",key="m_ev")
            with fc2:
                f_wash=st.checkbox("🚿 Lavage",key="m_wash")
                f_shop=st.checkbox("🛒 Boutique",key="m_shop")
            sort_by=st.radio("sort_m",
                ["Distance","Prix croissant","Prix décroissant","Mise à jour récente"],
                index=0,label_visibility="collapsed",key="sort_mobile",horizontal=False)

        filters=(f_24h,f_cb,f_ev,f_wash,f_shop)

        # Résultats
        if user_lat and user_lon:
            results_section(sb,carb_col,carb_name,user_lat,user_lon,
                            radius,sort_by,filters,st.session_state.theme,
                            mobile_tabs=True)
        else:
            st.info("📍 Activez la géolocalisation ou entrez une adresse ci-dessus")

    # ══════════════════════════════════════════════════════════════════════
    # LAYOUT DESKTOP
    # ══════════════════════════════════════════════════════════════════════
    else:
        with st.sidebar:
            st.markdown("## ⛽ EcoPlein")
            st.markdown('<small style="color:#8b949e">Carburant moins cher près de vous</small>',
                        unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("**🎨 Thème**")
            opts=["Auto 🌓","Clair ☀️","Sombre 🌙"]
            tc=st.radio("th_d",opts,index=opts.index(st.session_state.theme),
                        label_visibility="collapsed",horizontal=True,key="th_desktop")
            if tc!=st.session_state.theme:
                st.session_state.theme=tc; st.rerun()
            st.markdown("---")
            st.markdown("**🔴 Carburant**")
            carb_items=list(CARBURANTS.items())
            carb_labels=[k for k,v in carb_items]
            carb_sel=st.selectbox("carb_d",carb_labels,label_visibility="collapsed",key="carb_desktop")
            carb_col=CARBURANTS[carb_sel]
            carb_name=carb_sel.split(" ",1)[1] if " " in carb_sel else carb_sel
            st.markdown("---")
            st.markdown("**📏 Rayon**")
            radius=st.slider("r_d",2,50,10,label_visibility="collapsed",
                             format="%d km",key="radius_desktop")
            st.markdown("---")
            user_lat,user_lon=location_block(compact=False)
            if not user_lat and "gps_cache" in st.session_state:
                user_lat,user_lon=st.session_state.gps_cache
            if not user_lat and "manual_loc" in st.session_state:
                user_lat,user_lon=st.session_state.manual_loc
            st.markdown("---")
            st.markdown("**🔧 Filtres**")
            f_24h =st.checkbox("🕐 Automate 24h/24",key="d_24h")
            f_cb  =st.checkbox("💳 CB 24/24",key="d_cb")
            f_ev  =st.checkbox("⚡ Bornes électriques",key="d_ev")
            f_wash=st.checkbox("🚿 Lavage auto",key="d_wash")
            f_shop=st.checkbox("🛒 Boutique alim.",key="d_shop")
            st.markdown("---")
            st.markdown("**📊 Tri**")
            sort_by=st.selectbox("sort_d",
                ["Distance","Prix croissant","Prix décroissant","Mise à jour récente"],
                label_visibility="collapsed",key="sort_desktop")
            st.markdown("---")
            st.markdown('<small style="color:#6e7681">v4.0 · data.gouv.fr</small>',
                        unsafe_allow_html=True)

        filters=(f_24h,f_cb,f_ev,f_wash,f_shop)
        st.markdown("## ⛽ EcoPlein — Carburant le moins cher près de vous")

        if not user_lat or not user_lon:
            st.info("📍 Activez le GPS ou entrez une adresse dans la barre latérale.")
            st.pydeck_chart(pdk.Deck(
                map_style=CARTO_LIGHT,
                initial_view_state=pdk.ViewState(latitude=46.6,longitude=2.3,zoom=5)))
            return

        results_section(sb,carb_col,carb_name,user_lat,user_lon,
                        radius,sort_by,filters,st.session_state.theme,
                        mobile_tabs=False)

if __name__=="__main__":
    main()
