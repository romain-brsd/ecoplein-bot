# ═══════════════════════════════════════════════════════════════════════════════
# EcoPlein v30.1 — Refonte UX Premium "Deep Fuel"
# ─────────────────────────────────────────────────────────────────────────────
# HÉRITAGE v27 (toutes les features conservées) :
#   ①–⑫ + [A] Trajet intelligent + [B] Layout desktop + [C] Nav mobile
#
# NOUVEAUTÉS v30 :
#   [DS] Design System "Deep Fuel" — dark premium, JetBrains Mono pour les prix
#   [SH] Savings Hero — l'économie visible en 1 seconde dès l'ouverture
#   [SC] Station Card v30 — left border coloré, glass effect, prix monospace
#   [BD] Best Deal Hero — gradient border animé, affordance immédiate
#   [BN] Bottom Nav — floating pill frosted-glass (mobile)
#   [OB] Onboarding Premium — teal accent, promesse claire
#   Backend : 100% conservé (Supabase + ORS + cache adaptatif)
# ─────────────────────────────────────────────────────────────────────────────
# HÉRITAGE v26 (toutes les features conservées) :
#   ①–⑫ voir v24/v26 pour le détail des 12 améliorations
#
# NOUVEAUTÉS v27 :
#   [A] Onglet "Trajet" unique intelligent (remplace "En chemin" + "Voyage")
#       - Saisie départ + destination unique
#       - Intent cards : "Voir stations sur ma route" / "Planifier mes arrêts"
#       - Détection automatique trajet long (> 250 km) → suggestion planification
#       - "Trajet long détecté — optimiser les arrêts ?" CTA contextuel
#       - Suppression du switch persistant Rapide/Planifier (dette cognitive)
#       - Waypoints intermédiaires conservés (jusqu'à 3 étapes)
#
#   [B] Layout desktop refactorisé (refactor_notes.md)
#       - Résumé décisionnel compact (texte) à la place du bar chart
#       - Map sticky côté gauche conservée
#       - Contrôles véhicule NON dupliqués dans la zone résultats
#       - Bloc verdict : "Vaut-il le détour ?" condensé sous la best-deal
#
#   [C] Navigation mobile : 4 onglets (Stations, Carte, Trajet, Réglages)
#       au lieu de 5 — suppression de l'onglet "Voyage" séparé
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

# EcoPlein v30.1.0 — Refonte UX Premium "Deep Fuel" (dark design system + savings hero)
# Tables Supabase : stations_carburant / profils_vehicule / favoris / prix_historique
import streamlit as st
import uuid as _uuid
import pandas as pd
import requests
from supabase import create_client
from streamlit_js_eval import streamlit_js_eval, get_geolocation
from geopy.distance import geodesic
import pydeck as pdk
from datetime import datetime, timezone, timedelta, time as dtime
from typing import Optional
import json, re, math, time as _time
import io

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EcoPlein v30.1",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown("""
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#07080f">
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES CLÉS SESSION_STATE
# ═══════════════════════════════════════════════════════════════════════════════

KEY_TANK_CAP         = "tank_cap"
KEY_FILL_PCT         = "fill_pct"
KEY_MODE_COUT        = "mode_cout"
KEY_CONSO_PRESET     = "conso_preset"
KEY_CONSO_CUSTOM     = "conso_custom"
KEY_PRIX_MIN         = "prix_min_cache"
KEY_PRIX_MAX         = "prix_max_cache"
KEY_PRIX_MOY         = "prix_moy_cache"
KEY_BEST_STATION     = "best_station_id"
KEY_FAVORITES        = "favorites"
KEY_FAV_PRIX_SNAP    = "fav_prix_snapshot"   # ⑫ snapshot prix au moment du favori
KEY_ALERTS           = "prix_alerts"          # ⑫ {station_id: {carb_col: seuil}}
KEY_ACTIVE_TAB       = "active_tab"
KEY_ACTIVE_TAB_D     = "active_tab_d"
KEY_GPS_RESULT       = "gps_result"
KEY_GPS_LABEL        = "gps_label"
KEY_GPS_ASKED        = "gps_asked"
KEY_GPS_ATTEMPTS     = "gps_attempts"
KEY_ADDR_SELECTED    = "addr_selected"
KEY_VOY_RES          = "voy_res"
KEY_IS_FLEX          = "is_flex_fuel"         # ⑨ véhicule flex-fuel
KEY_CONSO_E85_FACTOR = "conso_e85_factor"     # ⑨ majoration conso E85 (défaut 1.25)
KEY_SHOW_ALERTS      = "show_alerts_panel"    # ⑫ panneau alertes ouvert
KEY_SESSION_ID       = "ecoplein_session_id"   # UUID anonyme persistant
# [A] Trajet intelligent v27.8 — aller/retour, autoroute/nationale
KEY_TRAJET_MODE      = "trajet_mode"          # "chemin" | "planifier" | None (avant choix)
KEY_TRAJET_DIST      = "trajet_dist_cache"    # distance calculée du trajet en km
KEY_TRAJET_AR        = "trajet_aller_retour"  # bool aller/retour
KEY_TRAJET_EVITE     = "trajet_evite_auto"    # bool éviter autoroutes/péages
KEY_ROUTE_ALT        = "rt_route_alt"         # itinéraire alternatif (nationale)

_SS_DEFAULTS: dict = {
    KEY_TANK_CAP:         50,
    KEY_FILL_PCT:         20,
    KEY_MODE_COUT:        "simple",
    KEY_CONSO_PRESET:     "🚗 Standard (6.5 L/100)",
    KEY_CONSO_CUSTOM:     6.5,
    KEY_FAVORITES:        set(),
    KEY_FAV_PRIX_SNAP:    {},
    KEY_ALERTS:           {},
    KEY_ACTIVE_TAB:       "stations",
    KEY_ACTIVE_TAB_D:     "stations",
    KEY_GPS_ASKED:        False,
    KEY_GPS_ATTEMPTS:     0,
    KEY_VOY_RES:          15,
    KEY_IS_FLEX:          False,
    KEY_CONSO_E85_FACTOR: 1.25,
    KEY_SHOW_ALERTS:      False,
    KEY_TRAJET_MODE:      None,
    KEY_TRAJET_DIST:      None,
    KEY_TRAJET_AR:        False,
    KEY_TRAJET_EVITE:     False,
}

def init_session_state() -> None:
    """Initialise toutes les clés session_state avec leurs valeurs par défaut."""
    for key, default in _SS_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES COLONNES SUPABASE
# ═══════════════════════════════════════════════════════════════════════════════

COL_SERVICES  = "services_service"
COL_HORAIRES  = "horaires_jour"
COL_AUTOMATE  = "horaires_automate_24_24"
COL_DISTANCE  = "distance_km"
COL_LAT       = "lat"
COL_LON       = "lon"
COL_GEOM      = "geom"
COL_ID        = "id"
COL_ADRESSE   = "adresse"
COL_VILLE     = "ville"
COL_CP        = "cp"
COL_ENSEIGNE  = "enseigne"


# ═══════════════════════════════════════════════════════════════════════════════
# CSS — DESIGN SYSTEM v24
# Nouveaux styles : .trend-*, .co2-badge, .alert-badge, .flex-box,
#                   .hist-box, .alert-panel, .share-btn, .fav-diff
# ═══════════════════════════════════════════════════════════════════════════════

CSS = """
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   EcoPlein v30.1 — Design System "Deep Fuel" (Dark Premium)
   ─────────────────────────────────────────────────────────────────────────
   Palette   : Espace sombre + teal accent + monospace pour les prix
   Typography: Plus Jakarta Sans (UI) + JetBrains Mono (prix & chiffres)
   Concept   : L'économie visible en 1 seconde
   ═══════════════════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900&family=JetBrains+Mono:wght@400;600;700;800&display=swap');

:root {
  /* ── Base surfaces ─────────────────────────────────────────────────── */
  --bg:         #07080f;
  --surface:    #0e1118;
  --surface-2:  #141927;
  --surface-3:  #1c2237;
  --glass:      rgba(14,17,24,0.85);
  --border:     rgba(255,255,255,0.07);
  --border-2:   rgba(255,255,255,0.13);

  /* ── Text ──────────────────────────────────────────────────────────── */
  --text:       #e2e8f0;
  --text-2:     #64748b;
  --text-3:     #94a3b8;

  /* ── Accent : Teal → savings green ────────────────────────────────── */
  --accent:     #2dd4bf;
  --accent-dim: rgba(45,212,191,0.15);
  --accent-glow:rgba(45,212,191,0.30);

  /* ── Semantic ──────────────────────────────────────────────────────── */
  --green:      #22c55e;
  --green-dim:  rgba(34,197,94,0.14);
  --amber:      #f59e0b;
  --amber-dim:  rgba(245,158,11,0.13);
  --red:        #f43f5e;
  --red-dim:    rgba(244,63,94,0.13);
  --blue:       #60a5fa;
  --blue-dim:   rgba(96,165,250,0.13);
  --purple:     #a78bfa;
  --fuel:       #fb923c;
  --fuel-dim:   rgba(251,146,60,0.15);
}

/* ── RESET & BASE ───────────────────────────────────────────────────────── */
html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
}
.stApp { background-color: var(--bg) !important; }

/* Override Streamlit white surfaces */
section[data-testid="stSidebar"],
div[data-testid="stVerticalBlock"],
div.stExpander { background: transparent !important; }

div[data-testid="stExpander"] > div:first-child {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}

/* Streamlit buttons — dark override */
.stButton > button {
  border-radius: 12px !important;
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  transition: all 0.18s ease !important;
  border: 1px solid var(--border-2) !important;
  background: var(--surface-2) !important;
  color: var(--text) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #2dd4bf, #0d9488) !important;
  color: #022c22 !important;
  border: none !important;
  box-shadow: 0 4px 16px var(--accent-glow) !important;
}
.stButton > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.3) !important;
}
/* Selectbox, inputs */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
  background: var(--surface-2) !important;
  border: 1px solid var(--border-2) !important;
  color: var(--text) !important;
  border-radius: 12px !important;
}

/* ── SAVINGS HERO ───────────────────────────────────────────────────────── */
/* Le premier truc visible : combien tu économises maintenant              */
.savings-hero {
  position: relative;
  background: linear-gradient(135deg, #061910 0%, #0a2e1a 50%, #061910 100%);
  border: 1px solid rgba(34,197,94,0.30);
  border-radius: 20px;
  padding: 16px 20px;
  margin: 0 0 14px;
  overflow: hidden;
}
.savings-hero::before {
  content: '';
  position: absolute;
  top: -50%; left: -20%;
  width: 50%; height: 200%;
  background: radial-gradient(ellipse, rgba(34,197,94,0.10) 0%, transparent 70%);
  pointer-events: none;
}
.sh-label   { font-size: .68rem; font-weight: 700; letter-spacing: .12em;
              text-transform: uppercase; color: var(--green); margin-bottom: 2px; }
.sh-amount  { font-family: 'JetBrains Mono', monospace; font-size: 2.6rem;
              font-weight: 800; color: #22c55e; line-height: 1; }
.sh-sub     { font-size: .78rem; color: var(--text-3); margin-top: 4px; }
.sh-sub b   { color: var(--text); }
.sh-stats   { display: flex; gap: 16px; margin-top: 10px; flex-wrap: wrap; }
.sh-stat    { text-align: center; }
.sh-stat-v  { font-family: 'JetBrains Mono', monospace; font-size: .95rem;
              font-weight: 700; line-height: 1.2; }
.sh-stat-l  { font-size: .62rem; color: var(--text-2); margin-top: 1px; }

/* ── STATION CARD ───────────────────────────────────────────────────────── */
.scard {
  display: grid;
  grid-template-columns: 76px 1fr 68px;
  gap: 0 12px;
  align-items: start;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 12px 13px;
  margin: 7px 0;
  color: var(--text);
  position: relative;
  overflow: hidden;
  transition: border-color 0.18s ease, transform 0.15s ease, box-shadow 0.18s ease;
}
.scard::before {
  content: '';
  position: absolute;
  left: 0; top: 12px; bottom: 12px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--border-2);
  transition: background 0.2s;
}
.scard.cheap::before { background: var(--green); }
.scard.avg::before   { background: var(--amber); }
.scard.exp::before   { background: var(--red); }

@media (hover: hover) {
  .scard:hover { border-color: var(--border-2); transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,0,0,0.25); }
  .scard.cheap:hover { border-color: rgba(34,197,94,0.25); box-shadow: 0 8px 24px rgba(34,197,94,0.08); }
  .scard.avg:hover   { border-color: rgba(245,158,11,0.25); box-shadow: 0 8px 24px rgba(245,158,11,0.08); }
  .scard.exp:hover   { border-color: rgba(244,63,94,0.25);  box-shadow: 0 8px 24px rgba(244,63,94,0.08); }
}
@media (hover: none) {
  .scard:active { opacity: 0.85; transform: scale(0.99); }
  .intent-card:active { opacity: 0.80; transform: scale(0.98); }
}

/* Price pill */
.sc-price { text-align:center; padding:9px 4px; border-radius:12px; border:1px solid var(--border); background: var(--surface-2); }
.sc-price.cheap { background: var(--green-dim); border-color: rgba(34,197,94,0.20); }
.sc-price.avg   { background: var(--amber-dim); border-color: rgba(245,158,11,0.20); }
.sc-price.exp   { background: var(--red-dim);   border-color: rgba(244,63,94,0.20); }

.sc-pval       { font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 800; line-height: 1; }
.sc-pval.cheap { color: var(--green) !important; }
.sc-pval.avg   { color: var(--amber) !important; }
.sc-pval.exp   { color: var(--red) !important; }
.sc-punit      { font-size: .62rem; color: var(--text-2) !important; margin-top: 2px; }
.sc-pfill      { font-family: 'JetBrains Mono', monospace; font-size: .78rem; color: var(--blue) !important; font-weight: 700; margin-top: 4px; }
.sc-plitre     { font-size: .60rem; color: var(--text-2) !important; }

/* Info column */
.sc-brand { color: var(--text) !important; font-weight: 700; font-size: .88rem; }
.sc-addr  { color: var(--text-2) !important; font-size: .72rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sc-meta  { color: var(--text-2) !important; font-size: .72rem; margin-top: 2px; }
.sc-svcs  { margin-top: 4px; display: flex; flex-wrap: wrap; gap: 3px; }
.sc-eco   { color: var(--green) !important; font-weight: 600; font-size: .72rem; margin-top: 3px; }
.sc-best  {
  display: inline-flex; align-items: center; gap: 4px;
  background: var(--accent-dim);
  border: 1px solid var(--accent-glow);
  color: var(--accent) !important;
  border-radius: 8px; padding: 1px 8px;
  font-size: .65rem; font-weight: 700; margin-bottom: 4px;
}

/* Freshness */
.sc-fr { font-size: .65rem; margin-top: 6px; text-align: center; font-weight: 700; line-height: 1.3; }

/* Nav column */
.sc-nav { display: flex; flex-direction: column; gap: 5px; }
.nav-a  {
  display: flex; justify-content: center; align-items: center;
  min-height: 28px; padding: 4px 5px; border-radius: 9px;
  text-decoration: none !important; font-size: .67rem; font-weight: 700;
  transition: opacity 0.15s;
}
.nav-a:hover { opacity: 0.82; }
.na-gmaps { background: #1a3a8f; color: #93c5fd !important; }
.na-waze  { background: #133348; color: #38bdf8 !important; }
.na-apple { background: #1c1c2a; color: var(--text-3) !important; }
.na-share { background: #2a1a4a; color: var(--purple) !important; }

/* ── BADGES ─────────────────────────────────────────────────────────────── */
.bg-g, .bg-b, .bg-w, .badge-open, .badge-closed, .eco-tag, .eco-tag-2 {
  border-radius: 8px; padding: 1px 7px; font-size: .67rem; font-weight: 700;
}
.bg-g, .badge-open  { background: var(--green-dim); color: var(--green) !important; }
.bg-b               { background: var(--blue-dim);  color: var(--blue) !important; }
.bg-w               { background: var(--surface-3); color: var(--text-3) !important; }
.badge-closed       { background: var(--red-dim);   color: var(--red) !important; }
.eco-tag            { background: var(--green-dim);  color: var(--green) !important; }
.eco-tag-2          { background: var(--amber-dim);  color: var(--amber) !important; }

/* Tendance */
.trend-up   { background: var(--red-dim);   color: var(--red) !important;   border-radius:7px; padding:1px 6px; font-size:.66rem; font-weight:700; }
.trend-down { background: var(--green-dim); color: var(--green) !important; border-radius:7px; padding:1px 6px; font-size:.66rem; font-weight:700; }
.trend-flat { background: var(--surface-3); color: var(--text-3) !important;border-radius:7px; padding:1px 6px; font-size:.66rem; font-weight:700; }

/* Favori diff */
.fav-diff-up   { color: var(--red) !important;   font-size: .68rem; font-weight: 700; }
.fav-diff-down { color: var(--green) !important; font-size: .68rem; font-weight: 700; }

/* CO₂ */
.co2-badge { background: var(--green-dim); border: 1px solid rgba(34,197,94,0.20); border-radius: 9px; padding: 3px 9px; font-size: .72rem; color: var(--green) !important; margin-top: 4px; display: inline-block; }

/* Flex-fuel */
.flex-box {
  background: linear-gradient(135deg, #1a0a3e, #2e1065);
  border: 1px solid rgba(167,139,250,.25);
  border-radius: 14px; padding: 12px 16px; margin: 8px 0;
  color: #f5f3ff;
}
.flex-winner { color: var(--purple) !important; font-size: 1.05rem; font-weight: 900; }
.flex-detail { color: rgba(245,243,255,.65) !important; font-size: .74rem; margin-top: 2px; }
.flex-eco    { color: #86efac !important; font-weight: 700; margin-top: 4px; font-size: .8rem; }

/* Alertes */
.alert-panel  { background: var(--amber-dim); border: 1px solid rgba(245,158,11,.25); border-radius: 14px; padding: 12px 16px; margin: 8px 0; }
.alert-row    { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid rgba(245,158,11,.15); font-size: .78rem; }
.alert-triggered { background: var(--green-dim); border: 1px solid rgba(34,197,94,.25); border-radius: 9px; padding: 7px 12px; margin: 4px 0; font-size: .8rem; color: var(--green) !important; }

/* ── BEST DEAL HERO ─────────────────────────────────────────────────────── */
.best-deal {
  position: relative;
  background: linear-gradient(135deg, #060f1a 0%, #0a1e2e 60%, #060f1a 100%);
  border-radius: 20px;
  padding: 16px 18px;
  margin-bottom: 12px;
  color: #f8fafc;
  overflow: hidden;
}
.best-deal::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 20px;
  padding: 1.5px;
  background: linear-gradient(135deg, rgba(45,212,191,0.6), rgba(96,165,250,0.3), rgba(45,212,191,0.1));
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
.best-deal::after {
  content: '';
  position: absolute;
  top: -30%; left: -10%;
  width: 40%; height: 160%;
  background: radial-gradient(ellipse, rgba(45,212,191,0.07) 0%, transparent 70%);
  pointer-events: none;
}

.bd-price  { font-family: 'JetBrains Mono', monospace; font-size: 2.4rem; font-weight: 800; color: var(--accent) !important; line-height: 1; }
.bd-name   { color: var(--text) !important; font-weight: 700; margin-top: 4px; }
.bd-sub    { color: var(--text-3) !important; font-size: .78rem; }
.bd-cout   { font-family: 'JetBrains Mono', monospace; color: var(--blue) !important; font-weight: 800; font-size: 1.1rem; }
.bd-litre  { color: var(--text-3) !important; font-size: .72rem; }
.bd-eco    { color: var(--green) !important; font-size: .8rem; margin-top: 3px; font-weight: 700; }
.bd-alert  { color: var(--red) !important; font-size: .73rem; margin-top: 2px; }
.bd-nav    { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }

/* ── KPI ────────────────────────────────────────────────────────────────── */
.kpi   { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 11px 12px; text-align: center; }
.kpi-v { font-family: 'JetBrains Mono', monospace; font-size: 1.15rem; font-weight: 800; line-height: 1; }
.kpi-l { font-size: .68rem; color: var(--text-2) !important; margin-top: 4px; letter-spacing: .04em; }

/* ── BOXES ──────────────────────────────────────────────────────────────── */
.calc-box  { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 11px 14px; margin: 8px 0; color: var(--text); font-size: .82rem; }
.calc-mini { background: var(--surface-2); border-radius: 9px; padding: 7px 9px; font-size: .75rem; text-align: center; color: var(--text) !important; }
.stop-now  { background: var(--red-dim);   border: 1px solid rgba(244,63,94,.25);  border-radius: 12px; padding: 11px 14px; margin: 8px 0; color: var(--red) !important; }
.stop-wait { background: var(--amber-dim); border: 1px solid rgba(245,158,11,.25); border-radius: 12px; padding: 11px 14px; margin: 8px 0; color: var(--amber) !important; }
.hist-box  { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; margin: 6px 0; }

/* ── GPS STATUS ─────────────────────────────────────────────────────────── */
.gps-ok   { background: var(--green-dim); color: var(--green) !important; border-radius: 10px; padding: 8px 14px; font-size: .80rem; margin: 6px 0; border: 1px solid rgba(34,197,94,.2); }
.gps-err  { background: var(--amber-dim); color: var(--amber) !important; border-radius: 10px; padding: 8px 14px; font-size: .80rem; margin: 6px 0; }
.gps-fail { background: var(--red-dim);   color: var(--red) !important;   border-radius: 10px; padding: 8px 14px; font-size: .80rem; margin: 6px 0; }

/* ── TABLES ─────────────────────────────────────────────────────────────── */
.htbl           { width: 100%; border-collapse: collapse; font-size: .74rem; }
.htbl td        { padding: 3px 6px; border-bottom: 1px solid var(--border); color: var(--text) !important; }
.htbl-today     { background: var(--green-dim) !important; }
.htbl-today td  { color: var(--green) !important; font-weight: 700; }

/* ── MISC ───────────────────────────────────────────────────────────────── */
.sec-label    { font-size: .62rem; font-weight: 800; letter-spacing: .10em; text-transform: uppercase; color: var(--accent) !important; margin: 12px 0 5px; }
.map-legend   { font-size: .69rem; color: var(--text-2) !important; margin-top: 4px; }
.sticky-map   { position: sticky; top: 12px; align-self: start; }
.slider-scale { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 6px; min-height: 18px; white-space: nowrap; color: var(--text-2) !important; font-size: .76rem !important; line-height: 1.2 !important; }
.sbar         { font-size: .75rem; padding: 4px 0 3px; color: var(--text-2) !important; margin-bottom: 4px; }
.sdot         { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
.sdot-g       { background: var(--green); box-shadow: 0 0 6px var(--green); }

/* ── ONBOARDING ─────────────────────────────────────────────────────────── */
.onboard      { text-align: center; padding: 2.5rem 1rem; }
.onboard-icon { font-size: 3.5rem; margin-bottom: 1rem; filter: drop-shadow(0 0 20px rgba(45,212,191,0.4)); }
.onboard h2   { color: var(--text) !important; font-weight: 800; font-size: 1.3rem; }
.onboard p    { color: var(--text-2) !important; font-size: .88rem; }

/* ── PRICE SUMMARY / DECISION ───────────────────────────────────────────── */
.price-summary { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 14px 16px; margin-top: 10px; }
.ps-verdict    { font-size: .98rem; font-weight: 800; margin-bottom: 6px; }
.ps-metrics    { display: flex; flex-wrap: wrap; gap: 14px; font-size: .82rem; color: var(--text); margin-bottom: 8px; }
.ps-best       { font-size: .76rem; color: var(--text-2); padding-top: 8px; border-top: 1px solid var(--border); }
.waypoint-box  { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 10px 14px; margin: 6px 0; }

/* ── DECISION SUMMARY ───────────────────────────────────────────────────── */
.decision-summary {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px 18px;
  margin: 10px 0;
}
.ds-title   { font-weight: 800; font-size: .9rem; margin-bottom: 10px; color: var(--text) !important; }
.ds-row     { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border); }
.ds-row:last-of-type { border-bottom: none; }
.ds-label   { color: var(--text-2) !important; font-size: .8rem; }
.ds-val     { font-weight: 700; color: var(--text) !important; font-size: .8rem; text-align: right; }
.ds-verdict {
  margin-top: 10px; padding: 8px 12px;
  border-radius: 10px; font-weight: 700; font-size: .8rem;
}
.ds-verdict.ok   { background: var(--green-dim); color: var(--green) !important; }
.ds-verdict.warn { background: var(--amber-dim); color: var(--amber) !important; }
.ds-verdict.info { background: var(--blue-dim);  color: var(--blue) !important; }

/* ── TRAJET INTENT CARDS ────────────────────────────────────────────────── */
.intent-card {
  background: var(--surface);
  border: 2px solid var(--border);
  border-radius: 18px;
  padding: 18px 16px;
  cursor: pointer;
  transition: border-color .15s ease, box-shadow .15s ease, transform .12s ease;
  text-align: center;
}
.intent-card:hover { border-color: var(--accent); box-shadow: 0 6px 20px var(--accent-glow); transform: translateY(-2px); }
.intent-card.ic-primary   { border-color: rgba(45,212,191,0.4); background: rgba(45,212,191,0.04); }
.intent-card.ic-secondary { border-color: rgba(96,165,250,0.4); background: rgba(96,165,250,0.04); }
.ic-icon  { font-size: 1.9rem; margin-bottom: 8px; }
.ic-title { font-size: .93rem; font-weight: 800; color: var(--text) !important; margin-bottom: 4px; }
.ic-desc  { font-size: .74rem; color: var(--text-2) !important; line-height: 1.4; }

.trajet-long-banner {
  background: linear-gradient(135deg, #0d1f4e, #1e3a8a);
  border: 1px solid rgba(96,165,250,0.25);
  border-radius: 14px; padding: 12px 16px; margin: 10px 0;
  color: #eff6ff;
}
.tlb-title { font-weight: 800; font-size: .9rem; margin-bottom: 3px; }
.tlb-sub   { font-size: .74rem; opacity: .8; }

/* ── BOTTOM NAV (mobile) ────────────────────────────────────────────────── */
/* Floating glass pill — the centerpiece of mobile navigation             */
.bnav-wrap {
  position: fixed;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  display: flex;
  gap: 4px;
  background: rgba(14,17,24,0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 24px;
  padding: 6px 8px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04);
  min-width: min(92vw, 380px);
  justify-content: space-around;
}
.bnav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 7px 14px;
  border-radius: 18px;
  cursor: pointer;
  transition: background 0.18s, transform 0.15s;
  flex: 1;
  text-align: center;
  min-width: 60px;
  position: relative;
}
.bnav-item.active {
  background: var(--accent-dim);
  box-shadow: 0 0 16px var(--accent-glow);
}
.bnav-icon { font-size: 1.2rem; line-height: 1; }
.bnav-label {
  font-size: .58rem;
  font-weight: 700;
  letter-spacing: .03em;
  color: var(--text-2);
  text-transform: uppercase;
}
.bnav-item.active .bnav-label { color: var(--accent); }
.bnav-badge {
  position: absolute;
  top: 4px; right: 8px;
  background: var(--red);
  color: #fff;
  border-radius: 99px;
  font-size: .52rem;
  font-weight: 800;
  padding: 1px 5px;
  line-height: 1.4;
}
/* Spacer to avoid content hidden behind fixed nav */
.bnav-spacer { height: 80px; }

/* ── VEHICLE SETTINGS ───────────────────────────────────────────────────── */
.cmp-row      { display: flex; align-items: center; gap: 8px; padding: 5px 10px; border-radius: 9px; margin: 3px 0; background: var(--surface-2); font-size: .78rem; }
.cmp-bar-wrap { flex: 1; background: var(--surface-3); border-radius: 6px; height: 5px; }
.cmp-bar      { height: 5px; border-radius: 6px; }

/* ── ANIMATIONS ─────────────────────────────────────────────────────────── */
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.scard { animation: fadeSlideUp 0.18s ease both; }
.scard:nth-child(1) { animation-delay:0.00s; }
.scard:nth-child(2) { animation-delay:0.04s; }
.scard:nth-child(3) { animation-delay:0.08s; }
.scard:nth-child(4) { animation-delay:0.12s; }
.scard:nth-child(5) { animation-delay:0.16s; }
.scard:nth-child(6) { animation-delay:0.20s; }
.scard:nth-child(7) { animation-delay:0.24s; }
.scard:nth-child(8) { animation-delay:0.28s; }
@media (prefers-reduced-motion: reduce) {
  .scard, .savings-hero, .best-deal { animation: none !important; transition: none !important; }
}

@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 0 var(--accent-glow); }
  50%       { box-shadow: 0 0 0 6px transparent; }
}

/* ── MISC OVERRIDES ─────────────────────────────────────────────────────── */
.share-btn { background: var(--surface-2); border: 1px solid var(--border-2); border-radius: 10px; padding: 5px 10px; font-size: .72rem; color: var(--text-2) !important; cursor: pointer; }
</style>
"""
st.html(CSS)



# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES MÉTIER
# ═══════════════════════════════════════════════════════════════════════════════

CARBURANTS = {
    "Gazole": "gazole", "SP95": "sp95", "SP98": "sp98",
    "E10": "e10", "E85": "e85", "GPLc": "gplc",
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
    ("Total",         ["TOTAL"]),
]

BRAND_GROUPS = {
    "Grandes surfaces": ["E.Leclerc","Intermarché","Carrefour","Super U","Hyper U","Système U","Auchan","Casino","Géant","Lidl","Netto"],
    "Pétroliers":       ["TotalEnergies","Total","Esso","BP","Shell","Avia","Agip","Elf"],
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

SVC_PRIORITY = ["Automate CB 24/24","Bornes électriques","Lavage automatique","Boutique alimentaire","Wifi"]

CONSO_PRESETS: dict[str, Optional[float]] = {
    "🚗 Standard (6.5 L/100)":       6.5,
    "🏙️ Citadine (5.5 L/100)":      5.5,
    "🚗 Berline diesel (5.0 L/100)": 5.0,
    "🛻 SUV / 4×4 (9.0 L/100)":     9.0,
    "🚐 Utilitaire (8.5 L/100)":     8.5,
    "⚡ Hybride (4.0 L/100)":        4.0,
    "✏️ Personnalisé":                None,
}

JOURS       = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
CARTO_DARK  = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
CARTO_LIGHT = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
ORS_BASE    = "https://api.openrouteservice.org/v2"

# ⑦ CO₂ par litre — données ADEME 2023 (g CO₂eq / L)
CO2_PAR_LITRE: dict[str, float] = {
    "gazole": 2640.0,
    "sp95":   2360.0,
    "sp98":   2360.0,
    "e10":    2240.0,
    "e85":     940.0,  # bioéthanol : forte réduction
    "gplc":   1630.0,
}


# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# ─────────────────────────────────────────────────────────────────
# PERSISTANCE SESSION — profil véhicule + favoris (Sprint 2)
# ─────────────────────────────────────────────────────────────────

def get_session_id() -> str:
    """Retourne ou crée un UUID anonyme persistant dans st.query_params."""
    if KEY_SESSION_ID in st.session_state:
        return st.session_state[KEY_SESSION_ID]
    sid = st.query_params.get("sid", "")
    if not sid or len(sid) < 10:
        sid = str(_uuid.uuid4())
        st.query_params["sid"] = sid
    st.session_state[KEY_SESSION_ID] = sid
    return sid

def load_profil_vehicule(sb) -> bool:
    """Charge le profil véhicule depuis Supabase et l'injecte en session_state.
    Retourne True si un profil existant a été trouvé."""
    try:
        sid  = get_session_id()
        resp = sb.table("profils_vehicule").select("*").eq("session_id", sid).limit(1).execute()
        if not resp.data:
            return False
        row = resp.data[0]
        st.session_state.setdefault(KEY_TANK_CAP,         row.get("tank_cap",         50))
        st.session_state.setdefault(KEY_FILL_PCT,         row.get("fill_pct",         20))
        st.session_state.setdefault(KEY_CONSO_PRESET,     row.get("conso_preset",     "Standard 6.5 L/100"))
        st.session_state.setdefault(KEY_CONSO_CUSTOM,     row.get("conso_custom",     6.5))
        st.session_state.setdefault(KEY_IS_FLEX,          row.get("is_flex",          False))
        st.session_state.setdefault(KEY_CONSO_E85_FACTOR, row.get("conso_e85_factor", 1.25))
        st.session_state.setdefault(KEY_MODE_COUT,        row.get("mode_cout",        "simple"))
        return True
    except Exception:
        return False

def save_profil_vehicule(sb) -> None:
    """Upsert du profil véhicule courant vers Supabase."""
    try:
        sid = get_session_id()
        sb.table("profils_vehicule").upsert({
            "session_id":        sid,
            "tank_cap":          st.session_state.get(KEY_TANK_CAP,         50),
            "fill_pct":          st.session_state.get(KEY_FILL_PCT,         20),
            "conso_preset":      st.session_state.get(KEY_CONSO_PRESET,     "Standard 6.5 L/100"),
            "conso_custom":      st.session_state.get(KEY_CONSO_CUSTOM,     6.5),
            "is_flex":           st.session_state.get(KEY_IS_FLEX,          False),
            "conso_e85_factor":  st.session_state.get(KEY_CONSO_E85_FACTOR, 1.25),
            "mode_cout":         st.session_state.get(KEY_MODE_COUT,        "simple"),
            "updated_at":        "now()",
        }, on_conflict="session_id").execute()
    except Exception:
        pass

def load_favoris_supabase(sb) -> None:
    """Charge les favoris depuis Supabase → injecte dans KEY_FAVORITES + KEY_FAV_PRIX_SNAP."""
    try:
        sid  = get_session_id()
        resp = sb.table("favoris").select("station_id,carb_col,prix_snap").eq("session_id", sid).execute()
        if not resp.data:
            return
        fav_ids  = {r["station_id"] for r in resp.data}
        prix_snap = {r["station_id"]: r.get("prix_snap") for r in resp.data if r.get("prix_snap")}
        st.session_state[KEY_FAVORITES]     = fav_ids
        st.session_state[KEY_FAV_PRIX_SNAP] = prix_snap
    except Exception:
        pass

def toggle_fav_supabase(sb, sid_station: str, prix: float) -> None:
    """Ajoute ou retire un favori en Supabase + session_state."""
    session_id = get_session_id()
    favs       = st.session_state.get(KEY_FAVORITES, set())
    carb_col   = st.session_state.get("carbd") or st.session_state.get("carbm", "gazole")
    try:
        if sid_station in favs:
            sb.table("favoris").delete().eq("session_id", session_id)              .eq("station_id", sid_station).eq("carb_col", carb_col).execute()
            favs.discard(sid_station)
            st.session_state.get(KEY_FAV_PRIX_SNAP, {}).pop(sid_station, None)
        else:
            sb.table("favoris").upsert({
                "session_id": session_id,
                "station_id": sid_station,
                "carb_col":   carb_col,
                "prix_snap":  prix,
            }, on_conflict="session_id,station_id,carb_col").execute()
            favs.add(sid_station)
            snaps = st.session_state.get(KEY_FAV_PRIX_SNAP, {})
            snaps[sid_station] = prix
            st.session_state[KEY_FAV_PRIX_SNAP] = snaps
        st.session_state[KEY_FAVORITES] = favs
    except Exception:
        # Fallback silencieux → bascule session_state uniquement
        if sid_station in favs:
            favs.discard(sid_station)
        else:
            favs.add(sid_station)
        st.session_state[KEY_FAVORITES] = favs


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS PURS
# ═══════════════════════════════════════════════════════════════════════════════

def s(v) -> str:
    return str(v) if v is not None else ""

def sl(v) -> list:
    if isinstance(v, list): return v
    if isinstance(v, str):
        try:
            r = json.loads(v); return r if isinstance(r, list) else []
        except: return []
    return []

def geom_to_latlon(g) -> tuple[float, float]:
    if isinstance(g, dict): return float(g.get("lat",0)), float(g.get("lon",0))
    if isinstance(g, str):
        try:
            d = json.loads(g); return float(d.get("lat",0)), float(d.get("lon",0))
        except: pass
    return 0.0, 0.0


# ② detect_brand avec cache + version vectorisée
@st.cache_data(ttl=3600, show_spinner=False)
def _cached_brand(enseigne: str, adresse: str) -> Optional[str]:
    """Détecte la marque depuis enseigne+adresse — résultat mémoïzé 1h.
    Arguments scalaires pour la sérialisation du cache Streamlit.
    """
    txt = f"{enseigne.upper()} {adresse.upper()}"
    for name, patterns in BRANDS:
        if any(p in txt for p in patterns):
            return name
    return enseigne.title() or None

def detect_brand(row: dict) -> Optional[str]:
    """Détecte la marque d'une station (dict). Utilise le cache _cached_brand."""
    return _cached_brand(
        s(row.get(COL_ENSEIGNE, "")),
        s(row.get(COL_ADRESSE, "")))

def detect_brand_series(df: pd.DataFrame) -> pd.Series:
    """② Version vectorisée de detect_brand — opère sur tout le DataFrame.

    Évite la conversion dict(r) à chaque ligne (×4 plus rapide sur 100+ stations).
    L'ordre BRANDS est respecté : TotalEnergies capté avant Total.
    """
    ens = df[COL_ENSEIGNE].fillna("").str.upper()
    adr = df[COL_ADRESSE].fillna("").str.upper()
    txt = ens + " " + adr
    result = pd.Series("", index=df.index)
    for name, patterns in reversed(BRANDS):
        mask = pd.Series(False, index=df.index)
        for p in patterns:
            mask |= txt.str.contains(p, regex=False, na=False)
        result[mask] = name
    no_brand = result == ""
    result[no_brand] = df.loc[no_brand, COL_ENSEIGNE].fillna("").str.title()
    return result


def freshness(v) -> tuple[str, str]:
    """Texte + style inline CSS de fraîcheur (couleur inline = pas de conflit cascade)."""
    if v is None: return "—", "color:#dc2626;"
    try:
        if hasattr(v, "to_pydatetime"): dt = v.to_pydatetime()
        elif isinstance(v, datetime):   dt = v
        else:
            raw = str(v).strip()
            if not raw or raw.lower() in ("nan","nat","none"): return "—","color:#dc2626;"
            raw = raw.replace("Z","+00:00")
            if re.match(r".*[+-]\d{2}$", raw): raw += ":00"
            dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        now   = datetime.now(timezone.utc)
        hours = (now - dt).total_seconds() / 3600
        same_day = dt.astimezone(timezone.utc).date() == now.date()
        date_txt = dt.strftime("%d/%m") if dt >= (now - timedelta(days=365)) else dt.strftime("%d/%m/%Y")
        if same_day:   return "🟢 Auj.",       "color:#16a34a;"
        if hours < 24: return f"🟢 {date_txt}", "color:#16a34a;"
        if hours < 48: return f"🟡 {date_txt}", "color:#eab308;"
        if hours < 72: return f"🟠 {date_txt}", "color:#f97316;"
        return                 f"🔴 {date_txt}", "color:#dc2626;"
    except:
        raw = str(v).strip()
        if not raw or raw.lower() in ("nan","nat","none"): return "—","color:#dc2626;"
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
        if m:
            yyyy,mm,dd = m.groups()
            now = datetime.now(timezone.utc)
            date_txt = f"{dd}/{mm}" if yyyy == str(now.year) else f"{dd}/{mm}/{yyyy}"
            return f"🔴 {date_txt}", "color:#dc2626;"
        return f"🔴 {raw[:10]}", "color:#dc2626;"

def freshness_hours(v) -> Optional[float]:
    """Âge du prix en heures, None si non parsable."""
    try:
        if hasattr(v,"to_pydatetime"): dt = v.to_pydatetime()
        elif isinstance(v, datetime):  dt = v
        else:
            raw = str(v).strip().replace("Z","+00:00")
            dt  = datetime.fromisoformat(raw)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except: return None

def dist_km(a: float, b: float, c: float, d: float) -> Optional[float]:
    try: return round(geodesic((a,b),(c,d)).km, 1)
    except: return None

def is_open_now(row: dict) -> Optional[bool]:
    """True si ouverte, False si fermée, None si inconnu."""
    hj = s(row.get(COL_HORAIRES))
    if not hj: return None
    if "Automate-24-24" in hj or row.get(COL_AUTOMATE) == "Oui": return True
    today = datetime.now().weekday()
    jour  = JOURS[today]
    m = re.search(rf"{jour}(\d{{2}})\.(\d{{2}})-(\d{{2}})\.(\d{{2}})", hj)
    if not m: return False
    now_t   = datetime.now().time()
    open_t  = dtime(int(m.group(1)), int(m.group(2)))
    close_t = dtime(int(m.group(3)), int(m.group(4)))
    return open_t <= now_t <= close_t

def _open_str(row: dict) -> str:
    """③ Chaîne statut ouverture — helper pour éviter le double appel is_open_now."""
    status = is_open_now(row)
    return "✅ Ouvert" if status is True else ("❌ Fermé" if status is False else "")

def hours_html(raw) -> str:
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
    badge = '<span class="bg-g">🕐 Automate 24h/24</span><br>' if is24 else ""
    return f"{badge}<table class='htbl'>{rows}</table>"

def open_badge(row: dict) -> str:
    status = is_open_now(row)
    if status is True:  return '<span class="badge-open">✅ Ouvert</span>'
    if status is False: return '<span class="badge-closed">❌ Fermé</span>'
    return ""

def price_cls(pf: float, moy: float) -> str:
    ratio = (pf - moy) / max(abs(moy * .03), .001)
    return "cheap" if ratio < -.5 else ("exp" if ratio > .5 else "avg")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS VÉHICULE + NOUVELLES FONCTIONS MÉTIER
# ═══════════════════════════════════════════════════════════════════════════════

def get_conso() -> float:
    preset = st.session_state.get(KEY_CONSO_PRESET,"🚗 Standard (6.5 L/100)")
    val    = CONSO_PRESETS.get(preset)
    return float(st.session_state.get(KEY_CONSO_CUSTOM, 6.5)) if val is None else val

def cout_reel_fn(prix: float, detour_km: float, litres: float, conso: float) -> float:
    return round(litres * prix + (detour_km * 2) * conso / 100 * prix, 2)

def calc_autonomie(tank: float, fill_pct: float, conso: float) -> float:
    litres = tank * (fill_pct / 100)
    return round(litres / conso * 100, 0) if conso > 0 else 0.0

def litres_a_faire(tank: float, fill_pct: float) -> float:
    return round(tank * (1 - fill_pct / 100), 1)


# ⑩ Score qualité composite
def score_station(row: dict, carb_col: str, litres: float,
                  conso: float, mode: str) -> float:
    """⑩ Score composite pour le tri "Meilleur choix".

    Composantes (ordre de grandeur harmonisé) :
    - Coût du plein (dominant, €)
    - Pénalité fraîcheur (+0.05€ par 24h au-delà de 6h)
    - Bonus services prioritaires (CB 24/24, automate 24h)
    - Pénalité distance en mode réel

    Retourne un float bas = meilleur.
    """
    pc    = f"{carb_col}_prix"
    prix  = float(row.get(pc, 99))
    dist  = float(row.get(COL_DISTANCE, 0) or 0)
    age_h = freshness_hours(row.get(f"{carb_col}_maj")) or 168

    cout = litres * prix
    if mode == "reel":
        cout = cout_reel_fn(prix, dist, litres, conso)

    penalite_fraicheur = max(0, (age_h - 6) / 24) * 0.05

    svcs = sl(row.get(COL_SERVICES, []))
    bonus_svcs = sum([
        -0.10 if "Automate CB 24/24" in svcs else 0,
        -0.05 if row.get(COL_AUTOMATE) == "Oui" else 0,
    ])
    return cout + penalite_fraicheur + bonus_svcs


# ⑨ Comparateur flex-fuel
def compare_flex_fuel(prix_e85: float, prix_sp95: float,
                      conso_e85_factor: float = 1.25,
                      conso_base: float = 6.5) -> dict:
    """⑨ Compare E85 vs SP95 pour un véhicule flex-fuel.

    L'E85 consomme ~25% de plus au volume mais coûte moins cher au litre.
    Retourne le carburant recommandé et le détail des coûts aux 100 km.

    Args:
        conso_e85_factor: Majoration conso en E85 (défaut 1.25 = +25%)
        conso_base:       Consommation SP95 de référence (L/100)
    """
    cout_sp95 = prix_sp95 * conso_base
    cout_e85  = prix_e85  * conso_base * conso_e85_factor
    eco_100   = round(cout_sp95 - cout_e85, 2)
    return {
        "recommande":    "E85" if cout_e85 < cout_sp95 else "SP95",
        "cout_sp95_100": round(cout_sp95, 2),
        "cout_e85_100":  round(cout_e85, 2),
        "eco_100":       eco_100,
        "eco_positive":  eco_100 > 0,
    }


# ⑦ CO₂
def co2_economise_html(litres: float, carb_col: str, pmin: float, pmax: float) -> str:
    """⑦ HTML badge CO₂ évité grâce au meilleur prix vs station la plus chère.

    Retourne '' si l'économie est nulle (station la plus chère).
    Source : ADEME 2023 — valeurs moyennes par carburant.
    """
    if pmin >= pmax: return ""
    litres_saved = litres * (pmax - pmin) / pmax
    co2_g  = litres_saved * CO2_PAR_LITRE.get(carb_col, 2400)
    co2_kg = co2_g / 1000
    if co2_kg < 0.05: return ""
    return (f'<div class="co2-badge">🌿 ~{co2_kg:.2f} kg CO₂ évités '
            f'vs station la plus chère</div>')


# ⑧ Tendance prix
def prix_tendance_html(prix_actuel: float, prix_veille: Optional[float]) -> str:
    """⑧ Badge tendance prix ↑ ↓ = depuis J-1.

    Utilise la colonne optionnelle `{carb_col}_prix_j1` de la table Supabase.
    Si absente, retourne ''.
    """
    if prix_veille is None: return ""
    diff = prix_actuel - prix_veille
    if abs(diff) < 0.002:
        return '<span class="trend-flat">= Stable</span>'
    if diff > 0:
        return f'<span class="trend-up">↑ +{diff:.3f}€</span>'
    return f'<span class="trend-down">↓ {diff:.3f}€</span>'


# ═══════════════════════════════════════════════════════════════════════════════
# DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_station_df(df: pd.DataFrame, carb_col: str) -> pd.DataFrame:
    """Harmonise les alias de colonnes legacy vers les constantes COL_*."""
    if df.empty: return df
    df = df.copy()
    legacy_map = {
        'servicesservice': COL_SERVICES, 'services_service': COL_SERVICES,
        'horairesjour': COL_HORAIRES, 'horaires_jour': COL_HORAIRES,
        'horairesautomate2424': COL_AUTOMATE, 'horaires_automate_24_24': COL_AUTOMATE,
        'distancekm': COL_DISTANCE, 'distance_km': COL_DISTANCE,
    }
    for src, dst in legacy_map.items():
        if src in df.columns and dst not in df.columns:
            df.rename(columns={src: dst}, inplace=True)
    required = [COL_SERVICES, COL_HORAIRES, COL_AUTOMATE, COL_DISTANCE,
                COL_LAT, COL_LON, COL_GEOM, COL_ID, COL_ADRESSE, COL_VILLE, COL_CP, COL_ENSEIGNE]
    for col in required:
        if col not in df.columns: df[col] = None
    pc, mc = f"{carb_col}_prix", f"{carb_col}_maj"
    if pc not in df.columns: df[pc] = None
    if mc not in df.columns: df[mc] = None
    return df


@st.cache_data(ttl=30, show_spinner=False)
def search_addresses(q: str) -> list[dict]:
    """Autocomplétion intelligente via api-adresse.data.gouv.fr + geo.api.gouv.fr.

    Stratégie robuste par ordre de priorité :
    1. Séparateur virgule → ville + adresse dans la ville
    2. Un seul mot → communes uniquement (évite les hameaux)
    3. Tentative A : premier token = ville, reste = adresse
    4. Tentative B : dernier token = ville, début = adresse
    5. Tentative C : chaque token testé comme ville isolée
    6. Fallback recherche libre sur la chaîne complète
    """
    q = q.strip()
    if len(q) < 2:
        return []

    BASE = "https://api-adresse.data.gouv.fr/search/"

    def _parse(feats: list) -> list[dict]:
        return [
            {"label": f["properties"]["label"],
             "lat":   f["geometry"]["coordinates"][1],
             "lon":   f["geometry"]["coordinates"][0]}
            for f in feats
        ]

    def _fetch(query: str, **extra) -> list[dict]:
        try:
            params = {"q": query, "limit": 8, "autocomplete": 1}
            params.update(extra)
            r = requests.get(BASE, params=params, timeout=4)
            feats = r.json().get("features", [])
            return [x for x in _parse(feats) if len(x["label"]) > 5]
        except:
            return []

    def _resolve_city(city_q: str) -> tuple[str, list]:
        """Retourne (nom_officiel, codes_postaux) via geo.api.gouv.fr (trié par population)."""
        try:
            r = requests.get(
                "https://geo.api.gouv.fr/communes",
                params={"nom": city_q, "fields": "nom,codesPostaux", "boost": "population", "limit": 1},
                timeout=4
            )
            data = r.json()
            if data:
                return data[0].get("nom", ""), data[0].get("codesPostaux", [])
        except:
            pass
        return "", []

    def _filter_by_city(results: list, cityname: str, postcodes: list) -> list:
        """Garde les résultats dont le label contient la ville ou un de ses codes postaux."""
        if not cityname:
            return results
        filtered = []
        for x in results:
            label = x["label"].lower()
            if cityname.lower() in label:
                filtered.append(x)
                continue
            if any(pc in x["label"] for pc in postcodes):
                filtered.append(x)
        return filtered

    sep = q.find(",")
    tokens = q.split()

    if sep > 0:
        # "Paris, 3 rue de la Paix" → ville + adresse
        city_q = q[:sep].strip()
        addr_q = q[sep + 1:].strip()
        cityname, postcodes = _resolve_city(city_q)
        if addr_q:
            results = _fetch(f"{addr_q} {city_q}")
            filtered = _filter_by_city(results, cityname, postcodes)
            if filtered:
                return filtered
        return _fetch(q)

    elif len(tokens) == 1:
        # Un seul mot → communes uniquement
        results = _fetch(q, type="municipality")
        if results:
            return results
        return _fetch(q)

    else:
        # Tentative A : premier token = ville, reste = adresse
        city_q = tokens[0]
        addr_q = " ".join(tokens[1:])
        cityname, postcodes = _resolve_city(city_q)
        if cityname and addr_q:
            results = _fetch(f"{addr_q} {city_q}")
            filtered = _filter_by_city(results, cityname, postcodes)
            if filtered:
                return filtered

        # Tentative B : dernier token = ville, début = adresse
        city_q2 = tokens[-1]
        addr_q2 = " ".join(tokens[:-1])
        cityname2, postcodes2 = _resolve_city(city_q2)
        if cityname2 and addr_q2:
            results = _fetch(f"{addr_q2} {city_q2}")
            filtered = _filter_by_city(results, cityname2, postcodes2)
            if filtered:
                return filtered

        # Tentative C : chaque token testé comme ville isolée
        for tok in tokens:
            if len(tok) >= 3:
                cn, _ = _resolve_city(tok)
                if cn:
                    return _fetch(tok, type="municipality")

        # Fallback final
        return _fetch(q)


@st.cache_data(ttl=3600, show_spinner=False)
def search_by_cp(cp: str) -> Optional[dict]:
    """⑤ Centroïde d'un code postal français via api-adresse.data.gouv.fr.

    Détecte un code postal (5 chiffres) et retourne {label, lat, lon}.
    Permet une saisie ultra-rapide sur mobile sans taper une adresse complète.
    """
    try:
        r = requests.get("https://api-adresse.data.gouv.fr/search/",
                         params={"q": cp, "type": "municipality", "limit": 1}, timeout=4)
        feats = r.json().get("features", [])
        if not feats: return None
        f = feats[0]
        return {"label": f["properties"]["label"],
                "lat":   f["geometry"]["coordinates"][1],
                "lon":   f["geometry"]["coordinates"][0]}
    except: return None


def _ttl_stations() -> int:
    """④ TTL adaptatif selon l'heure et le jour.

    - Matin en semaine (7h–9h) : 60s — période de mise à jour des prix
    - Week-end               : 120s — davantage de mises à jour
    - Reste du temps         : 300s
    """
    now = datetime.now()
    if now.weekday() >= 5: return 120
    if 7 <= now.hour < 9:  return 60
    return 300


@st.cache_data(ttl=_ttl_stations(), show_spinner=False)
def load_stations(_sb, carb_col: str, lat: float, lon: float,
                  radius: float) -> tuple[pd.DataFrame, bool]:
    """Charge les stations depuis Supabase.

    ④ TTL adaptatif : 60s matin semaine, 120s week-end, 300s sinon.
    Stratégie : RPC get_stations_proches → fallback bbox.
    """
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


@st.cache_data(ttl=600, show_spinner=False)
def load_prix_historique(_sb, station_id: str, carb_col: str, jours: int = 30) -> pd.DataFrame:
    """⑫ Charge l'historique de prix d'une station depuis la table prix_historique.

    Table attendue : prix_historique(station_id, carburant, prix, date)
    Retourne un DataFrame vide si la table n'existe pas (dégradation gracieuse).
    """
    since = (datetime.now(timezone.utc) - timedelta(days=jours)).isoformat()
    try:
        r = (_sb.table("prix_historique")
               .select("date, prix")
               .eq("station_id", str(station_id))
               .eq("carburant", carb_col)
               .gte("date", since)
               .order("date")
               .execute())
        return pd.DataFrame(r.data or [])
    except:
        return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING ORS
# ═══════════════════════════════════════════════════════════════════════════════

def get_ors_route(slat: float, slon: float, elat: float, elon: float,
                  api_key: str, avoid_highways: bool = False) -> dict:
    """Itinéraire simple A→B via ORS. Retourne {distance_km, duration_min, coords}."""
    url  = f"{ORS_BASE}/directions/driving-car/geojson"
    body: dict = {"coordinates": [[slon, slat], [elon, elat]]}
    if avoid_highways:
        body["options"] = {"avoid_features": ["tollways", "highways"]}
    try:
        r = requests.post(url, json=body, headers={"Authorization": api_key}, timeout=12)
        if r.status_code != 200:
            st.warning(f"ORS erreur {r.status_code}: {r.text[:120]}")
            return {}
        feat  = r.json()["features"][0]
        props = feat["properties"]["summary"]
        return {"distance_km":  round(props["distance"] / 1000, 1),
                "duration_min": round(props["duration"] / 60, 0),
                "coords":       feat["geometry"]["coordinates"]}
    except Exception as exc:
        st.warning(f"ORS indisponible : {exc}")
        return {}


def get_ors_route_multi(waypoints: list[dict], api_key: str) -> dict:
    """⑪ Itinéraire multi-étapes (jusqu'à 10 waypoints) via ORS.

    Args:
        waypoints: Liste de {lat, lon} dans l'ordre du trajet
        api_key:   Clé OpenRouteService

    Returns:
        {distance_km, duration_min, coords} ou {} si erreur.
    """
    if len(waypoints) < 2: return {}
    coords = [[w["lon"], w["lat"]] for w in waypoints]
    url    = f"{ORS_BASE}/directions/driving-car/geojson"
    try:
        r = requests.post(url, json={"coordinates": coords},
                          headers={"Authorization": api_key}, timeout=20)
        if r.status_code != 200:
            st.warning(f"ORS multi erreur {r.status_code}: {r.text[:120]}")
            return {}
        feat  = r.json()["features"][0]
        props = feat["properties"]["summary"]
        return {"distance_km":  round(props["distance"] / 1000, 1),
                "duration_min": round(props["duration"] / 60, 0),
                "coords":       feat["geometry"]["coordinates"]}
    except Exception as exc:
        st.warning(f"ORS multi indisponible : {exc}")
        return {}


def point_to_route_dist(lat: float, lon: float, coords: list,
                        step: int = 10) -> float:
    """① Distance minimale (km) du point au trajet ORS.

    Optimisation : passe grossière (1 point sur `step`) puis affinage
    sur les 5 voisins du meilleur candidat.
    Gain : ×8 à ×12 vs la version exhaustive pour un trajet de 300 km.
    """
    if not coords: return 999.0
    sampled  = coords[::step] or coords
    best_idx = 0
    best_d   = 999.0
    for i, c in enumerate(sampled):
        d = dist_km(lat, lon, c[1], c[0]) or 999
        if d < best_d:
            best_d   = d
            best_idx = i * step
    lo = max(0, best_idx - 5)
    hi = min(len(coords), best_idx + 6)
    return round(min(dist_km(lat, lon, c[1], c[0]) or 999 for c in coords[lo:hi]), 2)


def stations_on_route(df: pd.DataFrame, coords: list, corridor_km: float = 5.0) -> pd.DataFrame:
    """Filtre les stations dans le corridor du trajet. Ajoute 'detour_km'."""
    if df.empty or not coords: return df
    df = df.copy()
    df["detour_km"] = df.apply(
        lambda r: point_to_route_dist(
            float(r.get(COL_LAT,0)), float(r.get(COL_LON,0)), coords), axis=1)
    return df[df["detour_km"] <= corridor_km].sort_values("detour_km")


# ═══════════════════════════════════════════════════════════════════════════════
# ⑥ PARTAGE URL
# ═══════════════════════════════════════════════════════════════════════════════

def build_share_url(lat: float, lon: float, carb_col: str, prix: float) -> str:
    """⑥ Génère un URL partageable avec position, carburant et prix.

    Utilise st.query_params (Streamlit ≥ 1.30).
    Le destinataire voit directement les stations autour du point partagé.
    """
    try:
        base = st.secrets.get("APP_URL", "https://ecoplein.streamlit.app")
    except:
        base = "https://ecoplein.streamlit.app"
    return f"{base}?lat={lat:.5f}&lon={lon:.5f}&carb={carb_col}&prix={prix:.3f}"

def _read_share_params() -> None:
    """⑥ Lit les query params de l'URL et initialise la position si partagée."""
    try:
        params = st.query_params
        if "lat" in params and "lon" in params:
            lat = float(params["lat"])
            lon = float(params["lon"])
            if KEY_GPS_RESULT not in st.session_state:
                st.session_state[KEY_GPS_RESULT] = (lat, lon)
                st.session_state[KEY_GPS_LABEL]  = f"Lien partagé · {lat:.3f}°, {lon:.3f}°"
    except:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# ⑫ FAVORIS + SNAPSHOT + ALERTES
# ═══════════════════════════════════════════════════════════════════════════════

def toggle_fav(sid: str, prix_actuel: Optional[float] = None) -> None:
    """Ajoute/retire un favori. Snapshot le prix si ajout."""
    favs = st.session_state.get(KEY_FAVORITES, set())
    if sid in favs:
        favs.discard(sid)
        snap = st.session_state.get(KEY_FAV_PRIX_SNAP, {})
        snap.pop(sid, None)
        st.session_state[KEY_FAV_PRIX_SNAP] = snap
    else:
        favs.add(sid)
        if prix_actuel is not None:
            snap = st.session_state.get(KEY_FAV_PRIX_SNAP, {})
            snap[sid] = round(float(prix_actuel), 3)
            st.session_state[KEY_FAV_PRIX_SNAP] = snap
    st.session_state[KEY_FAVORITES] = favs

def is_fav(sid: str) -> bool:
    return sid in st.session_state.get(KEY_FAVORITES, set())

def fav_prix_diff_html(sid: str, prix_actuel: float) -> str:
    """⑫ HTML de variation de prix depuis l'ajout en favori."""
    snap = st.session_state.get(KEY_FAV_PRIX_SNAP, {})
    prix_ref = snap.get(sid)
    if prix_ref is None: return ""
    diff = prix_actuel - prix_ref
    if abs(diff) < 0.002: return '<span class="bg-w" style="font-size:.7rem">= même prix</span>'
    if diff > 0:
        return f'<span class="fav-diff-up">↑ +{diff:.3f}€ depuis l\'ajout</span>'
    return f'<span class="fav-diff-down">↓ {diff:.3f}€ depuis l\'ajout</span>'

def add_prix_alert(sid: str, carb_col: str, seuil: float) -> None:
    """⑫ Enregistre une alerte prix pour une station."""
    alerts = st.session_state.get(KEY_ALERTS, {})
    if sid not in alerts: alerts[sid] = {}
    alerts[sid][carb_col] = round(float(seuil), 3)
    st.session_state[KEY_ALERTS] = alerts

def remove_prix_alert(sid: str, carb_col: str) -> None:
    """⑫ Supprime une alerte prix."""
    alerts = st.session_state.get(KEY_ALERTS, {})
    if sid in alerts:
        alerts[sid].pop(carb_col, None)
        if not alerts[sid]: alerts.pop(sid)
    st.session_state[KEY_ALERTS] = alerts

def check_prix_alerts(df_stations: pd.DataFrame, carb_col: str) -> list[str]:
    """⑫ Vérifie si des stations surveillées ont atteint leur seuil de prix.

    Retourne une liste de messages d'alerte — affichés en st.toast() dans main().
    """
    alerts = st.session_state.get(KEY_ALERTS, {})
    pc     = f"{carb_col}_prix"
    msgs   = []
    for sid, seuils in alerts.items():
        seuil = seuils.get(carb_col)
        if seuil is None: continue
        row = df_stations[df_stations[COL_ID].astype(str) == sid]
        if row.empty: continue
        prix = float(row.iloc[0].get(pc, 9999))
        if prix <= seuil:
            brand = detect_brand(dict(row.iloc[0])) or sid
            msgs.append(f"🔔 **{brand}** → {prix:.3f}€ ≤ seuil {seuil:.3f}€")
    return msgs


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSANTS UI
# ═══════════════════════════════════════════════════════════════════════════════

def address_autocomplete_field(
    label: str,
    key: str,
    placeholder: str = "Ex : Lille  ou  Lille, Rue Faidherbe  ou  59000",
    selected_key: Optional[str] = None,
    show_label: bool = True,
) -> Optional[dict]:
    """
    Champ d'adresse avec autocomplétion en temps réel.
    show_label=False : n'affiche pas le sec-label (utile si le parent gère son propre header).
    Retourne dict {label, lat, lon} ou None.
    """
    if selected_key is None:
        selected_key = f"{key}_selected"

    # ── Déjà sélectionné ────────────────────────────────────────────
    if selected_key in st.session_state:
        info = st.session_state[selected_key]
        st.markdown(
            f'<div class="gps-ok" style="font-size:.82rem;padding:5px 10px;">' +
            f'📍 {info["label"]}</div>',
            unsafe_allow_html=True,
        )
        if st.button("✕ Changer", key=f"{key}_reset", use_container_width=True):
            del st.session_state[selected_key]
            st.session_state.pop(f"{key}_kv", None)
            st.rerun()
        return info

    # ── Champ de saisie ─────────────────────────────────────────────
    if show_label:
        st.markdown(f'<div class="sec-label">{label}</div>', unsafe_allow_html=True)
    query = st.text_input(
        label,
        key=f"{key}_kv",
        placeholder=placeholder,
        label_visibility="collapsed",
    )

    if not query or not query.strip():
        return None

    q = query.strip()

    # ── Code postal 5 chiffres ──────────────────────────────────────
    if re.match(r'^\d{5}$', q):
        with st.spinner("Recherche par code postal…"):
            result = search_by_cp(q)
        if result:
            st.session_state[selected_key] = result
            st.session_state.pop(f"{key}_kv", None)
            st.rerun()
        else:
            st.markdown(
                '<div class="intent-card" style="font-size:.8rem;">❌ Code postal introuvable.</div>',
                unsafe_allow_html=True,
            )
        return None

    if len(q) < 2:
        return None

    sugs = search_addresses(q)

    if not sugs:
        if len(q) >= 4:
            st.markdown(
                f'<div class="intent-card" style="font-size:.8rem;">' +
                f'🔍 Aucun résultat pour <em>«&nbsp;{q}&nbsp;»</em>.</div>',
                unsafe_allow_html=True,
            )
        return None

    # ── Suggestions ──────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:.75rem;opacity:.6;margin:4px 0 2px;">Sélectionnez :</div>',
        unsafe_allow_html=True,
    )
    for i, sug in enumerate(sugs[:5]):
        icon = "🏙️" if any(c.isdigit() for c in sug["label"][:6]) else "📍"
        if st.button(f"{icon} {sug['label']}", key=f"{key}_sug_{i}", use_container_width=True):
            st.session_state[selected_key] = sug
            st.session_state.pop(f"{key}_kv", None)
            st.rerun()

    return None


