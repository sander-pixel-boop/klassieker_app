import streamlit as st
import pandas as pd
import plotly.express as px
import unicodedata
import os
import functools
from thefuzz import process, fuzz
from app_utils.db import init_connection
from datetime import datetime

# --- CONFIGURATIE ---
st.set_page_config(page_title="Sporza Giro Evaluator", layout="wide", page_icon="📊")

if "ingelogde_speler" not in st.session_state:
    st.warning("⚠️ Ga terug naar de Home pagina om in te loggen.")
    st.stop()

speler_naam = st.session_state["ingelogde_speler"]

supabase = init_connection()
TABEL_NAAM = st.secrets.get("TABEL_NAAM", "gebruikers_data_test")

# --- CONSTANTEN ---
GIRO_ETAPPES = list(range(1, 22))  # 21 etappes

# Sporza Giromanager puntensysteem (top 20 per etappe)
SPORZA_GIRO_PUNTEN = {
    1: 100, 2: 80, 3: 70, 4: 60, 5: 50,
    6: 40,  7: 36, 8: 32, 9: 28, 10: 24,
    11: 20, 12: 18, 13: 16, 14: 14, 15: 12,
    16: 10, 17: 8,  18: 6,  19: 4,  20: 2
}
KOPMAN_MULTIPLIER = 2  # Kopman krijgt dubbele punten

# Etappe metadata (type voor context)
ETAPPE_TYPE = {
    1: "Vlak", 2: "Heuvel", 3: "Vlak/Heuvel", 4: "Vlak/Heuvel", 5: "Heuvel",
    6: "Heuvel", 7: "Berg", 8: "Heuvel", 9: "Berg", 10: "Tijdrit",
    11: "Heuvel", 12: "Vlak", 13: "Heuvel", 14: "Berg", 15: "Vlak",
    16: "Berg", 17: "Heuvel", 18: "Heuvel", 19: "Berg", 20: "Berg", 21: "Vlak"
}
ETAPPE_ROUTE = {
    1: "Nessebar - Burgas", 2: "Burgas - V. Tarnovo", 3: "Plovdiv - Sofia",
    4: "Catanzaro - Cosenza", 5: "Praia a Mare - Potenza", 6: "Paestum - Naples",
    7: "Formia - Blockhaus", 8: "Chieti - Fermo", 9: "Cervia - C. alle Scale",
    10: "Viareggio - Massa (TTT)", 11: "Porcari - Chiavari", 12: "Imperia - Novi Ligure",
    13: "Alessandria - Verbania", 14: "Aosta - Pila", 15: "Voghera - Milan",
    16: "Bellinzona - Carì", 17: "Cassano d'Adda - Andalo", 18: "Fai - Pieve di Soligo",
    19: "Feltre - Alleghe", 20: "Gemona - Piancavallo", 21: "Rome - Rome"
}

# Etappe wegingen (voor automatische kopman bepaling)
ETAPPE_WEIGHTS = {
    1: {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0},
    2: {"SPR": 0.3, "GC": 0.3, "ITT": 0.0, "MTN": 0.4},
    3: {"SPR": 0.9, "GC": 0.0, "ITT": 0.0, "MTN": 0.1},
    4: {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4},
    5: {"SPR": 0.1, "GC": 0.6, "ITT": 0.0, "MTN": 0.3},
    6: {"SPR": 0.8, "GC": 0.0, "ITT": 0.0, "MTN": 0.2},
    7: {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1},
    8: {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4},
    9: {"SPR": 0.0, "GC": 0.8, "ITT": 0.0, "MTN": 0.2},
    10: {"SPR": 0.0, "GC": 0.0, "ITT": 1.0, "MTN": 0.0},
    11: {"SPR": 0.2, "GC": 0.4, "ITT": 0.0, "MTN": 0.4},
    12: {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4},
    13: {"SPR": 0.6, "GC": 0.0, "ITT": 0.0, "MTN": 0.4},
    14: {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1},
    15: {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0},
    16: {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1},
    17: {"SPR": 0.1, "GC": 0.5, "ITT": 0.0, "MTN": 0.4},
    18: {"SPR": 0.3, "GC": 0.2, "ITT": 0.0, "MTN": 0.5},
    19: {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1},
    20: {"SPR": 0.0, "GC": 0.9, "ITT": 0.0, "MTN": 0.1},
    21: {"SPR": 1.0, "GC": 0.0, "ITT": 0.0, "MTN": 0.0},
}

