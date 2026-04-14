import io
from collections import Counter

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


st.set_page_config(page_title="IngredientIQ", layout="wide")

# -----------------------------
# STARTER REGULATORY DATABASE
# Replace/extend this later with CosIng CSV or your own cleaned database
# -----------------------------
REGULATORY_DB = {
    "retinol": {
        "eu": "restricted",
        "us": "allowed",
        "india": "allowed",
        "function": "skin conditioning, anti-ageing",
        "claims": ["anti-ageing", "renewal", "fine lines"],
        "notes": "May increase irritation and photosensitivity in some users."
    },
    "niacinamide": {
        "eu": "allowed",
        "us": "allowed",
        "india": "allowed",
        "function": "skin conditioning, brightening, barrier support",
        "claims": ["barrier support", "brightening", "oil balance"],
        "notes": "Generally well tolerated."
    },
    "salicylic acid": {
        "eu": "restricted",
        "us": "allowed",
        "india": "allowed",
        "function": "keratolytic, exfoliant, anti-acne",
        "claims": ["acne care", "oil control", "exfoliation"],
        "notes": "Use-level and product type matter for compliance."
    },
    "hydroquinone": {
        "eu": "restricted",
        "us": "restricted",
        "india": "restricted",
        "function": "skin lightening",
        "claims": ["pigmentation"],
        "notes": "High regulatory caution across markets."
    },
    "parfum": {
        "eu": "allowed",
        "us": "allowed",
        "india": "allowed",
        "function": "fragrance",
        "claims": ["sensory appeal"],
        "notes": "Fragrance can be a common irritation trigger in sensitive users."
    },
    "fragrance": {
        "eu": "allowed",
        "us": "allowed",
        "india": "allowed",
        "function": "fragrance",
        "claims": ["sensory appeal"],
        "notes": "Fragrance can be a common irritation trigger in sensitive users."
    },
    "formaldehyde": {
        "eu": "restricted",
        "us": "restricted",
        "india": "restricted",
        "function": "preservative",
        "claims": ["preservation"],
        "notes": "High scrutiny ingredient."
    },
    "methylisothiazolinone": {
        "eu": "restricted",
        "us": "restricted",
        "india": "restricted",
        "function": "preservative",
        "claims": ["preservation"],
        "notes": "Commonly scrutinized preservative."
    },
    "zinc oxide": {
        "eu": "allowed",
        "us": "allowed",
        "india": "allowed",
        "function": "uv filter, opacifying",
        "claims": ["sun protection"],
        "notes": "Widely used in sunscreens."
    },
    "titanium dioxide": {
        "eu": "allowed",
        "us": "allowed",
        "india": "allowed",
        "function": "uv filter, colorant",
        "claims": ["sun protection"],
        "notes": "Common sunscreen ingredient."
    },
    "triclosan": {
        "eu": "restricted",
        "us": "restricted",
        "india": "restricted",
        "function": "antimicrobial",
        "claims": ["antibacterial"],
        "notes": "Heavily scrutinized in multiple markets."
    }
}

STATUS_SCORES = {
    "allowed": 0,
    "restricted": 3,
    "banned": 6,
    "unknown": 2
}

STATUS_LABELS = {
    "allowed": "Allowed",
    "restricted": "Restricted",
    "banned": "Banned",
    "unknown": "Unknown"
}

# -----------------------------
# HELPERS
# -----------------------------
def normalize_ingredient(name: str) -> str:
    return name.strip().lower()

@st.cache_data(show_spinner=False)
def get_fda_total(ingredient: str) -> int:
    """
    Pull total FAERS reports that mention the ingredient-like product name.
    This is NOT a direct safety verdict; it is just one signal.
    """
    url = "https://api.fda.gov/drug/event.json"
    params = {
        "search": f'patient.drug.medicinalproduct:"{ingredient}"',
        "limit": 1
    }

    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 200:
            return int(r.json().get("meta", {}).get("results", {}).get("total", 0))
        return 0
    except requests.RequestException:
        return 0

@st.cache_data(show_spinner=False)
def get_top_reactions(ingredient: str) -> list[str]:
    url = "https://api.fda.gov/drug/event.json"
    params = {
        "search": f'patient.drug.medicinalproduct:"{ingredient}"',
        "limit": 50
    }

    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code != 200:
            return []

        reactions = []
        for report in r.json().get("results", []):
            for reaction in report.get("patient", {}).get("reaction", []):
                term = reaction.get("reactionmeddrapt")
                if term:
                    reactions.append(term)
        return reactions
    except requests.RequestException:
        return []