# ─────────────────────────────────────────────────────────────────
# HISTORIQUE DES PRIX — Sprint 3
# ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_prix_historique(station_id: str, carb_col: str, jours: int = 90) -> list[dict]:
    """Charge les N derniers jours d'historique pour une station/carburant.
    Retourne une liste de dicts {prix, capturé_le} triée par date ASC."""
    try:
        sb   = get_supabase()
        depuis = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=jours)).isoformat()
        resp = (sb.table("prix_historique")
                  .select("prix, capturé_le")
                  .eq("station_id", station_id)
                  .eq("carb_col", carb_col)
                  .gte("capturé_le", depuis)
                  .order("capturé_le", desc=False)
                  .limit(500)
                  .execute())
        return resp.data or []
    except Exception:
        return []

def render_historique_prix(station_id: str, carb_col: str, label_carb: str) -> None:
    """Historique prix — layout 100% natif Streamlit pour responsive parfait."""
    rows = load_prix_historique(station_id, carb_col, jours=90)
    if len(rows) < 2:
        st.markdown(
            '<div class="scard" style="font-size:.8rem;text-align:center;'
            'padding:14px 12px;color:var(--text-2);">'
            '&#128202; Historique disponible à la prochaine MAJ des prix.</div>',
            unsafe_allow_html=True)
        return

    df_h = pd.DataFrame(rows)
    df_h["capturé_le"] = pd.to_datetime(df_h["capturé_le"], utc=True)
    df_h = df_h.drop_duplicates("capturé_le").sort_values("capturé_le")

    vals      = df_h["prix"].tolist()
    prix_min  = min(vals)
    prix_max  = max(vals)
    prix_last = vals[-1]
    prix_prev = vals[-2]
    delta     = prix_last - prix_prev
    n_pts     = len(vals)
    n_jours   = max(1, (df_h["capturé_le"].iloc[-1] - df_h["capturé_le"].iloc[0]).days)

    # ── Ligne header : label + période + delta ────────────────────
    if abs(delta) < 0.0005:
        delta_cls, delta_str = "trend-flat", "= stable"
    elif delta > 0:
        delta_cls, delta_str = "trend-up",   f"&#8593; +{delta:.3f}&#8364;"
    else:
        delta_cls, delta_str = "trend-down",  f"&#8595; {delta:.3f}&#8364;"

    st.markdown(
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:6px;">'
        f'<span style="font-weight:700;font-size:.8rem;color:var(--text);">&#128202; {label_carb}</span>'
        f'<span class="bg-w" style="font-size:.68rem;">{n_jours}j &middot; {n_pts}&nbsp;pts</span>'
        f'<span class="{delta_cls}">{delta_str}</span>'
        f'</div>',
        unsafe_allow_html=True)

    # ── Spark line SVG ────────────────────────────────────────────
    W, H, PAD = 300, 52, 6
    span = prix_max - prix_min if prix_max != prix_min else 0.001
    pts  = " ".join(
        f"{round(PAD + i / max(n_pts - 1, 1) * (W - 2*PAD), 1)},"
        f"{round(PAD + (1 - (v - prix_min) / span) * (H - 2*PAD), 1)}"
        for i, v in enumerate(vals))
    cx = round(PAD + (W - 2*PAD), 1)
    cy = round(PAD + (1 - (vals[-1] - prix_min) / span) * (H - 2*PAD), 1)

    st.markdown(
        f'<svg viewBox="0 0 {W} {H}" width="100%" height="52" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" '
        f'style="display:block;margin-bottom:8px;">'
        f'<polyline points="{pts}" fill="none" stroke="var(--teal)" '
        f'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{cx}" cy="{cy}" r="4" fill="var(--teal)"/>'
        f'</svg>',
        unsafe_allow_html=True)

    # ── Footer 3 KPIs — st.columns natif ─────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:.6rem;color:var(--text-2);text-transform:uppercase;'
            f'letter-spacing:.05em;">Min</div>'
            f'<div style="font-size:.82rem;font-weight:700;color:var(--green);">'
            f'{prix_min:.3f}&#8364;</div></div>',
            unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:.6rem;color:var(--text-2);text-transform:uppercase;'
            f'letter-spacing:.05em;">Actuel</div>'
            f'<div style="font-size:.88rem;font-weight:800;color:var(--teal);">'
            f'{prix_last:.3f}&#8364;</div></div>',
            unsafe_allow_html=True)
    with c3:
        st.markdown(
            f'<div style="text-align:center;">'
            f'<div style="font-size:.6rem;color:var(--text-2);text-transform:uppercase;'
            f'letter-spacing:.05em;">Max</div>'
            f'<div style="font-size:.82rem;font-weight:700;color:var(--text-2);">'
            f'{prix_max:.3f}&#8364;</div></div>',
            unsafe_allow_html=True)