# --- HULPFUNCTIES ---
@functools.lru_cache(maxsize=1024)
def normalize_name(text):
    if not isinstance(text, str): return ""
    text = text.lower().strip()
    return "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))

@functools.lru_cache(maxsize=32)
def get_norm_lijst(alle_renners_tuple):
    return {normalize_name(r): r for r in alle_renners_tuple}

@functools.lru_cache(maxsize=2048)
def match_naam_cached(naam, alle_renners_tuple):
    """Gecachte versie van naam matching om dure fuzzy matching te voorkomen."""
    naam_norm = normalize_name(naam)
    bekende = {
        "pogacar": "tadej pogačar", "van der poel": "mathieu van der poel",
        "philipsen": "jasper philipsen", "van aert": "wout van aert",
        "pidcock": "thomas pidcock", "de lie": "arnaud de lie"
    }
    for key, correct in bekende.items():
        if key in naam_norm:
            for r in alle_renners_tuple:
                if correct in normalize_name(r): return r

    norm_lijst = get_norm_lijst(alle_renners_tuple)
    if naam_norm in norm_lijst: return norm_lijst[naam_norm]

    bests = process.extractBests(naam_norm, list(norm_lijst.keys()), scorer=fuzz.token_set_ratio, limit=3)
    if bests and bests[0][1] >= 75:
        return norm_lijst[bests[0][0]]
    return naam

def match_naam(naam, alle_renners):
    """Wrapper voor backwards compatibility en om lists naar tuples te casten voor caching."""
    return match_naam_cached(naam, tuple(alle_renners))

@st.cache_data
def load_stats():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    stats_file = os.path.join(base_dir, "data", "renners_stats.csv")
    if not os.path.exists(stats_file): return pd.DataFrame()
    df = pd.read_csv(stats_file, sep=None, engine='python')
    if 'Naam' in df.columns: df = df.rename(columns={'Naam': 'Renner'})
    for col in ['GC', 'SPR', 'ITT', 'MTN']:
        if col not in df.columns: df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df.drop_duplicates(subset=['Renner'])

@st.cache_data
def load_giro_results():
    """
    Verwacht: giro262/giro_uitslagen.csv
    Kolommen: Stage, Rnk, Rider
    Rnk kan 1-200, DNF, DNS, OTL zijn.
    """
    path = "data/giro262/giro_uitslagen.csv"
    if not os.path.exists(path): return pd.DataFrame()
    try:
        df = pd.read_csv(path, sep=None, engine='python')
        df.columns = df.columns.str.strip().str.title()
        if 'Stage' not in df.columns or 'Rnk' not in df.columns or 'Rider' not in df.columns:
            return pd.DataFrame()
        df['Stage'] = pd.to_numeric(df['Stage'], errors='coerce').dropna().astype(int)
        return df
    except Exception as e:
        st.error(f"Fout bij laden resultaten: {e}")
        return pd.DataFrame()

