# ═══════════════════════════════════════════════════════════════════════════════
# EcoPlein v18.1 — correctifs cohérence UX & calculs
# Nouveautés vs v13 :
#   • Police Outfit (Google Fonts) — plus aucune police système générique
#   • Couleur de marque : orange #f97316 au lieu du vert GitHub
#   • Desktop : PLUS DE SIDEBAR → barre de contrôles horizontale en haut
#   • Cards : layout 3 colonnes (prix | info | navigation), prix dominant à gauche
#   • Carte : pleine largeur, plus haute, arrière-plan navy #0a0f1e
#   • Tokens CSS : variables centralisées, un seul endroit pour changer les couleurs
#   • Python 3.9+ compat : aucune annotation X|Y
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import requests
from supabase import create_client
from streamlit_js_eval import streamlit_js_eval, get_geolocation
from geopy.distance import geodesic
import pydeck as pdk
from datetime import datetime, timezone, time as dtime
from typing import Optional
import json, re, math, time as _time

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN SYSTEM — CSS complet
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">

<style>
/* ── Tokens (modifier ici pour changer tout le design) ─────────────── */
:root {
  --accent:      #f97316;        /* orange — couleur de marque */
  --accent-dim:  rgba(249,115,22,.12);
  --accent-brd:  rgba(249,115,22,.25);
  --bg:          #0a0f1e;        /* fond principal */
  --surface:     #111827;        /* cartes */
  --surface-2:   #1a2236;        /* surface secondaire */
  --border:      rgba(255,255,255,.08);
  --text:        #f1f5f9;
  --text-2:      #94a3b8;
  --green:       #22c55e;
  --green-dim:   rgba(34,197,94,.12);
  --green-brd:   rgba(34,197,94,.25);
  --amber:       #f59e0b;
  --amber-dim:   rgba(245,158,11,.12);
  --red:         #ef4444;
  --red-dim:     rgba(239,68,68,.12);
  --blue:        #60a5fa;
  --blue-dim:    rgba(96,165,250,.12);
}

/* ── Font & Reset ──────────────────────────────────────────────────── */
html, body, [class*="css"], .stApp, button, input, select, textarea {
  font-family: 'Outfit', system-ui, sans-serif !important;
}
.block-container {
  padding-top: .5rem !important;
  padding-bottom: 5.5rem !important;
  padding-left: .75rem !important;
  padding-right: .75rem !important;
  max-width: 100% !important;
  background: var(--bg) !important;
}
header[data-testid="stHeader"] { display: none !important; }
h1, h2, h3 { margin-top: .2rem !important; }

/* ── Cacher la sidebar sur desktop — CONTRÔLES dans le topbar ──────── */
@media (min-width: 769px) {
  [data-testid="stSidebar"],
  [data-testid="stSidebarCollapsedControl"],
  [data-testid="collapsedControl"] {
    display: none !important;
  }
  section.main { margin-left: 0 !important; }
}
@media (max-width: 768px) {
  .block-container { padding-left:.5rem !important; padding-right:.5rem !important; }
}

/* ── TOP BAR (desktop) ─────────────────────────────────────────────── */
.topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 0 12px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.topbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text);
  white-space: nowrap;
}
.topbar-brand span { color: var(--accent); }
.topbar-sep {
  width: 1px; height: 24px;
  background: var(--border);
  flex-shrink: 0;
}

/* ── FILTER BAR (desktop) ──────────────────────────────────────────── */
.filter-bar {
  display: flex;
  gap: 8px;
  padding: 6px 0 10px;
  flex-wrap: wrap;
  align-items: center;
}
.fchip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 13px;
  border-radius: 20px;
  font-size: .78rem;
  font-weight: 600;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  white-space: nowrap;
  transition: all .15s;
}
.fchip.on {
  background: var(--accent-dim);
  border-color: var(--accent-brd);
  color: var(--accent);
}

/* ── STATION CARD — layout 3 colonnes ──────────────────────────────── */
/* [PRIX] | [INFO] | [NAV]  */
.scard {
  display: grid;
  grid-template-columns: 88px 1fr 72px;
  gap: 0 14px;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 13px 14px;
  margin: 7px 0;
  transition: border-color .15s, box-shadow .15s;
}
.scard:hover {
  border-color: rgba(249,115,22,.3);
  box-shadow: 0 0 0 1px rgba(249,115,22,.1), 0 4px 20px rgba(0,0,0,.3);
}

/* Colonne prix */
.sc-price {
  text-align: center;
  padding: 10px 4px;
  border-radius: 12px;
  border: 1.5px solid var(--border);
}
.sc-price.cheap { background:var(--green-dim); border-color:var(--green-brd); }
.sc-price.avg   { background:var(--amber-dim); border-color:rgba(245,158,11,.25); }
.sc-price.exp   { background:var(--red-dim);   border-color:rgba(239,68,68,.25); }
.sc-pval        { font-size:1.35rem; font-weight:900; line-height:1; }
.sc-pval.cheap  { color: var(--green); }
.sc-pval.avg    { color: var(--amber); }
.sc-pval.exp    { color: var(--red); }
.sc-punit       { font-size:.65rem; color:var(--text-2); margin-top:1px; }
.sc-pfill       { font-size:.78rem; font-weight:700; color:var(--blue); margin-top:5px; }
.sc-plitre      { font-size:.62rem; color:var(--text-2); }