def get_regulatory_status(ingredient: str, region: str) -> str:
    key = normalize_ingredient(ingredient)
    data = REGULATORY_DB.get(key)
    if not data:
        return "unknown"
    return data.get(region, "unknown")

def get_metadata(ingredient: str) -> dict:
    return REGULATORY_DB.get(normalize_ingredient(ingredient), {})

def score_fda_signal(total: int) -> int:
    if total > 1_000_000:
        return 4
    if total > 100_000:
        return 3
    if total > 10_000:
        return 2
    if total > 1_000:
        return 1
    return 0

def risk_score(status: str, fda_total: int) -> tuple[int, str]:
    """
    1 = low risk, 10 = high risk
    """
    base = 2 + STATUS_SCORES.get(status, 2)
    fda_component = score_fda_signal(fda_total)
    score = min(10, max(1, base + fda_component))

    if score >= 8:
        label = "High Risk"
    elif score >= 5:
        label = "Moderate Risk"
    else:
        label = "Lower Risk"
    return score, label

def marketability_score(status: str, fda_total: int, metadata: dict) -> tuple[int, str]:
    """
    Higher = easier to position/market, lower regulatory and perception friction
    """
    score = 8

    if status == "restricted":
        score -= 2
    elif status == "banned":
        score -= 5
    elif status == "unknown":
        score -= 2

    if fda_total > 100_000:
        score -= 2
    elif fda_total > 10_000:
        score -= 1

    if "fragrance" in metadata.get("function", "").lower():
        score -= 1

    score = max(1, min(10, score))

    if score >= 8:
        label = "Easy to Market"
    elif score >= 5:
        label = "Moderate Positioning Risk"
    else:
        label = "Harder to Market"
    return score, label

def generate_insights(ingredient: str, region: str, status: str, fda_total: int, top_reactions: list[str]) -> list[str]:
    metadata = get_metadata(ingredient)
    insights = []

    if status == "banned":
        insights.append(f"{ingredient.title()} appears unsuitable for launch in the selected region because it is marked as banned.")
    elif status == "restricted":
        insights.append(f"{ingredient.title()} may face formulation or concentration limits in {region.upper()}, so compliance review is needed before launch.")
    elif status == "allowed":
        insights.append(f"{ingredient.title()} does not show a starter-database restriction flag in {region.upper()}, but final compliance still depends on product format, concentration, and claims.")
    else:
        insights.append(f"{ingredient.title()} is not yet present in this starter regulatory database, so manual review is recommended.")

    if fda_total > 100_000:
        insights.append("There is a high volume of FDA adverse-event report mentions associated with this term, so this ingredient deserves closer scrutiny.")
    elif fda_total > 10_000:
        insights.append("This ingredient has moderate FDA report visibility, so it should be reviewed in context rather than treated as automatically unsafe.")
    else:
        insights.append("FDA report visibility is relatively low for this search term, though low volume does not prove safety.")

    if top_reactions:
        counts = Counter(top_reactions)
        common = [x[0] for x in counts.most_common(3)]
        insights.append(f"Most common reported reaction terms in the sampled FDA data: {', '.join(common)}.")

    function = metadata.get("function")
    if function:
        insights.append(f"Primary functional role: {function}.")

    claims = metadata.get("claims", [])
    if claims:
        insights.append(f"Likely marketing angles: {', '.join(claims)}.")

    note = metadata.get("notes")
    if note:
        insights.append(note)

    return insights

def build_report_text(ingredient: str, region: str, status: str, risk: int, risk_label: str,
                      market: int, market_label: str, fda_total: int, insights: list[str]) -> str:
    lines = [
        "IngredientIQ Report",
        "===================",
        f"Ingredient: {ingredient.title()}",
        f"Region: {region.upper()}",
        f"Regulatory Status: {STATUS_LABELS.get(status, 'Unknown')}",
        f"Risk Score: {risk}/10 ({risk_label})",
        f"Marketability Score: {market}/10 ({market_label})",
        f"FDA Report Count: {fda_total:,}",
        "",
        "Insights:"
    ]
    for item in insights:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("Disclaimer: This is an intelligence-style screening tool, not a formal regulatory opinion.")
    return "\n".join(lines)

def build_pdf(report_text: str) -> bytes | None:
    if not REPORTLAB_AVAILABLE:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    story = []
    for line in report_text.split("\n"):
        if line.strip() == "":
            story.append(Spacer(1, 10))
        else:
            story.append(Paragraph(line.replace(" ", "&nbsp;"), styles["BodyText"]))
            story.append(Spacer(1, 6))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def reaction_chart(reactions: list[str], ingredient: str):
    if not reactions:
        return None

    counts = Counter(reactions)
    top10 = counts.most_common(10)
    df = pd.DataFrame(top10, columns=["Reaction", "Count"])

    fig = px.bar(
        df,
        x="Count",
        y="Reaction",
        orientation="h",
        title=f"Top Reported Reactions for {ingredient.title()}"
    )
    fig.update_layout(height=420, yaxis=dict(autorange="reversed"))
    return fig

