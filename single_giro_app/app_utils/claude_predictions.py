"""
claude_predictions.py
---------------------
Drop-in replacement for genereer_ai_etappe_voorspellingen().

SETUP
-----
1. Add to .streamlit/secrets.toml:
       ANTHROPIC_API_KEY = "sk-ant-..."

2. Add to requirements.txt:
       anthropic>=0.25.0

3. In Sporza_Giro.py, replace the old import/usage — see INTEGRATION below.
"""

import json
import pandas as pd
import streamlit as st
from thefuzz import process

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_rider_context(df: pd.DataFrame) -> str:
    """
    Builds a concise CSV table of startlist riders for the Claude prompt.
    Uses the Renner names from the merged df (= exact startlist names) so
    that Claude's picks match df['Renner'] directly.
    """
    cols = [c for c in ["Renner", "Team", "Prijs", "GC", "SPR", "ITT", "MTN", "Giro_EV"]
            if c in df.columns]
    return (
        df.sort_values("Giro_EV", ascending=False)[cols]
        .to_csv(index=False)
    )


def _normalised_weights(w: dict) -> dict:
    """Normalise a weight dict to sum to 1.0, rounded to 2 decimals."""
    total = sum(w.values()) or 1.0
    return {k: round(v / total, 2) for k, v in w.items()}


def _build_stages_context(etappes: list, custom_weights: dict) -> list:
    """Serialise etappe metadata + normalised weights for the prompt."""
    return [
        {
            "id": e["id"],
            "route": e["route"],
            "km": e["km"],
            "type": e["type"],
            "weights": _normalised_weights(custom_weights.get(str(e["id"]), e["w"])),
        }
        for e in etappes
    ]


def _fuzzy_resolve(name: str, valid_names: list[str]) -> str | None:
    """
    Try to resolve a Claude-returned name to an exact df name.
    Claude sometimes adds accents or slight spelling differences.
    """
    if name in valid_names:
        return name

    # Use thefuzz to find the closest match
    match = process.extractOne(name, valid_names)
    if match and match[1] >= 85:
        return match[0]

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def genereer_claude_etappe_voorspellingen(
    df: pd.DataFrame,
    etappes: list,
    top_x: int,
    custom_weights: dict,
) -> tuple[dict, dict]:
    """
    Claude-powered replacement for genereer_ai_etappe_voorspellingen().

    Parameters
    ----------
    df             : merged DataFrame with startlist riders + stats (output of calculate_giro_ev)
    etappes        : GIRO_ETAPPES list
    top_x          : how many picks per stage
    custom_weights : st.session_state.giro_weights

    Returns
    -------
    predictions : dict  {stage_id_str: [name | None, ...]}   — same shape as before
    reasoning   : dict  {stage_id_str: str}                  — new, one sentence per stage
    """
    # --- dependency check -----------------------------------------------
    try:
        import anthropic
    except ImportError:
        st.error(
            "📦 De Anthropic library ontbreekt. Voeg `anthropic>=0.25.0` toe aan "
            "requirements.txt en herstart de app."
        )
        return {str(e["id"]): [None] * top_x for e in etappes}, {}

    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error(
            "🔑 Geen API key gevonden. Voeg `ANTHROPIC_API_KEY = 'sk-ant-...'` toe "
            "aan `.streamlit/secrets.toml`."
        )
        return {str(e["id"]): [None] * top_x for e in etappes}, {}

    client = anthropic.Anthropic(api_key=api_key)
    valid_names = df["Renner"].tolist()
    rider_csv = _build_rider_context(df)
    stages_list = _build_stages_context(etappes, custom_weights)
    n_stages = len(etappes)

    # --- prompts ------------------------------------------------------------
    system_prompt = (
        "Je bent een elite wieleranalyst voor fantasy wielerspellen. "
        "Je krijgt een rennerlijst (naam, team, prijs in M€, scores GC/SPR/ITT/MTN op 0-100, "
        "verwachte waarde EV) en een lijst etappes met profiel-wegingen.\n\n"
        "Wegingen uitleg:\n"
        "  SPR  = kans voor sprinters / klassieke renners\n"
        "  GC   = kans voor toplklimmers / klassementsrenners\n"
        "  ITT  = voordeel voor tijdrijders\n"
        "  MTN  = kans voor vluchters, punchers en aanvallers\n\n"
        "Regels:\n"
        "- Gebruik ALLEEN namen die exact voorkomen in de rennerlijst.\n"
        "- Kies renners waarvan de dominante score overeenkomt met de hoogste weging.\n"
        "- Geef je antwoord ALLEEN als geldig JSON — geen markdown, geen uitleg buiten de JSON."
    )

    user_prompt = (
        f"Beschikbare renners:\n{rider_csv}\n\n"
        f"Etappes:\n{json.dumps(stages_list, ensure_ascii=False)}\n\n"
        f"Voorspel voor ELKE etappe (id 1 t/m {n_stages}) de top {top_x} renners.\n"
        f"Geef per etappe:\n"
        f"  - \"picks\": lijst van PRECIES {top_x} namen (exacte namen uit de rennerlijst)\n"
        f"  - \"reasoning\": één Nederlandse zin waarom dit type renner deze etappe domineert "
        f"én waarom jouw eerste twee keuzes hier sterk zijn\n\n"
        f"Formaat (alle {n_stages} etappes):\n"
        "{\n"
        '  "1": {"picks": ["Naam1", "Naam2", ...], "reasoning": "..."},\n'
        '  "2": {"picks": [...], "reasoning": "..."},\n'
        f'  ...\n'
        f'  "{n_stages}": {{"picks": [...], "reasoning": "..."}}\n'
        "}"
    )

    # --- API call -----------------------------------------------------------
    with st.spinner("🤖 Claude analyseert alle 21 etappes..."):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = response.content[0].text
        except Exception as exc:
            st.error(f"Claude API fout: {exc}")
            return {str(e["id"]): [None] * top_x for e in etappes}, {}

    # --- parse --------------------------------------------------------------
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        parsed: dict = json.loads(clean)
    except json.JSONDecodeError as exc:
        st.error(f"Claude's antwoord kon niet worden geparsed als JSON: {exc}")
        st.code(raw[:500], language="text")
        return {str(e["id"]): [None] * top_x for e in etappes}, {}

    # --- build output -------------------------------------------------------
    predictions: dict[str, list] = {}
    reasoning: dict[str, str] = {}
    unresolved: list[str] = []

    for etappe in etappes:
        sid = str(etappe["id"])
        stage_data = parsed.get(sid, {})
        raw_picks: list = stage_data.get("picks", [])

        valid_picks: list = []
        for name in raw_picks:
            resolved = _fuzzy_resolve(name, valid_names)
            if resolved:
                valid_picks.append(resolved)
            else:
                unresolved.append(f"etappe {sid}: '{name}'")

        # Pad or trim to exactly top_x
        while len(valid_picks) < top_x:
            valid_picks.append(None)
        predictions[sid] = valid_picks[:top_x]
        reasoning[sid] = stage_data.get("reasoning", "")

    if unresolved:
        st.warning(
            f"⚠️ {len(unresolved)} renner(s) niet herkend en overgeslagen: "
            + ", ".join(unresolved[:5])
            + ("..." if len(unresolved) > 5 else "")
        )

    return predictions, reasoning