def bepaal_starters_en_kopman(team_renners, etappe_id, etappe_keuzes, df_stats, n_starters=9,
                              kopman_override=None):
    """
    Bepaalt de 9 starters + kopman voor een etappe.
    Voorspelde renners krijgen prioriteit; kopman = hoogst scorende gestarte renner.
    Als kopman_override is opgegeven (handmatige keuze uit de Bouwer), wordt die gebruikt
    mits de renner daadwerkelijk in de starters zit.
    """
    w = ETAPPE_WEIGHTS.get(etappe_id, {"SPR": 0.25, "GC": 0.25, "ITT": 0.25, "MTN": 0.25})
    s = sum(w.values()) or 1.0
    w = {k: v / s for k, v in w.items()}

    # Score per renner op basis van etappeprofiel
    scores = {}
    for r in team_renners:
        rij = df_stats[df_stats['Renner'] == r]
        if rij.empty:
            scores[r] = 0
        else:
            scores[r] = (
                rij.iloc[0].get('SPR', 0) * w['SPR'] +
                rij.iloc[0].get('GC', 0) * w['GC'] +
                rij.iloc[0].get('ITT', 0) * w['ITT'] +
                rij.iloc[0].get('MTN', 0) * w['MTN']
            )

    eid = str(etappe_id)
    voorspeld = [r for r in etappe_keuzes.get(eid, []) if r and r in team_renners]
    rest = sorted([r for r in team_renners if r not in voorspeld], key=lambda x: -scores.get(x, 0))
    prioriteit = voorspeld + rest

    starters = prioriteit[:n_starters]
    if not starters: return [], None

    # Kopman: gebruik handmatige override als die in de starters zit, anders auto
    if kopman_override and kopman_override in starters:
        kopman = kopman_override
        kopman_bron = "✏️"
    else:
        kopman = max(starters, key=lambda x: scores.get(x, 0))
        kopman_bron = "🤖"

    return starters, kopman, kopman_bron


def bereken_etappe_score(starters, kopman, etappe_id, df_uitslag_etappe, alle_renners):
    """Berekent de totale score voor één etappe."""
    punten_per_renner = {}
    # Cache de lijst van namen in de uitslag om herhaalde .tolist() en tuple conversies te voorkomen
    uitslag_namen_tuple = tuple(df_uitslag_etappe['Renner_Matched'].values)

    for renner in starters:
        # Match naam in uitslag
        gematcht = match_naam_cached(renner, uitslag_namen_tuple)
        rij = df_uitslag_etappe[df_uitslag_etappe['Renner_Matched'] == gematcht]
        if rij.empty:
            punten_per_renner[renner] = {"punten": 0, "positie": None, "kopman": renner == kopman}
            continue

        rank_raw = str(rij.iloc[0]['Rnk']).strip().upper()
        rank = int(rank_raw) if rank_raw.isdigit() else None
        base = SPORZA_GIRO_PUNTEN.get(rank, 0)
        mult = KOPMAN_MULTIPLIER if renner == kopman else 1
        totaal = int(base * mult)

        punten_per_renner[renner] = {
            "punten": totaal,
            "base_punten": base,
            "positie": rank,
            "kopman": renner == kopman,
            "multiplier": mult
        }
    return punten_per_renner


# --- HOOFD UI ---
st.title("📊 Sporza Giromanager Evaluator")
st.markdown("*Vergelijk hoe jouw team scoort etappe per etappe op basis van de echte uitslagen.*")

df_stats = load_stats()
df_results = load_giro_results()
alle_stats_renners = df_stats['Renner'].tolist() if not df_stats.empty else []

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 {speler_naam.capitalize()}")
    st.divider()

    # Teams inladen
    st.markdown("#### 📥 Teams inladen")
    col1, col2 = st.columns(2)

    teams = {}  # naam -> {"renners": [], "keuzes": {}}

    if speler_naam != "gast":
        with col1:
            if st.button("🤖 AI Solver", use_container_width=True):
                res = supabase.table(TABEL_NAAM).select("sporza_giro_team26").eq("username", speler_naam).execute()
                if res.data and res.data[0].get("sporza_giro_team26"):
                    d = res.data[0]["sporza_giro_team26"]
                    st.session_state["eval_ai_team"] = {
                        "renners": d.get("selected_riders", []),
                        "keuzes": d.get("predictions", {str(i): [None]*10 for i in range(1, 22)})
                    }
                    st.success("AI team geladen!")

        with col2:
            if st.button("🛠️ Bouwer", use_container_width=True):
                res = supabase.table(TABEL_NAAM).select("sporza_giro_team26_v2").eq("username", speler_naam).execute()
                if res.data and res.data[0].get("sporza_giro_team26_v2"):
                    d = res.data[0]["sporza_giro_team26_v2"]
                    st.session_state["eval_bouwer_team"] = {
                        "renners":       d.get("team", []),
                        "keuzes":        d.get("etappe_keuzes",  {str(i): [None, None, None] for i in range(1, 22)}),
                        "kopman_keuzes": d.get("kopman_keuzes",  {str(i): None               for i in range(1, 22)}),
                    }
                    st.success("Bouwer team geladen!")
    else:
        st.info("Log in met een account om cloud-opslag te gebruiken.")

    st.divider()
    st.markdown("#### ⚙️ Instellingen")
    n_starters = st.number_input("Starters per etappe", 6, 12, 9)
    toon_details = st.checkbox("Toon puntenopbouw per renner", value=True)

    st.divider()
    st.markdown("#### 📄 Resultaten status")
    if df_results.empty:
        st.warning("Geen `giro262/giro_uitslagen.csv` gevonden.")
        st.markdown("""
        **Formaat:**
        ```
        Stage,Rnk,Rider
        1,1,Pogacar Tadej
        1,2,del Toro Isaac
        1,DNF,Smith John
        ```
        """)
    else:
        gereden = sorted(df_results['Stage'].unique())
        st.success(f"✅ {len(gereden)} etappe(s) ingeladen (E{gereden[0]}–E{gereden[-1]})")


