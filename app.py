import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env):
    for _line in open(_env):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from modules.extractor import extract_depot
from modules.sector_lookup import lookup_etf_sektoren, apply_factsheet_data
from modules.factsheet_parser import parse_factsheet
from modules.allocation_engine import compute_portfolio
from modules.sektor_mapping import normalize as norm_sektor
from modules.exporter import export_excel, export_pdf
from config.settings import ASSET_CLASS_COLORS

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Allokat",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Globals ── */
[data-testid="stAppViewContainer"] { background: #F0F4F8; }
[data-testid="block-container"] { padding-top: 1.2rem; max-width: 1400px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: #0B1120 !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label { color: #7A96B0 !important; }
[data-testid="stSidebar"] .stButton button {
  background: rgba(255,255,255,0.07) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  color: #A0C0D8 !important;
  border-radius: 8px !important;
  width: 100% !important;
}

/* ── KPI Cards ── */
.kpi-card {
  background: #FFFFFF;
  border-radius: 14px;
  padding: 20px 22px;
  border: 1px solid #E2E8F0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  margin-bottom: 4px;
}
.kpi-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: #64748B;
  margin-bottom: 6px;
}
.kpi-value {
  font-size: 1.65rem;
  font-weight: 800;
  color: #0F172A;
  letter-spacing: -0.5px;
  line-height: 1.1;
}
.kpi-value.pos { color: #059669; }
.kpi-value.neg { color: #DC2626; }
.kpi-value.warn { color: #D97706; }
.kpi-sub { font-size: 0.74rem; color: #94A3B8; margin-top: 5px; }
.kpi-bar { height: 3px; border-radius: 2px; margin-top: 12px; }
.kpi-bar.blue   { background: linear-gradient(90deg,#3B82F6,#6366F1); }
.kpi-bar.green  { background: linear-gradient(90deg,#10B981,#34D399); }
.kpi-bar.red    { background: linear-gradient(90deg,#EF4444,#F87171); }
.kpi-bar.amber  { background: linear-gradient(90deg,#F59E0B,#FCD34D); }
.kpi-bar.grey   { background: linear-gradient(90deg,#94A3B8,#CBD5E1); }

/* ── Section headings ── */
.sect {
  font-size: 1rem; font-weight: 700; color: #0F172A;
  margin: 28px 0 14px;
  padding-bottom: 10px;
  border-bottom: 2px solid #E2E8F0;
}

/* ── Hero ── */
.hero {
  background: linear-gradient(135deg,#0F172A 0%,#1E3A5F 100%);
  border-radius: 18px;
  padding: 44px 40px 38px;
  margin-bottom: 24px;
}
.hero-title {
  font-size: 2.2rem; font-weight: 800; color: #FFFFFF;
  letter-spacing: -0.8px; margin-bottom: 10px;
}
.hero-sub { font-size: 1.0rem; color: rgba(255,255,255,0.68); line-height: 1.7; margin: 0; }
.hero-chips { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }
.hero-chip {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15);
  border-radius: 20px; padding: 4px 13px;
  font-size: 0.8rem; color: rgba(255,255,255,0.8); font-weight: 500;
}

/* ── Source badges ── */
.badge {
  display: inline-block; font-size: 0.68rem; font-weight: 700;
  padding: 2px 9px; border-radius: 20px; letter-spacing: 0.02em;
}
.badge-db    { background: #DBEAFE; color: #1E40AF; }
.badge-sfd   { background: #DCFCE7; color: #15803D; }
.badge-oracle { background: #FEF3C7; color: #92400E; }
.badge-yf    { background: #DCFCE7; color: #15803D; }
.badge-fs    { background: #FEF9C3; color: #713F12; }
.badge-miss  { background: #FEE2E2; color: #991B1B; }
.badge-dir   { background: #E0E7FF; color: #3730A3; }

/* ── Nav steps ── */
.nav-step {
  padding: 7px 12px; border-radius: 8px; margin-bottom: 3px;
  font-size: 0.81rem; display: flex; align-items: center; gap: 9px;
}
.nav-step.active { background: rgba(99,102,241,0.2); color: #A5B4FC !important; font-weight: 700; }
.nav-step.done   { color: #6A9AB0 !important; }
.nav-step.todo   { color: #4A7090 !important; }

/* ── Sector breakdown card ── */
.sec-card {
  background: #FFFFFF; border-radius: 12px;
  border: 1px solid #E2E8F0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  margin-bottom: 10px; overflow: hidden;
}
.sec-header {
  padding: 12px 16px;
  background: #F8FAFC;
  border-bottom: 1px solid #E2E8F0;
  display: flex; align-items: center; gap: 12px;
}
.sec-name { font-size: 0.9rem; font-weight: 700; color: #0F172A; }
.sec-pct  { font-size: 0.85rem; font-weight: 600; color: #475569; }
.sec-chf  { font-size: 0.78rem; color: #94A3B8; margin-left: auto; }

/* ── Disclaimer ── */
.disclaimer {
  background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;
  padding: 12px 16px; font-size: 0.73rem; color: #94A3B8; margin-top: 24px; line-height: 1.6;
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg,#3B5BDB,#6366F1) !important;
  border: none !important; border-radius: 10px !important;
  font-weight: 700 !important; padding: 0.6rem 1.4rem !important;
  color: #FFFFFF !important;
  box-shadow: 0 4px 14px rgba(59,91,219,0.3) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
  border: 1px solid #E2E8F0 !important;
  border-radius: 12px !important;
  background: white !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

def _init():
    for k, v in {
        "stage": "upload",
        "depots": [],
        "depot_names": [],
        "lookup_results": {},
        "portfolio": None,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ── Sidebar ───────────────────────────────────────────────────────────────────

STAGES = [("upload","Hochladen"),("review","Positionen"),("lookup","Allokation"),("dashboard","Dashboard")]

with st.sidebar:
    st.markdown('<div style="font-size:1.2rem;font-weight:800;color:#C8DFF0;margin-bottom:2px;">Allokat</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.72rem;color:#3A5A70;margin-bottom:16px;">Portfolio-Transparenz</div>', unsafe_allow_html=True)
    st.markdown("---")

    cur = [s[0] for s in STAGES].index(st.session_state.stage) if st.session_state.stage in [s[0] for s in STAGES] else 0
    for i, (key, label) in enumerate(STAGES):
        if i == cur:
            cls, icon = "active", "●"
        elif i < cur:
            cls, icon = "done", "✓"
        else:
            cls, icon = "todo", "○"
        st.markdown(f'<div class="nav-step {cls}"><span style="font-size:0.65rem">{icon}</span>{i+1}. {label}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div style="font-size:0.71rem;color:#4A7090;line-height:1.6;">PDF-Daten werden nur zur Extraktion via Anthropic API übermittelt. Nichts wird gespeichert.</div>', unsafe_allow_html=True)

    if st.session_state.stage != "upload":
        st.markdown("---")
        if st.button("↺  Neu starten"):
            for k in ["depots","depot_names","lookup_results","portfolio"]:
                st.session_state[k] = [] if k in ("depots","depot_names") else ({} if k=="lookup_results" else None)
            st.session_state.stage = "upload"
            st.rerun()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _kpi(label, value, sub="", vcls="", bar="blue"):
    return f"""<div class="kpi-card">
  <div class="kpi-label">{label}</div>
  <div class="kpi-value {vcls}">{value}</div>
  {"<div class='kpi-sub'>"+sub+"</div>" if sub else ""}
  <div class="kpi-bar {bar}"></div>
</div>"""

PALETTE = ["#3B5BDB","#6366F1","#0EA5E9","#10B981","#F59E0B","#EF4444","#8B5CF6","#06B6D4","#84CC16","#F97316","#EC4899","#14B8A6","#6B7280","#A78BFA"]

def _donut(labels, values, title, colors=None, height=320):
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.60,
        marker_colors=colors or PALETTE,
        textinfo="percent",
        textfont=dict(size=10, color="white"),
        hovertemplate="<b>%{label}</b><br>%{percent}<br>CHF %{value:,.0f}<extra></extra>",
        sort=True,
    ))
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=12,color="#0F172A"), x=0.5, y=0.98),
        showlegend=True,
        legend=dict(orientation="v", font=dict(size=9.5,color="#475569"), bgcolor="rgba(0,0,0,0)", x=1.0, y=0.5),
        margin=dict(t=30,b=4,l=4,r=4),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

# Source config: label, badge_class, link_template
# {isin} in template gets replaced
SOURCES = {
    "automatisch":          ("Datenbank",     "badge-db",     "https://www.justetf.com/de/find-etf.html?query={isin}"),
    "swissfunddata":        ("SwissFundData",  "badge-sfd",    "https://www.swissfunddata.ch/sfdpub/de/funds"),
    "oracle":               ("KI-Schätzung",  "badge-oracle", ""),
    "yfinance":             ("Börsendaten",    "badge-yf",     "https://finance.yahoo.com/quote/{isin}"),
    "factsheet":            ("Factsheet",      "badge-fs",     ""),
    "nutzer_bestätigt":     ("Bestätigt",      "badge-yf",     ""),
    "nicht_durchgerechnet": ("Fehlt",          "badge-miss",   ""),
    "direkt":               ("Direkt",         "badge-dir",    ""),
}

def _badge(confidence, isin=""):
    label, cls, tpl = SOURCES.get(confidence, (confidence, "badge-db", ""))
    url = tpl.replace("{isin}", isin) if isin and tpl else tpl
    inner = f'<span class="badge {cls}">{label}</span>'
    if url:
        return f'<a href="{url}" target="_blank" style="text-decoration:none;">{inner} <span style="font-size:0.6rem;color:#94A3B8;">↗</span></a>'
    return inner

# ── Stage: UPLOAD ─────────────────────────────────────────────────────────────

if st.session_state.stage == "upload":
    st.markdown("""
    <div class="hero">
      <div class="hero-title">Allokat</div>
      <p class="hero-sub">Verstehe, wie du wirklich investiert bist.<br>
         Lade deine Depotauszüge hoch — Allokat analysiert Sektoren, Rendite und Klumpenrisiken automatisch.</p>
      <div class="hero-chips">
        <span class="hero-chip">📊 Sektor-Allokation</span>
        <span class="hero-chip">📈 Rendite</span>
        <span class="hero-chip">🏦 Mehrere Depots</span>
        <span class="hero-chip">🔒 Keine Daten gespeichert</span>
        <span class="hero-chip">🇨🇭 CH-Fonds & ETFs</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "PDF-Depotauszüge — mehrere gleichzeitig möglich",
        type="pdf", accept_multiple_files=True,
        help="Unterstützt UBS, CS, Swissquote, Yuh, Raiffeisen, Kantonalbanken und weitere.",
    )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning("⚠️ `ANTHROPIC_API_KEY` nicht gesetzt.")

    if uploaded:
        st.caption(f"{len(uploaded)} Datei(en) ausgewählt")

    if uploaded and st.button("Depotauszüge analysieren", type="primary", use_container_width=True):
        st.session_state.depots = []
        bar = st.progress(0)
        for i, f in enumerate(uploaded):
            with st.spinner(f"Lese {f.name} …"):
                try:
                    r = extract_depot(f.read())
                    r["_filename"] = f.name
                    st.session_state.depots.append(r)
                    st.session_state.depot_names.append(f.name)
                except Exception as e:
                    st.error(f"Fehler bei {f.name}: {e}")
            bar.progress((i+1)/len(uploaded))
        if st.session_state.depots:
            st.session_state.stage = "review"
            st.rerun()

# ── Stage: REVIEW ─────────────────────────────────────────────────────────────

elif st.session_state.stage == "review":
    st.title("Positionen prüfen")
    st.markdown("Prüfe und korrigiere die extrahierten Positionen vor der Auswertung.")

    updated = []
    for idx, depot in enumerate(st.session_state.depots):
        bank = depot.get("bank","Unbekannt")
        st.markdown(f'<div class="sect">🏦 {bank} <span style="font-weight:400;color:#94A3B8;font-size:0.82rem"> · {depot.get("_filename","")}</span></div>', unsafe_allow_html=True)

        c1,c2,c3 = st.columns(3)
        c1.metric("Depot-Nr.", depot.get("depot_nummer") or "—")
        c2.metric("Datum", depot.get("auszugsdatum") or "—")
        c3.metric("Währung", depot.get("waehrung_basis","CHF"))

        pos = depot.get("positionen",[])
        if not pos:
            st.warning("Keine Positionen erkannt.")
            updated.append(depot)
            continue

        df = pd.DataFrame(pos)
        for col in ["isin","bezeichnung","typ","menge","marktwert","waehrung"]:
            if col not in df.columns: df[col] = None

        edited = st.data_editor(
            df[["isin","bezeichnung","typ","menge","marktwert","waehrung"]],
            key=f"ed_{idx}",
            column_config={
                "isin": st.column_config.TextColumn("ISIN", width="medium"),
                "bezeichnung": st.column_config.TextColumn("Bezeichnung", width="large"),
                "typ": st.column_config.SelectboxColumn("Typ", options=["Aktie","ETF","Fonds","Anleihe","Cash","Unbekannt"]),
                "menge": st.column_config.NumberColumn("Stücke", format="%.2f"),
                "marktwert": st.column_config.NumberColumn("Marktwert", format="%.2f"),
                "waehrung": st.column_config.SelectboxColumn("Währung", options=["CHF","EUR","USD","GBP","JPY","SEK","NOK","CAD","AUD"]),
            },
            num_rows="dynamic", use_container_width=True,
        )
        updated.append({**depot, "positionen": edited.to_dict("records")})

    if st.button("Bestätigen und Allokation laden", type="primary", use_container_width=True):
        st.session_state.depots = updated

        seen: set = set()
        to_lookup = []
        for d in updated:
            for p in d.get("positionen",[]):
                isin = str(p.get("isin") or "").strip()
                if isin.lower() in ("nan","none",""): isin=""
                if isin and p.get("typ") in ("ETF","Fonds","Aktie") and isin not in seen:
                    to_lookup.append((isin, p.get("bezeichnung",""), p.get("typ")))
                    seen.add(isin)

        lr_map = {}
        if to_lookup:
            bar = st.progress(0)
            status = st.empty()
            for i,(isin,bez,typ) in enumerate(to_lookup):
                status.markdown(f"Suche Daten für **{bez or isin}** ({typ}) …")
                lr_map[isin] = lookup_etf_sektoren(isin, bez)
                bar.progress((i+1)/len(to_lookup))
            status.empty()

        st.session_state.lookup_results = lr_map
        st.session_state.stage = "lookup"
        st.rerun()

# ── Stage: LOOKUP ─────────────────────────────────────────────────────────────

elif st.session_state.stage == "lookup":
    lr_map = st.session_state.lookup_results
    gefunden = {k:v for k,v in lr_map.items() if v.gefunden}
    fehlt    = {k:v for k,v in lr_map.items() if not v.gefunden}

    st.title("Allokation prüfen")

    n_all, n_f, n_m = len(lr_map), len(gefunden), len(fehlt)
    if n_m == 0 and n_all > 0:
        st.success(f"✅  Alle {n_all} Positionen automatisch erkannt.")
    elif n_f > 0:
        st.info(f"**{n_f} von {n_all}** erkannt — **{n_m}** benötigen ein Factsheet.")
    elif n_all == 0:
        st.info("Keine ETF/Fonds/Aktien gefunden.")

    if gefunden:
        st.markdown('<div class="sect">✅ Automatisch erkannt</div>', unsafe_allow_html=True)
        for isin, lr in sorted(gefunden.items(), key=lambda x: x[1].name or ""):
            # Normalize sector names in LookupResult for display consistency
            lr.sektoren = {norm_sektor(k): v for k,v in lr.sektoren.items()}
            # Merge duplicates after normalization
            merged = {}
            for k,v in lr.sektoren.items():
                merged[k] = merged.get(k, 0) + v
            lr.sektoren = merged

            src_html = _badge(lr.confidence, isin)
            with st.expander(f"**{lr.name or isin}**  ·  `{isin}`", expanded=False):
                col_a, col_b = st.columns([3,1])
                with col_a:
                    st.markdown(src_html, unsafe_allow_html=True)
                    if lr.confidence == "oracle":
                        st.warning("⚠️ KI-Schätzung — diese Daten basieren auf Trainingswissen und können ungenau sein. Für CH-Fonds: Factsheet hochladen für korrekte Zahlen.")
                    if lr.sektoren:
                        sec_df = pd.DataFrame([
                            {"Sektor": k, "Anteil": f"{v*100:.1f}%"}
                            for k,v in sorted(lr.sektoren.items(), key=lambda x:-x[1])
                        ])
                        st.dataframe(sec_df, hide_index=True, use_container_width=True)
                with col_b:
                    if st.button("Zurücksetzen", key=f"rst_{isin}"):
                        lr.gefunden = False; lr.sektoren = {}; lr.confidence = "nicht_durchgerechnet"
                        st.rerun()

    if fehlt:
        st.markdown('<div class="sect">⚠️ Factsheet benötigt</div>', unsafe_allow_html=True)
        st.caption("Für diese Positionen konnte keine Allokation ermittelt werden. Lade das Factsheet-PDF hoch.")
        for isin, lr in fehlt.items():
            with st.expander(f"**{lr.name or isin}**  ·  `{isin}`", expanded=True):
                col_l, col_r = st.columns([2,1])
                with col_l:
                    fs = st.file_uploader("Factsheet-PDF", type="pdf", key=f"fs_{isin}")
                    if fs:
                        with st.spinner("Lese Factsheet …"):
                            fd = parse_factsheet(fs.read())
                        if fd and (fd.get("sektoren") or fd.get("regionen")):
                            apply_factsheet_data(lr, fd.get("sektoren") or {}, fd.get("regionen") or {}, fd.get("daten_stand","?"))
                            st.success("Sektordaten eingelesen.")
                            st.rerun()
                        else:
                            st.error("Keine Sektordaten gefunden.")
                with col_r:
                    st.caption("Ohne Factsheet zählt die Position zum Gesamtvermögen, aber nicht zur Sektorallokation.")

    st.markdown("")
    if st.button("Dashboard anzeigen", type="primary", use_container_width=True):
        portfolio = compute_portfolio(st.session_state.depots, st.session_state.lookup_results)
        st.session_state.portfolio = portfolio
        st.session_state.stage = "dashboard"
        st.rerun()

# ── Stage: DASHBOARD ──────────────────────────────────────────────────────────

elif st.session_state.stage == "dashboard":
    portfolio = st.session_state.portfolio
    if not portfolio:
        st.error("Keine Portfolio-Daten.")
        st.stop()

    total       = portfolio["total_chf"]
    nicht_pct   = portfolio["nicht_durchgerechnet_pct"]
    rendite_chf = portfolio.get("rendite_chf")
    rendite_pct = portfolio.get("rendite_pct")
    positionen  = portfolio["positionen_detail"]

    st.title("Portfolio")

    # ── KPIs ─────────────────────────────────────────────────────────────────

    k1, k2, k3 = st.columns(3)

    with k1:
        st.markdown(_kpi(
            "Gesamtvermögen", f"CHF {total:,.0f}",
            f"{len(positionen)} Positionen · {len(st.session_state.depots)} Depot(s)",
            bar="blue"
        ), unsafe_allow_html=True)

    with k2:
        banks = list({d.get("bank","?") for d in st.session_state.depots})
        st.markdown(_kpi(
            "Depots", str(len(st.session_state.depots)),
            " · ".join(banks[:2]) + ("…" if len(banks) > 2 else ""),
            bar="blue"
        ), unsafe_allow_html=True)

    with k3:
        nd_pct_str = f"{nicht_pct*100:.1f}%"
        if nicht_pct > 0.1:
            vcls, bar = "neg", "red"
            nd_sub = "nicht durchgerechnet — Factsheets fehlen"
        elif nicht_pct > 0:
            vcls, bar = "warn", "amber"
            nd_sub = "nicht durchgerechnet"
        else:
            vcls, bar = "pos", "green"
            nd_sub = "vollständig erfasst"
            nd_pct_str = "100%"
        st.markdown(_kpi("Datenvollständigkeit", nd_pct_str, nd_sub, vcls=vcls, bar=bar), unsafe_allow_html=True)

    if nicht_pct > 0.05:
        st.warning(f"CHF {portfolio['nicht_durchgerechnet_chf']:,.0f} ({nicht_pct*100:.1f}%) nicht durchgerechnet. Lade Factsheets für vollständige Zahlen.")

    # ── Sektor-Allokation ─────────────────────────────────────────────────────

    st.markdown('<div class="sect">📊 Sektor-Allokation</div>', unsafe_allow_html=True)

    sek = portfolio["sektoren"]

    if sek:
        sek_sorted = dict(sorted(sek.items(), key=lambda x: x[1], reverse=True))
        sek_chf    = {k: v * total for k, v in sek_sorted.items()}

        col_pie, col_bar = st.columns([1, 1.5])

        with col_pie:
            fig_sek = _donut(
                list(sek_sorted.keys()),
                [v * total for v in sek_sorted.values()],
                "Sektoren",
                PALETTE,
            )
            st.plotly_chart(fig_sek, use_container_width=True)

        with col_bar:
            pcts = [v * 100 for v in sek_sorted.values()]
            chfs = [v * total for v in sek_sorted.values()]
            bar_colors = PALETTE[:len(sek_sorted)]

            fig_bar = go.Figure(go.Bar(
                x=pcts, y=list(sek_sorted.keys()),
                orientation="h",
                marker_color=bar_colors,
                marker_line_width=0,
                text=[f"CHF {c:,.0f}  ({p:.1f}%)" for c, p in zip(chfs, pcts)],
                textposition="outside",
                textfont=dict(size=10, color="#475569"),
                hovertemplate="<b>%{y}</b><br>CHF %{customdata:,.0f}<extra></extra>",
                customdata=chfs,
            ))
            fig_bar.update_layout(
                margin=dict(t=8, b=4, l=4, r=130),
                height=max(260, len(sek_sorted) * 33),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showticklabels=False, showgrid=False, zeroline=False,
                           range=[0, max(pcts) * 1.4 if pcts else 100]),
                yaxis=dict(tickfont=dict(size=11, color="#1E293B")),
                bargap=0.32, showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # ── Per-Sektor Holdings (Transparenz) ─────────────────────────────────
        st.markdown('<div class="sect">🔍 Titel pro Sektor</div>', unsafe_allow_html=True)
        st.caption("Welche Positionen sind in welchem Sektor investiert — und wie viel?")

        # Build sector → positions map
        sector_positions: dict[str, list] = {}
        for p in positionen:
            for sektor, anteil in p["sektoren_beitrag"].items():
                contrib = p["marktwert_chf"] * anteil
                if sektor not in sector_positions:
                    sector_positions[sektor] = []
                sector_positions[sektor].append({
                    "bank": p["bank"],
                    "bezeichnung": p["bezeichnung"],
                    "isin": p["isin"],
                    "typ": p["typ"],
                    "marktwert_chf": p["marktwert_chf"],
                    "beitrag_chf": contrib,
                    "anteil_pos": anteil,  # Anteil dieses Sektors in der Position
                })

        for i, (sektor, pct) in enumerate(sek_sorted.items()):
            if sektor not in sector_positions:
                continue
            chf_total_sektor = pct * total
            pos_in_sector = sorted(sector_positions[sektor], key=lambda x: -x["beitrag_chf"])

            color = PALETTE[i % len(PALETTE)]
            with st.expander(
                f"**{sektor}** — CHF {chf_total_sektor:,.0f}  ({pct*100:.1f}%)",
                expanded=False,
            ):
                rows = []
                for hp in pos_in_sector:
                    anteil_sektor = (hp["beitrag_chf"] / chf_total_sektor * 100) if chf_total_sektor else 0
                    anteil_portfolio = (hp["beitrag_chf"] / total * 100) if total else 0
                    rows.append({
                        "Bezeichnung": hp["bezeichnung"],
                        "Typ": hp["typ"],
                        "Bank": hp["bank"],
                        "Beitrag CHF": hp["beitrag_chf"],
                        "Anteil am Sektor": anteil_sektor,
                        "Anteil am Portfolio": anteil_portfolio,
                    })

                df_sec = pd.DataFrame(rows)
                st.dataframe(
                    df_sec,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Bezeichnung": st.column_config.TextColumn(width="large"),
                        "Beitrag CHF": st.column_config.NumberColumn(format="CHF %.0f"),
                        "Anteil am Sektor": st.column_config.NumberColumn(format="%.1f%%"),
                        "Anteil am Portfolio": st.column_config.NumberColumn(format="%.2f%%"),
                    },
                )
    else:
        st.info("Keine Sektordaten verfügbar — lade Factsheets in Schritt 3.")

    # ── Asset-Allokation + Währungen + Banken ─────────────────────────────────

    st.markdown('<div class="sect">🌍 Asset-Allokation, Währungen & Banken</div>', unsafe_allow_html=True)

    c_ak, c_wae, c_ban = st.columns(3)

    ak = portfolio["asset_klassen"]
    with c_ak:
        ak_cols = [ASSET_CLASS_COLORS.get(k,"#94A3B8") for k in ak.keys()]
        st.plotly_chart(_donut(
            list(ak.keys()), [v*total for v in ak.values()],
            "Asset-Klassen", ak_cols, height=290,
        ), use_container_width=True)

    wae = portfolio["waehrungen"]
    with c_wae:
        st.plotly_chart(_donut(
            list(wae.keys()), [v*total for v in wae.values()],
            "Währungen",
            ["#3B5BDB","#0EA5E9","#10B981","#F59E0B","#EF4444","#8B5CF6"],
            height=290,
        ), use_container_width=True)

    ban = portfolio["banken"]
    with c_ban:
        st.plotly_chart(_donut(
            list(ban.keys()), [v*total for v in ban.values()],
            "Nach Bank", PALETTE, height=290,
        ), use_container_width=True)

    # ── Positionen-Tabelle ────────────────────────────────────────────────────

    st.markdown('<div class="sect">📋 Alle Positionen</div>', unsafe_allow_html=True)

    CONF = {
        "automatisch":"Datenbank","swissfunddata":"SwissFundData","oracle":"KI-Schätzung",
        "yfinance":"Börsendaten","factsheet":"Factsheet","nutzer_bestätigt":"Bestätigt",
        "nicht_durchgerechnet":"Fehlt","direkt":"Direkt",
    }
    rows = []
    for p in positionen:
        rows.append({
            "Bank": p["bank"],
            "Bezeichnung": p["bezeichnung"],
            "ISIN": p["isin"],
            "Typ": p["typ"],
            "Marktwert CHF": p["marktwert_chf"],
            "Anteil %": round(p["marktwert_chf"]/total*100, 2) if total else 0,
            "Datenbasis": CONF.get(p["confidence"], p["confidence"]),
        })

    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True, use_container_width=True,
        column_config={
            "Bezeichnung": st.column_config.TextColumn(width="large"),
            "Marktwert CHF": st.column_config.NumberColumn(format="CHF %.0f"),
            "Anteil %": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    # ── Empfehlungen ──────────────────────────────────────────────────────────────

    st.markdown('<div class="sect">💡 Empfehlungen</div>', unsafe_allow_html=True)

    def _make_tips(portfolio):
        tips = []
        sek  = portfolio.get("sektoren", {})
        wae  = portfolio.get("waehrungen", {})
        ak   = portfolio.get("asset_klassen", {})
        total = portfolio.get("total_chf", 1)
        nicht_pct = portfolio.get("nicht_durchgerechnet_pct", 0)
        n_sek = len(sek)
        max_sek_pct = max(sek.values()) if sek else 0
        max_sek_name = max(sek, key=sek.get) if sek else "—"

        # Klumpenrisiko Sektor
        for s, pct in sorted(sek.items(), key=lambda x: -x[1]):
            if pct > 0.35:
                tips.append(("red", "Klumpenrisiko Sektor", f"**{s}** macht {pct*100:.0f}% aus — stark konzentriert. Sektorkorrekturen können 40–60% betragen. Prüfe ob das bewusst so gewählt ist."))
                break
            elif pct > 0.28:
                tips.append(("amber", "Erhöhte Sektorkonzentration", f"**{s}** bei {pct*100:.0f}% — im oberen Bereich. Keine Warnung, aber beachten."))
                break

        # Gute Diversifikation
        if n_sek >= 7 and max_sek_pct < 0.30:
            tips.append(("green", "Gut diversifiziert", f"Portfolio über {n_sek} Sektoren verteilt, kein Sektor über 30% — solide Streuung."))

        # Einzelaktien-Anteil
        aktie_pct = ak.get("Aktie", 0)
        if aktie_pct > 0.4:
            tips.append(("amber", "Hoher Einzelaktien-Anteil", f"{aktie_pct*100:.0f}% Einzeltitel — grösseres Klumpenrisiko als breite ETFs. Überprüfe ob du einzelne Sektoren zu stark gewichtest."))

        # Währungskonzentration
        chf_pct = wae.get("CHF", 0)
        if chf_pct > 0.75:
            tips.append(("amber", "Hohe CHF-Konzentration", f"{chf_pct*100:.0f}% in CHF — typisch für Schweizer Anleger, aber erhöht den Heimatmarktbias. Internationale ETFs prüfen."))
        elif chf_pct < 0.2:
            tips.append(("blue", "Gute Währungsdiversifikation", f"Nur {chf_pct*100:.0f}% in CHF — breite Währungsdiversifikation vorhanden."))

        # Fehlende Bereiche
        if "Schwellenländer" not in str(ak) and "Emerging" not in str(sek):
            if total > 30000:
                tips.append(("blue", "Kein Schwellenmarkt-Exposure", "Emerging Markets (Indien, China, Brasilien etc.) sind nicht vertreten — langfristig wachstumsstarke Region. MSCI EM ETF prüfen."))

        if "Immobilien" not in sek and total > 50000:
            tips.append(("blue", "Kein Immobilien-Exposure", "REITs / Immobilien-ETFs sind nicht im Portfolio. Bieten Inflationsschutz und Diversifikation."))

        # Datenvollständigkeit
        if nicht_pct > 0.15:
            tips.append(("red", "Analyse unvollständig", f"{nicht_pct*100:.0f}% des Portfolios nicht durchgerechnet. Das Bild ist verzerrt — Factsheets hochladen für vollständige Empfehlungen."))

        if not tips:
            tips.append(("green", "Keine kritischen Punkte", "Portfolio sieht auf den ersten Blick ausgewogen aus. Detailcheck beim nächsten Update empfohlen."))

        return tips

    COLOR_MAP = {
        "red":   ("#FEF2F2", "#DC2626", "#EF4444"),
        "amber": ("#FFFBEB", "#D97706", "#F59E0B"),
        "green": ("#F0FDF4", "#15803D", "#22C55E"),
        "blue":  ("#EFF6FF", "#1D4ED8", "#3B82F6"),
    }

    for color, titel, text in _make_tips(portfolio):
        bg, text_col, border = COLOR_MAP[color]
        st.markdown(f"""
    <div style="background:{bg};border-left:4px solid {border};border-radius:0 10px 10px 0;
    padding:14px 18px;margin-bottom:10px;">
    <div style="font-size:0.88rem;font-weight:700;color:{text_col};margin-bottom:3px;">{titel}</div>
    <div style="font-size:0.82rem;color:#374151;line-height:1.5;">{text}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Export ────────────────────────────────────────────────────────────────

    st.markdown('<div class="sect">⬇️ Export</div>', unsafe_allow_html=True)
    e1, e2 = st.columns(2)
    with e1:
        try:
            xl = export_excel(portfolio, st.session_state.depots)
            st.download_button("Excel herunterladen (.xlsx)", xl, "allokat_portfolio.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        except Exception as e:
            st.error(f"Excel: {e}")
    with e2:
        try:
            pdf = export_pdf(portfolio)
            st.download_button("PDF-Report", pdf, "allokat_portfolio.pdf", "application/pdf", use_container_width=True)
        except Exception as e:
            st.error(f"PDF: {e}")

    st.markdown("""<div class="disclaimer">
        Allokat zeigt den Ist-Zustand deines Portfolios basierend auf hochgeladenen Auszügen.
        Keine Anlageberatung. Alle Angaben ohne Gewähr. KI-Schätzungen sind Näherungswerte.
    </div>""", unsafe_allow_html=True)
