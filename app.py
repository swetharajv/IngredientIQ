import streamlit as st
import requests
import plotly.express as px
from collections import Counter

st.set_page_config(page_title="IngredientIQ", page_icon="🧴", layout="centered")

def get_fda_total(ingredient):
    url = "https://api.fda.gov/drug/event.json"
    params = {"search": f"patient.drug.medicinalproduct:{ingredient}", "limit": 1}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code == 200:
        return r.json()["meta"]["results"]["total"]
    return 0

def get_top_reactions(ingredient):
    url = "https://api.fda.gov/drug/event.json"
    params = {"search": f"patient.drug.medicinalproduct:{ingredient}", "limit": 100}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        return []
    reactions = []
    for report in r.json()["results"]:
        for reaction in report["patient"]["reaction"]:
            reactions.append(reaction["reactionmeddrapt"])
    return reactions

def clean_beauty_score(total):
    if total > 1000000:
        return 2, "🔴 Very High Risk"
    elif total > 100000:
        return 4, "🟠 High Report Volume"
    elif total > 10000:
        return 6, "🟡 Moderate Reports"
    else:
        return 8, "🟢 Low Report Volume"

st.title("🧴 IngredientIQ")
st.subheader("Cosmetic Ingredient Safety Checker")
st.write("Type any cosmetic ingredient to see its FDA safety data and Clean Beauty Score.")

ingredient = st.text_input("Enter ingredient name", placeholder="e.g. retinol, niacinamide, salicylic acid")

if ingredient:
    with st.spinner(f"Looking up {ingredient}..."):
        total = get_fda_total(ingredient)
        reactions = get_top_reactions(ingredient)

    if total == 0:
        st.warning("No FDA data found. Try a different spelling.")
    else:
        score, label = clean_beauty_score(total)
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Clean Beauty Score", f"{score} / 10")
            st.write(label)
        with col2:
            st.metric("FDA Adverse Event Reports", f"{total:,}")

        if reactions:
            st.markdown("---")
            st.subheader("Top Reported Reactions")
            counts = Counter(reactions)
            top10 = counts.most_common(10)
            labels = [r[0] for r in top10]
            values = [r[1] for r in top10]
            fig = px.bar(x=values, y=labels, orientation="h",
                        labels={"x": "Reports", "y": "Reaction"},
                        title=f"Top 10 Reactions for {ingredient.title()}",
                        color=values, color_continuous_scale="Reds")
            fig.update_layout(height=400, showlegend=False, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        if score >= 8:
            st.success(f"{ingredient.title()} has low FDA report volume. Generally well tolerated.")
        elif score >= 6:
            st.warning(f"{ingredient.title()} has moderate FDA reports. Use with caution.")
        else:
            st.error(f"{ingredient.title()} has high FDA report volume. Research carefully.")

st.markdown("---")
st.caption("Data: FDA FAERS via openFDA API. For informational purposes only. Built by Clinical Data Intelligence.")