/* Colonne info */
.sc-info        { min-width: 0; }
.sc-brand       { font-size:.88rem; font-weight:700; color:var(--text); margin:0 0 2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sc-addr        { font-size:.78rem; color:var(--text-2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sc-meta        { font-size:.71rem; color:var(--text-2); margin-top:3px; }
.sc-svcs        { margin-top:6px; line-height:2; }
.sc-eco         { font-size:.72rem; font-weight:600; color:var(--green); margin-top:4px; }

/* Colonne nav */
.sc-nav {
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: stretch;
}
.nav-a {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 5px 6px;
  border-radius: 10px;
  font-size: .7rem;
  font-weight: 700;
  text-decoration: none !important;
  transition: opacity .12s;
  min-height: 30px;
}
.nav-a:active { opacity: .75; }
.na-gmaps { background: #4285f4; color: #fff !important; }
.na-waze  { background: #05c8f7; color: #000 !important; }
.na-apple { background: #2c2c2e; color: #fff !important; }
.sc-fr    { font-size:.62rem; text-align:center; padding-top:3px; }
.fr-ok    { color: var(--green) !important; }
.fr-mid   { color: var(--amber) !important; }
.fr-old   { color: var(--red)   !important; }

/* ── BEST DEAL BANNER ──────────────────────────────────────────────── */
.best-deal {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 14px;
  align-items: center;
  background: linear-gradient(135deg, #0d2010 0%, #162d1a 100%);
  border: 1px solid rgba(34,197,94,.35);
  border-radius: 18px;
  padding: 14px 18px;
  margin-bottom: 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,.3), 0 0 0 1px rgba(34,197,94,.12);
  animation: slideDown .2s ease-out;
}
@keyframes slideDown { from{opacity:0;transform:translateY(-6px)} to{opacity:1;transform:translateY(0)} }
.bd-price    { font-size:2rem; font-weight:900; color:var(--green); line-height:1; }
.bd-meta     { min-width:0; }
.bd-name     { font-size:.9rem; font-weight:700; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bd-sub      { font-size:.74rem; color:var(--text-2); margin-top:2px; }
.bd-eco      { font-size:.72rem; color:var(--green); margin-top:3px; font-weight:600; }
.bd-nav      { display:flex; gap:6px; margin-top:8px; flex-wrap:wrap; }
.bd-right    { text-align:right; flex-shrink:0; }
.bd-cout     { font-size:1rem; font-weight:800; color:var(--blue); }
.bd-litre    { font-size:.68rem; color:var(--text-2); }

/* ── KPI CARDS (desktop) ───────────────────────────────────────────── */
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px 10px;
  text-align: center;
  margin-bottom: 8px;
}
.kpi-v { font-size:1.25rem; font-weight:800; line-height:1.2; }
.kpi-l { font-size:.65rem; color:var(--text-2); margin-top:3px; }

/* ── BADGES & LABELS ───────────────────────────────────────────────── */
.bg-g { background:var(--green-dim); color:var(--green) !important; border-radius:12px; padding:2px 8px; font-size:.67rem; margin:2px 2px 0 0; display:inline-block; font-weight:600; }
.bg-b { background:var(--blue-dim);  color:var(--blue)  !important; border-radius:12px; padding:2px 8px; font-size:.67rem; margin:2px 2px 0 0; display:inline-block; font-weight:600; }
.bg-w { background:var(--surface-2); color:var(--text-2)!important; border-radius:12px; padding:2px 8px; font-size:.67rem; margin:2px 2px 0 0; display:inline-block; }
.badge-open   { background:var(--green-dim); color:var(--green) !important; border-radius:10px; padding:1px 7px; font-size:.67rem; font-weight:700; }
.badge-closed { background:var(--red-dim);   color:var(--red)   !important; border-radius:10px; padding:1px 7px; font-size:.67rem; font-weight:700; }
.eco-tag      { background:var(--green-dim); color:var(--green) !important; border-radius:10px; padding:1px 7px; font-weight:700; font-size:.7rem; margin-right:4px; }
.eco-tag-2    { background:var(--amber-dim); color:var(--amber) !important; border-radius:10px; padding:1px 7px; font-weight:700; font-size:.7rem; }

/* ── GPS STATUS ────────────────────────────────────────────────────── */
.gps-ok   { background:var(--green-dim); color:var(--green)!important; border-radius:10px; padding:9px 14px; font-size:.82rem; margin:6px 0; }
.gps-err  { background:var(--amber-dim); color:var(--amber)!important; border-radius:10px; padding:9px 14px; font-size:.82rem; margin:6px 0; }
.gps-fail { background:var(--red-dim);   color:var(--red)  !important; border-radius:10px; padding:9px 14px; font-size:.82rem; margin:6px 0; }

/* ── HORAIRES ──────────────────────────────────────────────────────── */
.htbl { width:100%; font-size:.76rem; border-collapse:collapse; }
.htbl td { padding:3px 6px; border-bottom:1px solid var(--border); color:var(--text)!important; }
.htbl tr:last-child td { border-bottom:none; }
.htbl-today { background:var(--green-dim)!important; }
.htbl-today td { color:var(--green)!important; font-weight:700; }

/* ── CALCULATEUR ───────────────────────────────────────────────────── */
.calc-box  { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:13px 15px; margin-top:8px; }
.calc-mini { background:var(--surface-2); border-radius:9px; padding:7px 9px; font-size:.77rem; text-align:center; }

/* ── SUMMARY BAR ───────────────────────────────────────────────────── */
.sbar { display:flex; align-items:center; gap:8px; padding:4px 0 8px; font-size:.77rem; color:var(--text-2); flex-wrap:wrap; }
.sdot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.sdot-g { background:var(--green); box-shadow:0 0 6px rgba(34,197,94,.5); }
.sdot-o { background:var(--amber); }

/* ── SUGGESTIONS ADRESSE ───────────────────────────────────────────── */
.sug-btn button {
  background:var(--surface)!important; color:var(--text)!important;
  border:1px solid var(--border)!important; text-align:left!important;
  font-size:.83rem!important; border-radius:10px!important; padding:8px 12px!important;
}
.sug-btn button:hover { background:var(--accent-dim)!important; border-color:var(--accent-brd)!important; }

/* ── ONBOARDING ────────────────────────────────────────────────────── */
.onboard { display:flex; flex-direction:column; align-items:center; text-align:center; padding:2.5rem 1rem 1.5rem; gap:1rem; }
.onboard-icon { font-size:3.5rem; animation:float 3s ease-in-out infinite; }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
.onboard h2 { font-size:1.4rem; font-weight:800; margin:0; color:var(--text); }
.onboard p  { font-size:.88rem; color:var(--text-2); max-width:28ch; margin:0; line-height:1.5; }

/* ── MOBILE BOTTOM NAV ─────────────────────────────────────────────── */
/* Marqueur : bnav-trigger → le st.columns(4) suivant devient fixed bottom */
.bnav-trigger { display:none!important; height:0!important; margin:0!important; padding:0!important; }

@media (max-width: 768px) {
  .stMarkdown:has(>.bnav-trigger) + [data-testid="stHorizontalBlock"],
  .stMarkdown:has(>.bnav-trigger) + div > [data-testid="stHorizontalBlock"] {
    position:fixed!important; bottom:0!important; left:0!important; right:0!important;
    z-index:9998!important; background:rgba(10,15,30,.97)!important;
    backdrop-filter:blur(16px)!important; -webkit-backdrop-filter:blur(16px)!important;
    border-top:1px solid var(--border)!important;
    padding:2px 4px max(env(safe-area-inset-bottom,4px),4px)!important;
    margin:0!important; gap:0!important;
  }
  .stMarkdown:has(>.bnav-trigger) + [data-testid="stHorizontalBlock"] > div,
  .stMarkdown:has(>.bnav-trigger) + div > [data-testid="stHorizontalBlock"] > div {
    padding:0 2px!important; flex:1!important;
  }
  .stMarkdown:has(>.bnav-trigger) + [data-testid="stHorizontalBlock"] button,
  .stMarkdown:has(>.bnav-trigger) + div > [data-testid="stHorizontalBlock"] button {
    min-height:52px!important; height:52px!important;
    border-radius:8px!important; border:none!important;
    background:transparent!important; color:#64748b!important;
    font-size:.58rem!important; font-weight:700!important;
    text-transform:uppercase!important; letter-spacing:.05em!important;
    white-space:pre-line!important; line-height:1.3!important;
    box-shadow:none!important;
  }
  .stMarkdown:has(>.bnav-trigger) + [data-testid="stHorizontalBlock"] button[data-testid="baseButton-primary"],
  .stMarkdown:has(>.bnav-trigger) + div > [data-testid="stHorizontalBlock"] button[data-testid="baseButton-primary"] {
    color:var(--accent)!important; background:var(--accent-dim)!important;
  }
}

/* ── Carte sticky desktop ──────────────────────────────────────────── */
@media (min-width: 768px) {
  div[data-testid="stColumn"]:has(div[data-testid="stDeckGlJsonChart"]) {
    position:sticky; top:2rem; align-self:flex-start;
    height:calc(100vh - 3rem); overflow:hidden;
  }
}

/* ── Section labels ────────────────────────────────────────────────── */
.sec-label { font-size:.65rem; font-weight:700; letter-spacing:.09em; text-transform:uppercase; color:var(--accent); margin:14px 0 6px; }

/* ── Map legend ────────────────────────────────────────────────────── */
.map-legend { font-size:.71rem; color:var(--text-2); margin-top:4px; }

</style>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EcoPlein",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0a0f1e">
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

CARBURANTS = {
    "Gazole": "gazole",
    "SP95":   "sp95",
    "SP98":   "sp98",
    "E10":    "e10",
    "E85":    "e85",
    "GPLc":   "gplc",
}

BRANDS = [
    ("TotalEnergies", ["TOTALENERGIES","TOTAL ENERGIES","TOTAL ACCESS","TOTAL-ACCESS"]),
    ("Esso",          ["ESSO"]),
    ("BP",            [" BP ","BP-"]),
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
    ("Total",         ["TOTAL"]),   # EN DERNIER — ne pas capturer TotalEnergies
]

BRAND_GROUPS = {
    "Grandes surfaces": [
        "E.Leclerc","Intermarché","Carrefour","Super U",
        "Hyper U","Système U","Auchan","Casino","Géant","Lidl","Netto",
    ],
    "Pétroliers": [
        "TotalEnergies","Total","Esso","BP","Shell","Avia","Agip","Elf",
    ],
    "Autoroute / Relais": ["Relais"],
}

SVC = {
    "Automate CB 24/24":                         ("💳","bg-g"),
    "Bornes électriques":                        ("⚡","bg-g"),
    "Boutique alimentaire":                      ("🛒","bg-b"),
    "Lavage automatique":                        ("🚿","bg-b"),
    "Restauration à emporter":                   ("🍔","bg-b"),
    "Restauration sur place":                    ("🍽️","bg-b"),
    "Station de gonflage":                       ("🔧","bg-w"),
    "Toilettes publiques":                       ("🚻","bg-w"),
    "Wifi":                                      ("📶","bg-w"),
    "DAB (Distributeur automatique de billets)": ("💰","bg-w"),
    "Boutique non alimentaire":                  ("🏪","bg-w"),
    "Piste poids lourds":                        ("🚛","bg-w"),
    "Services réparation / entretien":           ("🔩","bg-w"),
    "Bar":                                       ("☕","bg-b"),
    "Laverie":                                   ("🫧","bg-w"),
    "Relais colis":                              ("📦","bg-w"),
    "Location de véhicule":                      ("🚙","bg-w"),
    "Carburant additivé":                        ("⚗️","bg-w"),
    "Vente de gaz domestique (Butane, Propane)": ("🔥","bg-w"),
}

# Services affichés sur la card (priorité, 4 max)
SVC_PRIORITY = [
    "Automate CB 24/24", "Bornes électriques",
    "Lavage automatique", "Boutique alimentaire", "Wifi",
]

CONSO_PRESETS = {
    "🚗 Standard (6.5 L/100)":       6.5,
    "🏙️ Citadine (5.5 L/100)":      5.5,
    "🚗 Berline diesel (5.0 L/100)": 5.0,
    "🛻 SUV / 4×4 (9.0 L/100)":     9.0,
    "🚐 Utilitaire (8.5 L/100)":     8.5,
    "⚡ Hybride (4.0 L/100)":        4.0,
    "✏️ Personnalisé":                None,
}

JOURS = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
CARTO_DARK  = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
CARTO_LIGHT = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
ORS_BASE = "https://api.openrouteservice.org/v2"


# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE — une connexion pour toute la session
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def s(v):
    return str(v) if v is not None else ""

def sl(v):
    if isinstance(v, list): return v
    if isinstance(v, str):
        try:
            r = json.loads(v)
            return r if isinstance(r, list) else []
        except: return []
    return []

def geom_to_latlon(g):
    if isinstance(g, dict):
        return float(g.get("lat", 0)), float(g.get("lon", 0))
    if isinstance(g, str):
        try:
            d = json.loads(g)
            return float(d.get("lat", 0)), float(d.get("lon", 0))
        except: pass
    return 0.0, 0.0

def detect_brand(row):
    """Détecte la marque — ordre BRANDS critique (spécifique → générique)."""
    txt = f"{s(row.get('enseigne')).upper()} {s(row.get('adresse')).upper()}"
    for name, patterns in BRANDS:
        for p in patterns:
            if p in txt:
                return name
    return s(row.get("enseigne")).title() or None

def freshness(v):
    """(label, classe_css) selon l'âge de la mise à jour des prix."""
    if not v: return "?", "fr-old"
    try:
        raw = str(v).replace("Z", "+00:00")
        dt  = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        d = (datetime.now(timezone.utc) - dt).days
        if d == 0: return "🟢 Auj.", "fr-ok"
        if d <= 2: return f"🟡 {d}j", "fr-mid"
        return f"🔴 {d}j", "fr-old"
    except: return "?", "fr-old"

def dist_km(a, b, c, d):
    try: return round(geodesic((a, b), (c, d)).km, 1)
    except: return None

def is_open_now(row):
    """True / False / None (non renseigné)."""
    hj = s(row.get("horaires_jour"))
    if not hj: return None
    if "Automate-24-24" in hj or row.get("horaires_automate_24_24") == "Oui":
        return True
    today = datetime.now().weekday()
    jour  = JOURS[today]
    m = re.search(rf"{jour}(\d{{2}})\.(\d{{2}})-(\d{{2}})\.(\d{{2}})", hj)
    if not m: return False
    now_t   = datetime.now().time()
    open_t  = dtime(int(m.group(1)), int(m.group(2)))
    close_t = dtime(int(m.group(3)), int(m.group(4)))
    return open_t <= now_t <= close_t

def hours_html(raw):
    """Tableau HTML des horaires, jour actuel surligné."""
    hj = s(raw)
    if not hj: return "<span style='opacity:.5;font-size:.8rem'>Non renseignés</span>"
    is24  = "Automate-24-24" in hj
    today = datetime.now().weekday()
    rows  = ""
    for i, j in enumerate(JOURS):
        m   = re.search(rf"{j}(\d{{2}}\.\d{{2}})-(\d{{2}}\.\d{{2}})", hj)
        css = ' class="htbl-today"' if i == today else ""
        h   = (f"{m.group(1).replace('.','h')}–{m.group(2).replace('.','h')}"
               if m else ("24h/24" if is24 else "Fermé"))
        rows += f"<tr{css}><td style='width:70px;font-weight:600'>{j[:3]}.</td><td>{h}</td></tr>"
    b = '<span class="bg-g">🕐 Automate 24h/24</span><br>' if is24 else ""
    return f"{b}<table class='htbl'>{rows}</table>"

def open_badge(row):
    status = is_open_now(row)
    if status is True:  return '<span class="badge-open">✅ Ouvert</span>'
    if status is False: return '<span class="badge-closed">❌ Fermé</span>'
    return ""

def price_cls(pf, moy):
    """cheap / avg / exp selon l'écart à la moyenne."""
    ratio = (pf - moy) / max(abs(moy * .03), .001)
    return "cheap" if ratio < -.5 else ("exp" if ratio > .5 else "avg")

def nav_links(lat, lon):
    """Balises <a> Maps / Waze / Apple."""
    g = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
    w = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
    a = f"http://maps.apple.com/?daddr={lat},{lon}"
    return (f'<a href="{g}" target="_blank" class="nav-a na-gmaps">🗺️ Maps</a>'
            f'<a href="{w}" target="_blank" class="nav-a na-waze">🚗 Waze</a>'
            f'<a href="{a}" target="_blank" class="nav-a na-apple"> Apple</a>')


# ═══════════════════════════════════════════════════════════════════════════════
# DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=30, show_spinner=False)
def search_addresses(q):
    """Autocomplétion via api-adresse.data.gouv.fr (officiel, gratuit)."""
    if len(q) < 3: return []
    try:
        r = requests.get(
            "https://api-adresse.data.gouv.fr/search/",
            params={"q": q, "limit": 6, "autocomplete": 1},
            timeout=4,
        )
        return [{"label": f["properties"]["label"],
                 "lat":   f["geometry"]["coordinates"][1],
                 "lon":   f["geometry"]["coordinates"][0]}
                for f in r.json().get("features", [])]
    except: return []


@st.cache_data(ttl=300, show_spinner=False)
def load_stations(_sb, carb_col, lat, lon, radius):
    """Stations depuis Supabase. RPC d'abord, fallback bbox si absent."""
    try:
        r = _sb.rpc("get_stations_proches", {
            "user_lat": lat, "user_lon": lon,
            "carburant_col": carb_col, "radius_km": radius,
        }).execute()
        if r.data:
            df = pd.DataFrame(r.data)
            df.rename(columns={"prix": f"{carb_col}_prix",
                                "prix_maj": f"{carb_col}_maj"}, inplace=True)
            return df, True
    except Exception as e:
        st.caption(f"ℹ️ Fallback direct (RPC: {str(e)[:60]})")
    try:
        lat_min = lat - radius / 111
        lat_max = lat + radius / 111
        lon_d   = radius / (111 * math.cos(math.radians(lat)))
        r = (_sb.table("stations_carburant").select("*")
               .not_.is_(f"{carb_col}_prix", "null")
               .gte("lat", lat_min).lte("lat", lat_max)
               .gte("lon", lon - lon_d).lte("lon", lon + lon_d)
               .execute())
        return pd.DataFrame(r.data or []), False
    except Exception as e2:
        st.error(f"❌ Supabase : {e2}")
        return pd.DataFrame(), False


# ═══════════════════════════════════════════════════════════════════════════════
# FAVORIS
# ═══════════════════════════════════════════════════════════════════════════════

def toggle_fav(sid):
    favs = st.session_state.get("favorites", set())
    favs.discard(sid) if sid in favs else favs.add(sid)
    st.session_state.favorites = favs

def is_fav(sid):
    return sid in st.session_state.get("favorites", set())


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSANTS UI
# ═══════════════════════════════════════════════════════════════════════════════

def location_block():
    """Bloc GPS + adresse. Retourne (lat, lon, label) ou (None,None,None).
    Utilise st.radio (pas st.tabs) pour éviter le conflit CSS bottom nav."""

    method = st.radio("Méthode", ["📍 GPS", "🔍 Adresse"],
                      horizontal=True, label_visibility="collapsed",
                      key="loc_method")

    if method == "📍 GPS":
        st.markdown("<small>Votre navigateur demandera l'autorisation GPS.</small>",
                    unsafe_allow_html=True)
        if st.button("📡 Me localiser", key="gps_btn",
                     use_container_width=True, type="primary"):
            st.session_state.gps_asked    = True
            st.session_state.gps_attempts = 0
            st.session_state.pop("gps_result", None)

        if st.session_state.get("gps_asked"):
            attempts = st.session_state.get("gps_attempts", 0)
            with st.spinner(f"Localisation… ({attempts+1}/5)"):
                try:   loc = get_geolocation()
                except: loc = None

            if loc and isinstance(loc, dict) and loc.get("coords"):
                c = loc["coords"]
                lat, lon = float(c["latitude"]), float(c["longitude"])
                acc = c.get("accuracy", 0)
                st.session_state.gps_result   = (lat, lon)
                st.session_state.gps_asked    = False
                st.session_state.gps_attempts = 0
                st.markdown(f'<div class="gps-ok">✅ Position trouvée · ±{acc:.0f} m</div>',
                            unsafe_allow_html=True)
            elif attempts < 5:
                st.session_state.gps_attempts = attempts + 1
                st.markdown(
                    f'<div class="gps-err">⏳ En attente… ({attempts+1}/5) '
                    '— autorisez la géolocalisation.</div>', unsafe_allow_html=True)
                _time.sleep(0.5)
                st.rerun()
            else:
                st.session_state.gps_asked = False
                st.session_state.gps_attempts = 0
                st.markdown(
                    '<div class="gps-fail">❌ GPS indisponible. '
                    'Vérifiez les permissions ou utilisez la recherche adresse.</div>',
                    unsafe_allow_html=True)
                if st.button("🔄 Réessayer", key="gps_retry"):
                    st.session_state.gps_asked    = True
                    st.session_state.gps_attempts = 0
                    st.rerun()

        if "gps_result" in st.session_state:
            lat, lon = st.session_state.gps_result
            gps_lbl  = st.session_state.get("gps_label", f"{lat:.4f}, {lon:.4f}")
            st.markdown(f'<div class="gps-ok">📍 {gps_lbl}</div>',
                        unsafe_allow_html=True)
            return lat, lon, gps_lbl
    else:
        if "addr_selected" in st.session_state:
            info = st.session_state.addr_selected
            st.markdown(f'<div class="gps-ok">✅ {info["label"]}</div>',
                        unsafe_allow_html=True)
            if st.button("✏️ Changer", key="addr_reset", use_container_width=True):
                del st.session_state.addr_selected
                st.rerun()
            return info["lat"], info["lon"], info["label"]

        query = st.text_input("Adresse", placeholder="Ex : 5 rue de la Paix, Paris",
                              label_visibility="collapsed", key="addr_query_field")
        if query and len(query) >= 3:
            with st.spinner("Recherche…"):
                sugs = search_addresses(query)
            if sugs:
                st.markdown("**Sélectionnez :**")
                for i, sug in enumerate(sugs):
                    with st.container():
                        st.markdown('<div class="sug-btn">', unsafe_allow_html=True)
                        if st.button(f"📍 {sug['label']}", key=f"sug_{i}",
                                     use_container_width=True):
                            st.session_state.addr_selected = sug
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
            elif len(query) >= 5:
                st.caption("Aucun résultat — essayez une autre formulation.")
        elif query:
            st.caption("Tapez au moins 3 caractères…")

    return None, None, None


def render_tank_settings(key_prefix="ts_"):
    """Sliders réservoir. key_prefix évite les conflits mobile/desktop."""
    c1, c2 = st.columns(2)
    with c1:
        tank = st.select_slider("🛢️ Réservoir",
                                options=list(range(20, 115, 5)),
                                value=st.session_state.get("tank_cap", 50),
                                key=f"{key_prefix}tank",
                                format_func=lambda x: f"{x} L")
    with c2:
        fill = st.select_slider("🪣 Niveau actuel",
                                options=list(range(0, 95, 5)),
                                value=st.session_state.get("fill_pct", 20),
                                key=f"{key_prefix}fill",
                                format_func=lambda x: f"{x} %")
    st.session_state["tank_cap"] = tank
    st.session_state["fill_pct"] = fill
    return tank, fill


def render_detour_calc(df_sorted, carb_col, prix_min, litres_needed, key_prefix=""):
    """Calcule si le détour vers la station la moins chère est rentable."""
    pc = f"{carb_col}_prix"
    st.markdown("**🧮 Vaut-il le détour ?**")

    preset = st.selectbox("Profil", list(CONSO_PRESETS.keys()),
                          key=f"{key_prefix}preset", label_visibility="collapsed")
    conso = (st.number_input("Conso L/100", 2.0, 20.0, 6.5, 0.5,
                             key=f"{key_prefix}cval")
             if CONSO_PRESETS[preset] is None else CONSO_PRESETS[preset])

    best_row     = df_sorted[df_sorted[pc] == prix_min].iloc[0]
    best_dist    = float(best_row.get("distance_km", 0) or 0)
    closest_row  = df_sorted.sort_values("distance_km").iloc[0]
    closest_px   = float(closest_row[pc])
    closest_dist = float(closest_row.get("distance_km", 0) or 0)

    if abs(prix_min - closest_px) < 0.0005:
        st.markdown('<div class="calc-box"><span style="color:var(--green);font-size:.85rem">'
                    '✅ La moins chère est aussi la plus proche !</span></div>',
                    unsafe_allow_html=True)
        return

    detour_km   = max((best_dist - closest_dist) * 2, best_dist)
    cout_detour = detour_km * conso / 100 * prix_min
    eco_brute   = (closest_px - prix_min) * litres_needed
    eco_nette   = eco_brute - cout_detour
    ok    = eco_nette > 0
    color = "var(--green)" if ok else "var(--red)"
    icon  = "✅" if ok else "⚠️"
    msg   = "ça vaut le coup !" if ok else "le détour coûte plus que l'économie."

    st.markdown(
        f'<div class="calc-box">'
        f'<div style="font-size:.72rem;color:var(--text-2);margin-bottom:7px">'
        f'🏠 {closest_dist:.1f} km @ {closest_px:.3f}€ → 🏆 {best_dist:.1f} km @ {prix_min:.3f}€</div>'
        f'<div style="display:flex;gap:7px;margin-bottom:7px">'
        f'<div class="calc-mini" style="flex:1"><div style="color:var(--green);font-weight:800">+{eco_brute:.2f}€</div>'
        f'<div style="font-size:.7rem;color:var(--text-2)">Économie brute</div></div>'
        f'<div class="calc-mini" style="flex:1"><div style="color:var(--red);font-weight:800">−{cout_detour:.2f}€</div>'
        f'<div style="font-size:.7rem;color:var(--text-2)">Détour ({detour_km:.1f} km)</div></div>'
        f'</div>'
        f'<div style="color:{color};font-weight:800;font-size:.9rem">'
        f'{icon} Gain réel : {eco_nette:+.2f}€ — {msg}</div></div>',
        unsafe_allow_html=True)


def render_best_deal(row, carb_col, u_lat, u_lon):
    """Bannière 'Meilleure offre' en haut des résultats."""
    pc    = f"{carb_col}_prix"
    prix  = float(row.get(pc, 0))
    brand = detect_brand(row)
    label = f"{brand} · " if brand else ""
    d     = row.get("distance_km") or dist_km(u_lat, u_lon,
                                              *geom_to_latlon(row.get("geom")))
    tank  = st.session_state.get("tank_cap", 50)
    fill  = st.session_state.get("fill_pct", 20)
    litre = round(tank * (1 - fill / 100), 1)
    cout  = round(litre * prix, 2)
    moy   = st.session_state.get("prix_moy_cache", prix)
    eco   = round(litre * (moy - prix), 2)
    eco_s = f'<div class="bd-eco">💚 −{eco:.2f}€ vs la moyenne</div>' if eco > 0.3 else ""
    open_s = open_badge(row)
    lat, lon = row.get("lat", u_lat), row.get("lon", u_lon)
    g = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
    w = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
    a = f"http://maps.apple.com/?daddr={lat},{lon}"

    st.markdown(f"""
<div class="best-deal">
  <div class="bd-price">{prix:.3f}€</div>
  <div class="bd-meta">
    <div class="bd-name">🏆 {label}{s(row.get("adresse",""))}</div>
    <div class="bd-sub">📍 {d} km · {s(row.get("ville",""))} {open_s}</div>
    {eco_s}
    <div class="bd-nav">
      <a href="{g}" target="_blank" class="nav-a na-gmaps">🗺️ Maps</a>
      <a href="{w}" target="_blank" class="nav-a na-waze">🚗 Waze</a>
      <a href="{a}" target="_blank" class="nav-a na-apple"> Apple</a>
    </div>
  </div>
  <div class="bd-right">
    <div class="bd-cout">💶 {cout:.2f}€</div>
    <div class="bd-litre">{litre:.0f} L estimés</div>
  </div>
</div>""", unsafe_allow_html=True)


def render_card(row, carb_col, u_lat, u_lon, moy, idx=0):
    """Station card — layout 3 colonnes : PRIX | INFO | NAV.
    Design complètement différent de la v13 :
    - Prix affiché en grand sur la gauche avec fond coloré
    - Info structurée au centre (marque, adresse, services)
    - Navigation compacte à droite (Maps/Waze/Apple)
    - Favori et horaires en ligne sous la card (non imbriqués dans l'HTML)
    """
    pc = f"{carb_col}_prix"
    prix = row.get(pc)
    if prix is None: return

    pf     = float(prix)
    cls    = price_cls(pf, moy)
    fr, fr_cls = freshness(row.get(f"{carb_col}_maj"))
    d      = row.get("distance_km") or dist_km(u_lat, u_lon,
                                               *geom_to_latlon(row.get("geom")))
    brand  = detect_brand(row)
    open_s = open_badge(row)

    svcs = "".join(
        f'<span class="{SVC[sv][1]}">{SVC[sv][0]} {sv}</span>'
        for sv in sl(row.get("services_service"))
        if sv in SVC_PRIORITY and sv in SVC
    )
    if row.get("horaires_automate_24_24") == "Oui":
        svcs = '<span class="bg-g">🕐 24h/24</span>' + svcs

    tank   = st.session_state.get("tank_cap", 50)
    fill   = st.session_state.get("fill_pct", 20)
    pmax   = st.session_state.get("prix_max_cache", moy)
    litres = round(tank * (fill / 100), 1)

    mode_cout = st.session_state.get("mode_cout", "reel")
    detour_km = float(row.get("distance_km", 0) or 0)
    conso = get_conso()
    cout_affiche = cout_reel_fn(pf, detour_km, litres, conso) if mode_cout == "reel" else round(litres * pf, 2)

    eco_v    = round(litres * (moy - pf), 2)
    eco_mx   = round(litres * (pmax - pf), 2)
    best_id  = st.session_state.get("best_station_id")
    is_best  = str(row.get("id")) == str(best_id)
    best_badge = '<div class="sc-best">💡 Meilleur choix</div>' if is_best else ""

    eco_html = ""
    if eco_v > 0.3:
        eco_html += '<span class="eco-tag">💡 ' + format(eco_v, '.2f') + '€ économisés vs moyenne</span>'
    if eco_mx > 0.5:
        eco_html += '<span class="eco-tag-2">💡 ' + format(eco_mx, '.2f') + '€ économisés vs plus cher</span>'

    sid = str(row.get("id", f"{d}_{pf}"))
    lat, lon = row.get("lat", u_lat), row.get("lon", u_lon)
    g = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
    w = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
    a = f"http://maps.apple.com/?daddr={lat},{lon}"

    station_name = brand or s(row.get("adresse", ""))
    svcs_line = '<div class="sc-svcs">' + svcs + '</div>' if svcs else ""
    eco_line  = '<div class="sc-eco">' + eco_html + '</div>' if eco_html else ""

    st.markdown(f"""
<div class="scard">
  <div class="sc-info" style="grid-column: 1 / -1; margin-bottom: 2px;">
    {best_badge}
  </div>

  <div class="sc-price {cls}">
    <div class="sc-pval {cls}">{pf:.3f}</div>
    <div class="sc-punit">€/L</div>
    <div class="sc-pfill">{cout_affiche:.2f}€</div>
    <div class="sc-plitre">{litres:.0f}L estimés</div>
  </div>

  <div class="sc-info">
    <div class="sc-brand">{station_name}</div>
    <div class="sc-addr">{s(row.get("adresse",""))}</div>
    <div class="sc-meta">📍 {d} km · {s(row.get("cp",""))} {s(row.get("ville",""))} {open_s}</div>
    {svcs_line}
    {eco_line}
  </div>

  <div class="sc-nav">
    <a href="{g}" target="_blank" class="nav-a na-gmaps">🗺️ Maps</a>
    <a href="{w}" target="_blank" class="nav-a na-waze">🚗 Waze</a>
    <a href="{a}" target="_blank" class="nav-a na-apple"> Apple</a>
    <div class="sc-fr {fr_cls}">{fr}</div>
  </div>

</div>""", unsafe_allow_html=True)

    # Bouton favori + expander horaires — hors HTML (composants Streamlit)
    fav_col, det_col = st.columns([1, 4])
    with fav_col:
        icon = "⭐" if is_fav(sid) else "☆"
        if st.button(f"{icon} Favori", key=f"fav_{sid}_{idx}",
                     use_container_width=True):
            toggle_fav(sid)
            st.rerun()
    with det_col:
        with st.expander("ℹ️ Horaires & services complets", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🕐 Horaires**")
                st.markdown(hours_html(row.get("horaires_jour")),
                            unsafe_allow_html=True)
            with c2:
                st.markdown("**🛎️ Services**")
                all_sv = sl(row.get("services_service"))
                if all_sv:
                    st.markdown("".join(
                        f'<span class="{SVC.get(sv,("","bg-w"))[1]}">'
                        f'{SVC.get(sv,("•","bg-w"))[0]} {sv}</span><br>'
                        for sv in all_sv if sv in SVC
                    ) or "<span style='opacity:.5;font-size:.8rem'>Aucun</span>",
                    unsafe_allow_html=True)
                else:
                    st.caption("Non renseignés")


def render_bottom_nav(active, n_filters=0):
    """Bottom nav mobile — 5 onglets : Stations | Carte | En chemin | Voyage | Réglages."""
    items = [
        ("stations", "⛽\nStations"),
        ("map",      "🗺️\nCarte"),
        ("chemin",   "➡️\nEn chemin"),
        ("voyage",   "🛣️\nVoyage"),
        ("settings", f"⚙️\nRéglages{f' ({n_filters})' if n_filters else ''}"),
    ]
    st.markdown('<div class="bnav-trigger"></div>', unsafe_allow_html=True)
    cols    = st.columns(5)
    clicked = None
    for i, (key, label) in enumerate(items):
        with cols[i]:
            if st.button(label, key=f"bnav_{key}", use_container_width=True,
                         type="primary" if key == active else "secondary"):
                clicked = key
    if clicked and clicked != active:
        st.session_state["active_tab"] = clicked
        st.rerun()


def render_onboarding():
    st.markdown("""
<div class="onboard">
  <div class="onboard-icon">⛽</div>
  <h2>Trouvez le carburant<br>le moins cher</h2>
  <p>Activez votre GPS ou entrez une adresse pour démarrer.</p>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CARTE PYDECK
# ═══════════════════════════════════════════════════════════════════════════════

def prepare_map_data(df_d, carb_col, pmin, pmax, u_lat, u_lon):
    """Ajoute les colonnes nécessaires au rendu pydeck (couleur, tooltip…)."""
    pc = f"{carb_col}_prix"

    def color(p):
        """Vert→orange→rouge selon position dans [pmin, pmax]."""
        if pmax == pmin: return [96, 165, 250, 220]
        r = (p - pmin) / (pmax - pmin)
        if r < .33:  return [34,  197,  94, 230]   # vert
        if r < .66:  return [245, 158,  11, 230]   # orange/amber
        return             [239,  68,  68, 230]    # rouge

    dm = df_d.copy()
    dm["color"]     = dm[pc].astype(float).apply(color)
    dm["price_str"] = dm[pc].astype(float).apply(lambda p: f"{p:.3f}€/L")
    dm["brand_str"] = dm.apply(lambda r: detect_brand(dict(r)) or "Station", axis=1)
    dm["dist_str"]  = dm["distance_km"].apply(
        lambda d: f"📍 {d:.1f} km" if pd.notna(d) else "")
    dm["open_str"]  = dm.apply(lambda r: (
        "✅ Ouvert" if is_open_now(dict(r)) is True
        else ("❌ Fermé" if is_open_now(dict(r)) is False else "")), axis=1)
    dm["fr_str"]    = dm[f"{carb_col}_maj"].apply(
        lambda v: f"Mis à jour : {freshness(v)[0]}")
    dm["svcs_str"]  = dm["services_service"].apply(lambda v: "  ".join(
        f"{SVC[sv][0]} {sv}" for sv in sl(v)
        if sv in SVC_PRIORITY and sv in SVC
    )[:90])
    for col in ["adresse", "ville"]:
        dm[col] = dm[col].fillna("") if col in dm.columns else ""
    return dm


def build_deck(dm, user_lat, user_lon, radius, dark_mode):
    """Construit le Deck pydeck avec tooltip enrichi."""
    zoom      = 13 if radius <= 5 else (12 if radius <= 10 else (11 if radius <= 20 else 10))
    map_style = CARTO_DARK if dark_mode else CARTO_LIGHT

    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=dm[["lat","lon","color","price_str","brand_str",
                 "adresse","ville","dist_str","open_str","fr_str","svcs_str"]],
        get_position=["lon","lat"],
        get_color="color",
        get_radius=100,
        pickable=True,
        auto_highlight=True,
        highlight_color=[249, 115, 22, 255],  # orange au survol (couleur de marque)
    )
    text = pdk.Layer(
        "TextLayer",
        data=dm[["lat","lon","price_str"]],
        get_position=["lon","lat"],
        get_text="price_str",
        get_size=11,
        get_color=[240, 240, 240, 200],
        get_pixel_offset=[0, -18],
        pickable=False,
    )
    user_dot = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": user_lat, "lon": user_lon}]),
        get_position=["lon","lat"],
        get_color=[249, 115, 22, 255],  # point orange = vous
        get_radius=90,
        pickable=False,
    )

    # Tooltip complet : toutes les infos sans avoir à ouvrir une card
    tooltip = {
        "html": """
<div style='font-family:Outfit,system-ui,sans-serif;min-width:210px'>
  <div style='font-weight:800;font-size:.95rem;margin-bottom:3px'>{brand_str}</div>
  <div style='font-size:.78rem;opacity:.8;margin-bottom:6px'>{adresse}, {ville}</div>
  <div style='font-size:1.5rem;font-weight:900;color:#22c55e;margin:5px 0'>{price_str}</div>
  <div style='font-size:.74rem;opacity:.7'>{dist_str} &nbsp;·&nbsp; {open_str}</div>
  <div style='font-size:.7rem;opacity:.6;margin-top:2px'>{fr_str}</div>
  <div style='margin-top:6px;font-size:.72rem;opacity:.8'>{svcs_str}</div>
</div>""",
        "style": {
            "backgroundColor": "#111827",
            "color": "#f1f5f9",
            "borderRadius": "12px",
            "padding": "12px 15px",
            "boxShadow": "0 8px 30px rgba(0,0,0,.5)",
            "border": "1px solid rgba(255,255,255,.08)",
        },
    }

    return pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=user_lat, longitude=user_lon,
            zoom=zoom, pitch=0),
        layers=[scatter, text, user_dot],
        tooltip=tooltip,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SHOW RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

def show_results(sb, carb_col, carb_name, user_lat, user_lon,
                 radius, sort_by, filters, is_mobile,
                 tank_cap=50, dark_mode=True):
    """Charge, filtre, trie et affiche les stations."""

    with st.spinner(f"Recherche {carb_name} dans {radius} km…"):
        df, via_rpc = load_stations(sb, carb_col, user_lat, user_lon, float(radius))

    if df.empty:
        st.warning("Aucune station trouvée. Essayez d'augmenter le rayon.")
        return

    pc = f"{carb_col}_prix"
    mc = f"{carb_col}_maj"

    # Nettoyage géo
    if "lat" not in df.columns:
        df[["lat","lon"]] = df["geom"].apply(lambda g: pd.Series(geom_to_latlon(g)))
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df[(df["lat"].notna()) & (df["lon"].notna()) & (df["lat"] != 0) & (df["lon"] != 0)]

    # Distance
    if "distance_km" not in df.columns:
        df["distance_km"] = df.apply(
            lambda r: dist_km(user_lat, user_lon, r["lat"], r["lon"]) or 9999, axis=1)

    df = df[df["distance_km"].astype(float) <= float(radius)]
    df = df[df[pc].notna()]
    if df.empty:
        st.warning("Aucune station dans ce rayon avec des prix renseignés.")
        return

    # Filtres
    f_24h, f_cb, f_ev, f_wash, f_open, brand_group, f_resto, f_wifi, f_dab = filters
    def has(v, svc): return svc in sl(v)
    n_before = len(df)
    if f_24h:  df = df[df["horaires_automate_24_24"] == "Oui"]
    if f_cb:   df = df[df["services_service"].apply(lambda v: has(v,"Automate CB 24/24"))]
    if f_ev:   df = df[df["services_service"].apply(lambda v: has(v,"Bornes électriques"))]
    if f_wash: df = df[df["services_service"].apply(lambda v: has(v,"Lavage automatique"))]
    if f_open: df = df[df.apply(lambda r: is_open_now(dict(r)) is True, axis=1)]
    if f_resto:df = df[df["services_service"].apply(
                    lambda v: has(v,"Restauration à emporter") or has(v,"Restauration sur place"))]
    if f_wifi: df = df[df["services_service"].apply(lambda v: has(v,"Wifi"))]
    if f_dab:  df = df[df["services_service"].apply(
                    lambda v: has(v,"DAB (Distributeur automatique de billets)"))]
    if brand_group and brand_group != "Toutes":
        allowed = BRAND_GROUPS.get(brand_group, [])
        df = df[df.apply(lambda r: detect_brand(dict(r)) in allowed, axis=1)]
    if df.empty:
        st.warning("Aucune station avec ces filtres. Essayez d'en désactiver certains.")
        return
    if 0 < len(df) <= 3 and len(df) < n_before:
        st.warning(f"⚠️ Filtres très restrictifs — seulement {len(df)} station(s) trouvée(s).")

    # Tri
    mode = st.session_state.get("mode_cout", "reel")
    litres_score = round(st.session_state.get("tank_cap", tank_cap)
                         * (1 - st.session_state.get("fill_pct", 20) / 100), 1)
    conso_score = get_conso()
    df = df.copy()
    df["detour_km"] = pd.to_numeric(df.get("distance_km", 0), errors="coerce").fillna(0)
    df["cout_affiche"] = df[pc].astype(float).apply(
        lambda prix: round(litres_score * prix, 2)
    )
    if mode == "reel":
        df["cout_affiche"] = df.apply(
            lambda r: cout_reel_fn(float(r[pc]), float(r.get("detour_km", 0) or 0), litres_score, conso_score),
            axis=1
        )
        df["score"] = df["cout_affiche"] + (df["detour_km"].fillna(0) * 0.05)

    if sort_by == "Prix ↑":
        if mode == "reel":
            df_d = df.sort_values("score")
            sort_label = "meilleur choix (coût + distance)"
        else:
            df_d = df.sort_values(pc)
            sort_label = "prix au litre"
    elif sort_by == "Prix ↓":
        df_d = df.sort_values(pc, ascending=False)
        sort_label = "prix au litre décroissant"
    elif sort_by == "Récent":
        df_d = df.sort_values(mc, ascending=False, na_position="last")
        sort_label = "mise à jour récente"
    else:
        df_d = df.sort_values("distance_km")
        sort_label = "distance"

    # Stats
    pv   = df_d[pc].astype(float)
    moy  = pv.mean()
    pmin, pmax = pv.min(), pv.max()
    st.session_state.update({
        "prix_min_cache": pmin,
        "prix_max_cache": pmax,
        "prix_moy_cache": moy,
    })

    best = (df_d.sort_values("score").iloc[0] if (not df_d.empty and "score" in df_d.columns) else (df_d.iloc[0] if not df_d.empty else None))
    if best is not None:
        st.session_state["best_station_id"] = best.get("id")

    # Carte
    dm   = prepare_map_data(df_d, carb_col, pmin, pmax, user_lat, user_lon)
    deck = build_deck(dm, user_lat, user_lon, radius, dark_mode)
    legend = ('<div class="map-legend">🟢 moins cher &nbsp;·&nbsp; '
              '🟡 moyen &nbsp;·&nbsp; 🔴 plus cher &nbsp;·&nbsp; '
              '🟠 vous</div>')
    n_filters = sum([f_24h, f_cb, f_ev, f_wash, f_open])

    # ── MOBILE ──────────────────────────────────────────────────────────────
    if is_mobile:
        active_view = st.session_state.get("active_tab", "stations")

        if active_view == "map":
            st.markdown(
                f'<div class="sbar"><span class="sdot sdot-g"></span>'
                f'<b>{len(df_d)}</b> stations · '
                f'<b style="color:var(--green)">{pmin:.3f}€</b> min · '
                f'<b style="color:var(--red)">{pmax:.3f}€</b> max</div>',
                unsafe_allow_html=True)
            st.pydeck_chart(deck, use_container_width=True, height=490)
            st.markdown(legend, unsafe_allow_html=True)
            return

        if active_view == "favs":
            fav_ids = st.session_state.get("favorites", set())
            if not fav_ids:
                st.markdown("""
<div class="onboard">
  <div class="onboard-icon">⭐</div>
  <h2>Aucun favori</h2>
  <p>Tapez ☆ Favori sous une station pour l'épingler ici.</p>
</div>""", unsafe_allow_html=True)
                return
            if "id" not in df_d.columns:
                st.info("Identifiants manquants — impossible d'afficher les favoris.")
                return
            fav_df = df_d[df_d["id"].astype(str).isin(fav_ids)]
            if fav_df.empty:
                st.info("Vos favoris ne sont pas dans le rayon actuel.")
                return
            for i, (_, r) in enumerate(fav_df.iterrows()):
                render_card(dict(r), carb_col, user_lat, user_lon, moy, i)
            return

        # Vue STATIONS
        if best is not None:
            render_best_deal(dict(best), carb_col, user_lat, user_lon)

        flt = (f" · <span style='color:var(--accent)'>{n_filters} filtre(s)</span>"
               if n_filters else "")
        st.markdown(
            f'<div class="sbar"><span class="sdot sdot-g"></span>'
            f'<b>{len(df_d)}</b> stations · {sort_label}{flt}</div>',
            unsafe_allow_html=True)

        with st.expander("🛢️ Réservoir & calculateur de détour", expanded=False):
            render_tank_settings(key_prefix="mob_ts_")
            if best is not None:
                l_ = round(st.session_state.get("tank_cap",50)
                           * (1-st.session_state.get("fill_pct",20)/100), 1)
                render_detour_calc(df_d, carb_col, pmin, l_, key_prefix="mob_dtc_")

        list_df = df_d[df_d["id"].astype(str) != str(best.get("id"))] if (best is not None and "id" in df_d.columns) else df_d
        for i, (_, r) in enumerate(list_df.head(30).iterrows()):
            render_card(dict(r), carb_col, user_lat, user_lon, moy, i)

    # ── DESKTOP ──────────────────────────────────────────────────────────────
    else:
        tank_ = st.session_state.get("tank_cap", tank_cap)

        # KPIs en ligne
        k1, k2, k3, k4 = st.columns(4)
        status = "🟢 Temps réel" if via_rpc else "🟡 Fallback"
        st.markdown(f'<div class="sbar"><span class="sdot sdot-g"></span>'
                    f'{status} · <b>{len(df_d)}</b> stations · {carb_name}</div>',
                    unsafe_allow_html=True)
        for col_, val_, lbl_, clr_ in [
            (k1, f"{pmin:.3f}€", f"Min {carb_name}", "var(--green)"),
            (k2, f"{moy:.3f}€",  "Moyenne",           "var(--text)"),
            (k3, f"{pmax:.3f}€", "Max",                "var(--red)"),
            (k4, f"−{round((pmax-pmin)*tank_,2):.2f}€", f"Éco/{tank_}L", "var(--blue)"),
        ]:
            with col_:
                st.markdown(
                    f'<div class="kpi"><div class="kpi-v" style="color:{clr_}">{val_}</div>'
                    f'<div class="kpi-l">{lbl_}</div></div>', unsafe_allow_html=True)
        st.markdown("")

        # Carte + liste côte à côte
        col_map, col_list = st.columns([6, 4])
        with col_map:
            st.pydeck_chart(deck, use_container_width=True, height=500)
            st.markdown(legend, unsafe_allow_html=True)

        with col_list:
            if best is not None:
                render_best_deal(dict(best), carb_col, user_lat, user_lon)
            with st.expander("🛢️ Réservoir & calculateur de détour", expanded=False):
                render_tank_settings(key_prefix="dsk_ts_")
                if best is not None:
                    l_ = round(st.session_state.get("tank_cap",50)
                               * (1-st.session_state.get("fill_pct",20)/100), 1)
                    render_detour_calc(df_d, carb_col, pmin, l_, key_prefix="dsk_dtc_")
            st.markdown(f"**📋 {len(df_d)} stations · tri : {sort_label}**")
            list_df = df_d[df_d["id"].astype(str) != str(best.get("id"))] if (best is not None and "id" in df_d.columns) else df_d
            for i, (_, r) in enumerate(list_df.head(25).iterrows()):
                render_card(dict(r), carb_col, user_lat, user_lon, moy, i)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════════════
# v15 — HELPERS VÉHICULE & COÛT RÉEL
# ═══════════════════════════════════════════════════════════════════════════════

def get_conso() -> float:
    """Consommation active (L/100) depuis session_state."""
    preset = st.session_state.get("conso_preset", "🚗 Standard (6.5 L/100)")
    val    = CONSO_PRESETS.get(preset)
    if val is None:
        return float(st.session_state.get("conso_custom", 6.5))
    return val


def cout_reel_fn(prix: float, detour_km: float, litres: float, conso: float) -> float:
    """Coût total = plein + aller-retour détour selon consommation."""
    return round(litres * prix + (detour_km * 2) * conso / 100 * prix, 2)


def calc_autonomie(tank: int, fill_pct: int, conso: float) -> float:
    """Autonomie restante en km."""
    litres = tank * (fill_pct / 100)
    return round(litres / conso * 100, 0) if conso > 0 else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# v15 — API OPENROUTESERVICE
# ═══════════════════════════════════════════════════════════════════════════════

def get_ors_route(slat, slon, elat, elon, api_key):
    """Retourne {distance_km, duration_min, coords} ou {} si erreur."""
    url  = f"{ORS_BASE}/directions/driving-car/geojson"
    body = {"coordinates": [[slon, slat], [elon, elat]]}
    try:
        r = requests.post(url, json=body,
                          headers={"Authorization": api_key}, timeout=10)
        if r.status_code != 200:
            return {}
        feat  = r.json()["features"][0]
        props = feat["properties"]["summary"]
        coords = feat["geometry"]["coordinates"]
        return {
            "distance_km":  round(props["distance"] / 1000, 1),
            "duration_min": round(props["duration"] / 60, 0),
            "coords":       coords,
        }
    except Exception:
        return {}


def point_to_route_dist(lat, lon, coords):
    """Distance minimale du point à la polyligne (km)."""
    if not coords:
        return 999.0
    best = min(dist_km(lat, lon, c[1], c[0]) or 999 for c in coords)
    return round(best, 2)


def stations_on_route(df, coords, corridor_km=5.0):
    """Filtre les stations dans corridor_km du trajet."""
    if df.empty or not coords:
        return df
    df = df.copy()
    df["detour_km"] = df.apply(
        lambda r: point_to_route_dist(float(r.get("lat", 0)),
                                      float(r.get("lon", 0)), coords), axis=1)
    return df[df["detour_km"] <= corridor_km].sort_values("detour_km")


# ═══════════════════════════════════════════════════════════════════════════════
# v15 — RENDER VEHICLE SETTINGS (remplace render_tank_settings dans nouveaux onglets)
# ═══════════════════════════════════════════════════════════════════════════════

def render_vehicle_settings(key_prefix="vs_"):
    """Réservoir + niveau + profil conso + mode coût."""
    c1, c2 = st.columns(2)
    with c1:
        tank = st.select_slider("🛢️ Réservoir",
                                options=list(range(20, 115, 5)),
                                value=st.session_state.get("tank_cap", 50),
                                key=f"{key_prefix}tank",
                                format_func=lambda x: f"{x} L")
    with c2:
        fill = st.select_slider("🪣 Niveau actuel",
                                options=list(range(0, 95, 5)),
                                value=st.session_state.get("fill_pct", 20),
                                key=f"{key_prefix}fill",
                                format_func=lambda x: f"{x} %")
    st.session_state["tank_cap"] = tank
    st.session_state["fill_pct"] = fill

    preset = st.selectbox(
        "🚗 Profil véhicule", list(CONSO_PRESETS.keys()),
        index=list(CONSO_PRESETS.keys()).index(
            st.session_state.get("conso_preset", "🚗 Standard (6.5 L/100)")),
        key=f"{key_prefix}conso_preset")
    st.session_state["conso_preset"] = preset

    if CONSO_PRESETS[preset] is None:
        custom = st.number_input("Conso (L/100)", 2.0, 20.0,
                                 float(st.session_state.get("conso_custom", 6.5)),
                                 0.5, key=f"{key_prefix}cval")
        st.session_state["conso_custom"] = custom

    mode = st.radio(
        "💰 Calcul du coût",
        ["Prix au litre uniquement", "Prix + coût du trajet (aller-retour)"],
        index=0 if st.session_state.get("mode_cout", "reel") == "simple" else 1,
        horizontal=True, key=f"{key_prefix}mode")
    st.session_state["mode_cout"] = "simple" if "uniquement" in mode else "reel"

    conso  = get_conso()
    litres = round(tank * (1 - fill / 100), 1)
    auto   = calc_autonomie(tank, fill, conso)
    st.markdown(
        f'<div class="calc-box" style="margin-top:6px;font-size:.8rem">'
        f'🔋 Autonomie estimée : <b>{auto:.0f} km</b> · {litres:.0f} L restants'
        f'</div>', unsafe_allow_html=True)
    return tank, fill


# ═══════════════════════════════════════════════════════════════════════════════
# v15 — ONGLET EN CHEMIN (A → B)
# ═══════════════════════════════════════════════════════════════════════════════

def tab_en_chemin(sb, carb_col, carb_name, dark_mode=True):
    st.markdown("### 🗺️ Stations en chemin")
    ors_key = st.secrets.get("ORS_API_KEY", "")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec-label">📍 Départ</div>', unsafe_allow_html=True)
        dep_q = st.text_input("Départ", placeholder="Ex: Lille, Gare",
                              key="rt_dep", label_visibility="collapsed")
    with c2:
        st.markdown('<div class="sec-label">🏁 Arrivée</div>', unsafe_allow_html=True)
        arr_q = st.text_input("Arrivée", placeholder="Ex: Paris Opéra",
                              key="rt_arr", label_visibility="collapsed")

    corridor = st.slider("Corridor autour du trajet (km)", 1, 15, 5, key="rt_corridor")

    with st.expander("⚙️ Paramètres véhicule", expanded=False):
        render_vehicle_settings("rt_vs_")

    if dep_q and arr_q and st.button("🔍 Stations en chemin", type="primary", key="btn_rt"):
        dep_s = search_addresses(dep_q)
        arr_s = search_addresses(arr_q)
        if not dep_s: st.error("Départ introuvable."); return
        if not arr_s: st.error("Arrivée introuvable."); return
        st.session_state["rt_dep_data"] = dep_s[0]
        st.session_state["rt_arr_data"] = arr_s[0]
        if not ors_key:
            st.warning("ORS_API_KEY manquante → rayon autour du point médian.")
            d_approx = (dist_km(dep_s[0]["lat"], dep_s[0]["lon"],
                                arr_s[0]["lat"], arr_s[0]["lon"]) or 50) * 1.25
            st.session_state["rt_route"] = {
                "distance_km": d_approx, "duration_min": d_approx / 100 * 60, "coords": []}
        else:
            with st.spinner("Calcul itinéraire…"):
                st.session_state["rt_route"] = get_ors_route(
                    dep_s[0]["lat"], dep_s[0]["lon"],
                    arr_s[0]["lat"], arr_s[0]["lon"], ors_key)

    dep   = st.session_state.get("rt_dep_data")
    arr   = st.session_state.get("rt_arr_data")
    route = st.session_state.get("rt_route")

    if not dep or not arr:
        st.info("Entrez un départ et une arrivée pour démarrer.")
        return

    if route:
        st.markdown(
            f'<div class="calc-box">🛣️ <b>{route["distance_km"]:.0f} km</b> · '
            f'⏱️ {route["duration_min"]:.0f} min</div>', unsafe_allow_html=True)

    mid_lat  = (dep["lat"] + arr["lat"]) / 2
    mid_lon  = (dep["lon"] + arr["lon"]) / 2
    r_search = max((route.get("distance_km", 50) if route else 50) / 2 + corridor, 20)

    with st.spinner("Chargement des stations…"):
        df, _ = load_stations(sb, carb_col, mid_lat, mid_lon, min(r_search, 100))

    if df.empty:
        st.warning("Aucune station trouvée."); return

    if "lat" not in df.columns:
        df[["lat","lon"]] = df["geom"].apply(lambda g: pd.Series(geom_to_latlon(g)))
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df[(df["lat"].notna()) & (df["lon"].notna())]

    pc = f"{carb_col}_prix"
    df = df[df[pc].notna()]
    if df.empty:
        st.warning("Aucune station avec prix."); return

    coords = route.get("coords", []) if route else []
    if coords:
        df = stations_on_route(df, coords, corridor)
    else:
        df["detour_km"] = df.apply(
            lambda r: dist_km(dep["lat"], dep["lon"],
                              float(r["lat"]), float(r["lon"])) or 999, axis=1)
        df = df[df["detour_km"] <= r_search]

    if df.empty:
        st.warning("Aucune station dans le corridor."); return

    tank   = st.session_state.get("tank_cap", 50)
    fill   = st.session_state.get("fill_pct", 20)
    conso  = get_conso()
    litres = round(tank * (1 - fill / 100), 1)
    mode   = st.session_state.get("mode_cout", "simple")

    df["distance_km"] = df.apply(
        lambda r: dist_km(dep["lat"], dep["lon"],
                          float(r["lat"]), float(r["lon"])) or 0, axis=1)

    if mode == "reel":
        df["cout_affiche"] = df.apply(
            lambda r: cout_reel_fn(float(r[pc]),
                                   float(r.get("detour_km", r.get("distance_km", 0))),
                                   litres, conso), axis=1)
        df = df.sort_values("cout_affiche")
        sort_label = "coût total (trajet inclus)"
    else:
        df["cout_affiche"] = df[pc].astype(float) * litres
        df = df.sort_values(pc)
        sort_label = "prix au litre"

    pv   = df[pc].astype(float)
    moy  = pv.mean()
    pmin = pv.min()
    pmax = pv.max()

    dm   = prepare_map_data(df, carb_col, pmin, pmax, dep["lat"], dep["lon"])
    deck = build_deck(dm, dep["lat"], dep["lon"], 50, dark_mode)

    st.markdown(f"**{len(df)} stations · {carb_name} · tri : {sort_label}**")
    st.pydeck_chart(deck, use_container_width=True, height=300)

    for i, (_, r) in enumerate(df.head(20).iterrows()):
        rd = dict(r)
        rd["distance_km"] = rd.get("detour_km", rd.get("distance_km", 0))
        render_card(rd, carb_col, dep["lat"], dep["lon"], moy, i)


# ═══════════════════════════════════════════════════════════════════════════════
# v15 — ONGLET PLANIFICATEUR VOYAGE
# ═══════════════════════════════════════════════════════════════════════════════

def tab_voyage(sb, carb_col, carb_name, dark_mode=True):
    st.markdown("### 🛣️ Planificateur de voyage")
    ors_key = st.secrets.get("ORS_API_KEY", "")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec-label">📍 Départ</div>', unsafe_allow_html=True)
        dep_q = st.text_input("Départ voy.", placeholder="Ex: Lille",
                              key="voy_dep", label_visibility="collapsed")
    with c2:
        st.markdown('<div class="sec-label">🏁 Destination</div>', unsafe_allow_html=True)
        arr_q = st.text_input("Arrivée voy.", placeholder="Ex: Bordeaux",
                              key="voy_arr", label_visibility="collapsed")

    with st.expander("⚙️ Paramètres véhicule", expanded=True):
        render_vehicle_settings("voy_vs_")

    reserve_pct = st.slider("Réserve minimum avant arrêt (%)", 5, 30, 15, key="voy_res",
                             help="L'app recommande un arrêt avant ce niveau")
    tank   = st.session_state.get("tank_cap", 50)
    fill   = st.session_state.get("fill_pct", 20)
    conso  = get_conso()
    auto_utile = calc_autonomie(tank, max(fill - reserve_pct, 0), conso)
    auto_plein = calc_autonomie(tank, 100 - reserve_pct, conso)

    if dep_q and arr_q and st.button("🗺️ Planifier", type="primary", key="btn_voy"):
        dep_s = search_addresses(dep_q)
        arr_s = search_addresses(arr_q)
        if not dep_s: st.error("Départ introuvable."); return
        if not arr_s: st.error("Arrivée introuvable."); return
        st.session_state["voy_dep_data"] = dep_s[0]
        st.session_state["voy_arr_data"] = arr_s[0]
        if not ors_key:
            d = (dist_km(dep_s[0]["lat"], dep_s[0]["lon"],
                         arr_s[0]["lat"], arr_s[0]["lon"]) or 100) * 1.25
            st.session_state["voy_route"] = {
                "distance_km": d, "duration_min": d / 100 * 60, "coords": []}
            st.warning("ORS_API_KEY manquante → distance estimée à vol d'oiseau ×1.25")
        else:
            with st.spinner("Calcul de l'itinéraire…"):
                st.session_state["voy_route"] = get_ors_route(
                    dep_s[0]["lat"], dep_s[0]["lon"],
                    arr_s[0]["lat"], arr_s[0]["lon"], ors_key)

    dep   = st.session_state.get("voy_dep_data")
    arr   = st.session_state.get("voy_arr_data")
    route = st.session_state.get("voy_route")

    if not dep or not arr or not route:
        st.info("Renseignez départ et destination pour planifier vos arrêts."); return

    dist_totale = route.get("distance_km", 0)
    duree_min   = route.get("duration_min", 0)
    coords      = route.get("coords", [])
    pc          = f"{carb_col}_prix"

    st.markdown(
        f'<div class="calc-box">'
        f'🛣️ <b>{dist_totale:.0f} km</b> · ⏱️ {duree_min/60:.1f}h · '
        f'🔋 Autonomie utile : <b>{auto_utile:.0f} km</b></div>',
        unsafe_allow_html=True)

    if dist_totale <= auto_utile:
        st.success(f"✅ Trajet faisable sans arrêt "
                   f"({auto_utile:.0f} km autonomie ≥ {dist_totale:.0f} km).")
    else:
        n_arrets = max(1, math.ceil((dist_totale - auto_utile) / auto_plein))
        cout_total = 0.0
        px_ref     = st.session_state.get("prix_min_cache", 1.9)
        litres_voy = round((dist_totale / 100) * conso, 1)

        st.markdown(
            f'<div class="calc-box">'
            f'📊 <b>{n_arrets} arrêt(s)</b> recommandé(s) · '
            f'~{litres_voy:.0f} L consommés · '
            f'~{litres_voy * px_ref:.2f}€ estimés</div>',
            unsafe_allow_html=True)

        # Points d'arrêt théoriques
        arrets = []
        km_cur = auto_utile
        while km_cur < dist_totale - 30:
            ratio = km_cur / dist_totale
            if coords:
                idx = min(int(ratio * len(coords)), len(coords) - 1)
                c   = coords[idx]
                arrets.append({"lat": c[1], "lon": c[0], "km": km_cur})
            else:
                arrets.append({
                    "lat": dep["lat"] + (arr["lat"] - dep["lat"]) * ratio,
                    "lon": dep["lon"] + (arr["lon"] - dep["lon"]) * ratio,
                    "km": km_cur})
            km_cur += auto_plein

        st.markdown(f"---\n#### ⛽ Arrêts — {carb_name}")

        for i, arret in enumerate(arrets):
            st.markdown(f"**Arrêt {i+1}** — km {arret['km']:.0f}")
            with st.spinner(f"Recherche arrêt {i+1}…"):
                df_a, _ = load_stations(sb, carb_col, arret["lat"], arret["lon"], 20)

            if df_a.empty:
                st.warning(f"Aucune station pour l'arrêt {i+1}."); continue

            if "lat" not in df_a.columns:
                df_a[["lat","lon"]] = df_a["geom"].apply(
                    lambda g: pd.Series(geom_to_latlon(g)))
            df_a["lat"] = pd.to_numeric(df_a["lat"], errors="coerce")
            df_a["lon"] = pd.to_numeric(df_a["lon"], errors="coerce")
            df_a = df_a[(df_a["lat"].notna()) & (df_a[pc].notna())]
            if df_a.empty: continue

            df_a["distance_km"] = df_a.apply(
                lambda r: dist_km(arret["lat"], arret["lon"],
                                  float(r["lat"]), float(r["lon"])) or 999, axis=1)
            df_a = df_a.sort_values(pc).head(3)
            moy_a = df_a[pc].astype(float).mean()

            for j, (_, r) in enumerate(df_a.iterrows()):
                render_card(dict(r), carb_col,
                            arret["lat"], arret["lon"], moy_a, i * 100 + j)

            best_px  = float(df_a.iloc[0][pc])
            litres_a = round(tank * (1 - reserve_pct / 100), 1)
            cout_a   = round(litres_a * best_px, 2)
            cout_total += cout_a
            st.caption(f"Plein recommandé : {litres_a:.0f} L · {cout_a:.2f}€")
            st.markdown("---")

        if cout_total > 0:
            st.markdown(
                f'<div class="calc-box" style="border:1px solid var(--green);margin-top:8px">'
                f'💰 <b>Coût total estimé : {cout_total:.2f}€</b> '
                f'({n_arrets} arrêt(s) · {carb_name} · {conso} L/100)</div>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN v15 — onglets : Stations | En chemin | Voyage | Favoris | Réglages
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    sb = get_supabase()

    screen_w  = streamlit_js_eval(js_expressions="window.innerWidth", key="vp")
    dark_mode = streamlit_js_eval(
        js_expressions="window.matchMedia('(prefers-color-scheme: dark)').matches",
        key="dark_mode")
    is_mobile = isinstance(screen_w, (int, float)) and screen_w < 768
    use_dark  = dark_mode is not False

    user_lat, user_lon = None, None
    if "gps_result" in st.session_state:
        user_lat, user_lon = st.session_state.gps_result
    elif "addr_selected" in st.session_state:
        info = st.session_state.addr_selected
        user_lat, user_lon = info["lat"], info["lon"]

    # ══════════════════════════════════════════════════════════════════════
    # MOBILE
    # ══════════════════════════════════════════════════════════════════════
    if is_mobile:
        active_tab = st.session_state.get("active_tab", "stations")

        h1, h2 = st.columns([1, 3])
        with h1:
            st.markdown(
                '<div style="display:flex;align-items:center;gap:6px;padding:4px 0">'
                '<span style="font-size:1.4rem">⛽</span>'
                '<span style="font-size:.95rem;font-weight:800">EcoPlein</span></div>',
                unsafe_allow_html=True)
        with h2:
            if active_tab in ("stations", "map", "favs", "chemin", "voyage"):
                carb_name = st.selectbox("Carburant", list(CARBURANTS.keys()),
                                         label_visibility="collapsed", key="carb_m")
                carb_col  = CARBURANTS[carb_name]
            else:
                carb_name = st.session_state.get("carb_m", "Gazole")
                carb_col  = CARBURANTS.get(carb_name, "gazole")

        # Onglet RÉGLAGES
        if active_tab == "settings":
            st.markdown("### ⚙️ Réglages")
            st.markdown('<div class="sec-label">📍 Ma position</div>', unsafe_allow_html=True)
            new_lat, new_lon, _ = location_block()
            if new_lat: user_lat, user_lon = new_lat, new_lon
            st.markdown('<div class="sec-label">📏 Rayon</div>', unsafe_allow_html=True)
            radius = st.select_slider("Rayon", options=[2,5,10,15,20,30,50],
                                      value=st.session_state.get("radius_m", 10),
                                      format_func=lambda x: f"{x} km",
                                      key="radius_m", label_visibility="collapsed")
            st.markdown('<div class="sec-label">🔽 Filtres</div>', unsafe_allow_html=True)
            fc1, fc2 = st.columns(2)
            with fc1:
                f_24h  = st.checkbox("🕐 24h/24",          key="m_24h")
                f_cb   = st.checkbox("💳 CB 24/24",         key="m_cb")
                f_open = st.checkbox("✅ Ouvert maintenant", key="m_open")
            with fc2:
                f_ev   = st.checkbox("⚡ Bornes élect.",    key="m_ev")
                f_wash = st.checkbox("🚿 Lavage auto.",     key="m_wash")
            brand_group = st.selectbox("Type", ["Toutes"] + list(BRAND_GROUPS.keys()),
                                       label_visibility="collapsed", key="m_brand")
            st.markdown('<div class="sec-label">↕️ Tri</div>', unsafe_allow_html=True)
            sort_by = st.radio("Tri", ["Distance","Prix ↑","Prix ↓","Récent"],
                               horizontal=True, label_visibility="collapsed", key="sort_m")
            st.markdown('<div class="sec-label">🚗 Mon véhicule</div>', unsafe_allow_html=True)
            render_vehicle_settings("mob_set_vs_")
            st.caption("v15 · data.gouv.fr · ORS")
            n_act = sum([bool(st.session_state.get(k)) for k in ("m_24h","m_cb","m_ev","m_wash","m_open")])
            render_bottom_nav("settings", n_act)
            return

        # Onglet EN CHEMIN
        if active_tab == "chemin":
            tab_en_chemin(sb, carb_col, carb_name, use_dark)
            render_bottom_nav("chemin")
            return

        # Onglet VOYAGE
        if active_tab == "voyage":
            tab_voyage(sb, carb_col, carb_name, use_dark)
            render_bottom_nav("voyage")
            return

        # Onboarding
        if not user_lat:
            render_onboarding()
            st.markdown('<div class="sec-label">📍 Activer ma position</div>', unsafe_allow_html=True)
            new_lat, new_lon, _ = location_block()
            if new_lat:
                user_lat, user_lon = new_lat, new_lon
                st.session_state["active_tab"] = "stations"
                st.rerun()
            render_bottom_nav(active_tab)
            return

        radius      = st.session_state.get("radius_m", 10) or 10
        sort_by     = st.session_state.get("sort_m",   "Distance") or "Distance"
        f_24h       = bool(st.session_state.get("m_24h",  False))
        f_cb        = bool(st.session_state.get("m_cb",   False))
        f_ev        = bool(st.session_state.get("m_ev",   False))
        f_wash      = bool(st.session_state.get("m_wash", False))
        f_open      = bool(st.session_state.get("m_open", False))
        brand_group = st.session_state.get("m_brand", "Toutes") or "Toutes"
        n_act       = sum([f_24h, f_cb, f_ev, f_wash, f_open])

        show_results(sb, carb_col, carb_name, user_lat, user_lon,
                     radius, sort_by,
                     (f_24h, f_cb, f_ev, f_wash, f_open, brand_group,
                      bool(st.session_state.get("d_resto", False)),
                      bool(st.session_state.get("d_wifi",  False)),
                      bool(st.session_state.get("d_dab",   False))),
                     is_mobile=True, dark_mode=use_dark)
        render_bottom_nav(active_tab, n_act)

    # ══════════════════════════════════════════════════════════════════════
    # DESKTOP — barre horizontale + onglets natifs Streamlit
    # ══════════════════════════════════════════════════════════════════════
    else:
        # ── Ligne 1 : Logo | Chips carburant | Nav onglets ───────────────
        nav1, nav2, nav3, nav4, nav5 = st.columns([1.2, 3.5, 1, 1, 1])
        with nav1:
            st.markdown(
                '<div style="display:flex;align-items:center;gap:8px;padding:6px 0">'
                '<span style="font-size:1.5rem">⛽</span>'
                '<span style="font-size:1.05rem;font-weight:900;color:#f1f5f9">Eco'
                '<span style="color:#f97316">Plein</span></span></div>',
                unsafe_allow_html=True)
        with nav2:
            # Carburant en selectbox minimaliste
            carb_keys = list(CARBURANTS.keys())
            cur_carb  = st.session_state.get("carb_d", "Gazole")
            carb_name = st.selectbox("Carburant", carb_keys,
                                     index=carb_keys.index(cur_carb),
                                     label_visibility="collapsed", key="carb_d")
            carb_col  = CARBURANTS[carb_name]
        with nav3:
            if st.button("⛽ Stations", use_container_width=True,
                         type="primary" if st.session_state.get("active_tab_d","stations")=="stations" else "secondary",
                         key="nav_st"):
                st.session_state["active_tab_d"] = "stations"; st.rerun()
        with nav4:
            if st.button("🗺️ En chemin", use_container_width=True,
                         type="primary" if st.session_state.get("active_tab_d","stations")=="chemin" else "secondary",
                         key="nav_ch"):
                st.session_state["active_tab_d"] = "chemin"; st.rerun()
        with nav5:
            if st.button("🛣️ Voyage", use_container_width=True,
                         type="primary" if st.session_state.get("active_tab_d","stations")=="voyage" else "secondary",
                         key="nav_voy"):
                st.session_state["active_tab_d"] = "voyage"; st.rerun()

        active_tab_d = st.session_state.get("active_tab_d", "stations")

        # ── Valeurs filtres depuis session state ─────────────────────────
        radius      = st.session_state.get("rad_d", 10) or 10
        sort_by     = st.session_state.get("sort_d", "Distance") or "Distance"
        f_24h       = bool(st.session_state.get("d_24h",  False))
        f_cb        = bool(st.session_state.get("d_cb",   False))
        f_ev        = bool(st.session_state.get("d_ev",   False))
        f_wash      = bool(st.session_state.get("d_wash", False))
        f_open      = bool(st.session_state.get("d_open", False))
        f_resto     = bool(st.session_state.get("d_resto", False))
        f_wifi      = bool(st.session_state.get("d_wifi",  False))
        f_dab       = bool(st.session_state.get("d_dab",   False))
        brand_group = st.session_state.get("d_brand", "Toutes") or "Toutes"

        # ── Panneau ⚙️ Mon véhicule · Filtres (global toutes pages) ──────
        with st.expander("⚙️ Mon véhicule · Filtres services", expanded=False):
            v1, v2, v3 = st.columns(3)
            with v1:
                st.markdown('<div class="sec-label">🛢️ Réservoir</div>', unsafe_allow_html=True)
                tank = st.select_slider("Capacité totale", options=list(range(20, 115, 5)),
                                        value=st.session_state.get("tank_cap", 50),
                                        format_func=lambda x: f"{x} L", key="veh_tank")
                st.session_state["tank_cap"] = tank
                fill_pct = st.select_slider("Niveau actuel", options=list(range(0, 105, 5)),
                                            value=st.session_state.get("fill_pct", 20),
                                            format_func=lambda x: f"{x} %", key="veh_fill")
                st.session_state["fill_pct"] = fill_pct
            with v2:
                st.markdown('<div class="sec-label">⚡ Consommation</div>', unsafe_allow_html=True)
                preset = st.selectbox("Profil véhicule", list(CONSO_PRESETS.keys()),
                                      key="veh_preset", label_visibility="collapsed")
                if CONSO_PRESETS[preset] is None:
                    conso_val = st.number_input("L/100 km", 2.0, 20.0, 6.5, 0.5,
                                                key="veh_conso_custom", label_visibility="collapsed")
                else:
                    conso_val = CONSO_PRESETS[preset]
                st.session_state["conso_veh"] = conso_val
                litres_restants = round(tank * (1 - fill_pct / 100), 1)
                autonomie = round(litres_restants / conso_val * 100, 0) if conso_val else 0
                st.markdown(
                    f'<div class="calc-mini" style="margin-top:8px">'
                    f'🔋 <b>{litres_restants} L</b> restants · '
                    f'🛣️ <b>~{autonomie:.0f} km</b> d\'autonomie</div>',
                    unsafe_allow_html=True)
            with v3:
                st.markdown('<div class="sec-label">🔧 Services requis</div>', unsafe_allow_html=True)
                f_24h  = st.checkbox("🕐 Automate 24h/24",    key="d_24h",   value=f_24h)
                f_cb   = st.checkbox("💳 CB 24h/24",           key="d_cb",    value=f_cb)
                f_ev   = st.checkbox("⚡ Bornes électriques",  key="d_ev",    value=f_ev)
                f_wash = st.checkbox("🚿 Lavage automatique",  key="d_wash",  value=f_wash)
                f_open = st.checkbox("✅ Ouvert maintenant",   key="d_open",  value=f_open)
                f_resto= st.checkbox("🍔 Restauration",        key="d_resto", value=f_resto)
                f_wifi = st.checkbox("📶 Wifi",                key="d_wifi",  value=f_wifi)
                f_dab  = st.checkbox("💰 DAB / Distributeur", key="d_dab",   value=f_dab)
                brand_group = st.selectbox("Marque", ["Toutes"] + list(BRAND_GROUPS.keys()),
                                           label_visibility="collapsed", key="d_brand")

        if active_tab_d == "stations":
            # ── Barre position + rayon + tri (propre à Stations) ─────────
            tb1, tb2, tb3 = st.columns([3, 1.5, 1.5])
            with tb1:
                st.markdown('<div class="sec-label">📍 Ma position</div>', unsafe_allow_html=True)
                if user_lat:
                    if "addr_selected" in st.session_state and st.session_state.addr_selected.get("label"):
                        pos_label = st.session_state.addr_selected["label"]
                    elif "gps_label" in st.session_state:
                        pos_label = st.session_state["gps_label"]
                    else:
                        pos_label = f"{user_lat:.4f}, {user_lon:.4f}"
                    pos_ok = f'<div class="gps-ok" style="padding:4px 8px;font-size:.78rem">✅ {pos_label}</div>'
                    st.markdown(pos_ok, unsafe_allow_html=True)
                    if st.button("🔄 Changer la position", key="pos_reset_d"):
                        st.session_state.pop("gps_result", None)
                        st.session_state.pop("addr_selected", None)
                        st.rerun()
                else:
                    c_gps, c_addr = st.columns([1, 2])
                    with c_gps:
                        if st.button("📡 Me localiser", key="gps_btn_d",
                                     use_container_width=True, type="primary"):
                            st.session_state.gps_asked    = True
                            st.session_state.gps_attempts = 0
                    with c_addr:
                        query = st.text_input("Adresse", placeholder="Adresse…",
                                              label_visibility="collapsed", key="addr_d_bar")
                        if query and len(query) >= 3:
                            sugs = search_addresses(query)
                            if sugs:
                                st.session_state.addr_selected = sugs[0]
                                user_lat = sugs[0]["lat"]
                                user_lon = sugs[0]["lon"]
                                st.rerun()
            with tb2:
                st.markdown('<div class="sec-label">📏 Rayon</div>', unsafe_allow_html=True)
                radius = st.slider("Rayon", 2, 50, 10, format="%d km",
                                   label_visibility="collapsed", key="rad_d")
            with tb3:
                st.markdown('<div class="sec-label">↕️ Tri</div>', unsafe_allow_html=True)
                sort_by = st.selectbox("Tri", ["Distance","Prix ↑","Prix ↓","Récent"],
                                       label_visibility="collapsed", key="sort_d")
        else:
            carb_name = st.session_state.get("carb_d", "Gazole")
            carb_col  = CARBURANTS.get(carb_name, "gazole")

        # GPS desktop
        if not user_lat and st.session_state.get("gps_asked"):
            attempts = st.session_state.get("gps_attempts", 0)
            with st.spinner(f"Localisation… ({attempts+1}/5)"):
                try:   loc = get_geolocation()
                except: loc = None
            if loc and isinstance(loc, dict) and loc.get("coords"):
                c = loc["coords"]
                user_lat = float(c["latitude"])
                user_lon = float(c["longitude"])
                st.session_state["gps_result"]   = (user_lat, user_lon)
                st.session_state["gps_asked"]    = False
                st.session_state["gps_attempts"] = 0
                try:
                    rv = requests.get(
                        "https://nominatim.openstreetmap.org/reverse",
                        params={"lat": user_lat, "lon": user_lon,
                                "format": "json", "addressdetails": 1},
                        headers={"User-Agent": "EcoPlein/1.0"},
                        timeout=4).json()
                    parts = rv.get("address", {})
                    city  = (parts.get("city") or parts.get("town")
                             or parts.get("village") or parts.get("municipality", ""))
                    road  = parts.get("road", "")
                    st.session_state["gps_label"] = f"{road}, {city}".strip(", ") or rv.get("display_name", "")[:60]
                except Exception:
                    st.session_state["gps_label"] = f"{user_lat:.4f}, {user_lon:.4f}"
                st.rerun()
            else:
                st.session_state["gps_attempts"] = attempts + 1
                if attempts >= 4:
                    st.session_state["gps_asked"] = False
                    st.warning("GPS indisponible. Entrez une adresse ci-dessous.")
                else:
                    _time.sleep(1)
                    st.rerun()

        # ── Contenu selon onglet actif ───────────────────────────────────
        if active_tab_d == "stations":
            if not user_lat or not user_lon:
                st.markdown("""
<div style="text-align:center;padding:3rem 1rem;opacity:.7">
  <div style="font-size:3rem;margin-bottom:1rem">⬆️</div>
  <div style="font-size:1.1rem;font-weight:700;color:#f1f5f9">
    Activez le GPS ou entrez une adresse</div>
  <div style="font-size:.9rem;color:#94a3b8">Utilisez les contrôles en haut.</div>
</div>""", unsafe_allow_html=True)
                st.pydeck_chart(pdk.Deck(
                    map_style=CARTO_DARK if use_dark else CARTO_LIGHT,
                    initial_view_state=pdk.ViewState(latitude=46.6, longitude=2.3, zoom=5)))
            else:
                show_results(
                    sb, carb_col, carb_name, user_lat, user_lon,
                    radius, sort_by,
                    (f_24h, f_cb, f_ev, f_wash, f_open, brand_group,
                     f_resto, f_wifi, f_dab),
                    is_mobile=False,
                    tank_cap=st.session_state.get("tank_cap", 50),
                    dark_mode=use_dark,
                )
        elif active_tab_d == "chemin":
            tab_en_chemin(sb, carb_col, carb_name, use_dark)
        elif active_tab_d == "voyage":
            tab_voyage(sb, carb_col, carb_name, use_dark)

if __name__ == "__main__":
    main()