def location_block() -> tuple[Optional[float], Optional[float], Optional[str]]:
    """Bloc position : GPS ou adresse ou code postal.

    ⑤ Détecte automatiquement les codes postaux (5 chiffres) et appelle
    search_by_cp() directement, sans passer par le flow adresse standard.
    """
    method = st.radio("Méthode", ["📍 GPS", "🔍 Adresse / CP"],
                      horizontal=True, label_visibility="collapsed", key="loc_method")

    if method == "📍 GPS":
        st.markdown("<small>Votre navigateur demandera l'autorisation GPS.</small>",
                    unsafe_allow_html=True)
        if st.button("📡 Me localiser", key="gps_btn", use_container_width=True, type="primary"):
            st.session_state[KEY_GPS_ASKED]    = True
            st.session_state[KEY_GPS_ATTEMPTS] = 0
            st.session_state.pop(KEY_GPS_RESULT, None)

        if st.session_state.get(KEY_GPS_ASKED):
            attempts = st.session_state.get(KEY_GPS_ATTEMPTS, 0)
            with st.spinner(f"Localisation… ({attempts+1}/5)"):
                try: loc = get_geolocation()
                except: loc = None
            if loc and isinstance(loc, dict) and loc.get("coords"):
                c   = loc["coords"]
                lat, lon = float(c["latitude"]), float(c["longitude"])
                acc = c.get("accuracy", 0)
                st.session_state[KEY_GPS_RESULT]   = (lat, lon)
                st.session_state[KEY_GPS_ASKED]    = False
                st.session_state[KEY_GPS_ATTEMPTS] = 0
                st.markdown(f'<div class="gps-ok">✅ Position trouvée · ±{acc:.0f} m</div>',
                            unsafe_allow_html=True)
            elif attempts < 5:
                st.session_state[KEY_GPS_ATTEMPTS] = attempts + 1
                st.markdown(f'<div class="gps-err">⏳ En attente… ({attempts+1}/5)</div>',
                            unsafe_allow_html=True)
                _time.sleep(0.5); st.rerun()
            else:
                st.session_state[KEY_GPS_ASKED]    = False
                st.session_state[KEY_GPS_ATTEMPTS] = 0
                st.markdown('<div class="gps-fail">❌ GPS indisponible. Utilisez l\'adresse.</div>',
                            unsafe_allow_html=True)
                if st.button("🔄 Réessayer", key="gps_retry"):
                    st.session_state[KEY_GPS_ASKED]    = True
                    st.session_state[KEY_GPS_ATTEMPTS] = 0
                    st.rerun()

        if KEY_GPS_RESULT in st.session_state:
            lat, lon = st.session_state[KEY_GPS_RESULT]
            lbl      = st.session_state.get(KEY_GPS_LABEL, f"{lat:.4f}, {lon:.4f}")
            st.markdown(f'<div class="gps-ok">📍 {lbl}</div>', unsafe_allow_html=True)
            return lat, lon, lbl

    else:
        if KEY_ADDR_SELECTED in st.session_state:
            info = st.session_state[KEY_ADDR_SELECTED]
            st.markdown(f'<div class="gps-ok">✅ {info["label"]}</div>', unsafe_allow_html=True)
            if st.button("✏️ Changer", key="addr_reset", use_container_width=True):
                del st.session_state[KEY_ADDR_SELECTED]; st.rerun()
            return info["lat"], info["lon"], info["label"]

        info = address_autocomplete_field(
            label="Adresse ou code postal",
            key="addrquery",
            placeholder="Ex : 59000, Lille, 3 rue de la Paix Paris…",
            selected_key=KEY_ADDR_SELECTED,
        )
        if info:
            return info["lat"], info["lon"], info["label"]

    return None, None, None


def render_vehicle_settings(key_prefix: str = "vs_") -> tuple[float, float]:
    """Réglages véhicule : réservoir, niveau, conso, mode coût.
    ⑨ Ajoute le toggle flex-fuel et le facteur de majoration E85.
    """
    c1, c2 = st.columns(2)
    with c1:
        tank = st.select_slider(
            "🛢️ Réservoir", options=list(range(20,115,5)),
            value=st.session_state.get(KEY_TANK_CAP,50),
            key=f"{key_prefix}tank", format_func=lambda x: f"{x} L")
        st.markdown(f'<div class="slider-scale"><span>20 L</span><span>{tank} L</span><span>110 L</span></div>',
                    unsafe_allow_html=True)
    with c2:
        fill = st.select_slider(
            "🪣 Niveau actuel", options=list(range(0,105,5)),
            value=st.session_state.get(KEY_FILL_PCT,20),
            key=f"{key_prefix}fill", format_func=lambda x: f"{x} %")
        st.markdown(f'<div class="slider-scale"><span>0 %</span><span>{fill} %</span><span>100 %</span></div>',
                    unsafe_allow_html=True)
    st.session_state[KEY_TANK_CAP] = tank
    st.session_state[KEY_FILL_PCT] = fill

    preset = st.selectbox(
        "🚗 Profil véhicule", list(CONSO_PRESETS.keys()),
        index=list(CONSO_PRESETS.keys()).index(
            st.session_state.get(KEY_CONSO_PRESET,"🚗 Standard (6.5 L/100)")),
        key=f"{key_prefix}conso_preset")
    st.session_state[KEY_CONSO_PRESET] = preset
    if CONSO_PRESETS[preset] is None:
        custom = st.number_input("Conso (L/100)", 2.0, 20.0,
                                 float(st.session_state.get(KEY_CONSO_CUSTOM,6.5)), 0.5,
                                 key=f"{key_prefix}cval")
        st.session_state[KEY_CONSO_CUSTOM] = custom

    mode = st.radio("💰 Calcul du coût",
                    ["Prix au litre uniquement","Prix + coût du trajet (aller-retour)"],
                    index=0 if st.session_state.get(KEY_MODE_COUT,"simple")=="simple" else 1,
                    horizontal=True, key=f"{key_prefix}mode")
    st.session_state[KEY_MODE_COUT] = "simple" if "uniquement" in mode else "reel"
    try:
        save_profil_vehicule(get_supabase())
    except Exception:
        pass

    # ⑨ Flex-fuel
    is_flex = st.checkbox("🔄 Véhicule flex-fuel (E85 / SP95)",
                          value=st.session_state.get(KEY_IS_FLEX,False),
                          key=f"{key_prefix}flex")
    st.session_state[KEY_IS_FLEX] = is_flex
    if is_flex:
        factor = st.slider("Majoration conso E85 (%)", 10, 40,
                           int((st.session_state.get(KEY_CONSO_E85_FACTOR,1.25)-1)*100),
                           key=f"{key_prefix}e85f")
        st.session_state[KEY_CONSO_E85_FACTOR] = 1 + factor/100
        st.caption(f"Majoration : +{factor}% → conso E85 = {get_conso()*st.session_state[KEY_CONSO_E85_FACTOR]:.1f} L/100")

    conso = get_conso()
    litre = litres_a_faire(tank, fill)
    auto  = calc_autonomie(tank, fill, conso)
    pct_vide   = min(100, max(0, round((1 - fill / 100) * 100)))
    bar_color  = "#22c55e" if fill < 25 else "#f59e0b" if fill < 60 else "#60a5fa" if fill < 95 else "#a78bfa"
    litre_lbl  = f"{litre:.0f} L à faire" if litre > 0 else "⛽ Réservoir plein !"
    preset_lbl = st.session_state.get(KEY_CONSO_PRESET, "Standard")[:22]
    st.markdown(f"""
<div class="calc-box" style="margin-top:8px;padding:12px 14px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span style="font-size:.65rem;color:var(--accent);text-transform:uppercase;letter-spacing:.10em;font-weight:800">Récapitulatif</span>
    <span style="font-size:.68rem;color:var(--text-3)">{preset_lbl}</span>
  </div>
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
    <span style="font-size:.72rem;color:var(--text-2);width:72px;flex-shrink:0">Réservoir</span>
    <div class="cmp-bar-wrap" style="flex:1">
      <div class="cmp-bar" style="width:{pct_vide}%;background:{bar_color}"></div>
    </div>
    <span style="font-size:.75rem;font-weight:700;font-family:'JetBrains Mono',monospace;color:var(--text);white-space:nowrap">{litre_lbl}</span>
  </div>
  <div style="display:flex;gap:12px;flex-wrap:wrap">
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--accent)">{auto:.0f} km</div><div class="sh-stat-l">Autonomie</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--text)">{conso:.1f} L/100</div><div class="sh-stat-l">Conso</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--blue)">{litre:.0f} L</div><div class="sh-stat-l">À faire</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--text-3)">{tank} L</div><div class="sh-stat-l">Réservoir</div></div>
  </div>
</div>""", unsafe_allow_html=True)
    return tank, fill


def render_detour_calc(df_sorted: pd.DataFrame, carb_col: str, prix_min: float,
                       litres_needed: float, key_prefix: str = "") -> None:
    """Calcule si le détour vers la station la moins chère vaut le coup."""
    pc = f"{carb_col}_prix"
    st.markdown("**🧮 Vaut-il le détour ?**")
    preset = st.selectbox("Profil", list(CONSO_PRESETS.keys()),
                          key=f"{key_prefix}preset", label_visibility="collapsed")
    conso  = (st.number_input("Conso L/100",2.0,20.0,6.5,0.5,key=f"{key_prefix}cval")
              if CONSO_PRESETS[preset] is None else CONSO_PRESETS[preset])

    best_row     = df_sorted[df_sorted[pc] == prix_min].iloc[0]
    best_dist    = float(best_row.get(COL_DISTANCE,0) or 0)
    closest_row  = df_sorted.sort_values(COL_DISTANCE).iloc[0]
    closest_px   = float(closest_row[pc])
    closest_dist = float(closest_row.get(COL_DISTANCE,0) or 0)

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