# Bouw teams dict op uit session state
if "eval_ai_team" in st.session_state and st.session_state["eval_ai_team"]["renners"]:
    teams[f"🤖 AI Solver ({speler_naam})"] = st.session_state["eval_ai_team"]
if "eval_bouwer_team" in st.session_state and st.session_state["eval_bouwer_team"]["renners"]:
    teams[f"🛠️ Bouwer ({speler_naam})"] = st.session_state["eval_bouwer_team"]

# --- HOOFD CONTENT ---
if df_results.empty:
    st.info("👆 Voeg `giro262/giro_uitslagen.csv` toe en laad een team in via de zijbalk om te beginnen.")
    st.stop()

if not teams:
    st.info("👈 Laad je AI Solver of Bouwer team in via de zijbalk om je score te zien.")
    st.stop()

# Match rijdersnamen in uitslagen naar stats-namen
@st.cache_data
def prep_uitslag(df_raw, alle_renners):
    df = df_raw.copy()
    df['Renner_Matched'] = df['Rider'].apply(lambda x: match_naam(str(x).strip(), alle_renners))
    return df

df_results_matched = prep_uitslag(df_results, alle_stats_renners)
gereden_etappes = sorted(df_results_matched['Stage'].unique())

# --- SCORE BEREKENING ---
alle_resultaten = []   # per team per etappe: totaalscore
alle_details = []      # per team per etappe per renner: detail

# Cache etappe dataframes to avoid re-filtering in loops
df_etappes_dict = {etappe_id: df_results_matched[df_results_matched['Stage'] == etappe_id] for etappe_id in gereden_etappes}

for team_naam, team_data in teams.items():
    team_renners  = team_data["renners"]
    etappe_keuzes = team_data["keuzes"]
    kopman_keuzes = team_data.get("kopman_keuzes", {})
    cumulatief = 0

    for etappe_id in gereden_etappes:
        df_etappe = df_etappes_dict[etappe_id]

        # Gebruik de handmatige kopman als die beschikbaar is
        kopman_override = kopman_keuzes.get(str(etappe_id))

        starters, kopman, kopman_bron = bepaal_starters_en_kopman(
            team_renners, etappe_id, etappe_keuzes, df_stats, n_starters,
            kopman_override=kopman_override
        )
        if not starters:
            continue

        punten_dict = bereken_etappe_score(starters, kopman, etappe_id, df_etappe, alle_stats_renners)
        etappe_totaal = sum(v["punten"] for v in punten_dict.values())
        cumulatief += etappe_totaal

        alle_resultaten.append({
            "Team":       team_naam,
            "Etappe":     etappe_id,
            "Label":      f"E{etappe_id}",
            "Type":       ETAPPE_TYPE.get(etappe_id, "?"),
            "Route":      ETAPPE_ROUTE.get(etappe_id, ""),
            "Punten":     etappe_totaal,
            "Cumulatief": cumulatief,
            "Kopman":     kopman,
            "KopmanBron": kopman_bron,
        })

        for renner, info in punten_dict.items():
            alle_details.append({
                "Team":       team_naam,
                "Etappe":     etappe_id,
                "Renner":     renner,
                "Kopman":     "©" if info.get("kopman") else "",
                "Positie":    f"P{info['positie']}" if info.get("positie") else "-",
                "BasePunten": info.get("base_punten", 0),
                "Multiplier": f"x{info.get('multiplier', 1)}" if info.get("kopman") else "-",
                "Punten":     info["punten"],
            })