# -----------------------------
# UI
# -----------------------------
st.title("IngredientIQ")
st.caption("Cosmetic ingredient screening for regulatory risk, safety signals, and marketability.")
st.markdown(
    "Use this as an **early-stage intelligence tool** before a deeper ingredient audit."
)

region = st.selectbox(
    "Select market / region",
    options=["eu", "us", "india"],
    format_func=lambda x: {"eu": "EU", "us": "US", "india": "India"}[x]
)

mode = st.radio("Mode", ["Single ingredient", "Compare ingredients"], horizontal=True)

if mode == "Single ingredient":
    ingredient = st.text_input(
        "Enter ingredient name",
        placeholder="e.g. retinol, niacinamide, salicylic acid"
    )
    ingredients = [ingredient] if ingredient else []
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        i1 = st.text_input("Ingredient 1", placeholder="retinol")
    with c2:
        i2 = st.text_input("Ingredient 2", placeholder="niacinamide")
    with c3:
        i3 = st.text_input("Ingredient 3", placeholder="salicylic acid")
    ingredients = [i for i in [i1, i2, i3] if i.strip()]

results_for_compare = []

for ingredient in ingredients:
    if not ingredient.strip():
        continue

    with st.spinner(f"Analyzing {ingredient}..."):
        total = get_fda_total(ingredient)
        reactions = get_top_reactions(ingredient)

    status = get_regulatory_status(ingredient, region)
    metadata = get_metadata(ingredient)

    risk, risk_label = risk_score(status, total)
    market, market_label = marketability_score(status, total, metadata)
    insights = generate_insights(ingredient, region, status, total, reactions)

    results_for_compare.append({
        "Ingredient": ingredient.title(),
        "Region": region.upper(),
        "Regulatory Status": STATUS_LABELS.get(status, "Unknown"),
        "Risk Score": risk,
        "Marketability Score": market,
        "FDA Reports": total
    })

    if mode == "Single ingredient":
        st.markdown(f"## {ingredient.title()}")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Regulatory Status", STATUS_LABELS.get(status, "Unknown"))
        m2.metric("Risk Score", f"{risk}/10", risk_label)
        m3.metric("Marketability", f"{market}/10", market_label)
        m4.metric("FDA Reports", f"{total:,}")

        function = metadata.get("function", "Not available in starter database")
        st.write(f"**Function:** {function}")

        if status == "restricted":
            st.error(f"This ingredient is flagged as restricted in {region.upper()}.")
        elif status == "banned":
            st.error(f"This ingredient is flagged as banned in {region.upper()}.")
        elif status == "allowed":
            st.success(f"This ingredient is marked as allowed in {region.upper()} in the starter database.")
        else:
            st.warning("Regulatory status not found in starter database. Add CosIng-backed lookup next.")

        st.markdown("### Smart Insights")
        for point in insights:
            st.write(f"- {point}")

        fig = reaction_chart(reactions, ingredient)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        report_text = build_report_text(
            ingredient=ingredient,
            region=region,
            status=status,
            risk=risk,
            risk_label=risk_label,
            market=market,
            market_label=market_label,
            fda_total=total,
            insights=insights
        )

        st.markdown("### Download Report")
        st.download_button(
            label="Download text report",
            data=report_text,
            file_name=f"{normalize_ingredient(ingredient)}_ingredientiq_report.txt",
            mime="text/plain"
        )

        pdf_bytes = build_pdf(report_text)
        if pdf_bytes:
            st.download_button(
                label="Download PDF report",
                data=pdf_bytes,
                file_name=f"{normalize_ingredient(ingredient)}_ingredientiq_report.pdf",
                mime="application/pdf"
            )
        else:
            st.info("PDF export requires reportlab. Add `reportlab` to your requirements.txt.")

        st.markdown("---")

if mode == "Compare ingredients" and results_for_compare:
    st.markdown("## Comparison Table")
    df_compare = pd.DataFrame(results_for_compare)
    st.dataframe(df_compare, use_container_width=True)

    fig_compare = px.bar(
        df_compare,
        x="Ingredient",
        y="Risk Score",
        title=f"Risk Score Comparison ({region.upper()})"
    )
    st.plotly_chart(fig_compare, use_container_width=True)

st.caption(
    "Data source for signal layer: openFDA FAERS API. "
    "This app is an intelligence tool, not a medical or formal regulatory decision engine."
)