def render_best_deal(row: dict, carb_col: str, u_lat: float, u_lon: float,
                     pmax: float = 0.0) -> None:
    """v30 — Hero card meilleure offre avec gradient border animé.

    Affordance immédiate : prix en monospace géant + économie en vert
    ⑦ CO₂ · ⑨ Flex-fuel · ⑧ Tendance
    """
    pc    = f"{carb_col}_prix"
    prix  = float(row.get(pc, 0))
    brand = detect_brand(row)
    label = f"{brand} · " if brand else ""
    d     = row.get(COL_DISTANCE) or dist_km(u_lat, u_lon, *geom_to_latlon(row.get(COL_GEOM)))
    tank  = st.session_state.get(KEY_TANK_CAP, 50)
    fill  = st.session_state.get(KEY_FILL_PCT, 20)
    litre = litres_a_faire(tank, fill)
    litre = litre if litre > 0 else tank  # réservoir plein → affiche coût plein théorique
    cout  = round(litre * prix, 2)
    moy   = st.session_state.get(KEY_PRIX_MOY, prix)
    pmax_ = pmax or st.session_state.get(KEY_PRIX_MAX, prix)
    eco   = round(litre * (moy - prix), 2)
    lat   = float(row.get(COL_LAT, u_lat) or u_lat)
    lon   = float(row.get(COL_LON, u_lon) or u_lon)

    eco_html   = (f'<div class="bd-eco">💚 Vous économisez <b>−{eco:.2f}€</b> vs la moyenne</div>'
                  if eco > 0.30 else "")
    age_h      = freshness_hours(row.get(f"{carb_col}_maj"))
    alert_html = ""
    if age_h is not None and age_h > 72:
        alert_html = f'<div class="bd-alert">⚠️ Prix non mis à jour depuis {age_h:.0f}h</div>'

    # ⑦ CO₂
    co2_html = co2_economise_html(litre, carb_col, prix, pmax_)

    # ⑧ Tendance
    prix_j1   = row.get(f"{carb_col}_prix_j1")
    tend_html = prix_tendance_html(prix, float(prix_j1) if prix_j1 else None)

    g = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
    w = f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"
    a = f"http://maps.apple.com/?daddr={lat},{lon}"
    share_url = build_share_url(lat, lon, carb_col, prix)

    dist_txt = f"📍 {d:.1f} km · " if d else ""
    fr_text, _ = freshness(row.get(f"{carb_col}_maj"))

    st.markdown(f"""
<div class="best-deal">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
    <div style="flex:1;min-width:0">
      <div style="font-size:.62rem;font-weight:800;letter-spacing:.10em;text-transform:uppercase;
           color:#2dd4bf;margin-bottom:6px">🏆 MEILLEUR CHOIX</div>
      <div class="bd-price">{prix:.3f}<span style="font-size:1rem;opacity:.6"> €/L</span>
           <span style="font-size:.9rem;margin-left:8px">{tend_html}</span></div>
      <div class="bd-name" style="margin-top:6px">{label}{s(row.get(COL_ADRESSE,'')).strip()}</div>
      <div class="bd-sub">{dist_txt}{s(row.get(COL_VILLE,''))} {open_badge(row)}</div>
      {eco_html}{alert_html}
      <div style="margin-top:4px">{co2_html}</div>
      <div style="font-size:.65rem;color:rgba(255,255,255,0.35);margin-top:4px">{fr_text}</div>
      <div class="bd-nav">
        <a href="{g}" target="_blank" class="nav-a na-gmaps">🗺️ Maps</a>
        <a href="{w}" target="_blank" class="nav-a na-waze">🚗 Waze</a>
        <a href="{a}" target="_blank" class="nav-a na-apple">Apple</a>
        <a href="{share_url}" target="_blank" class="nav-a na-share">📤 Partager</a>
      </div>
    </div>
    <div style="text-align:right;flex-shrink:0">
      <div class="bd-cout">{cout:.2f}€</div>
      <div class="bd-litre">{litre:.0f} L estimés</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ⑨ Flex-fuel si activé et E85 disponible localement
    if st.session_state.get(KEY_IS_FLEX) and carb_col in ("sp95", "sp98", "e10"):
        prix_e85_cache = st.session_state.get("best_e85_prix_cache")
        if prix_e85_cache:
            factor = st.session_state.get(KEY_CONSO_E85_FACTOR, 1.25)
            conso  = get_conso()
            res = compare_flex_fuel(float(prix_e85_cache), prix, factor, conso)
            winner = res["recommande"]
            eco100 = res["eco_100"]
            eco_str = f"−{eco100:.2f}€/100 km" if eco100 > 0 else f"+{abs(eco100):.2f}€/100 km"
            st.markdown(
                f'<div class="flex-box">'
                f'<div class="flex-winner">⛽ Flex-fuel : {winner} recommandé</div>'
                f'<div class="flex-detail">'
                f'SP95 : {res["cout_sp95_100"]:.2f}€/100 km · '
                f'E85 : {res["cout_e85_100"]:.2f}€/100 km</div>'
                f'<div class="flex-eco">{eco_str} en choisissant {winner}</div>'
                f'</div>', unsafe_allow_html=True)


def render_prix_chart(df_hist: pd.DataFrame, sid: str) -> None:
    """⑫ Affiche la courbe de prix historique (st.line_chart natif)."""
    if df_hist.empty:
        st.caption("Historique non disponible (table prix_historique absente ou vide)")
        return
    df_hist = df_hist.copy()
    df_hist["date"] = pd.to_datetime(df_hist["date"])
    df_hist = df_hist.set_index("date").sort_index()
    pmin_h  = df_hist["prix"].min()
    pmax_h  = df_hist["prix"].max()
    st.markdown(
        f'<div class="hist-box">'
        f'📈 Min {pmin_h:.3f}€ · Max {pmax_h:.3f}€ · {len(df_hist)} relevés</div>',
        unsafe_allow_html=True)
    st.line_chart(df_hist["prix"], use_container_width=True, height=110, color="#16a34a")


def render_alert_panel(df_stations: pd.DataFrame, carb_col: str) -> None:
    """⑫ Panneau de gestion des alertes prix actives."""
    alerts = st.session_state.get(KEY_ALERTS, {})
    pc     = f"{carb_col}_prix"
    if not alerts:
        st.caption("Aucune alerte configurée. Utilisez le bouton 🔔 sous une station.")
        return
    st.markdown("**🔔 Alertes prix actives**")
    for sid, seuils in list(alerts.items()):
        seuil = seuils.get(carb_col)
        if seuil is None: continue
        row = df_stations[df_stations[COL_ID].astype(str) == sid]
        nom  = detect_brand(dict(row.iloc[0])) if not row.empty else sid[:12]
        prix_actuel = float(row.iloc[0].get(pc, 9999)) if not row.empty else None
        triggered = prix_actuel is not None and prix_actuel <= seuil
        color = "var(--green)" if triggered else "var(--amber)"
        status = f"✅ {prix_actuel:.3f}€ ≤ seuil" if triggered else f"⏳ {prix_actuel:.3f}€ > {seuil:.3f}€" if prix_actuel else f"Seuil : {seuil:.3f}€"
        st.markdown(
            f'<div class="alert-row">'
            f'<span>{nom}</span>'
            f'<span style="color:{color};font-weight:700">{status}</span>'
            f'</div>', unsafe_allow_html=True)
        if st.button(f"🗑️ Supprimer", key=f"del_alert_{sid}_{carb_col}"):
            remove_prix_alert(sid, carb_col); st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER CARD — helpers privés + fonction principale
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_coords(row: dict, ulat: float, ulon: float) -> tuple[float, float]:
    lat, lon = row.get(COL_LAT), row.get(COL_LON)
    if lat in (None,0,"","0") or lon in (None,0,"","0"):
        lat, lon = geom_to_latlon(row.get(COL_GEOM))
    try: return float(lat), float(lon)
    except: return float(ulat), float(ulon)

def _resolve_distance(row: dict, slat: float, slon: float,
                      ulat: float, ulon: float) -> Optional[float]:
    raw_d = row.get(COL_DISTANCE)
    try: raw_d = float(raw_d) if raw_d is not None else None
    except: raw_d = None
    calc_d = dist_km(float(ulat), float(ulon), slat, slon) if slat and slon and ulat and ulon else None
    if raw_d is not None and raw_d <= 100 and calc_d is not None and abs(raw_d - calc_d) <= 20:
        return raw_d
    return calc_d if calc_d is not None else raw_d

def _build_price_html(pf: float, cls: str, cout: float, litres: float) -> str:
    return (f'<div class="sc-price {cls}">'
            f'<div class="sc-pval {cls}">{pf:.3f}</div>'
            f'<div class="sc-punit">€/L</div>'
            f'<div class="sc-pfill">{cout:.2f}€</div>'
            f'<div class="sc-plitre">{litres:.0f}L estimés</div>'
            f'</div>')

def _build_eco_html(litres: float, pf: float, moy: float, pmax: float) -> str:
    parts = []
    eco_vs_moy = round(litres * (moy - pf), 2)
    eco_vs_max = round(litres * (pmax - pf), 2)
    if eco_vs_moy > 0.30: parts.append(f'<span class="eco-tag">−{eco_vs_moy:.2f}€ vs moy</span>')
    if eco_vs_max > 0.50: parts.append(f'<span class="eco-tag-2">−{eco_vs_max:.2f}€ vs max</span>')
    return "".join(parts)

def _build_svcs_html(row: dict) -> str:
    parts = []
    if row.get(COL_AUTOMATE) == "Oui": parts.append('<span class="bg-g">24h/24</span>')
    for sv in sl(row.get(COL_SERVICES)):
        if sv in SVC_PRIORITY and sv in SVC:
            icon, css_cls = SVC[sv]
            parts.append(f'<span class="{css_cls}">{icon}</span>')
    return "".join(parts)

def _build_info_html(row: dict, station_name: str, d: Optional[float],
                     open_s: str, best_badge: str, svcs_html: str,
                     eco_html: str, tend_html: str, fav_diff: str) -> str:
    dist_txt  = f"📍 {d:.1f} km · " if d is not None else ""
    cp_ville  = f"{s(row.get(COL_CP))} {s(row.get(COL_VILLE))}".strip()
    svcs_line = f'<div class="sc-svcs">{svcs_html}</div>' if svcs_html else ""
    eco_line  = f'<div class="sc-eco">{eco_html}</div>'  if eco_html  else ""
    tend_line = f'<div style="margin-top:2px">{tend_html}</div>' if tend_html else ""
    fav_line  = f'<div style="margin-top:2px">{fav_diff}</div>' if fav_diff else ""
    return (f'<div class="sc-info">{best_badge}'
            f'<div class="sc-brand">{station_name}</div>'
            f'<div class="sc-addr">{s(row.get(COL_ADRESSE,""))}</div>'
            f'<div class="sc-meta">{dist_txt}{cp_ville} {open_s}</div>'
            f'{svcs_line}{eco_line}{tend_line}{fav_line}</div>')

def _build_nav_html(g: str, w: str, a: str, share_url: str, fr_html: str) -> str:
    return (f'<div class="sc-nav">'
            f'<a href="{g}" target="_blank" class="nav-a na-gmaps">🗺️ Maps</a>'
            f'<a href="{w}" target="_blank" class="nav-a na-waze">🚗 Waze</a>'
            f'<a href="{a}" target="_blank" class="nav-a na-apple">Apple</a>'
            f'{fr_html}</div>')


def _render_card_expander(row: dict, carb_col: str, sid: str, prix: float, sb) -> None:
    """Expander de la carte : horaires, services, ⑫ historique, ⑫ alerte."""
    tabs_labels = ["🕐 Horaires & Services", "📈 Historique", "🔔 Alerte prix"]
    tab_h, tab_hist, tab_alert = st.tabs(tabs_labels)

    with tab_h:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🕐 Horaires**")
            st.markdown(hours_html(row.get(COL_HORAIRES, "")), unsafe_allow_html=True)
        with c2:
            st.markdown("**🛎️ Services**")
            all_sv = sl(row.get(COL_SERVICES))
            if all_sv:
                badges = "".join(
                    f'<span class="{SVC.get(sv,(sv,"bg-w"))[1]}">'
                    f'{SVC.get(sv,(sv,"bg-w"))[0]} {sv}</span><br>'
                    for sv in all_sv if sv in SVC)
                st.markdown(badges or '<span style="opacity:.5;font-size:.8rem">Aucun</span>',
                            unsafe_allow_html=True)
            else:
                st.caption("Non renseignés")

    with tab_hist:
        # Sprint 3 : historique via prix_historique Supabase
        _carb_labels = {
            "gazole": "Gazole", "sp95": "SP95", "sp98": "SP98",
            "e10": "E10", "e85": "E85", "gplc": "GPLc"
        }
        render_historique_prix(
            station_id=str(sid),
            carb_col=carb_col,
            label_carb=_carb_labels.get(carb_col, carb_col.upper())
        )

    with tab_alert:
        # ⑫ Alerte prix
        alerts = st.session_state.get(KEY_ALERTS, {})
        seuil_actuel = alerts.get(str(sid), {}).get(carb_col)
        if seuil_actuel:
            st.markdown(f'<div class="alert-row">Seuil actif : <b>{seuil_actuel:.3f}€</b></div>',
                        unsafe_allow_html=True)
            if st.button("🗑️ Supprimer l'alerte", key=f"rm_al_{sid}"):
                remove_prix_alert(str(sid), carb_col); st.rerun()
        else:
            seuil_val = st.number_input(
                f"Me prévenir quand ≤ (€/L)",
                min_value=0.5, max_value=5.0,
                value=round(max(prix - 0.05, 0.5), 3),
                step=0.010, format="%.3f",
                key=f"alert_seuil_{sid}")
            if st.button(f"🔔 Activer l'alerte à {seuil_val:.3f}€", key=f"set_al_{sid}"):
                add_prix_alert(str(sid), carb_col, seuil_val)
                st.success(f"✅ Alerte activée à {seuil_val:.3f}€")
                st.rerun()


def render_card(row: dict, carb_col: str, ulat: float, ulon: float,
                moy: float, idx: int = 0, sb=None) -> None:
    """v30 — Station card premium : left border coloré + prix monospace.

    Layout 3 colonnes : [price-pill | info | nav]
    La couleur du left-border et du pill change selon cheap/avg/exp.
    """
    pc   = f"{carb_col}_prix"
    prix = row.get(pc)
    if prix is None: return

    pf            = float(prix)
    cls           = price_cls(pf, moy)
    fr_text, fr_style = freshness(row.get(f"{carb_col}_maj"))
    fr_html  = f'<div class="sc-fr" style="{fr_style}">{fr_text}</div>'

    slat, slon = _resolve_coords(row, ulat, ulon)
    d          = _resolve_distance(row, slat, slon, ulat, ulon)

    tank      = st.session_state.get(KEY_TANK_CAP, 50)
    fill      = st.session_state.get(KEY_FILL_PCT, 20)
    pmax      = st.session_state.get(KEY_PRIX_MAX, moy)
    mode_cout = st.session_state.get(KEY_MODE_COUT, "simple")
    litres      = litres_a_faire(tank, fill)
    litres_calc = litres if litres > 0 else tank  # réservoir plein → coût plein théorique
    conso       = get_conso()
    detour_d    = float(row.get(COL_DISTANCE) or 0)
    cout        = (cout_reel_fn(pf, detour_d, litres_calc, conso)
                   if mode_cout == "reel" else round(litres_calc * pf, 2))

    brand        = detect_brand(row)
    station_name = brand or s(row.get(COL_ADRESSE, ""))
    open_s       = open_badge(row)
    sid          = str(row.get(COL_ID, f"{d}-{pf}"))
    best_id      = str(st.session_state.get(KEY_BEST_STATION, ""))
    is_best      = bool(best_id) and sid == best_id
    best_badge   = '<div class="sc-best">🏆 Meilleur choix</div>' if is_best else ""

    # ⑧ Tendance
    prix_j1   = row.get(f"{carb_col}_prix_j1")
    tend_html = prix_tendance_html(pf, float(prix_j1) if prix_j1 else None)

    # ⑫ Favori diff
    fav_diff = fav_prix_diff_html(sid, pf) if is_fav(sid) else ""

    nav_lat = slat if slat else ulat
    nav_lon = slon if slon else ulon
    g   = f"https://www.google.com/maps/dir/?api=1&destination={nav_lat},{nav_lon}"
    w   = f"https://waze.com/ul?ll={nav_lat},{nav_lon}&navigate=yes"
    a   = f"http://maps.apple.com/?daddr={nav_lat},{nav_lon}"
    su  = build_share_url(nav_lat, nav_lon, carb_col, pf)

    price_html = _build_price_html(pf, cls, cout, litres_calc)
    svcs_html  = _build_svcs_html(row)
    eco_html   = _build_eco_html(litres_calc, pf, moy, pmax)
    info_html  = _build_info_html(row, station_name, d, open_s,
                                  best_badge, svcs_html, eco_html, tend_html, fav_diff)
    nav_html   = _build_nav_html(g, w, a, su, fr_html)

    # v30: add class to scard for left-border coloring
    st.markdown(f'<div class="scard {cls}">{price_html}{info_html}{nav_html}</div>',
                unsafe_allow_html=True)

    fav_col, det_col = st.columns([1, 4])
    with fav_col:
        icon = "★" if is_fav(sid) else "☆"
        if st.button(f"{icon} Favori", key=f"fav_{sid}_{idx}", use_container_width=True):
            toggle_fav_supabase(sb, sid, pf); st.rerun()
    with det_col:
        with st.expander("ℹ️ Détails complets", expanded=False):
            _render_card_expander(row, carb_col, sid, pf, sb)



# ═══════════════════════════════════════════════════════════════════════════════
# NAVIGATION MOBILE
# ═══════════════════════════════════════════════════════════════════════════════

def render_bottom_nav(active: str, n_filters: int = 0) -> None:
    """v30 — Bottom nav flottant style pill frosted-glass.

    4 onglets : Stations / Carte / Trajet / Réglages
    Design : fond verre dépoli, onglet actif teal, badge filtres.
    """
    items = [
        ("stations", "⛽", "Stations"),
        ("map",      "🗺️", "Carte"),
        ("trajet",   "🛣️", "Trajet"),
        ("settings", "⚙️", f"Réglages"),
    ]
    # Boutons Streamlit standards (fonctionnels) + CSS overlay pour le style pill
    badge_html = f'<span class="bnav-badge">{n_filters}</span>' if n_filters > 0 else ""
    cols = st.columns(4)
    clicked = None
    for i, (key, icon, label) in enumerate(items):
        with cols[i]:
            extra = f" ({n_filters})" if key == "settings" and n_filters else ""
            btn_label = f"{icon} {label}{extra}"
            if st.button(btn_label, key=f"bnav_{key}", use_container_width=True,
                         type="primary" if key == active else "secondary"):
                clicked = key
    # CSS inline pour l'apparence pill sur desktop/mobile
    st.markdown('<div class="bnav-spacer"></div>', unsafe_allow_html=True)
    if clicked and clicked != active:
        st.session_state[KEY_ACTIVE_TAB] = clicked; st.rerun()

def render_onboarding() -> None:
    """v30 — Écran d'accueil premium avec animation teal."""
    st.markdown("""
<div class="onboard" style="padding:3rem 1rem 2rem">
  <div class="onboard-icon">⛽</div>
  <h2 style="font-size:1.5rem;font-weight:900;margin-bottom:.5rem">
    Trouvez le carburant<br><span style="color:#2dd4bf">le moins cher</span> près de vous
  </h2>
  <p style="max-width:320px;margin:0 auto .5rem">
    Activez votre GPS ou entrez une adresse pour voir<br>
    l'économie disponible autour de vous.
  </p>
  <div style="display:inline-flex;align-items:center;gap:6px;
    background:rgba(45,212,191,0.10);border:1px solid rgba(45,212,191,0.20);
    border-radius:12px;padding:6px 16px;font-size:.78rem;color:#2dd4bf;margin-top:8px">
    🌿 Données temps réel · prix mis à jour toutes les heures
  </div>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CARTE PYDECK
# ═══════════════════════════════════════════════════════════════════════════════

def prepare_map_data(df_d: pd.DataFrame, carb_col: str, pmin: float,
                     pmax: float, u_lat: float, u_lon: float) -> pd.DataFrame:
    """② ③ Version optimisée : detect_brand vectorisé + _open_str appelé 1× par ligne."""
    pc = f"{carb_col}_prix"

    def color(p: float) -> list[int]:
        if pmax == pmin: return [96,165,250,220]
        r = (p - pmin) / (pmax - pmin)
        if r < .33: return [34,197,94,230]
        if r < .66: return [245,158,11,230]
        return [239,68,68,230]

    dm = df_d.copy()
    dm["color"]     = dm[pc].astype(float).apply(color)
    dm["price_str"] = dm[pc].astype(float).apply(lambda p: f"{p:.3f}€/L")
    # ② vectorisé
    dm["brand_str"] = detect_brand_series(dm).replace("", "Station")
    dm["dist_str"]  = dm[COL_DISTANCE].apply(lambda d: f"📍 {d:.1f} km" if pd.notna(d) else "")
    # ③ 1 seul appel par ligne
    dm["open_str"]  = dm.apply(lambda r: _open_str(dict(r)), axis=1)
    dm["fr_str"]    = dm[f"{carb_col}_maj"].apply(lambda v: f"Maj : {freshness(v)[0]}")
    dm["svcs_str"]  = dm[COL_SERVICES].apply(lambda v: "  ".join(
        f"{SVC[sv][0]} {sv}" for sv in sl(v) if sv in SVC_PRIORITY and sv in SVC)[:90])
    for col in [COL_ADRESSE, COL_VILLE]:
        dm[col] = dm[col].fillna("") if col in dm.columns else ""
    return dm


def build_deck(dm: pd.DataFrame, user_lat: float, user_lon: float,
               radius: float, dark_mode: bool,
               route_coords: Optional[list] = None) -> pdk.Deck:
    """Carte pydeck avec scatter + texte + PathLayer ORS optionnel."""
    zoom      = 13 if radius <= 5 else (12 if radius <= 10 else (11 if radius <= 20 else 10))
    map_style = CARTO_DARK if dark_mode else CARTO_LIGHT

    scatter = pdk.Layer("ScatterplotLayer",
        data=dm[[COL_LAT,COL_LON,"color","price_str","brand_str",
                 COL_ADRESSE,COL_VILLE,"dist_str","open_str","fr_str","svcs_str"]],
        get_position=[COL_LON,COL_LAT], get_color="color", get_radius=100,
        pickable=True, auto_highlight=True, highlight_color=[249,115,22,255])
    text = pdk.Layer("TextLayer",
        data=dm[[COL_LAT,COL_LON,"price_str"]],
        get_position=[COL_LON,COL_LAT], get_text="price_str",
        get_size=11, get_color=[240,240,240,200], get_pixel_offset=[0,-18], pickable=False)
    user_dot = pdk.Layer("ScatterplotLayer",
        data=pd.DataFrame([{COL_LAT:user_lat,COL_LON:user_lon}]),
        get_position=[COL_LON,COL_LAT], get_color=[249,115,22,255], get_radius=90, pickable=False)

    layers = [scatter, text, user_dot]
    if route_coords and len(route_coords) >= 2:
        layers.insert(0, pdk.Layer("PathLayer",
            data=[{"path":[[c[0],c[1]] for c in route_coords]}],
            get_path="path", get_color=[249,115,22,200], get_width=4,
            width_min_pixels=3, pickable=False))

    tooltip = {
        "html": """
<div style='font-family:DM Sans,system-ui,sans-serif;min-width:210px'>
  <div style='font-weight:800;font-size:.95rem;margin-bottom:3px'>{brand_str}</div>
  <div style='font-size:.78rem;opacity:.8;margin-bottom:6px'>{adresse}, {ville}</div>
  <div style='font-size:1.5rem;font-weight:900;color:#22c55e;margin:5px 0'>{price_str}</div>
  <div style='font-size:.74rem;opacity:.7'>{dist_str} &nbsp;·&nbsp; {open_str}</div>
  <div style='font-size:.7rem;opacity:.6;margin-top:2px'>{fr_str}</div>
  <div style='margin-top:6px;font-size:.72rem;opacity:.8'>{svcs_str}</div>
</div>""",
        "style": {"backgroundColor":"#0e1118","color":"#e2e8f0","borderRadius":"14px",
                  "padding":"12px 15px","boxShadow":"0 12px 40px rgba(0,0,0,.7)",
                  "border":"1px solid rgba(45,212,191,.15)"},
    }
    return pdk.Deck(map_style=map_style,
                    initial_view_state=pdk.ViewState(latitude=user_lat,longitude=user_lon,zoom=zoom,pitch=0),
                    layers=layers, tooltip=tooltip)


# ═══════════════════════════════════════════════════════════════════════════════
# SHOW RESULTS — orchestrateur principal
# ═══════════════════════════════════════════════════════════════════════════════

def _load_and_clean(sb, carb_col: str, user_lat: float, user_lon: float,
                    radius: float) -> tuple[pd.DataFrame, bool]:
    df, via_rpc = load_stations(sb, carb_col, user_lat, user_lon, float(radius))
    if df.empty: return df, via_rpc
    if COL_LAT not in df.columns:
        df[[COL_LAT,COL_LON]] = df[COL_GEOM].apply(lambda g: pd.Series(geom_to_latlon(g)))
    df[COL_LAT] = pd.to_numeric(df[COL_LAT], errors="coerce")
    df[COL_LON] = pd.to_numeric(df[COL_LON], errors="coerce")
    df = df[(df[COL_LAT].notna()) & (df[COL_LON].notna()) & (df[COL_LAT]!=0) & (df[COL_LON]!=0)]
    if COL_DISTANCE not in df.columns:
        df[COL_DISTANCE] = df.apply(
            lambda r: dist_km(user_lat,user_lon,r[COL_LAT],r[COL_LON]) or 9999, axis=1)
    df = df[df[COL_DISTANCE].astype(float) <= float(radius)]
    return df, via_rpc

def _apply_filters(df: pd.DataFrame, filters: tuple, carb_col: str) -> pd.DataFrame:
    f_24h,f_cb,f_ev,f_wash,f_open,brand_group,f_resto,f_wifi,f_dab = filters
    def has(v, svc): return svc in sl(v)
    if f_24h:   df = df[df[COL_AUTOMATE]=="Oui"]
    if f_cb:    df = df[df[COL_SERVICES].apply(lambda v: has(v,"Automate CB 24/24"))]
    if f_ev:    df = df[df[COL_SERVICES].apply(lambda v: has(v,"Bornes électriques"))]
    if f_wash:  df = df[df[COL_SERVICES].apply(lambda v: has(v,"Lavage automatique"))]
    if f_open:  df = df[df.apply(lambda r: is_open_now(dict(r)) is True, axis=1)]
    if f_resto: df = df[df[COL_SERVICES].apply(lambda v: has(v,"Restauration à emporter") or has(v,"Restauration sur place"))]
    if f_wifi:  df = df[df[COL_SERVICES].apply(lambda v: has(v,"Wifi"))]
    if f_dab:   df = df[df[COL_SERVICES].apply(lambda v: has(v,"DAB (Distributeur automatique de billets)"))]
    if brand_group and brand_group != "Toutes":
        allowed = BRAND_GROUPS.get(brand_group,[])
        df = df[df.apply(lambda r: detect_brand(dict(r)) in allowed, axis=1)]
    return df

def _apply_sort(df: pd.DataFrame, sort_by: str, carb_col: str,
                litres: float, conso: float, mode: str) -> tuple[pd.DataFrame, str]:
    """⑩ Utilise score_station() composite à la place du score inline."""
    pc = f"{carb_col}_prix"
    mc = f"{carb_col}_maj"
    df = df.copy()
    # ⑩ Score composite
    df["score"]        = df.apply(lambda r: score_station(dict(r),carb_col,litres,conso,mode), axis=1)
    df["cout_affiche"] = df[pc].astype(float) * litres
    labels = {
        "Prix fiable ↑": ("score", True,  "meilleur choix (qualité + distance)"),
        "Prix ↑":        (pc,      True,  "prix au litre ↑"),
        "Prix ↓":        (pc,      False, "prix au litre ↓"),
        "Récent":        (mc,      False, "mise à jour récente"),
    }
    if sort_by in labels:
        col, asc, label = labels[sort_by]
        return df.sort_values(col, ascending=asc, na_position="last"), label
    return df.sort_values(COL_DISTANCE), "distance"

def _render_decision_summary(df_d: pd.DataFrame, carb_col: str,
                              pmin: float, pmax: float,
                              best: Optional[pd.Series],
                              litres: float) -> None:
    """[B] Résumé décisionnel compact (texte) — remplace bar chart + price_summary.

    Répond à une seule question : quelle est la meilleure option pour ma situation ?
    Source : refactor_notes.md — "Use text, not a dense chart."
    Contenu : écart de prix, top 3 gap, moins chère, verdict détour.
    """
    pc     = f"{carb_col}_prix"
    spread = float(pmax) - float(pmin)
    top3   = df_d.sort_values(pc).head(3)
    top3_gap = (float(top3.iloc[-1][pc]) - float(top3.iloc[0][pc])) if len(top3) >= 2 else 0.0
    eco_total = round(spread * litres, 2)

    if best is not None:
        best_name  = detect_brand(dict(best)) or s(best.get(COL_ADRESSE,""))[:22]
        best_dist  = float(best.get(COL_DISTANCE,0) or 0)
        best_price = float(best.get(pc,pmin))
    else:
        best_name, best_dist, best_price = "—", 0.0, float(pmin)

    # Verdict détour : compare la moins chère vs la plus proche
    closest = df_d.sort_values(COL_DISTANCE).iloc[0] if not df_d.empty else None
    if closest is not None and best is not None:
        c_dist = float(closest.get(COL_DISTANCE,0) or 0)
        c_prix = float(closest.get(pc, pmax))
        conso  = get_conso()
        det_km = max((best_dist - c_dist) * 2, best_dist)
        det_cost = det_km * conso / 100 * best_price
        eco_net  = round((c_prix - best_price) * litres - det_cost, 2)
        is_same  = abs(best_price - c_prix) < 0.003
        if is_same:
            verdict_cls, verdict_text = "ok",   "✅ La moins chère est aussi la plus proche"
        elif eco_net > 0:
            verdict_cls, verdict_text = "ok",   f"✅ Détour rentable · +{eco_net:.2f}€ économisés"
        else:
            verdict_cls, verdict_text = "warn", f"⚠️ Détour non rentable · {eco_net:.2f}€ net"
    else:
        verdict_cls, verdict_text = "info", "ℹ️ Définissez votre position pour le verdict"

    spread_note = ("top 3 quasi identiques" if top3_gap <= 0.005
                   else ("faible dispersion" if spread <= 0.05 else "forte dispersion"))

    st.markdown(f"""
<div class="decision-summary">
  <div class="ds-title">📊 Résumé décisionnel</div>
  <div class="ds-row">
    <span class="ds-label">Écart min→max</span>
    <span class="ds-val" style="color:{'var(--green)' if spread < 0.04 else 'var(--red)'}">
      {spread:.3f} €/L · {spread_note}
    </span>
  </div>
  <div class="ds-row">
    <span class="ds-label">Écart top 3</span>
    <span class="ds-val">{top3_gap:.3f} €/L</span>
  </div>
  <div class="ds-row">
    <span class="ds-label">Moins chère</span>
    <span class="ds-val">{best_name} · {best_dist:.1f} km · {best_price:.3f}€</span>
  </div>
  <div class="ds-row">
    <span class="ds-label">Gain potentiel</span>
    <span class="ds-val" style="color:var(--green)">−{eco_total:.2f}€ sur {litres:.0f}L</span>
  </div>
  <div class="ds-verdict {verdict_cls}">{verdict_text}</div>
</div>""", unsafe_allow_html=True)

def _export_csv(df_d: pd.DataFrame, carb_col: str) -> bytes:
    """Génère un CSV des stations pour téléchargement."""
    pc = f"{carb_col}_prix"
    mc = f"{carb_col}_maj"
    cols_export = [COL_ID,COL_ENSEIGNE,COL_ADRESSE,COL_VILLE,COL_CP,COL_DISTANCE,pc,mc]
    cols_ok     = [c for c in cols_export if c in df_d.columns]
    df_exp      = df_d[cols_ok].copy()
    df_exp["marque"] = detect_brand_series(df_exp) if COL_ENSEIGNE in df_exp.columns else ""
    buf = io.StringIO()
    df_exp.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
    return buf.getvalue().encode("utf-8-sig")



def render_savings_hero(pmin: float, pmax: float, moy: float,
                        litres: float, n_stations: int, carb_name: str) -> None:
    """v30.1 — Savings Hero avec 3 modes : réservoir plein / prix stables / normal."""
    spread     = round(pmax - pmin, 3)
    ref        = litres if litres > 0 else 50.0
    eco_max    = round(spread * ref, 2)
    eco_vs_moy = round((moy - pmin) * ref, 2)

    # ── Mode réservoir plein ────────────────────────────────────────────
    if litres == 0:
        st.markdown(f"""
<div class="savings-hero" style="background:linear-gradient(135deg,#0a1628 0%,#0f2044 50%,#0a1628 100%);border-color:rgba(96,165,250,0.30)">
  <div class="sh-label" style="color:var(--blue)">⛽ Réservoir plein — Prix du marché</div>
  <div class="sh-amount" style="color:var(--blue);font-size:2rem">{pmin:.3f}€<span style="font-size:1rem;font-weight:400;color:var(--text-3)"> /L</span></div>
  <div class="sh-sub">Meilleur prix disponible · <b>{n_stations}</b> stations {carb_name} autour de vous</div>
  <div class="sh-stats">
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--green)">{pmin:.3f}€</div><div class="sh-stat-l">Prix min</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--text-3)">{moy:.3f}€</div><div class="sh-stat-l">Moyenne</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:#f43f5e">{pmax:.3f}€</div><div class="sh-stat-l">Prix max</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--amber)">{spread:.3f}€</div><div class="sh-stat-l">Écart marché</div></div>
  </div>
  <div style="margin-top:10px;font-size:.72rem;color:var(--text-2);border-top:1px solid rgba(255,255,255,0.07);padding-top:8px">
    💡 Ajustez votre niveau de réservoir dans <b>Réglages → Mon véhicule</b> pour voir vos économies potentielles
  </div>
</div>""", unsafe_allow_html=True)
        return

    # ── Mode prix stables ───────────────────────────────────────────────
    mode_stable = eco_max < 0.20
    label_eco   = "✅ Prix stables — marché homogène" if mode_stable else "💚 Économie disponible maintenant"
    color_eco   = "#22c55e"
    st.markdown(f"""
<div class="savings-hero">
  <div class="sh-label">{label_eco}</div>
  <div class="sh-amount">{'~' if mode_stable else '−'}{eco_max:.2f}€</div>
  <div class="sh-sub">sur votre plein de <b>{litres:.0f} L</b> en choisissant la moins chère
    vs la plus chère · <b>{n_stations}</b> stations {carb_name}</div>
  <div class="sh-stats">
    <div class="sh-stat"><div class="sh-stat-v" style="color:{color_eco}">{pmin:.3f}€</div><div class="sh-stat-l">Prix min</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--text-3)">{moy:.3f}€</div><div class="sh-stat-l">Moyenne</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:#f43f5e">{pmax:.3f}€</div><div class="sh-stat-l">Prix max</div></div>
    <div class="sh-stat"><div class="sh-stat-v" style="color:var(--blue)">−{eco_vs_moy:.2f}€</div><div class="sh-stat-l">vs moyenne</div></div>
  </div>