df_res = pd.DataFrame(alle_resultaten)
df_det = pd.DataFrame(alle_details) if alle_details else pd.DataFrame()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🏆 Klassement & Verloop", "🔍 Etappe Details", "📋 Team Overzicht"])

# ── TAB 1: KLASSEMENT ──────────────────────────────────────────────
with tab1:
    st.subheader("📈 Cumulatief Puntenverloop")

    # Metrics per team
    if not df_res.empty:
        metric_cols = st.columns(len(teams))
        for i, (team_naam, _) in enumerate(teams.items()):
            df_team = df_res[df_res["Team"] == team_naam]
            totaal = df_team["Cumulatief"].max() if not df_team.empty else 0
            laatste = df_team.iloc[-1]["Punten"] if not df_team.empty else 0
            beste_etappe_row = df_team.loc[df_team["Punten"].idxmax()] if not df_team.empty else None
            beste = f"E{int(beste_etappe_row['Etappe'])}: {int(beste_etappe_row['Punten'])}pt" if beste_etappe_row is not None else "-"
            with metric_cols[i]:
                st.metric(
                    label=team_naam,
                    value=f"{int(totaal)} pt",
                    delta=f"Laatste etappe: +{int(laatste)}pt",
                    help=f"Beste etappe: {beste}"
                )

        st.divider()

        # Lijndiagram
        fig = px.line(
            df_res,
            x="Label", y="Cumulatief", color="Team",
            markers=True,
            labels={"Label": "Etappe", "Cumulatief": "Cumulatieve punten"},
            title="Puntenverloop Sporza Giromanager",
            custom_data=["Route", "Type", "Kopman", "Punten"]
        )
        fig.update_traces(
            hovertemplate="<b>%{x}</b> – %{customdata[0]}<br>Type: %{customdata[1]}<br>Kopman: %{customdata[2]}<br>Etappe: +%{customdata[3]}pt<br>Totaal: %{y}pt<extra></extra>"
        )
        fig.update_layout(xaxis=dict(categoryorder="array", categoryarray=[f"E{i}" for i in gereden_etappes]))
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Punten per etappe staafdiagram
        fig2 = px.bar(
            df_res, x="Label", y="Punten", color="Team", barmode="group",
            labels={"Label": "Etappe", "Punten": "Punten"},
            title="Punten per Etappe"
        )
        fig2.update_layout(xaxis=dict(categoryorder="array", categoryarray=[f"E{i}" for i in gereden_etappes]))
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # Pivot tabel
        st.subheader("📊 Punten per Etappe – Overzicht")
        df_pivot = df_res.pivot(index="Team", columns="Label", values="Punten")
        totalen = df_res.groupby("Team")["Punten"].sum().rename("Totaal")
        df_pivot.insert(0, "Totaal", totalen)
        df_pivot = df_pivot.sort_values("Totaal", ascending=False)

        # Kleur hoogste score groen per kolom
        def highlight_max(col):
            is_max = col == col.max()
            return ['background-color: rgba(0,200,100,0.2)' if v else '' for v in is_max]

        st.dataframe(
            df_pivot.style.apply(highlight_max),
            use_container_width=True
        )