</div>""", unsafe_allow_html=True)


def show_results(sb, carb_col: str, carb_name: str,
                 user_lat: float, user_lon: float,
                 radius: float, sort_by: str, filters: tuple,
                 is_mobile: bool, tank_cap: int = 50,
                 dark_mode: bool = True) -> None:
    """Orchestrateur principal : charge → filtre → trie → affiche.

    ⑫ Vérifie les alertes prix au chargement.
    ⑦ Met en cache le prix E85 min pour le comparateur flex-fuel.
    """
    with st.spinner(f"Recherche {carb_name} dans {radius} km…"):
        df, via_rpc = _load_and_clean(sb, carb_col, user_lat, user_lon, radius)

    pc = f"{carb_col}_prix"
    mc = f"{carb_col}_maj"

    if df.empty:
        st.warning("Aucune station trouvée. Essayez d'augmenter le rayon."); return
    df = df[df[pc].notna()]
    if df.empty:
        st.warning("Aucune station dans ce rayon avec des prix renseignés."); return

    # ⑫ Vérification alertes prix
    alerts = check_prix_alerts(df, carb_col)
    for msg in alerts:
        st.toast(msg, icon="🔔")

    # ⑨ Cache prix E85 min pour le comparateur flex-fuel
    if carb_col != "e85":
        df_e85, _ = load_stations(sb, "e85", user_lat, user_lon, float(radius))
        if not df_e85.empty and "e85_prix" in df_e85.columns:
            e85_min = df_e85["e85_prix"].dropna().astype(float).min()
            st.session_state["best_e85_prix_cache"] = e85_min if not pd.isna(e85_min) else None
        else:
            st.session_state["best_e85_prix_cache"] = None

    n_before = len(df)
    df = _apply_filters(df, filters, carb_col)
    if df.empty:
        st.warning("Aucune station avec ces filtres. Essayez d'en désactiver certains."); return
    if 0 < len(df) <= 3 < n_before:
        st.warning(f"⚠️ Filtres restrictifs — seulement {len(df)} station(s).")

    tank_s   = st.session_state.get(KEY_TANK_CAP, tank_cap)
    fill_s   = st.session_state.get(KEY_FILL_PCT, 20)
    litres_s = litres_a_faire(tank_s, fill_s)
    conso_s  = get_conso()
    mode     = st.session_state.get(KEY_MODE_COUT, "simple")

    df_d, sort_label = _apply_sort(df, sort_by, carb_col, litres_s, conso_s, mode)

    pv   = df_d[pc].astype(float)
    moy  = pv.mean()
    pmin, pmax = pv.min(), pv.max()
    st.session_state.update({KEY_PRIX_MIN:pmin, KEY_PRIX_MAX:pmax, KEY_PRIX_MOY:moy})

    best = None
    if not df_d.empty:
        best = df_d.sort_values("score").iloc[0]
        st.session_state[KEY_BEST_STATION] = str(best.get(COL_ID,""))
    else:
        st.session_state[KEY_BEST_STATION] = ""

    dm     = prepare_map_data(df_d, carb_col, pmin, pmax, user_lat, user_lon)
    deck   = build_deck(dm, user_lat, user_lon, radius, dark_mode)
    legend = ('<div class="map-legend">🟢 moins cher &nbsp;·&nbsp; 🟡 moyen &nbsp;·&nbsp; 🔴 plus cher &nbsp;·&nbsp; 🟠 vous</div>')
    n_filters = sum(bool(f) for f in filters[:5])

    def list_sans_best(dfd):
        if best is not None and COL_ID in dfd.columns:
            return dfd[dfd[COL_ID].astype(str) != str(best.get(COL_ID,""))]
        return dfd

    # ── MOBILE ────────────────────────────────────────────────────────────────
    if is_mobile:
        active_view = st.session_state.get(KEY_ACTIVE_TAB, "stations")

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
            fav_ids = st.session_state.get(KEY_FAVORITES, set())
            if not fav_ids:
                st.markdown('<div class="onboard"><div class="onboard-icon">⭐</div>'
                            '<h2>Aucun favori</h2>'
                            '<p>Appuyez sur ☆ Favori sous une station pour l\'épingler ici.</p></div>',
                            unsafe_allow_html=True)
                return
            if COL_ID not in df_d.columns: st.info("Identifiants manquants."); return
            fav_df = df_d[df_d[COL_ID].astype(str).isin(fav_ids)]
            if fav_df.empty: st.info("Vos favoris ne sont pas dans le rayon actuel."); return
            for i, (_, r) in enumerate(fav_df.iterrows()):
                render_card(dict(r), carb_col, user_lat, user_lon, moy, i, sb=sb)
            return

        # v30: Savings Hero banner — l'économie visible en 1 seconde
        render_savings_hero(pmin, pmax, moy, litres_s, len(df_d), carb_name)
        if best is not None:
            render_best_deal(dict(best), carb_col, user_lat, user_lon, pmax)
        flt = (f" · <span style='color:var(--accent)'>{n_filters} filtre(s)</span>" if n_filters else "")
        st.markdown(
            f'<div class="sbar"><span class="sdot sdot-g"></span>'
            f'<b style="color:var(--text)">{len(df_d)}</b> stations · '
            f'<span style="color:var(--text-3)">{sort_label}</span>{flt}</div>',
            unsafe_allow_html=True)
        with st.expander("🛢️ Réservoir & détour", expanded=False):
            render_vehicle_settings("mob_ts_")
            if best is not None:
                l_ = litres_a_faire(st.session_state.get(KEY_TANK_CAP,50), st.session_state.get(KEY_FILL_PCT,20))
                render_detour_calc(df_d, carb_col, pmin, l_, key_prefix="mob_dtc_")
        for i, (_, r) in enumerate(list_sans_best(df_d).head(30).iterrows()):
            render_card(dict(r), carb_col, user_lat, user_lon, moy, i, sb=sb)

    # ── DESKTOP ───────────────────────────────────────────────────────────────
    # [B] Layout refactorisé (refactor_notes.md) :
    #   - Résumé décisionnel compact (texte) sous la carte, pas de bar chart
    #   - Contrôles véhicule NON dupliqués ici (uniquement dans le panneau Réglages)
    #   - Map sticky gauche, liste scrollable droite
    else:
        tank_    = st.session_state.get(KEY_TANK_CAP, tank_cap)
        litres_s = litres_a_faire(tank_, st.session_state.get(KEY_FILL_PCT, 20))
        status   = "🟢 Temps réel" if via_rpc else "🟡 Fallback"
        st.markdown(
            f'<div class="sbar"><span class="sdot sdot-g"></span>'
            f'{status} · <b style="color:var(--text)">{len(df_d)}</b> stations · '
            f'<b style="color:var(--accent)">{carb_name}</b></div>',
            unsafe_allow_html=True)

        # v30: Savings Hero banner
        render_savings_hero(pmin, pmax, moy, litres_s, len(df_d), carb_name)
        k1, k2 = st.columns(2)
        if litres_s > 0:
            cout_plein = round(litres_s * pmin, 2)
            eco_total  = round((pmax - pmin) * litres_s, 2)
            kpi_pairs  = [
                (k1, f"{cout_plein:.2f}€", f"Coût plein · {litres_s:.0f} L au meilleur prix", "var(--accent)"),
                (k2, f"+{eco_total:.2f}€",  "Économie max vs station la plus chère",           "var(--green)"),
            ]
        else:
            kpi_pairs = [
                (k1, f"{pmin:.3f}€/L",          f"Meilleur prix {carb_name}",    "var(--blue)"),
                (k2, f"{round(pmax-pmin,3):.3f}€", "Écart min → max du secteur", "var(--amber)"),
            ]
        for col_, val_, lbl_, clr_ in kpi_pairs:
            with col_:
                st.markdown(f'''<div class="kpi">
  <div class="kpi-v" style="color:{clr_}">{val_}</div>
  <div class="kpi-l">{lbl_}</div>
</div>''', unsafe_allow_html=True)
        col_map, col_list = st.columns([6, 4])
        with col_map:
            # Map sticky : l'utilisateur garde le contexte spatial en scrollant
            st.markdown('<div class="sticky-map">', unsafe_allow_html=True)
            st.pydeck_chart(deck, use_container_width=True, height=520)
            st.markdown(legend, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("")
            # [B] Résumé décisionnel compact — remplace bar chart + price_summary
            _render_decision_summary(df_d, carb_col, pmin, pmax, best, litres_s)
            st.markdown("")
            st.download_button(
                "⬇️ Exporter les stations (CSV)", data=_export_csv(df_d, carb_col),
                file_name=f"ecoplein_{carb_col}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv", use_container_width=True)

        with col_list:
            if best is not None:
                render_best_deal(dict(best), carb_col, user_lat, user_lon, pmax)
            # ⑫ Alertes prix
            with st.expander("🔔 Alertes prix", expanded=bool(st.session_state.get(KEY_ALERTS))):
                render_alert_panel(df_d, carb_col)
            # [B] Pas de render_vehicle_settings ici — uniquement dans le panneau ☰ Réglages
            st.markdown(f"**📋 {len(df_d)} stations · tri : {sort_label}**")
            for i, (_, r) in enumerate(list_sans_best(df_d).head(25).iterrows()):
                render_card(dict(r), carb_col, user_lat, user_lon, moy, i, sb=sb)


# ═══════════════════════════════════════════════════════════════════════════════
# [A] ONGLET TRAJET UNIQUE — moteur contextuel intelligent
# ─────────────────────────────────────────────────────────────────────────────
# Remplace "En chemin" + "Voyage" (CPO doc — Alternative A + C)
# Architecture :
#   1. Saisie unique départ + destination (+ waypoints optionnels)
#   2. Calcul distance ORS ou vol d'oiseau
#   3. Intent cards orientées outcome (verbes, pas modes persistants)
#   4. Si distance > 250 km → bannière contextuelle + planification suggérée
#   5. Sous-fonctions isolées : _trajet_mode_chemin / _trajet_mode_planifier
# ═══════════════════════════════════════════════════════════════════════════════

_SEUIL_LONG_TRAJET = 250  # km — au-delà : suggestion planification mise en avant


def _stop_now_or_wait(auto_km, df_now, df_later, carb_col, litres, conso,
                      dist_ref: float = 0):
    """Conseil arrêt — tient compte de la distance de référence (simple ou A/R)."""
    pc = f"{carb_col}_prix"
    if dist_ref > 0 and auto_km >= dist_ref * 1.05:
        pct = int(auto_km / dist_ref * 100) if dist_ref else 0
        return {"action": "ok",
                "label": (f"✅ Plein non obligatoire — autonomie {auto_km:.0f} km "
                           f"({pct}% du trajet couvert). Stations opportunistes ci-dessous.")}
    if df_now.empty or df_later.empty:
        return {"action": "now", "label": "⛽ Arrêtez-vous maintenant."}
    px_now   = float(df_now.iloc[0][pc])
    px_later = float(df_later.iloc[0][pc])
    cout_now  = litres * px_now
    km_gap    = max(auto_km * 0.3, 10)
    cout_wait = round(km_gap * conso / 100, 2) * px_now + litres * px_later
    if cout_now <= cout_wait:
        eco = round(cout_wait - cout_now, 2)
        return {"action": "now", "label": f"✅ Arrêtez-vous maintenant — {eco:.2f}€ d'économie vs plus tard."}
    eco = round(cout_now - cout_wait, 2)
    return {"action": "wait", "label": f"⏳ Attendez la prochaine station — {eco:.2f}€ d'économie."}


def _trajet_mode_chemin(sb, dep: dict, arr: dict, route: dict, wps: list,
                        corridor: int, carb_col: str, carb_name: str,
                        dark_mode: bool) -> None:
    """Sous-mode 'Voir stations sur ma route'.
    Stations dans le corridor du trajet — ① point_to_route_dist optimisé.
    ⑪ Multi-waypoints conservés.
    """
    coords   = route.get("coords", []) if route else []
    mid_lat  = (dep["lat"] + arr["lat"]) / 2
    mid_lon  = (dep["lon"] + arr["lon"]) / 2
    r_search = max((route.get("distance_km", 50) if route else 50) / 2 + corridor, 20)
    pc       = f"{carb_col}_prix"

    with st.spinner("Chargement des stations sur le trajet…"):
        df, _ = load_stations(sb, carb_col, mid_lat, mid_lon, min(r_search, 100))
    if df.empty: st.warning("Aucune station trouvée."); return

    if COL_LAT not in df.columns:
        df[[COL_LAT, COL_LON]] = df[COL_GEOM].apply(lambda g: pd.Series(geom_to_latlon(g)))
    df[COL_LAT] = pd.to_numeric(df[COL_LAT], errors="coerce")
    df[COL_LON] = pd.to_numeric(df[COL_LON], errors="coerce")
    df = df[(df[COL_LAT].notna()) & (df[COL_LON].notna()) & (df[pc].notna())]
    if df.empty: st.warning("Aucune station avec prix."); return

    if coords:
        df = stations_on_route(df, coords, corridor)
    else:
        df["detour_km"] = df.apply(
            lambda r: dist_km(dep["lat"], dep["lon"],
                              float(r[COL_LAT]), float(r[COL_LON])) or 999, axis=1)
        df = df[df["detour_km"] <= r_search]
    if df.empty: st.warning("Aucune station dans le corridor."); return

    tank    = st.session_state.get(KEY_TANK_CAP, 50)
    fill    = st.session_state.get(KEY_FILL_PCT, 20)
    conso   = get_conso()
    litres  = litres_a_faire(tank, fill)
    mode    = st.session_state.get(KEY_MODE_COUT, "simple")
    auto_km = calc_autonomie(tank, fill, conso)

    df[COL_DISTANCE] = df.apply(
        lambda r: dist_km(dep["lat"], dep["lon"],
                          float(r[COL_LAT]), float(r[COL_LON])) or 0, axis=1)

    # Sélecteur de tri (identique onglet Stations)
    _sort_opts = ["Prix ↑", "Prix fiable ↑", "Récent", "Détour ↑"]
    if mode == "reel":
        _sort_opts.insert(0, "Coût réel ↑")
    sort_by_rt = st.selectbox(
        "Trier par", _sort_opts, key="rt_sort_by",
        label_visibility="collapsed")

    mc = f"{carb_col}_maj"
    df["cout_affiche"] = df[pc].astype(float) * litres
    if sort_by_rt == "Coût réel ↑" and mode == "reel":
        df["cout_affiche"] = df.apply(
            lambda r: cout_reel_fn(float(r[pc]),
                                   float(r.get("detour_km", r.get(COL_DISTANCE, 0))),
                                   litres, conso), axis=1)
        df = df.sort_values("cout_affiche")
        sort_label = "coût total (trajet inclus)"
    elif sort_by_rt == "Prix fiable ↑":
        df["score"] = df.apply(lambda r: score_station(dict(r), carb_col, litres, conso, mode), axis=1)
        df = df.sort_values("score")
        sort_label = "meilleur choix (prix + fraîcheur)"
    elif sort_by_rt == "Récent":
        df = df.sort_values(mc, ascending=False, na_position="last")
        sort_label = "mise à jour récente"
    elif sort_by_rt == "Détour ↑":
        df = df.sort_values("detour_km", ascending=True)
        sort_label = "détour minimal"
    else:  # Prix ↑
        df = df.sort_values(pc)
        sort_label = "prix au litre ↑"

    pv   = df[pc].astype(float)
    moy  = pv.mean(); pmin = pv.min(); pmax_ = pv.max()

    seuil_now = auto_km * 0.15
    df_now    = df[df[COL_DISTANCE] <= max(seuil_now, 5)].sort_values(pc)
    df_later  = df[df[COL_DISTANCE] >  max(seuil_now, 5)].sort_values(pc)
    _dist_ref = st.session_state.get(KEY_TRAJET_DIST, 0) or 0
    _ar       = st.session_state.get(KEY_TRAJET_AR, False)
    _dist_ref = _dist_ref * (2 if _ar else 1)
    advice    = _stop_now_or_wait(auto_km, df_now, df_later, carb_col, litres, conso,
                                  dist_ref=_dist_ref)
    box_cls   = "stop-now" if advice["action"] == "now" else "stop-wait"
    st.markdown(
        f'<div class="{box_cls}"><div style="font-weight:700;font-size:.88rem">{advice["label"]}</div>'
        f'<div style="font-size:.74rem;opacity:.7;margin-top:4px">'
        f'Autonomie : <b>{auto_km:.0f} km</b> · Réservoir : <b>{fill:.0f}%</b> ({litres:.0f} L à faire)'
        f'</div></div>', unsafe_allow_html=True)

    dm   = prepare_map_data(df, carb_col, pmin, pmax_, dep["lat"], dep["lon"])
    deck = build_deck(dm, dep["lat"], dep["lon"], 50, dark_mode, route_coords=coords)
    st.markdown(f"**{len(df)} stations · {carb_name} · tri : {sort_label}**")
    st.pydeck_chart(deck, use_container_width=True, height=300)
    st.markdown(
        '<div class="map-legend">🟢 moins cher · 🟡 moyen · 🔴 plus cher · 🟠 départ · — trajet</div>',
        unsafe_allow_html=True)

    if wps and len(wps) > 2:
        wp_names = [w.get("label", "?")[:20] for w in wps[1:-1]]
        st.markdown(f"🔵 Étapes : **{' → '.join(wp_names)}**")

    for i, (_, r) in enumerate(df.head(20).iterrows()):
        rd = dict(r)
        rd[COL_DISTANCE] = rd.get("detour_km", rd.get(COL_DISTANCE, 0))
        render_card(rd, carb_col, dep["lat"], dep["lon"], moy, i, sb=sb)


def _trajet_mode_planifier(sb, dep: dict, arr: dict, route: dict,
                            carb_col: str, carb_name: str) -> None:
    """Sous-mode 'Planifier mes arrêts carburant'.
    Arrêts calculés selon autonomie utile. ⑦ CO₂ total du voyage.
    """
    reserve_pct = st.session_state.get(KEY_VOY_RES, 15)
    tank        = st.session_state.get(KEY_TANK_CAP, 50)
    fill        = st.session_state.get(KEY_FILL_PCT, 20)
    conso       = get_conso()
    auto_utile  = calc_autonomie(tank, max(fill - reserve_pct, 0), conso)
    auto_plein  = calc_autonomie(tank, 100 - reserve_pct, conso)
    pc          = f"{carb_col}_prix"
    coords      = route.get("coords", []) if route else []
    dist_totale = route.get("distance_km", 0)
    duree_min   = route.get("duration_min", 0)

    st.markdown(
        f'<div class="calc-box">🛣️ <b>{dist_totale:.0f} km</b> · ⏱️ {duree_min/60:.1f}h · '
        f'🔋 Autonomie utile : <b>{auto_utile:.0f} km</b></div>',
        unsafe_allow_html=True)

    if dist_totale <= auto_utile:
        st.success(f"✅ Trajet faisable sans arrêt ({auto_utile:.0f} km ≥ {dist_totale:.0f} km).")
        return

    n_arrets   = max(1, math.ceil((dist_totale - auto_utile) / auto_plein))
    px_ref     = st.session_state.get(KEY_PRIX_MIN, 1.9)
    litres_voy = round((dist_totale / 100) * conso, 1)
    co2_voy    = round(litres_voy * CO2_PAR_LITRE.get(carb_col, 2400) / 1000, 1)

    st.markdown(
        f'<div class="calc-box">📊 <b>{n_arrets} arrêt(s)</b> recommandé(s) · '
        f'~{litres_voy:.0f} L consommés · ~{litres_voy * px_ref:.2f}€ estimés</div>',
        unsafe_allow_html=True)
    st.markdown(
        f'<div class="co2-badge" style="margin:6px 0">🌿 Émissions estimées : ~{co2_voy:.1f} kg CO₂</div>',
        unsafe_allow_html=True)

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
                "km":  km_cur,
            })
        km_cur += auto_plein

    st.markdown(f"---\n#### ⛽ Arrêts recommandés — {carb_name}")
    cout_total = 0.0

    for i, arret in enumerate(arrets):
        st.markdown(f"**Arrêt {i+1}** — environ km {arret['km']:.0f}")
        with st.spinner(f"Recherche arrêt {i+1}…"):
            df_a, _ = load_stations(sb, carb_col, arret["lat"], arret["lon"], 20)
        if df_a.empty: st.warning(f"Aucune station pour l'arrêt {i+1}."); continue
        if COL_LAT not in df_a.columns:
            df_a[[COL_LAT, COL_LON]] = df_a[COL_GEOM].apply(
                lambda g: pd.Series(geom_to_latlon(g)))
        df_a[COL_LAT] = pd.to_numeric(df_a[COL_LAT], errors="coerce")
        df_a[COL_LON] = pd.to_numeric(df_a[COL_LON], errors="coerce")
        df_a = df_a[(df_a[COL_LAT].notna()) & (df_a[pc].notna())]
        if df_a.empty: continue
        df_a[COL_DISTANCE] = df_a.apply(
            lambda r: dist_km(arret["lat"], arret["lon"],
                              float(r[COL_LAT]), float(r[COL_LON])) or 999, axis=1)
        df_a     = df_a.sort_values(pc).head(3)
        moy_a    = df_a[pc].astype(float).mean()
        litres_a = litres_a_faire(tank, reserve_pct)
        cout_a   = round(litres_a * float(df_a.iloc[0][pc]), 2)
        cout_total += cout_a
        for j, (_, r) in enumerate(df_a.iterrows()):
            render_card(dict(r), carb_col, arret["lat"], arret["lon"],
                        moy_a, i * 100 + j, sb=sb)
        st.caption(f"Plein recommandé : {litres_a:.0f} L · {cout_a:.2f}€")
        st.markdown("---")

    if cout_total > 0:
        st.markdown(
            f'<div class="calc-box" style="border:1px solid var(--green);margin-top:8px">'
            f'💰 <b>Coût total estimé : {cout_total:.2f}€</b> '
            f'({n_arrets} arrêt(s) · {carb_name} · {conso} L/100)</div>',
            unsafe_allow_html=True)


def tab_trajet(sb, carb_col: str, carb_name: str, dark_mode: bool = True) -> None:
    """[A] Onglet Trajet — moteur contextuel intelligent.

    CPO doc — Alternative A + C :
    - Un seul point d'entrée départ → destination
    - Intent cards orientées outcome (verbes, pas modes)
    - Bannière si trajet long > 250 km, suggestion planification en premier
    - Pas de switch persistant (évite la dette cognitive)
    - L'utilisateur choisit une action, pas une architecture interne
    """
    st.markdown("### 🗺️ Mon trajet")
    ors_key = st.secrets.get("ORS_API_KEY", "")

    # ── Ligne Départ / Arrivée ──────────────────────────────────────
    # GPS bouton uniquement si position connue ET départ non encore choisi
    _has_gps    = KEY_GPS_RESULT in st.session_state
    _dep_done   = "rt_dep_selected" in st.session_state

    # Header Départ : label + bouton GPS inline si dispo
    dep_header_html = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">'                       '<span class="sec-label" style="margin:0">📍 Départ</span>'
    if _has_gps and not _dep_done:
        _gps_lat, _gps_lon = st.session_state[KEY_GPS_RESULT]
        _gps_label = st.session_state.get(KEY_GPS_LABEL, f"{_gps_lat:.4f}, {_gps_lon:.4f}")
    dep_header_html += '</div>'

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(dep_header_html, unsafe_allow_html=True)
        # Bouton GPS compact sous le label, seulement si GPS dispo et pas encore choisi
        if _has_gps and not _dep_done:
            if st.button(f"📍 Ma position : {_gps_label[:28]}{'…' if len(_gps_label)>28 else ''}",
                         key="rt_dep_from_gps", use_container_width=True, type="primary"):
                st.session_state["rt_dep_selected"] = {
                    "label": _gps_label, "lat": _gps_lat, "lon": _gps_lon}
                st.rerun()
            st.markdown(
                '<div style="font-size:.7rem;color:var(--color-text-muted);'
                'text-align:center;margin:2px 0 6px">ou</div>',
                unsafe_allow_html=True)
        dep_info = address_autocomplete_field(
            label="📍 Départ",
            key="rt_dep",
            placeholder="Ville, adresse ou code postal…",
            selected_key="rt_dep_selected",
            show_label=False,
        )

    with c2:
        arr_info = address_autocomplete_field(
            label="🏁 Arrivée",
            key="rt_arr",
            placeholder="Ville, adresse ou code postal…",
            selected_key="rt_arr_selected",
        )

    use_waypoints = st.checkbox("➕ Ajouter des étapes intermédiaires", key="rt_use_wp")
    wp_infos = []
    if use_waypoints:
        n_wp    = st.select_slider("Nombre d'étapes", options=[1, 2, 3], key="rt_n_wp")
        wp_cols = st.columns(n_wp)
        for i, col in enumerate(wp_cols):
            with col:
                wp_info = address_autocomplete_field(
                    label=f"Étape {i+1}",
                    key=f"rt_wp_{i}",
                    placeholder="Ex : Reims…",
                    selected_key=f"rt_wp{i}_selected",
                )
                wp_infos.append(wp_info)

    _deps_ok = "rt_dep_selected" in st.session_state
    _arrs_ok = "rt_arr_selected" in st.session_state
    if not _deps_ok or not _arrs_ok:
        _missing = []
        if not _deps_ok: _missing.append("départ")
        if not _arrs_ok: _missing.append("arrivée")
        st.markdown(
            f'<div class="intent-card" style="opacity:.6;font-size:.8rem;text-align:center;">' +
            f'Renseignez le {" et le ".join(_missing)} pour continuer</div>',
            unsafe_allow_html=True,
        )

    # ── Options trajet ────────────────────────────────────────────────
    co1, co2 = st.columns(2)
    with co1:
        aller_retour = st.checkbox(
            "↩️ Aller / retour", key=KEY_TRAJET_AR,
            help="Double la distance de référence pour les calculs d'autonomie")
    with co2:
        evite_auto = st.checkbox(
            "🛣️ Éviter autoroutes / péages", key=KEY_TRAJET_EVITE,
            help="Calcule aussi l'itinéraire via nationales")

    if _deps_ok and _arrs_ok and st.button("🔍 Calculer le trajet", type="primary",
                                            key="btn_rt", use_container_width=True):
        dep_info = st.session_state["rt_dep_selected"]
        arr_info = st.session_state["rt_arr_selected"]

        waypoints = [dep_info] + [w for w in wp_infos if w is not None] + [arr_info]

        st.session_state["rt_dep_data"]   = dep_info
        st.session_state["rt_arr_data"]   = arr_info
        st.session_state["rt_waypoints"]  = waypoints
        st.session_state[KEY_TRAJET_MODE] = None
        st.session_state.pop(KEY_ROUTE_ALT, None)

        if not ors_key:
            d_approx = (dist_km(dep_info["lat"], dep_info["lon"],
                                arr_info["lat"], arr_info["lon"]) or 50) * 1.25
            st.session_state["rt_route"]      = {
                "distance_km": d_approx, "duration_min": d_approx / 100 * 60, "coords": []}
            st.session_state[KEY_TRAJET_DIST] = d_approx
        else:
            with st.spinner("Calcul itinéraire ORS…"):
                r_main = (get_ors_route_multi(waypoints, ors_key) if len(waypoints) > 2
                          else get_ors_route(dep_info["lat"], dep_info["lon"],
                                             arr_info["lat"], arr_info["lon"], ors_key,
                                             avoid_highways=False))
                r_alt = get_ors_route(dep_info["lat"], dep_info["lon"],
                                      arr_info["lat"], arr_info["lon"], ors_key,
                                      avoid_highways=True)
            _evite = st.session_state.get(KEY_TRAJET_EVITE, False)
            if _evite and r_alt:
                st.session_state["rt_route"]    = r_alt
                st.session_state[KEY_ROUTE_ALT] = r_main
            else:
                st.session_state["rt_route"]    = r_main
                st.session_state[KEY_ROUTE_ALT] = r_alt
            st.session_state[KEY_TRAJET_DIST] = st.session_state["rt_route"].get("distance_km", 0)

    dep   = st.session_state.get("rt_dep_data")
    arr   = st.session_state.get("rt_arr_data")
    route = st.session_state.get("rt_route")
    wps   = st.session_state.get("rt_waypoints", [])
    dist  = st.session_state.get(KEY_TRAJET_DIST)

    if not dep or not arr:
        st.info("Entrez un départ et une arrivée pour démarrer."); return

    if not route:
        return

    # ── Calculs de référence ─────────────────────────────────────────
    tank      = st.session_state.get(KEY_TANK_CAP, 50)
    fill      = st.session_state.get(KEY_FILL_PCT, 20)
    conso     = get_conso()
    auto_km   = calc_autonomie(tank, fill, conso)
    litres    = litres_a_faire(tank, fill)
    ar        = st.session_state.get(KEY_TRAJET_AR, False)
    dist_ref  = (dist or 0) * (2 if ar else 1)

    # ── Comparatif autoroute / nationale ─────────────────────────────
    route_alt  = st.session_state.get(KEY_ROUTE_ALT)
    evite_auto = st.session_state.get(KEY_TRAJET_EVITE, False)
    route_auto = route_alt if evite_auto else route
    route_nat  = route     if evite_auto else route_alt

    if route_auto and route_nat and route_auto.get("distance_km") and route_nat.get("distance_km"):
        prix_moy = st.session_state.get(KEY_PRIX_MOY, 1.85)
        ess_auto = round(route_auto["distance_km"] / 100 * conso * prix_moy, 2)
        ess_nat  = round(route_nat["distance_km"]  / 100 * conso * prix_moy, 2)
        diff_ess = round(ess_nat - ess_auto, 2)
        diff_min = int(route_nat["duration_min"] - route_auto["duration_min"])
        diff_km  = round(route_nat["distance_km"] - route_auto["distance_km"], 0)
        tag_auto = " ✅" if evite_auto else ""
        tag_nat  = " ✅" if not evite_auto else ""
        eco_line = (
            f'<span style="color:var(--green)">✅ Nationale : +{diff_ess:.2f}€ essence mais +{diff_min} min — économies péages non incluses</span>'
            if diff_ess > 0 else
            f'<span style="color:var(--amber,#f59e0b)">⚠️ Nationale : {abs(diff_ess):.2f}€ moins chère en essence (+{diff_km:.0f} km · +{diff_min} min)</span>'
        )
        st.markdown(
            f'<div class="calc-box" style="font-size:.82rem">'
            f'<b>🛣️ Comparatif d\'itinéraires</b><br>'
            f'<span style="opacity:.75">Autoroute{tag_auto}</span> · '
            f'<b>{route_auto["distance_km"]:.0f} km</b> · '
            f'⏱ {route_auto["duration_min"]/60:.1f}h · ⛽ {ess_auto:.2f}€ essence<br>'
            f'<span style="opacity:.75">Nationale{tag_nat}</span> · '
            f'<b>{route_nat["distance_km"]:.0f} km</b> · '
            f'⏱ {route_nat["duration_min"]/60:.1f}h · ⛽ {ess_nat:.2f}€ essence<br>'
            + eco_line + '</div>',
            unsafe_allow_html=True)
    else:
        n_wps   = max(0, len(wps) - 2)
        wp_txt  = f" · {n_wps} étape(s)" if n_wps > 0 else ""
        ar_txt  = " (A/R)" if ar else ""
        src_txt = "🗺️ ORS" if route.get("coords") else "📐 Estimation"
        st.markdown(
            f'<div class="calc-box">🛣️ <b>{route["distance_km"]:.0f} km{ar_txt}</b> · '
            f'⏱️ {route["duration_min"]/60:.1f}h{wp_txt} · {src_txt}</div>',
            unsafe_allow_html=True)

    # ── Bandeau contextuel autonomie ──────────────────────────────────
    ar_txt = " (A/R)" if ar else ""
    if dist_ref > 0:
        pct_auto = int(auto_km / dist_ref * 100) if dist_ref else 0
        if auto_km >= dist_ref * 1.05:
            b_cls = "stop-wait"
            b_msg = (f"✅ Plein non obligatoire — {auto_km:.0f} km d'autonomie "
                     f"pour {dist_ref:.0f} km{ar_txt} ({pct_auto}% couvert)")
        elif auto_km >= dist_ref * 0.70:
            b_cls = "stop-wait"
            b_msg = (f"⚠️ Autonomie juste — {auto_km:.0f} km pour {dist_ref:.0f} km{ar_txt}. "
                     f"Un arrêt est conseillé.")
        else:
            b_cls = "stop-now"
            b_msg = (f"🛑 Arrêt obligatoire — {auto_km:.0f} km d'autonomie "
                     f"insuffisants pour {dist_ref:.0f} km{ar_txt}.")
        st.markdown(
            f'<div class="{b_cls}"><div style="font-weight:700;font-size:.88rem">{b_msg}</div>'
            f'<div style="font-size:.74rem;opacity:.7;margin-top:3px">'
            f'Réservoir : <b>{fill}%</b> · {litres:.0f} L à faire · Conso : {conso} L/100'
            f'</div></div>',
            unsafe_allow_html=True)

    # ── Corridor + stations ───────────────────────────────────────────
    st.markdown("---")
    corridor = st.slider("📡 Corridor de recherche (km)", 1, 20, 5, key="rt_corridor")
    _trajet_mode_chemin(sb, dep, arr, route, wps, corridor, carb_col, carb_name, dark_mode)

    # Planification auto si arrêt obligatoire
    if dist_ref > 0 and auto_km < dist_ref * 0.95:
        st.markdown("---")
        st.markdown("#### 🗓️ Planification automatique des arrêts")
        _trajet_mode_planifier(sb, dep, arr, route, carb_col, carb_name)


# ═══════════════════════════════════════════════════════════════════════════════
# GPS DESKTOP
# ═══════════════════════════════════════════════════════════════════════════════

def _poll_gps_desktop(user_lat, user_lon):
    if not user_lat and st.session_state.get(KEY_GPS_ASKED):
        attempts = st.session_state.get(KEY_GPS_ATTEMPTS,0)
        with st.spinner(f"Localisation… ({attempts+1}/5)"):
            try: loc = get_geolocation()
            except: loc = None
        if loc and isinstance(loc,dict) and loc.get("coords"):
            c = loc["coords"]
            user_lat = float(c["latitude"]); user_lon = float(c["longitude"])
            st.session_state[KEY_GPS_RESULT]   = (user_lat,user_lon)
            st.session_state[KEY_GPS_ASKED]    = False
            st.session_state[KEY_GPS_ATTEMPTS] = 0
            try:
                rv = requests.get("https://nominatim.openstreetmap.org/reverse",
                    params={"lat":user_lat,"lon":user_lon,"format":"json","addressdetails":1},
                    headers={"User-Agent":"EcoPlein/1.0"},timeout=4).json()
                parts = rv.get("address",{})
                city  = parts.get("city") or parts.get("town") or parts.get("village") or ""
                road  = parts.get("road","")
                st.session_state[KEY_GPS_LABEL] = (f"{road}, {city}".strip(", ") or rv.get("display_name","")[:60])
            except:
                st.session_state[KEY_GPS_LABEL] = f"{user_lat:.4f}, {user_lon:.4f}"
            st.rerun()
        else:
            st.session_state[KEY_GPS_ATTEMPTS] = attempts+1
            if attempts >= 4:
                st.session_state[KEY_GPS_ASKED] = False; st.warning("GPS indisponible. Entrez une adresse.")
            else:
                _time.sleep(1); st.rerun()
    return user_lat, user_lon


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Point d'entrée de l'application EcoPlein v27.

    Séquence :
        1. init_session_state()
        2. Lecture query params partagés (⑥)
        3. Détection mobile/desktop + dark mode
        4. Résolution position utilisateur
        5. Routing vers la vue active

    [C] Navigation mobile : 4 onglets (Stations / Carte / Trajet / Réglages)
    [A] Onglet Trajet remplace "En chemin" + "Voyage"
    [B] Desktop : 2 onglets de trajet (Stations / Trajet) + panneau Réglages
    """
    init_session_state()
    _read_share_params()   # ⑥ lecture URL partagée

    sb = get_supabase()
    # ── Sprint 2 : session anonyme + chargement profil ───────
    get_session_id()
    if not st.session_state.get("_profil_loaded"):
        load_profil_vehicule(sb)
        load_favoris_supabase(sb)
        st.session_state["_profil_loaded"] = True

    screen_w  = streamlit_js_eval(js_expressions="window.innerWidth", key="vp")
    dark_mode = streamlit_js_eval(
        js_expressions="window.matchMedia('(prefers-color-scheme: dark)').matches",
        key="dark_mode")
    is_mobile = isinstance(screen_w, (int, float)) and screen_w < 768
    use_dark  = dark_mode is not False

    # Résolution position
    user_lat, user_lon = None, None
    if KEY_GPS_RESULT in st.session_state:
        user_lat, user_lon = st.session_state[KEY_GPS_RESULT]
    elif KEY_ADDR_SELECTED in st.session_state:
        info       = st.session_state[KEY_ADDR_SELECTED]
        user_lat   = info["lat"]
        user_lon   = info["lon"]

    # ══════════════════════════════════════════════════════════════════════════
    # MOBILE — 4 onglets
    # ══════════════════════════════════════════════════════════════════════════
    if is_mobile:
        active_tab = st.session_state.get(KEY_ACTIVE_TAB, "stations")

        # Header : logo + sélecteur carburant
        h1, h2 = st.columns([1, 3])
        with h1:
            st.markdown(
                '<div style="display:flex;align-items:center;gap:6px;padding:4px 0">'
                '<span style="font-size:1.4rem">⛽</span>'
                '<span style="font-size:.95rem;font-weight:800">Eco'
                '<span style="color:#f97316">Plein</span></span></div>',
                unsafe_allow_html=True)
        with h2:
            # Le sélecteur carburant est affiché sur tous les onglets actifs sauf réglages
            if active_tab in ("stations", "map", "trajet"):
                carb_name = st.selectbox("Carburant", list(CARBURANTS.keys()),
                                         label_visibility="collapsed", key="carb_m")
                carb_col  = CARBURANTS[carb_name]
            else:
                carb_name = st.session_state.get("carb_m", "Gazole")
                carb_col  = CARBURANTS.get(carb_name, "gazole")

        # ── Onglet RÉGLAGES ───────────────────────────────────────────────────
        if active_tab == "settings":
            st.markdown("### ⚙️ Réglages")
            st.markdown('<div class="sec-label">📍 Ma position</div>', unsafe_allow_html=True)
            new_lat, new_lon, _ = location_block()
            if new_lat:
                user_lat, user_lon = new_lat, new_lon

            st.markdown('<div class="sec-label">📏 Rayon de recherche</div>', unsafe_allow_html=True)
            radius = st.select_slider(
                "Rayon", options=[2, 5, 10, 15, 20, 30, 50],
                value=st.session_state.get("radius_m", 10),
                format_func=lambda x: f"{x} km",
                key="radius_m", label_visibility="collapsed")
            st.markdown(
                f'<div class="slider-scale"><span>2 km</span>'
                f'<span>{radius} km</span><span>50 km</span></div>',
                unsafe_allow_html=True)

            st.markdown('<div class="sec-label">🔽 Filtres</div>', unsafe_allow_html=True)
            fc1, fc2 = st.columns(2)
            with fc1:
                f_24h  = st.checkbox("🕐 24h/24",           key="m_24h")
                f_cb   = st.checkbox("💳 CB 24/24",          key="m_cb")
                f_open = st.checkbox("✅ Ouvert maintenant",  key="m_open")
            with fc2:
                f_ev   = st.checkbox("⚡ Bornes élect.",  key="m_ev")
                f_wash = st.checkbox("🚿 Lavage auto.",   key="m_wash")
            brand_group = st.selectbox(
                "Type de marque", ["Toutes"] + list(BRAND_GROUPS.keys()),
                label_visibility="collapsed", key="m_brand")

            st.markdown('<div class="sec-label">↕️ Tri</div>', unsafe_allow_html=True)
            st.radio("Tri", ["Distance", "Prix fiable ↑", "Prix ↑", "Prix ↓", "Récent"],
                     horizontal=True, label_visibility="collapsed", key="sort_m")

            st.markdown('<div class="sec-label">🚗 Mon véhicule</div>', unsafe_allow_html=True)
            render_vehicle_settings("mob_set_vs_")

            st.markdown('<div class="sec-label">🛣️ Planification voyage</div>', unsafe_allow_html=True)
            st.slider("Réserve minimum avant arrêt (%)", 5, 30,
                      int(st.session_state.get(KEY_VOY_RES, 15)), key=KEY_VOY_RES,
                      help="Pourcentage de réservoir minimal avant d'envisager un arrêt")

            st.caption("v30.1 · data.gouv.fr · OpenRouteService · ADEME 2023")
            n_act = sum([bool(st.session_state.get(k))
                         for k in ("m_24h", "m_cb", "m_ev", "m_wash", "m_open")])
            render_bottom_nav("settings", n_act)
            return

        # ── [A] Onglet TRAJET (remplace chemin + voyage) ──────────────────────
        if active_tab == "trajet":
            tab_trajet(sb, carb_col, carb_name, use_dark)
            render_bottom_nav("trajet")
            return

        # ── Onboarding si pas de position ─────────────────────────────────────
        if not user_lat:
            render_onboarding()
            st.markdown('<div class="sec-label">📍 Activer ma position</div>',
                        unsafe_allow_html=True)
            new_lat, new_lon, _ = location_block()
            if new_lat:
                user_lat, user_lon = new_lat, new_lon
                st.session_state[KEY_ACTIVE_TAB] = "stations"
                st.rerun()
            render_bottom_nav(active_tab)
            return

        # ── Onglets STATIONS / CARTE ──────────────────────────────────────────
        radius      = st.session_state.get("radius_m", 10) or 10
        sort_by     = st.session_state.get("sort_m", "Distance") or "Distance"
        f_24h       = bool(st.session_state.get("m_24h",  False))
        f_cb        = bool(st.session_state.get("m_cb",   False))
        f_ev        = bool(st.session_state.get("m_ev",   False))
        f_wash      = bool(st.session_state.get("m_wash", False))
        f_open      = bool(st.session_state.get("m_open", False))
        brand_group = st.session_state.get("m_brand", "Toutes") or "Toutes"
        n_act       = sum([f_24h, f_cb, f_ev, f_wash, f_open])

        show_results(
            sb, carb_col, carb_name, user_lat, user_lon,
            radius, sort_by,
            (f_24h, f_cb, f_ev, f_wash, f_open, brand_group, False, False, False),
            is_mobile=True, dark_mode=use_dark)
        render_bottom_nav(active_tab, n_act)

    # ══════════════════════════════════════════════════════════════════════════
    # DESKTOP — barre de nav 2 onglets + panneau Réglages
    # [B] Stations / Trajet (fusionne En chemin + Voyage)
    # ══════════════════════════════════════════════════════════════════════════
    else:
        # Barre de navigation desktop : Logo | Carburant | Stations | Trajet
        nav1, nav2, nav3, nav4 = st.columns([1.2, 3.5, 1, 1])
        with nav1:
            st.markdown(
                '<div style="display:flex;align-items:center;gap:8px;padding:6px 0">'
                '<span style="font-size:1.5rem">⛽</span>'
                '<span style="font-size:1.05rem;font-weight:900;color:#e2e8f0;'
                'font-family:Plus Jakarta Sans,sans-serif">Eco'
                '<span style="color:#2dd4bf">Plein</span></span>'
                '<span style="font-size:.52rem;background:rgba(45,212,191,.15);'
                'border:1px solid rgba(45,212,191,.25);color:#2dd4bf;border-radius:6px;'
                'padding:1px 5px;font-weight:700">v30</span></div>',
                unsafe_allow_html=True)
        with nav2:
            carb_keys = list(CARBURANTS.keys())
            cur_carb  = st.session_state.get("carb_d", "Gazole")
            carb_name = st.selectbox(
                "Carburant", carb_keys,
                index=carb_keys.index(cur_carb),
                label_visibility="collapsed", key="carb_d")
            carb_col = CARBURANTS[carb_name]
        with nav3:
            active_d = st.session_state.get(KEY_ACTIVE_TAB_D, "stations")
            if st.button("⛽ Stations", use_container_width=True,
                         type="primary" if active_d == "stations" else "secondary",
                         key="nav_st"):
                st.session_state[KEY_ACTIVE_TAB_D] = "stations"; st.rerun()
        with nav4:
            # [A] Bouton unique "Trajet" remplace "En chemin" + "Voyage"
            if st.button("🗺️ Trajet", use_container_width=True,
                         type="primary" if active_d == "trajet" else "secondary",
                         key="nav_trajet"):
                st.session_state[KEY_ACTIVE_TAB_D] = "trajet"; st.rerun()

        active_tab_d = st.session_state.get(KEY_ACTIVE_TAB_D, "stations")

        # Lecture filtres (avant le panneau Réglages qui les re-définit)
        radius      = st.session_state.get("rad_d",   10)    or 10
        sort_by     = st.session_state.get("sort_d",  "Distance") or "Distance"
        f_24h       = bool(st.session_state.get("d_24h",  False))
        f_cb        = bool(st.session_state.get("d_cb",   False))
        f_ev        = bool(st.session_state.get("d_ev",   False))
        f_wash      = bool(st.session_state.get("d_wash", False))
        f_open      = bool(st.session_state.get("d_open", False))
        f_resto     = bool(st.session_state.get("d_resto", False))
        f_wifi      = bool(st.session_state.get("d_wifi",  False))
        f_dab       = bool(st.session_state.get("d_dab",   False))
        brand_group = st.session_state.get("d_brand", "Toutes") or "Toutes"

        # ── Panneau Réglages (expander global) ────────────────────────────────
        # [B] Contrôles véhicule UNIQUEMENT ici — pas dupliqués dans show_results
        with st.expander("☰ Réglages", expanded=False):
            st.markdown("### 🚗 Mon véhicule")
            col_vs, col_recap = st.columns([1.15, 1])
            with col_vs:
                render_vehicle_settings("desk_vs_")
            with col_recap:
                tank_r    = st.session_state.get(KEY_TANK_CAP, 50)
                fill_r    = st.session_state.get(KEY_FILL_PCT, 20)
                conso_r   = get_conso()
                litres_r  = litres_a_faire(tank_r, fill_r)
                auto_r    = calc_autonomie(tank_r, fill_r, conso_r)
                st.markdown(
                    f'<div class="calc-box" style="margin-top:28px;line-height:1.65">'
                    f'⛽ <b>Autonomie : {auto_r:.0f} km</b><br>'
                    f'🪣 À faire : <b>{litres_r:.0f} L</b><br>'
                    f'🚗 <b>{st.session_state.get(KEY_CONSO_PRESET,"Standard")}</b>'
                    f'</div>', unsafe_allow_html=True)

            st.markdown("### 🛣️ Planification")
            st.slider("Réserve minimum avant arrêt (%)", 5, 30,
                      int(st.session_state.get(KEY_VOY_RES, 15)), key=KEY_VOY_RES,
                      help="Pourcentage de réservoir avant de chercher un arrêt")

            st.markdown("### ⛽ Filtres stations")
            f1, f2 = st.columns(2)
            with f1:
                f_24h  = st.checkbox("🕐 24h/24",             key="d_24h",  value=f_24h)
                f_cb   = st.checkbox("💳 CB 24/24",            key="d_cb",   value=f_cb)
                f_ev   = st.checkbox("⚡ Bornes électriques",  key="d_ev",   value=f_ev)
                f_wash = st.checkbox("🚿 Lavage automatique",  key="d_wash", value=f_wash)
            with f2:
                f_open  = st.checkbox("✅ Ouvert maintenant",  key="d_open",  value=f_open)
                f_resto = st.checkbox("🍔 Restauration",       key="d_resto", value=f_resto)
                f_wifi  = st.checkbox("📶 Wifi",               key="d_wifi",  value=f_wifi)
                f_dab   = st.checkbox("💰 DAB",                key="d_dab",   value=f_dab)
            brand_group = st.selectbox(
                "Marque", ["Toutes"] + list(BRAND_GROUPS.keys()), key="d_brand")

        # ── Onglet STATIONS ───────────────────────────────────────────────────
        if active_tab_d == "stations":
            # Barre de position + rayon + tri en haut
            tb1, tb2, tb3 = st.columns([3, 1.5, 1.5])
            with tb1:
                st.markdown('<div class="sec-label">📍 Ma position</div>', unsafe_allow_html=True)
                if user_lat:
                    if (KEY_ADDR_SELECTED in st.session_state
                            and st.session_state[KEY_ADDR_SELECTED].get("label")):
                        pos_label = st.session_state[KEY_ADDR_SELECTED]["label"]
                    elif KEY_GPS_LABEL in st.session_state:
                        pos_label = st.session_state[KEY_GPS_LABEL]
                    else:
                        pos_label = f"{user_lat:.4f}, {user_lon:.4f}"
                    st.markdown(
                        f'<div class="gps-ok" style="padding:4px 8px;font-size:.78rem">'
                        f'✅ {pos_label}</div>', unsafe_allow_html=True)
                    if st.button("🔄 Changer la position", key="pos_reset_d"):
                        st.session_state.pop(KEY_GPS_RESULT, None)
                        st.session_state.pop(KEY_ADDR_SELECTED, None)
                        st.rerun()
                else:
                    c_gps, c_addr = st.columns([1, 2])
                    with c_gps:
                        if st.button("📡 Me localiser", key="gps_btn_d",
                                     use_container_width=True, type="primary"):
                            st.session_state[KEY_GPS_ASKED]    = True
                            st.session_state[KEY_GPS_ATTEMPTS] = 0
                    with c_addr:
                        query = st.text_input(
                            "Adresse ou CP", placeholder="Ex : 59000 ou 5 rue de la Paix…",
                            label_visibility="collapsed", key="addr_d_bar")
                        if query and re.match(r"^\d{5}$", query.strip()):
                            cp_r = search_by_cp(query.strip())
                            if cp_r:
                                st.session_state[KEY_ADDR_SELECTED] = cp_r
                                user_lat = cp_r["lat"]; user_lon = cp_r["lon"]
                                st.rerun()
                        elif query and len(query) >= 3:
                            sugs = search_addresses(query)
                            if sugs:
                                st.session_state[KEY_ADDR_SELECTED] = sugs[0]
                                user_lat = sugs[0]["lat"]; user_lon = sugs[0]["lon"]
                                st.rerun()
            with tb2:
                st.markdown('<div class="sec-label">📏 Rayon</div>', unsafe_allow_html=True)
                radius = st.slider("Rayon", 2, 50, 10, format="%d km",
                                   label_visibility="collapsed", key="rad_d")
            with tb3:
                st.markdown('<div class="sec-label">↕️ Tri</div>', unsafe_allow_html=True)
                sort_by = st.selectbox(
                    "Tri", ["Distance", "Prix fiable ↑", "Prix ↑", "Prix ↓", "Récent"],
                    label_visibility="collapsed", key="sort_d")

        # GPS polling desktop (ne bloque pas si déjà localisé)
        user_lat, user_lon = _poll_gps_desktop(user_lat, user_lon)

        # ── Dispatch contenu ──────────────────────────────────────────────────
        if active_tab_d == "stations":
            if not user_lat or not user_lon:
                st.markdown("""
<div style="text-align:center;padding:3rem 1rem;opacity:.7">
  <div style="font-size:3rem;margin-bottom:1rem">⬆️</div>
  <div style="font-size:1.1rem;font-weight:700">Activez le GPS ou entrez une adresse / code postal</div>
  <div style="font-size:.85rem;margin-top:.5rem">Utilisez les contrôles en haut de page.</div>
</div>""", unsafe_allow_html=True)
                st.pydeck_chart(pdk.Deck(
                    map_style=CARTO_DARK if use_dark else CARTO_LIGHT,
                    initial_view_state=pdk.ViewState(
                        latitude=46.6, longitude=2.3, zoom=5)))
            else:
                show_results(
                    sb, carb_col, carb_name, user_lat, user_lon,
                    radius, sort_by,
                    (f_24h, f_cb, f_ev, f_wash, f_open, brand_group,
                     f_resto, f_wifi, f_dab),
                    is_mobile=False,
                    tank_cap=st.session_state.get(KEY_TANK_CAP, 50),
                    dark_mode=use_dark)

        elif active_tab_d == "trajet":
            # [A] Onglet Trajet unique — moteur contextuel
            tab_trajet(sb, carb_col, carb_name, use_dark)


if __name__ == "__main__":
    main()