# ── TAB 2: ETAPPE DETAILS ─────────────────────────────────────────────
with tab2:
    st.subheader("🔍 Puntenopbouw per Etappe")

    geselecteerde_etappe = st.selectbox(
        "Kies een etappe:",
        options=gereden_etappes,
        format_func=lambda x: f"Etappe {x}: {ETAPPE_ROUTE.get(x, '')} ({ETAPPE_TYPE.get(x, '')})",
        help="Selecteer een etappe om de gedetailleerde puntenopbouw te bekijken."
    )

    if geselecteerde_etappe and not df_det.empty:
        df_etappe_detail = df_det[df_det["Etappe"] == geselecteerde_etappe]

        # Overzicht scores voor deze etappe
        st.markdown("**Scores per Team:**")
        ovz = df_res[df_res["Etappe"] == geselecteerde_etappe][["Team", "Punten", "Kopman"]]
        ovz_cols = st.columns(len(ovz))
        for i, (_, row) in enumerate(ovz.iterrows()):
            with ovz_cols[i]:
                st.metric(row["Team"], f"{int(row['Punten'])} pt", help=f"Kopman: {row['Kopman']}")

        st.divider()

        # Detail per team
        team_tabs = st.tabs(list(teams.keys()))
        for i, team_naam in enumerate(teams.keys()):
            with team_tabs[i]:
                df_t = df_etappe_detail[df_etappe_detail["Team"] == team_naam].copy()
                if df_t.empty:
                    st.info("Geen data voor dit team.")
                    continue

                df_t_display = df_t[["Renner", "Kopman", "Positie", "BasePunten", "Multiplier", "Punten"]]
                df_t_display = df_t_display.sort_values("Punten", ascending=False)

                if toon_details:
                    def kleur_rijen(row):
                        if row["Kopman"] == "©":
                            return ["background-color: rgba(255,215,0,0.15)"] * len(row)
                        if row["Punten"] > 0:
                            return ["background-color: rgba(0,200,100,0.08)"] * len(row)
                        return [""] * len(row)

                    st.dataframe(
                        df_t_display.style.apply(kleur_rijen, axis=1),
                        hide_index=True,
                        use_container_width=True
                    )

                totaal_etappe = df_t["Punten"].sum()
                scorende = df_t[df_t["Punten"] > 0]
                st.markdown(
                    f"**Totaal: {int(totaal_etappe)} pt** &nbsp;|&nbsp; "
                    f"{len(scorende)} renner(s) scoorden punten"
                )


# ── TAB 3: TEAM OVERZICHT ─────────────────────────────────────────────
with tab3:
    st.subheader("📋 Team Samenstelling & Kopmannen per Etappe")
    st.markdown(
        "**✏️** = Handmatig ingesteld in de Bouwer &nbsp;|&nbsp; "
        "**🤖** = Automatisch op basis van etappeprofiel"
    )

    for team_naam, team_data in teams.items():
        team_renners  = team_data["renners"]
        etappe_keuzes = team_data["keuzes"]
        kopman_keuzes = team_data.get("kopman_keuzes", {})

        handmatig_count = sum(1 for v in kopman_keuzes.values() if v)

        with st.expander(f"**{team_naam}** – {len(team_renners)} renners | {handmatig_count} handmatige kopmannen"):
            c_renners, c_kopmannen = st.columns([1, 2])

            with c_renners:
                st.markdown("**Selectie:**")
                for r in sorted(team_renners):
                    st.write(f"- {r}")

            with c_kopmannen:
                st.markdown("**Kopman per gereden etappe:**")
                kopman_data = []
                for eid in gereden_etappes:
                    km_override = kopman_keuzes.get(str(eid))
                    starters, kopman, kopman_bron = bepaal_starters_en_kopman(
                        team_renners, eid, etappe_keuzes, df_stats, n_starters,
                        kopman_override=km_override
                    )
                    etappe_row = df_res[(df_res["Team"] == team_naam) & (df_res["Etappe"] == eid)]
                    score = int(etappe_row["Punten"].values[0]) if not etappe_row.empty else 0
                    kopman_data.append({
                        "Etappe": f"E{eid} – {ETAPPE_ROUTE.get(eid, '')}",
                        "Type":   ETAPPE_TYPE.get(eid, ""),
                        "Kopman": f"{kopman_bron} {kopman}" if kopman else "-",
                        "Score":  score
                    })

                st.dataframe(
                    pd.DataFrame(kopman_data),
                    hide_index=True,
                    use_container_width=True,
                    height=400
                )
